#!/usr/bin/env python3
"""Audit historických dat bez čtení snímků (požadavek uživatele 16. 11. 2026): po změně pravidel a nástrojů projde data a vypíše
rozpory s návrhem, čím je opravit. Jen čte, nic nezapisuje; opravy dělá badatel nástrojem tools/oprava.py, opravným řádkem deníku
(tools/denik.py pridej --opravuje) nebo novým úkolem (druhé čtení, dočtení rozsahu).

Použití (z kořene projektu): python3 -I tools/audit_dat.py [--json] [--kontrola druh,svazek,…]

Kontroly (název → co hlídá → čím opravit):
  druh                 druh zápisu proti klíči a názvu (sňatek s druhem S/N/Z …)          → oprava.py (pole druh)
  svazek               svazek zápisu v katalogu data/svazky.json                           → svazky.py, oprava.py
  datum                rok zápisu proti faktu osoby (* × †) u účastníka s rolí v události   → druhé čtení nebo oprava.py
                       (bez účastníků zápisu se nesrovnává: seznam r osoby cituje i křty jejích dětí)
  osoby_deniku         osoby u řádku deníku s odkazem na zápis proti účastníkům zápisu     → opravný řádek deníku
  doc_bez_zapisu       osoba se stavem doc bez jediného zápisu (r ani účastník)            → úkol: najít zápis, jinak prob
  negativ_bez_rozsahu  „nenalezeno“ v deníku bez rozsahu a bez snímků                       → úkol: dočíst rozsah, opravný řádek
Zatím nekontroluje (vyžaduje víc dat nebo úsudek): místo mimo kraj farnosti, tvary příjmení napříč zápisy, otevřené otázky
vyřešené zápisem, odkaz zápisu proti svazku, tvrzení doc bez druhého čtení (tvrzení na webu zatím nejsou).
Výstup: seznam nálezů {kontrola, kde, popis, navrh, oprava}; kód 0 i s nálezy (je to zpráva, ne brána).
"""
import json
import os
import re
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DRUH_PODLE_SLOVA = (("snatek", "O"), ("oddani", "O"), ("ohlasky", "O"), ("krest", "N"), ("narozeni", "N"), ("umrti", "Z"),
                    ("pohreb", "Z"), ("birmovani", "B"))
ZNAK_DRUHU = {"N": "*", "O": "×", "Z": "†"}
ROLE_UDALOSTI = {"N": ("křtěnec",), "O": ("ženich", "nevěsta"), "Z": ("zemřelý",)}


