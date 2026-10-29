#!/usr/bin/env python3
"""Matriky SOA Litoměřice (digi.soalitomerice.cz, Sbírka matrik Severočeského kraje) bez prohlížeče.

Použití (z kořene projektu):
  litomerice.py hledat "Obec" [slovo ...] [--stran N]
        -> knihy s obcí (pole „obce“ u knihy je výčet všech obcí v ní). Další slova zúží výsledek (musí být v řádku všechna:
           rok, farnost, druh N/O/Z). N stran po 99 knihách (výchozí 1). Výpis: id | pořadí | popis (druh • obce, roky, NAD, sign.)
  litomerice.py info <id>
        -> záhlaví knihy: původce (farnost, vyznání), roky, signatura, inventární číslo, územní rozsah, počet snímků
  litomerice.py snimek <id> <snímek> <vystup.jpg> [nahled] [x0,y0,x1,y1]
        -> snímek v plném rozlišení; "nahled" = 1/4 rozlišení; výřez v relativních souřadnicích 0–1
  litomerice.py link <id> <snímek>   -> trvalý odkaz na snímek (pole `odkaz` v zaznamy.json)
  litomerice.py svazek <id>          -> zapíše svazek do data/svazky.json (klíč soal_<id>)
<id> je první sloupec výpisu `hledat`. Portál ukazuje záznam podle pořadí ve výsledcích hledání, proto si nástroj u každého id
zapamatuje dotaz (pracovni/litomerice_dotazy.json); jinak ho zadej přepínačem --dotaz "Obec".
POZOR: portál po zhruba 100 rychlých požadavcích na své stránky zablokuje přístup na 30 minut. Každé `snimek`/`info`/`link` je
~4 požadavky; nástroj dělá pauzy, ale nestahuj desítky snímků za sebou (obrázkový server limit nemá). Pomocníkům to napiš do zadání.
"""
import html, http.cookiejar, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://digi.soalitomerice.cz/digitalnibadatelna"
MATRIKY = "35b8e5b8-81b6-4940-9901-35ef06c73709"   # typ záznamu „Matriky“ ve formuláři portálu
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "pracovni", "litomerice_dotazy.json")
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
_op.addheaders = [("User-Agent", "Mozilla/5.0 (rodokmen)")]
_posledni = [0.0]


def get(url, data=None):
    """Požadavek na stránku portálu s pauzou ≥ 0,7 s od předchozího (limit portálu)."""
    err = None
    for attempt in range(3):
        time.sleep(max(0.0, 0.7 - (time.time() - _posledni[0])))
        _posledni[0] = time.time()
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data, doseq=True).encode() if data else None)
            with _op.open(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except OSError as e:
            err = e
            if getattr(e, "code", 0) in (403, 404):
                break
            time.sleep(3 * (attempt + 1))
    raise err


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def hledej(dotaz, strana=1):
    """Spustí hledání mezi matrikami (99 záznamů na stránku) a vrátí HTML stránky výsledků."""
    home = get(BASE + "/")
    f = re.search(r'<form id="searchForm".*?</form>', home, re.S)
    if not f:
        sys.exit("Portál změnil stránku (nenašel jsem hledací formulář). Hledej v prohlížeči.")
    data = re.findall(r'<input type="hidden" name="(_[^"]+)" value="([^"]*)"', f.group(0))
    data += [("patternTxt", dotaz), ("themasCheck", MATRIKY), ("wordOperator", "AND"), ("pageRecords", "99")]
    page = get(BASE + "/vysledekList", data)
    if strana > 1:
        page = get(f"{BASE}/vysledekList?page={strana}&actualRow=&actualUuid=")
    if "ProArch Server Exception" in page[:6000]:
        sys.exit("Portál vrátil chybu serveru (možná dočasná blokace po příliš mnoha požadavcích – počkej 30 minut).")
    return page


def zaznamy(page):
    out = []
    for li in re.findall(r'<li class="minicard[^"]*">(.*?)</li>', page, re.S):
        m = re.search(r'href="/digitalnibadatelna/vysledekDetail/([^"?]+)\?page=(\d+)"', li)
        if m:
            out.append((m.group(1), int(m.group(2)), text(li)))
    return out


def nacti_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def uloz_cache(d):
    if os.path.isdir(os.path.dirname(CACHE)):   # jen v projektu (existuje pracovni/)
        tmp = CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, CACHE)


