#!/usr/bin/env python3
"""Kontrola jednotnosti sestaveného webu (Fáze B, ADR 0004): jednotná značka rodu a žádný procesní text.

Použití: python3 -I tools/kontrola_webu.py <složka se stránkami> [--site web/src/data/site.json]

Chyby (návratový kód 1):
  - holý název rodu v textu stránky (má být značka; spusť znackuj_rody.py),
  - značka rodu v jiné barvě, než má rod v datech, nebo značka neznámého rodu,
  - rody v nadpisech h2/h3 jedné stránky nejdou podle čísla zakladatele,
  - procesní údaje v textu stránky: čísla úkolů, jména agentů a modelů, cesty do pracovni/, „čtyři oči“, „ověřeno na snímku“.
  - vztah nebo účast v zápisu jen z jedné strany: rodič bez dítěte na své stránce (a naopak), partner bez partnera, zápis, který
    není na stránce svého účastníka, nebo účastník, který není na stránce zápisu. Očekávání se bere z dat projektu (data/osoby.py,
    data/zaznamy.json včetně pole ucastnici), ne z exportu. Jen se site.json celého rodokmenu (verze „vse“ nebo jediný web);
    --data SLOŽKA = jiná složka dat, --bez-vazeb = tuto kontrolu vynechat.
Upozornění (kód 0): skloněný tvar názvu rodu v textu (např. „Novákových“), který se nenahrazuje; vztah z dat, který web neuvádí ani
z jedné strany (skrytá osoba).
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import rody_html as rh  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCES = [
    ("číslo úkolu", re.compile(r"\b(?:U-\d{3,}|N\d{1,2}[a-z])\b")),
    ("jméno agenta nebo modelu", re.compile(r"\b(?:pomocník\w*|subagent\w*|sonnet\w*|haiku\w*|claude)\b", re.I)),
    ("údaj o procesu", re.compile(r"čtyři oči|ověřeno na snímku|čteno na výřezu", re.I)),
    ("cesta do pracovní složky", re.compile(r"pracovni[/\\]", re.I)),
]
ZNACKA = re.compile(r'<span class="rod-znak"><span class="dot" style="background:\s*([^";]+)"></span><a href="/rod/([^/"]+)/?">')
NADPIS = re.compile(r"<h([23])\b[^>]*>(.*?)</h\1>", re.S | re.I)


KONTEJNER = re.compile(r'<[a-z]+\b[^>]*\bclass="(?:[^"]*\s)?rod-box(?:\s[^"]*)?"[^>]*>', re.I)   # přesně třída rod-box, ne rod-box-hlava
CAST_HLEDAME = re.compile(r'data-hledame="([a-z]+)"')
DATA_ROD = re.compile(r'\bdata-rod(?:="([^"]*)")?(?=[\s/>])')


def kontroluj_kontejnery(html, jmeno, podle_slugu, chyby):
    """Kontejner vázaný na rod (class rod-box, data-rod=<slug>) má barvu rodu (--c), obecný (data-rod="") žádnou; na stránce Co hledáme
    má každý rod v otázkách pro rodinu a v otevřených otázkách jen jeden kontejner (rozhodnutí uživatele 16. 11. 2026)."""
    for m in KONTEJNER.finditer(html):
        tag = m.group(0)
        rod = DATA_ROD.search(tag)
        barva = re.search(r"--c:\s*([^;\"]+)", tag)
        if not rod:
            chyby.append(f"{jmeno}: kontejner rodu bez data-rod (obecný má data-rod=\"\")")
            continue
        if rod.group(1) in (None, "", "obecne"):   # obecný: data-rod="obecne" (komponenta), "" (Markdown) nebo holý atribut
            if barva:
                chyby.append(f"{jmeno}: obecný kontejner má barvu rodu {barva.group(1).strip()}")
            continue
        if podle_slugu is None:
            continue
        r = podle_slugu.get(rod.group(1))
        if not r:
            chyby.append(f"{jmeno}: kontejner neznámého rodu {rod.group(1)}")
        elif not barva:
            chyby.append(f"{jmeno}: kontejner rodu {r['name']} je bez barvy rodu")
        elif barva.group(1).strip().lower() != r["color"].lower():
            chyby.append(f"{jmeno}: barva kontejneru rodu {r['name']} je {barva.group(1).strip()}, rod má {r['color']}")
    casti = list(CAST_HLEDAME.finditer(html))
    for i, c in enumerate(casti):
        if c.group(1) not in ("rodina", "otevrene"):
            continue
        usek = html[c.end():casti[i + 1].start() if i + 1 < len(casti) else len(html)]
        rody = [DATA_ROD.search(t.group(0)) for t in KONTEJNER.finditer(usek)]
        rody = ["" if x.group(1) in (None, "obecne") else x.group(1) for x in rody if x]
        for r in sorted({x for x in rody if rody.count(x) > 1}):
            chyby.append(f"{jmeno}: v části {c.group(1)} má rod {r or 'Obecné'} víc kontejnerů (má být jeden)")


def kontroluj(cesta, rody, rx, podle_slugu, chyby, upozorneni):
    html = rh.cti(cesta)
    jmeno = os.path.relpath(cesta)
    if rx:
        holé = []
        rh.projdi(html, lambda t: holé.extend(m.group(0) for m in rx.finditer(t)) or t)
        for n in sorted(set(holé)):
            chyby.append(f"{jmeno}: holý název rodu „{n}“ (má být značka; znackuj_rody.py)")
    for m in (ZNACKA.finditer(html) if rody else ()):   # bez dat rodů (--site chybí) se značky nekontrolují
        r = podle_slugu.get(m.group(2))
        if not r:
            chyby.append(f"{jmeno}: značka neznámého rodu /rod/{m.group(2)}/")
        elif r["color"].lower() != m.group(1).strip().lower():
            chyby.append(f"{jmeno}: barva značky rodu {r['name']} je {m.group(1).strip()}, rod má {r['color']}")
    poradi = []
    for m in (NADPIS.finditer(html) if rody else ()):
        z = ZNACKA.search(m.group(2))
        if z and podle_slugu.get(z.group(2)) and podle_slugu[z.group(2)]["k"] is not None:
            poradi.append((podle_slugu[z.group(2)]["k"], podle_slugu[z.group(2)]["name"]))
    for (k1, n1), (k2, n2) in zip(poradi, poradi[1:]):
        if k2 < k1:
            chyby.append(f"{jmeno}: pořadí rodů v nadpisech: {n2} (č. {k2}) je za {n1} (č. {k1})")
            break
    kontroluj_kontejnery(html, jmeno, podle_slugu if rody else None, chyby)
    texty = []
    rh.projdi(html, lambda t: texty.append(t) or t, skip=rh.SKIP_JEN_KOD, preskoc_znacku=False)
    text = " ".join(texty)
    for nazev, rxp in PROCES:
        for m in rxp.finditer(text):
            chyby.append(f"{jmeno}: procesní údaj na stránce ({nazev}): {m.group(0)}")
            break
    for r in rody:
        if len(r["name"]) < 6:
            continue
        kmen = r["name"][:-2]
        videno = set()
        rh.projdi(html, lambda t: videno.update(x for x in re.findall(r"(?<!\w)" + re.escape(kmen) + r"\w+", t)
                                                 if x != r["name"]) or t)
        for x in sorted(videno):
            upozorneni.append(f"{jmeno}: skloněný tvar „{x}“ (název rodu {r['name']}) se nenahrazuje")


ODKAZ_OSOBA = re.compile(r'href="/osoba/([^/"#?]+)/?["#?]')
ODKAZ_ZAPIS = re.compile(r'href="/zdroj/([^/"#?]+)/?["#?]')


def vazby_z_dat(data):
    """Vztahy přímo z dat projektu, nezávisle na exportu: (rodič, dítě), dvojice partnerů a kdo patří ke kterému zápisu.
    Osoba je „k<číslo>“ (přímý předek) nebo „o:<zkratka>“ (RODINA) – stejné označení nese export v poli tree."""
    import json
    import ucastnici
    ns = {}
    with open(os.path.join(data, "osoby.py"), encoding="utf-8-sig") as f:
        exec(f.read(), ns)
    try:
        with open(os.path.join(data, "zaznamy.json"), encoding="utf-8-sig") as f:
            zaz = json.load(f)
    except OSError:
        zaz = []
    ucastnici.dopln_r(ns, zaz)
    P, R, SAME = ns.get("P") or {}, ns.get("RODINA") or {}, ns.get("SAME") or {}

    def ref(v):
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, int):
            v = SAME.get(v, v)
            return f"k{v}" if v in P else None
        return f"o:{v}" if v in R else None

    rodic_dite, partneri, zapisy = set(), set(), {}
    for k in P:
        if k in SAME:
            continue
        for par in (2 * k, 2 * k + 1):
            if ref(par):
                rodic_dite.add((ref(par), f"k{k}"))
        if ref(2 * k) and ref(2 * k + 1):
            partneri.add(frozenset((ref(2 * k), ref(2 * k + 1))))
    for oid, o in R.items():
        for pole in ("otec", "matka"):
            if ref(o.get(pole)):
                rodic_dite.add((ref(o[pole]), f"o:{oid}"))
        for v in o.get("partner") or []:
            if ref(v):
                partneri.add(frozenset((ref(v), f"o:{oid}")))
    for pr in ns.get("PARTNERI") or []:
        a, b = ref(pr.get("a")), ref(pr.get("b"))
        if a and b and a != b:
            partneri.add(frozenset((a, b)))
    for k, o in list(P.items()) + list(R.items()):
        r = ref(k)
        for klic in (o or {}).get("r", []) if r else []:
            zapisy.setdefault(klic, set()).add(r)
    return rodic_dite, partneri, zapisy


def kontroluj_vazby(slozka, site_data, data, chyby, upozorneni):
    """Úplnost vztahů na sestaveném webu (analyza/navrh-optimalizace.md, oddíl 7): co je v datech vztahem dvou osob nebo účastí v zápisu,
    musí být vidět na stránkách **obou** stran. Očekávání se bere z dat projektu, ne z exportu; export slouží jen jako adresář stránek
    a jako maska soukromí (vztah, který export neuvádí ani z jedné strany, je jen upozornění: skrytá osoba)."""
    lide = site_data.get("people") or {}
    lide = list(lide.values()) if isinstance(lide, dict) else lide
    podle = {p.get("tree"): p for p in lide if isinstance(p, dict) and p.get("tree") and p.get("slug")}
    cache = {}

    def html(*cesta):
        p = os.path.join(slozka, *cesta, "index.html")
        if p not in cache:
            cache[p] = rh.cti(p) if os.path.isfile(p) else None
        return cache[p]

    def odkazy(p):
        h = html("osoba", p["slug"])
        return None if h is None else set(ODKAZ_OSOBA.findall(h))

    def sl(seznam):
        return {x.get("slug") if isinstance(x, dict) else x for x in seznam or []}

    rodic_dite, partneri, zapisy = vazby_z_dat(data)
    n = 0
    for a, b in sorted(rodic_dite):
        pa, pb = podle.get(a), podle.get(b)
        if not pa or not pb or odkazy(pa) is None or odkazy(pb) is None:
            continue
        v_exportu = (pb["slug"] in sl(pa.get("kids")) | sl(pa.get("children"))
                     or pa["slug"] in sl(pb.get("parents")) | {pb.get("father"), pb.get("mother")})
        if not v_exportu:
            upozorneni.append(f"vztah rodič–dítě {pa['name']} → {pb['name']} je v datech, web ho neuvádí ani z jedné strany (soukromí?)")
            continue
        n += 1
        if pb["slug"] not in odkazy(pa):
            chyby.append(f"osoba/{pa['slug']}: chybí dítě {pb['name']} (stránka {pb['slug']} rodiče uvádí)")
        if pa["slug"] not in odkazy(pb):
            chyby.append(f"osoba/{pb['slug']}: chybí rodič {pa['name']} (stránka {pa['slug']} dítě uvádí)")
    for dvojice in sorted(partneri, key=sorted):
        a, b = sorted(dvojice)
        pa, pb = podle.get(a), podle.get(b)
        if not pa or not pb or odkazy(pa) is None or odkazy(pb) is None:
            continue
        v_exportu = (pb["slug"] in sl(pa.get("partners")) | {pa.get("spouse")}
                     or pa["slug"] in sl(pb.get("partners")) | {pb.get("spouse")})
        if not v_exportu:
            upozorneni.append(f"partnerství {pa['name']} × {pb['name']} je v datech, web ho neuvádí ani z jedné strany (soukromí?)")
            continue
        n += 1
        for x, y in ((pa, pb), (pb, pa)):
            if y["slug"] not in odkazy(x):
                chyby.append(f"osoba/{x['slug']}: chybí partner {y['name']} (stránka {y['slug']} partnerství uvádí)")
    for klic, osoby in sorted(zapisy.items()):
        hz = html("zdroj", klic)
        if hz is None:
            continue   # zápis na webu není (skrytý, nebo jen v datech)
        u_zapisu = set(ODKAZ_OSOBA.findall(hz))
        for r in sorted(osoby):
            p = podle.get(r)
            ho = html("osoba", p["slug"]) if p else None
            if ho is None or klic not in (p.get("records") or []):
                continue   # osoba stránku nemá, nebo její zápisy přístup nevidí
            n += 1
            if klic not in set(ODKAZ_ZAPIS.findall(ho)):
                chyby.append(f"osoba/{p['slug']}: chybí zápis {klic}, ve kterém osoba vystupuje")
            if p["slug"] not in u_zapisu:
                chyby.append(f"zdroj/{klic}: chybí osoba {p['name']}, která v zápisu vystupuje")
    return n


def kontroluj_nepotvrzene(slozka, data, chyby):
    """Na stránce Co hledáme nesmí být text veřejné otázky, kterou uživatel nepotvrdil (ADR 0003, 0009). Očekávání z dat projektu."""
    import json
    p = os.path.join(data, "verejne_otazky.json")
    try:
        with open(p, encoding="utf-8-sig") as f:
            zaznamy = json.load(f).get("otazky") or []
    except (OSError, ValueError, AttributeError):
        return
    norm = lambda s: " ".join(str(s).split()).casefold()
    tajne = [(z.get("id"), norm(z.get("otazka") or z.get("co_hledat") or "")) for z in zaznamy
             if isinstance(z, dict) and "potvrzeno" not in z]
    tajne = [(i, t) for i, t in tajne if len(t) >= 12]
    if not tajne:
        return
    for cesta in rh.html_soubory(slozka):
        if os.path.basename(os.path.dirname(cesta)) != "hledame":
            continue
        texty = []
        rh.projdi(rh.cti(cesta), lambda t: texty.append(t) or t, skip=rh.SKIP_JEN_KOD, preskoc_znacku=False)
        text = norm(" ".join(texty))
        for i, t in tajne:
            if t in text:
                chyby.append(f"{os.path.relpath(cesta)}: nepotvrzená veřejná otázka {i} je na webu (otazky.py potvrd)")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    slozka = args[0]
    site = args[args.index("--site") + 1] if "--site" in args else os.path.join(ROOT, "web", "src", "data", "site.json")
    if not os.path.isdir(slozka):
        sys.exit(f"Složka {slozka} neexistuje.")
    rody = rh.nacti_rody(site) if os.path.exists(site) else []
    rx = rh.regex_nazvu(rody)
    podle_slugu = {r["slug"]: r for r in rody}
    chyby, upozorneni, n = [], [], 0
    for cesta in rh.html_soubory(slozka):
        n += 1
        kontroluj(cesta, rody, rx, podle_slugu, chyby, upozorneni)
    data_dir = args[args.index("--data") + 1] if "--data" in args else os.path.join(ROOT, "data")
    kontroluj_nepotvrzene(slozka, data_dir, chyby)
    vazeb = None
    if os.path.exists(site) and "--bez-vazeb" not in args:
        import json
        try:
            with open(site, encoding="utf-8") as f:
                site_data = json.load(f)
            data = args[args.index("--data") + 1] if "--data" in args else os.path.join(ROOT, "data")
            if site_data.get("people") and os.path.isfile(os.path.join(data, "osoby.py")):
                vazeb = kontroluj_vazby(slozka, site_data, data, chyby, upozorneni)
        except (OSError, ValueError) as e:
            upozorneni.append(f"vazby se nekontrolovaly: {e}")
    for u in upozorneni[:30]:
        print("upozornění:", u)
    for ch in chyby:
        print("CHYBA:", ch)
    print(f"kontrola webu: {n} stránek, {len(chyby)} chyb, {len(upozorneni)} upozornění"
          + (f", {vazeb} vztahů a účastí v zápisech ověřeno z obou stran" if vazeb is not None else ""))
    sys.exit(1 if chyby else 0)


if __name__ == "__main__":
    main()
