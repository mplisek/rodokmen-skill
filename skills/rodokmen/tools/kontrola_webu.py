#!/usr/bin/env python3
"""Kontrola jednotnosti sestaveného webu (Fáze B, ADR 0004): jednotná značka rodu a žádný procesní text.

Použití: python3 -I tools/kontrola_webu.py <složka se stránkami> [--site web/src/data/site.json]

Chyby (návratový kód 1):
  - holý název rodu v textu stránky (má být značka; spusť znackuj_rody.py),
  - značka rodu v jiné barvě, než má rod v datech, nebo značka neznámého rodu,
  - rody v nadpisech h2/h3 jedné stránky nejdou podle čísla zakladatele,
  - procesní údaje v textu stránky: čísla úkolů, jména agentů a modelů, cesty do pracovni/, „čtyři oči“, „ověřeno na snímku“.
Upozornění (kód 0): skloněný tvar názvu rodu v textu (např. „Novákových“), který se nenahrazuje.
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


def kontroluj(cesta, rody, rx, podle_slugu, chyby, upozorneni):
    html = rh.cti(cesta)
    jmeno = os.path.relpath(cesta)
    if rx:
        holé = []
        rh.projdi(html, lambda t: holé.extend(m.group(0) for m in rx.finditer(t)) or t)
        for n in sorted(set(holé)):
            chyby.append(f"{jmeno}: holý název rodu „{n}“ (má být značka; znackuj_rody.py)")
    for m in ZNACKA.finditer(html):
        r = podle_slugu.get(m.group(2))
        if not r:
            chyby.append(f"{jmeno}: značka neznámého rodu /rod/{m.group(2)}/")
        elif r["color"].lower() != m.group(1).strip().lower():
            chyby.append(f"{jmeno}: barva značky rodu {r['name']} je {m.group(1).strip()}, rod má {r['color']}")
    poradi = []
    for m in NADPIS.finditer(html):
        z = ZNACKA.search(m.group(2))
        if z and podle_slugu.get(z.group(2)) and podle_slugu[z.group(2)]["k"] is not None:
            poradi.append((podle_slugu[z.group(2)]["k"], podle_slugu[z.group(2)]["name"]))
    for (k1, n1), (k2, n2) in zip(poradi, poradi[1:]):
        if k2 < k1:
            chyby.append(f"{jmeno}: pořadí rodů v nadpisech: {n2} (č. {k2}) je za {n1} (č. {k1})")
            break
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
    for u in upozorneni[:30]:
        print("upozornění:", u)
    for ch in chyby:
        print("CHYBA:", ch)
    print(f"kontrola webu: {n} stránek, {len(chyby)} chyb, {len(upozorneni)} upozornění")
    sys.exit(1 if chyby else 0)


if __name__ == "__main__":
    main()