def hledat(args, stran):
    if not args:
        sys.exit(__doc__)
    cache = nacti_cache()
    videno = 0
    for p in range(1, stran + 1):
        page = hledej(args[0], p)
        rows = zaznamy(page)
        if not rows:
            break
        for id_, poradi, popis in rows:
            cache[id_] = args[0]
            if all(w.lower() in popis.lower() for w in args[1:]):
                print(f"{id_} | {poradi} | {popis[:300]}")
        videno += len(rows)
        if len(rows) < 99:
            break
    uloz_cache(cache)
    celkem = re.search(r'Nalezeno \(Zobrazeno\)</span>\s*<span class="number">([\d\s\xa0]+)</span>', page)
    if videno == 0:
        print("Nic nenalezeno (zkus jiný tvar jména obce nebo bez přívlastku).", file=sys.stderr)
    elif celkem and videno < int(re.sub(r"\D", "", celkem.group(1))):
        print(f"… celkem {celkem.group(1).strip()} knih, načteno {videno}; víc dá --stran, užší výběr další slovo", file=sys.stderr)


def detail(id_, dotaz=None):
    """Najde záznam ve výsledcích hledání (pořadí = parametr page) a vrátí jeho detail a seznam snímků."""
    dotaz = dotaz or nacti_cache().get(id_)
    if not dotaz:
        sys.exit(f"Neznám dotaz, kterým se záznam najde. Spusť nejdřív `litomerice.py hledat \"Obec\"` nebo přidej --dotaz \"Obec\".")
    poradi = next((pr for i, pr, _ in zaznamy(hledej(dotaz)) if i == id_), None)   # jedna stránka (99 knih) stačí
    if not poradi:
        sys.exit("Záznam není v prvních 99 výsledcích dotazu. Použij užší dotaz (--dotaz „Obec farnost“).")
    det = get(f"{BASE}/vysledekDetail/{id_}?page={poradi}")
    img = get(f"{BASE}/vysledekDetail?page={poradi}&actualDetailTab=attachmentsImg")
    ent = re.search(r'entityuuid="([^"]+)"', img)
    sel = re.search(r'class="getScanSelect".*?</select>', img, re.S)
    moznosti = re.findall(r'<option[^>]*value="(\d+)%20([0-9a-f]+)"', sel.group(0)) if sel else []
    return det, (ent.group(1) if ent else None), {int(n): u for n, u in moznosti}


def stranka_snimku(id_, n, dotaz):
    det, ent, snimky = detail(id_, dotaz)
    if not snimky or not ent:
        sys.exit("Kniha nemá online snímky (nebo portál změnil stránku).")
    if n not in snimky:
        sys.exit(f"Snímek musí být číslo 1–{max(snimky)}.")
    url = f"{BASE}/showZoomifySeparate?imageNumberSeparate={n}&myEntityUuid={ent}&myImageUuid={snimky[n]}"
    z = get(url)
    cesta = re.search(r'https://images\.soalitomerice\.cz/[^"\' <>]+?\.(?:jpg|JPG)', z)
    if not cesta:
        sys.exit("Cestu k obrázku se nepodařilo najít (portál změnil stránku nebo je omezený). Stáhni snímek v prohlížeči.")
    return cesta.group(0), url


def info(id_, dotaz):
    det, ent, snimky = detail(id_, dotaz)
    t = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", det, flags=re.S))
    i = t.find("Souhrnná identifikace")
    print((t[i:i + 2500] if i >= 0 else t[:2500]).strip())
    print(f"Snímků online: {max(snimky) if snimky else 0}")