def jload(n, vychozi):
    try:
        with open(os.path.join(DATA, n), encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vychozi


def bez_diakritiky(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if not unicodedata.combining(c)).lower()


def roky(t):
    return [int(x) for x in re.findall(r"(?<!\d)(1[5-9]\d\d)(?!\d)", str(t or ""))]


def denik():
    out = []
    try:
        with open(os.path.join(DATA, "denik.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    out.append(r)
    except OSError:
        pass
    nahrazene = {r.get("opravuje") for r in out if r.get("opravuje") is not None}
    return [r for r in out if r.get("id") not in nahrazene]   # platí jen nejnovější verze řádku


def audit():
    ns = runpy.run_path(os.path.join(DATA, "osoby.py"))
    P, RODINA = ns.get("P") or {}, ns.get("RODINA") or {}
    zaznamy = [z for z in jload("zaznamy.json", []) if isinstance(z, dict)]
    svazky = jload("svazky.json", {})
    nalezy = []

    def nalez(kontrola, kde, popis, navrh, oprava, **navic):
        nalezy.append(dict(kontrola=kontrola, kde=kde, popis=popis, navrh=navrh, oprava=oprava, **navic))

    ucast = {}   # zápis → osoby (účastníci)
    for z in zaznamy:
        ucast[z["klic"]] = {str(u.get("osoba")) for u in z.get("ucastnici") or [] if isinstance(u, dict) and u.get("osoba") is not None}
    cituje = {}   # osoba → zápisy (r + účastník)
    for skup in (P, RODINA):
        for k, o in skup.items():
            for r in (o or {}).get("r") or []:
                cituje.setdefault(str(k), set()).add(r)
    for klic, os_ in ucast.items():
        for o in os_:
            cituje.setdefault(o, set()).add(klic)

    for z in zaznamy:
        text = bez_diakritiky(z.get("klic", "") + " " + z.get("nazev", ""))
        cekany = next((d for slovo, d in DRUH_PODLE_SLOVA if slovo in text), None)
        if cekany and z.get("druh") != cekany and not ("index" in text or "rejstrik" in text):
            nalez("druh", z["klic"], f"druh {z.get('druh')} neodpovídá zápisu („{z.get('nazev', '')}“)",
                  {"soubor": "zaznamy", "klic": z["klic"], "pole": {"druh": cekany}}, "oprava.py")
        if z.get("svazek") and z["svazek"] not in svazky:
            nalez("svazek", z["klic"], f"svazek {z['svazek']} není v data/svazky.json",
                  "doplnit svazek (svazky.py, portálový nástroj) nebo opravit klíč svazku (oprava.py)", "svazky.py / oprava.py")
        znak = ZNAK_DRUHU.get(z.get("druh"))
        rz = roky(z.get("datum"))
        role = ROLE_UDALOSTI.get(z.get("druh"), ())
        if znak and rz:   # jen osoby s jistou rolí v události (účastníci zápisu); seznam r cituje i křty dětí, ty se nesrovnávají
            for u in z.get("ucastnici") or []:
                if not isinstance(u, dict) or u.get("role") not in role:
                    continue
                o = str(u.get("osoba"))
                osoba = P.get(int(o)) if o.isdigit() else RODINA.get(o)
                fakty = [f for f in (osoba or {}).get("f") or [] if str(f).lstrip().startswith(znak)]
                rf = [r for f in fakty for r in roky(f)]
                if rf and min(abs(r - rz[-1]) for r in rf) > 1:
                    nalez("datum", z["klic"], f"rok zápisu {rz[-1]} × fakt osoby {o}: {fakty[0]}",
                          "druhé čtení data v zápisu, pak oprava faktu nebo zápisu (oprava.py)", "druhé čtení / oprava.py", osoba=o)
    for r in denik():
        odkaz = r.get("odkaz") or r.get("zaznam")
        os_r = {str(x) for x in r.get("osoby") or []}
        if odkaz in ucast and ucast[odkaz] and os_r and not (os_r & ucast[odkaz]):
            nalez("osoby_deniku", str(r.get("id")), f"řádek {r.get('id')} má osoby {sorted(os_r)}, zápis {odkaz} účastníky {sorted(ucast[odkaz])}",
                  "opravný řádek deníku se správnými osobami (denik.py pridej --opravuje)", "denik.py --opravuje")
        if r.get("vysledek") == "nenalezeno" and not str(r.get("rozsah") or "").strip() and not r.get("snimky"):
            nalez("negativ_bez_rozsahu", str(r.get("id")), f"řádek {r.get('id')} „nenalezeno“ bez rozsahu („{str(r.get('hledano', ''))[:80]}“)",
                  "úkol: dočíst a zapsat rozsah, nebo opravný řádek s rozsahem", "úkol / denik.py --opravuje")

    for skup in (P, RODINA):
        for k, o in skup.items():
            if (o or {}).get("st") == "doc" and not cituje.get(str(k)):
                nalez("doc_bez_zapisu", str(k), f"osoba {k} ({o.get('n', '')}) je doc bez zápisu",
                      "úkol: najít a přečíst zápis; do té doby st prob (oprava.py)", "úkol / oprava.py", osoba=str(k))
    return nalezy


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = sys.argv[1:] if argv is None else argv
    if a and a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    nalezy = audit()
    if "--kontrola" in a:
        chci = set(a[a.index("--kontrola") + 1].split(","))
        nalezy = [n for n in nalezy if n["kontrola"] in chci]
    if "--json" in a:
        print(json.dumps({"nalezy": nalezy}, ensure_ascii=False, indent=1))
        return 0
    if not nalezy:
        print("audit dat: bez nálezů")
        return 0
    for n in nalezy:
        navrh = n["navrh"] if isinstance(n["navrh"], str) else json.dumps(n["navrh"], ensure_ascii=False)
        print(f"[{n['kontrola']}] {n['kde']}: {n['popis']}\n    → {navrh}")
    pocty = {}
    for n in nalezy:
        pocty[n["kontrola"]] = pocty.get(n["kontrola"], 0) + 1
    print("audit dat: " + ", ".join(f"{k} {v}" for k, v in sorted(pocty.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
