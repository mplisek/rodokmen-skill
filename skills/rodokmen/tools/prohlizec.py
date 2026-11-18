#!/usr/bin/env python3
"""Vlastní prohlížeč pro čtení portálů, kam skript nesmí (SOA Třeboň, eBadatelna, ZA Opava, MZA – viz ZAKAZ v tools/slusne.py).

Čtení v prohlížeči tempem člověka je u těchto portálů povolené (reference/portaly.md, SKILL.md → Šetrně k archivům). Prohlížeč se nespouští ručně
(Start-Process, vlastní skript s Playwrightem), ale tímto nástrojem. Pravidla jsou zabudovaná v něm, ne v dobré vůli čtenáře:

  - Edge se spustí jako VLASTNÍ instance (vlastní --user-data-dir v pracovni/, --remote-debugging-port, bez adresy portálu), takže se
    nepřipojí k běžícímu prohlížeči uživatele (ten by volbu port ignoroval);
  - jen portály ze ZAKAZ (ostatní čti nástroji přes brzdu, mezipaměť a mapu knihy), jeden archiv na jednu relaci;
  - mezi akcemi pauza aspoň 5 s (10 s při --listovani), nejvýš 120 otevření stránky za hodinu (žádné smyčky přes celé svazky);
  - HTTP 403/429/503, CAPTCHA nebo „příliš mnoho požadavků“ = stop: zapíše se do stavu brzdy (slusne.py) a nástroj další akce na ten archiv odmítne;
  - snímek obrazovky jen do pracovni/.

Použití (z kořene projektu):
  prohlizec.py stav                         Playwright, Edge, běžící relace (uživatel nic nespouští ani nenastavuje)
  prohlizec.py start [--port 9222]          spustí vlastní Edge (about:blank); jinak nic
  prohlizec.py otevri <url> [--listovani]   přejde na adresu portálu (pauza, kontrola stopu)
  prohlizec.py klik <selektor> [--listovani]       klik na prvek stránky
  prohlizec.py pis <selektor> <text>               vyplní pole (např. hledání)
  prohlizec.py text [<selektor>]            vypíše text stránky nebo prvku (bez pauzy, jen čtení)
  prohlizec.py snimek <pracovni/soubor.png>        snímek obrazovky do pracovni/
  prohlizec.py stop                         ukončí vlastní Edge a relaci

Playwright: `python -m pip install --user playwright` (prohlížeč se nestahuje, použije se Edge). Nástroj běží bez -I, aby ho viděl i z
user-site. Návratové kódy: 0 v pořádku, 2 chyba použití nebo prostředí, 4 stop (archiv nás zpomaluje), 5 přihlášení nebo ověření člověkem.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slusne  # noqa: E402 – stav brzdy (stopky) a seznam portálů, kam skript nesmí; prohlížeč s ní sdílí stopky

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRACOVNI = os.path.join(ROOT, "pracovni")
STAV = os.path.join(PRACOVNI, ".prohlizec.json")
PROFIL = os.path.join(PRACOVNI, "prohlizec_profil")
PAUZA, PAUZA_LISTOVANI, MAX_OTEVRENI_ZA_HODINU = 5.0, 10.0, 120
STOP_TEXT = re.compile(r"captcha|nejste robot|are you a robot|unusual traffic|too many requests|příliš mnoho požadavků|přístup byl zablokován|"
                       r"access denied|byl[ai]? jste zablokován", re.I)
PRIHLASENI = re.compile(r"přihlaste se|přihlášení je vyžadováno|please log ?in|sign in to continue", re.I)


class Stop(Exception):
    """Další akce na archiv se odmítá (kód 4) nebo je potřeba člověk (kód 5)."""
    def __init__(self, zprava, kod=4):
        super().__init__(zprava)
        self.kod = kod


# ---------- čistá pravidla (testovatelná bez prohlížeče) ----------
def host_z_url(url):
    return (urlsplit(url).hostname or "").lower().rstrip(".")


def zakazany_portal(host):
    """Portál ze ZAKAZ (skript nesmí) – jen tam je prohlížeč určený. Vrací suffix, jinak None."""
    return next((s for s in slusne.ZAKAZ if host == s or host.endswith("." + s)), None)


def pauza(minule, ted, listovani=False):
    """Kolik sekund ještě čekat od poslední akce (0 = hned)."""
    potreba = PAUZA_LISTOVANI if listovani else PAUZA
    return max(0.0, potreba - (ted - minule)) if minule else 0.0


def moc_otevreni(otevreni, ted):
    return len([t for t in otevreni if t > ted - 3600]) >= MAX_OTEVRENI_ZA_HODINU


def duvod_stopu(status, text):
    """Důvod, proč archiv zastavit (HTTP 403/429/503, CAPTCHA, „příliš mnoho požadavků“), jinak None."""
    if status in (403, 429, 503):
        return f"HTTP {status}"
    if text and STOP_TEXT.search(text):
        return "stránka žádá ověření člověkem nebo hlásí zablokování"
    return None


def cesta_snimku(soubor, koren=None):
    """Absolutní cesta snímku obrazovky; jen uvnitř pracovni/ projektu, jinak ValueError."""
    koren = os.path.abspath(koren or ROOT)
    p = os.path.abspath(os.path.join(koren, soubor))
    pracovni = os.path.join(koren, "pracovni") + os.sep
    if not p.startswith(pracovni) or not p.lower().endswith((".png", ".jpg", ".jpeg")):
        raise ValueError("snímek obrazovky jen do pracovni/ (.png nebo .jpg)")
    return p


def stav_nacti(cesta=None):
    try:
        with open(cesta or STAV, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def stav_uloz(st, cesta=None):
    cesta = cesta or STAV
    os.makedirs(os.path.dirname(cesta), exist_ok=True)
    with open(cesta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def web_zastaven(host):
    """Je web zastavený brzdou (po odmítnutí z nástrojů nebo z prohlížeče)? Vrací text, jinak None."""
    skupina, _ = slusne._skupina(host)
    if not skupina:
        return None
    st = slusne._nacti(slusne._cesta(skupina))
    return f"{skupina} je zastavený brzdou do {slusne._cas(st['stop'])} ({st.get('duvod', '')})" if st.get("stop", 0) > time.time() else None


def pred_akci(st, host, ted, listovani=False, otevreni=False):
    """Zkontroluje pravidla před akcí; vrací počet sekund, které je třeba počkat. Stop -> Stop."""
    if not zakazany_portal(host):
        raise Stop(f"{host} smí skript: čti ho nástroji přes brzdu, mezipaměť a mapu knihy (tools/), prohlížeč je jen pro portály ze ZAKAZ", 2)
    if st.get("host") and st["host"] != host:
        raise Stop(f"relace je vázaná na archiv {st['host']} (jeden prohlížeč na jeden archiv): nejdřív `prohlizec.py stop`", 2)
    zast = web_zastaven(host)
    if zast:
        raise Stop(f"{zast}. Nezkoušej to znovu dřív, nic neobcházej, řekni uživateli, co se stalo.")
    if otevreni and moc_otevreni(st.get("otevreni", []), ted):
        raise Stop(f"{MAX_OTEVRENI_ZA_HODINU} otevření stránky za hodinu je strop: žádné smyčky přes celé svazky; počkej, nebo úkol vrať uživateli.")
    return pauza(st.get("posledni", 0), ted, listovani)


def po_akci(st, host, ted, otevreni=False):
    st["host"] = host
    st["posledni"] = ted
    if otevreni:
        st["otevreni"] = [t for t in st.get("otevreni", []) if t > ted - 3600] + [ted]
    return st


def vyhodnot_stranku(host, status, text):
    """Po načtení stránky: stop (zapíše se do brzdy) nebo přihlášení (kód 5); jinak nic."""
    duvod = duvod_stopu(status, text)
    if duvod:
        try:
            slusne.zastav(host, f"prohlížeč: {duvod}")
        except SystemExit:
            pass
        raise Stop(f"{host}: {duvod}. Archiv nás zpomaluje – další akce se na něj odmítají. Řekni uživateli, co se stalo; nic neobcházej.")
    if text and PRIHLASENI.search(text):
        raise Stop(f"{host}: stránka žádá přihlášení – vrať úkol uživateli.", 5)


def akce(co, args, page, st, host, ted, spi=time.sleep):
    """Provede jednu akci nad stránkou (Playwright `page` nebo náhrada) podle pravidel; vrací výstup. `spi` = čekání (v testech náhrada)."""
    cti = co == "text"
    if not cti:
        cekej = pred_akci(st, host, ted, listovani=bool(args.get("listovani")), otevreni=(co == "otevri"))
        if cekej:
            spi(cekej)
            ted = time.time() if spi is time.sleep else ted + cekej
    out = ""
    status = None
    if co == "otevri":
        odpoved = page.goto(args["url"], wait_until="domcontentloaded", timeout=60000)
        status = getattr(odpoved, "status", None)
    elif co == "klik":
        page.click(args["selektor"], timeout=30000)
    elif co == "pis":
        page.fill(args["selektor"], args["text"], timeout=30000)
    elif co == "text":
        out = page.inner_text(args.get("selektor") or "body", timeout=30000)
    elif co == "snimek":
        page.screenshot(path=cesta_snimku(args["soubor"]), full_page=False)
        out = f"uloženo: {args['soubor']}"
    else:
        raise ValueError(f"neznámá akce {co}")
    if not cti:
        vyhodnot_stranku(host, status, page.inner_text("body", timeout=30000)[:4000] if co != "snimek" else "")
        po_akci(st, host, ted, otevreni=(co == "otevri"))
    return out


# ---------- prostředí: Playwright, Edge, vlastní instance ----------
def playwright_je():
    """Vidí Playwright běžný Python (s user-site)? Nástroj běží bez -I; kontrola v podprocesu bez -I."""
    return subprocess.run([sys.executable, "-c", "import playwright"], capture_output=True).returncode == 0


def najdi_edge():
    kandidati = [os.environ.get("RODOKMEN_EDGE"), shutil.which("msedge"), shutil.which("microsoft-edge"),
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", shutil.which("google-chrome"), shutil.which("chromium")]
    return next((k for k in kandidati if k and os.path.isfile(k)), None)


def port_zije(port):
    import urllib.request   # jen 127.0.0.1: vlastní prohlížeč, ne web archivu
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def start(port=9222):
    st = stav_nacti()
    if st.get("port") and port_zije(st["port"]):
        return f"už běží (port {st['port']})"
    edge = najdi_edge()
    if not edge:
        raise Stop("Edge ani Chrome nenalezen (nastav RODOKMEN_EDGE na cestu k programu)", 2)
    os.makedirs(PROFIL, exist_ok=True)
    args = [edge, f"--remote-debugging-port={port}", f"--user-data-dir={PROFIL}", "--no-first-run", "--no-default-browser-check", "about:blank"]
    kw = {"creationflags": 0x00000008 | 0x00000200} if os.name == "nt" else {"start_new_session": True}   # oddělený proces
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    for _ in range(40):
        if port_zije(port):
            stav_uloz({"pid": p.pid, "port": port, "profil": PROFIL, "start": time.strftime("%Y-%m-%d %H:%M:%S")})
            return f"vlastní Edge běží (port {port}, profil {os.path.relpath(PROFIL, ROOT)})"
        time.sleep(0.5)
    raise Stop(f"Edge se nepřipojil na port {port} do 20 s (zkus jiný --port)", 2)


def stop():
    st = stav_nacti()
    if not st.get("pid"):
        return "žádná vlastní relace"
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(st["pid"]), "/T", "/F"], capture_output=True)
        else:
            os.kill(int(st["pid"]), 15)
    except OSError:
        pass
    try:
        os.remove(STAV)
    except OSError:
        pass
    return "vlastní Edge ukončen"


def prehled():
    st = stav_nacti()
    zije = bool(st.get("port")) and port_zije(st["port"])
    return {"playwright": playwright_je(), "edge": najdi_edge(), "relace": zije, "port": st.get("port") if zije else None,
            "archiv": st.get("host") if zije else None,
            "napoveda": None if playwright_je() else "python -m pip install --user playwright (uživatel nic nespouští, nainstaluj to ty)"}


def pripoj(port):
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    br = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    ctx = br.contexts[0] if br.contexts else br.new_context()
    return pw, (ctx.pages[0] if ctx.pages else ctx.new_page())


def main(argv=None):
    a = sys.argv[1:] if argv is None else list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    co, rest = a[0], a[1:]
    listovani = "--listovani" in rest
    rest = [x for x in rest if x != "--listovani"]
    try:
        if co == "stav":
            print(json.dumps(prehled(), ensure_ascii=False, indent=1))
            return 0
        if co == "start":
            port = int(rest[rest.index("--port") + 1]) if "--port" in rest else 9222
            print(start(port))
            return 0
        if co == "stop":
            print(stop())
            return 0
        if co not in ("otevri", "klik", "pis", "text", "snimek"):
            print(f"neznámý příkaz {co}", file=sys.stderr)
            return 2
        st = stav_nacti()
        if not st.get("port") or not port_zije(st["port"]):
            print("vlastní prohlížeč neběží: prohlizec.py start", file=sys.stderr)
            return 2
        if not playwright_je():
            print("Playwright chybí: python -m pip install --user playwright", file=sys.stderr)
            return 2
        args = {"listovani": listovani}
        if co == "otevri":
            args["url"], host = rest[0], host_z_url(rest[0])
        else:
            host = st.get("host") or ""
            if co == "klik":
                args["selektor"] = rest[0]
            elif co == "pis":
                args["selektor"], args["text"] = rest[0], rest[1]
            elif co == "text":
                args["selektor"] = rest[0] if rest else None
            elif co == "snimek":
                args["soubor"] = rest[0]
        if co != "otevri" and not host:
            print("relace ještě nemá archiv: nejdřív prohlizec.py otevri <url>", file=sys.stderr)
            return 2
        pw, page = pripoj(st["port"])
        try:
            print(akce(co, args, page, st, host if co != "text" else (host or ""), time.time()))
        finally:
            stav_uloz(st)
            pw.stop()
        return 0
    except Stop as e:
        print(f"prohlizec: {e}", file=sys.stderr)
        return e.kod
    except (IndexError, ValueError) as e:
        print(f"chyba použití: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