def snimek(id_, n, out, nahled, orez, dotaz):
    cesta, url = stranka_snimku(id_, n, dotaz)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cil = out if not orez else os.path.join(tempfile.mkdtemp(prefix="soal_"), "cely.jpg")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(HERE, "soal_zoomify.py"), cesta, "2" if nahled else "0", cil],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr.strip() or r.stdout.strip())
    if orez:
        magick = subprocess.run([sys.executable, "-I", "-c", "import sys;sys.path.insert(0,sys.argv[1]);import soal_zoomify as z;print(z.magick())",
                                 HERE], capture_output=True, text=True).stdout.strip()
        w, h = map(int, subprocess.run([magick, cil + "[0]", "-format", "%w %h", "info:"], capture_output=True, text=True).stdout.split())
        x0, y0, x1, y1 = orez
        subprocess.run([magick, cil, "-crop", f"{int((x1 - x0) * w)}x{int((y1 - y0) * h)}+{int(x0 * w)}+{int(y0 * h)}", "+repage",
                        "-quality", "88", out], check=True)
        os.remove(cil)
        os.rmdir(os.path.dirname(cil))
    print(out, "odkaz:", url)


def svazek(id_, dotaz):
    det, ent, snimky = detail(id_, dotaz)
    t = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", det, flags=re.S))

    def pole(a, b):
        m = re.search(r"\d+\|\s*" + re.escape(a) + r"\s*:?\s*(.*?)\s*(?=\d+\|\s*" + re.escape(b) + ")", t)
        return m.group(1).strip() if m else ""
    puvodce = (re.search(r"Původce matriky:\s*(.*?)\s*(?=\d+\|)", t) or [0, ""])[1].split(" (")[0]
    obsah = pole("Popis obsahu", "Indexy") or (re.search(r"Popis obsahu\s*(.*?)\s*(?=\d+\||Indexy)", t) or [0, ""])[1]
    sign = (re.search(r"Signatura\s+(\S+)", t) or [0, ""])[1]
    nazev = f"{puvodce[:160]}, {obsah[:120]}" + (f", sign. {sign}" if sign else "")
    path = os.path.join(ROOT, "data", "svazky.json")
    d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    d[f"soal_{id_[:12]}"] = {"archiv": "SOA Litoměřice – Sbírka matrik Severočeského kraje", "portal": "digi.soalitomerice.cz",
                             "svazek": nazev.strip(", "), "popis": "", "url": f"{BASE}/entityDetail/{id_}"}
    tmp = path + ".tmp"   # zápis přes dočasný soubor: přerušení nesmí zkrátit svazky.json
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    print(f"soal_{id_[:12]} -> {nazev}")


def okno(s):
    p = [float(v) for v in s.split(",")]
    if len(p) != 4 or not all(0 <= v <= 1 for v in p) or p[0] >= p[2] or p[1] >= p[3]:
        sys.exit("Výřez: x0,y0,x1,y1 v rozsahu 0–1 (zleva doprava, shora dolů).")
    return p


def cislo(s):
    if not (s.isascii() and s.isdigit()):
        sys.exit("Snímek musí být číslo.")
    return int(s)


if __name__ == "__main__":
    a = sys.argv[1:]
    stran, dotaz = 1, None
    for volba in ("--stran", "--dotaz"):
        if volba in a:
            i = a.index(volba)
            if i + 1 >= len(a) or (volba == "--stran" and not (a[i + 1].isdigit() and int(a[i + 1]) >= 1)):
                sys.exit(f"{volba} chce hodnotu (--stran kladné číslo, --dotaz text).")
            if volba == "--stran":
                stran = int(a[i + 1])
            else:
                dotaz = a[i + 1]
            del a[i:i + 2]
    if not a:
        sys.exit(__doc__)
    if a[0] == "hledat":
        hledat(a[1:], stran)
    elif a[0] == "info" and len(a) == 2:
        info(a[1], dotaz)
    elif a[0] == "snimek" and len(a) >= 4:
        rest = a[4:]
        snimek(a[1], cislo(a[2]), a[3], "nahled" in rest, next((okno(r) for r in rest if "," in r), None), dotaz)
    elif a[0] == "link" and len(a) == 3:
        print(stranka_snimku(a[1], cislo(a[2]), dotaz)[1])
    elif a[0] == "svazek" and len(a) == 2:
        svazek(a[1], dotaz)
    else:
        sys.exit(__doc__)
