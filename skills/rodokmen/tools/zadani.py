#!/usr/bin/env python3
"""Zadání pro čtenáře jako soubor (analyza/navrh-optimalizace.md, E1): řídicí agent ho sestaví jedním příkazem, nástroj ho zkontroluje
dřív, než se čtenář spustí (osoby a svazek existují, pramen hledanou roli vede, rozsah dává smysl). Zapisuje jen do pracovni/zadani/.

Použití (z kořene projektu):
  python3 -I tools/zadani.py novy U-0101 --otazka "Najdi křest osoby 88." --hleda křtěnec --osoba "88:křtěnec:* asi 1812, otec chalupník"
        --svazek 0a1b2c3d [--portal aron] --snimky 40-52 --vratit datum,otec,matka,kmotri [--strop 12,12] [--nezamenit "klíč:znaky jmenovce"]
        (--osoba a --nezamenit lze opakovat; existující zadání přepíše jen s --prepis)
  python3 -I tools/zadani.py rozsir U-0101 --snimky 53-55 --duvod "řádek pokračuje na další straně" [--vratit kmotri]
        schválené rozšíření rozsahu (pokračování téhož úkolu); čtenář smí číst i tyto snímky
  python3 -I tools/zadani.py ukaz U-0101
        vypíše zadání a zprávu pro čtenáře (cesta k zadání a k souboru nálezu)

Pole a dovolené hodnoty: `tools/vysledek.py vzor zadani`. Zadání nenese přepis hledaného zápisu ani pravidla publikace.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vysledek  # noqa: E402 – jediný zdroj tvaru zadání


def cesta(ukol):
    return vysledek.cesta_zadani(ukol)


def rozsah(text):
    m = re.fullmatch(r"\s*(\d+)\s*(?:[-–]\s*(\d+))?\s*", text or "")
    if not m:
        sys.exit(f"--snimky OD-DO (je „{text}“)")
    return [int(m.group(1)), int(m.group(2) or m.group(1))]


def uloz(ukol, d):
    ch = vysledek.over_zadani(d)
    if ch:
        sys.exit("ODMÍTNUTO, zadání se nezapsalo:\n  " + "\n  ".join(ch))
    p = cesta(ukol)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)
    return p


def zprava(ukol):
    rel = lambda p: os.path.relpath(p, vysledek.ROOT).replace("\\", "/")   # noqa: E731
    return (f"Assignment: {rel(cesta(ukol))}. Write the finding to {rel(vysledek.cesta_nalezu(ukol))} "
            f"and check it with tools/vysledek.py over before you finish.")


def cmd_novy(a):
    if os.path.exists(cesta(a.ukol)) and not a.prepis:
        sys.exit(f"zadání {a.ukol} už existuje (rozšíření: zadani.py rozsir; nové zadání téhož úkolu: --prepis)")
    osoby = []
    for o in a.osoba or []:
        cast = o.split(":", 2)
        if len(cast) < 2:
            sys.exit(f"--osoba KLÍČ:ROLE[:znaky] (je „{o}“)")
        osoby.append({"id": cast[0].strip(), "role": cast[1].strip(), **({"znaky": cast[2].strip()} if len(cast) > 2 and cast[2].strip() else {})})
    nez = []
    for o in a.nezamenit or []:
        k, _, znaky = o.partition(":")
        nez.append({"id": k.strip(), "znaky": znaky.strip()})
    d = {"schema": "zadani/1", "ukol": a.ukol, "otazka": a.otazka, "hleda_roli": a.hleda, "osoby": osoby,
         "pramen": {"portal": a.portal, "svazek": a.svazek}, "rozsah": {"snimky": rozsah(a.snimky)},
         "vratit": [x.strip() for x in (a.vratit or "").split(",") if x.strip()]}
    if nez:
        d["nezamenit_s"] = nez
    if a.strop:
        m = re.fullmatch(r"(\d+),(\d+)", a.strop)
        if not m:
            sys.exit("--strop KROKŮ,SNÍMKŮ (např. 12,12)")
        d["strop"] = {"kroku": int(m.group(1)), "snimku": int(m.group(2))}
    uloz(a.ukol, d)
    print(zprava(a.ukol))
    return 0


def cmd_rozsir(a):
    if not os.path.exists(cesta(a.ukol)):
        sys.exit(f"zadání {a.ukol} neexistuje (zadani.py novy)")
    d = vysledek.nacti(cesta(a.ukol))
    r = {"snimky": rozsah(a.snimky), "duvod": a.duvod}
    if a.vratit:
        r["vratit"] = [x.strip() for x in a.vratit.split(",") if x.strip()]
    d.setdefault("rozsireni", []).append(r)
    uloz(a.ukol, d)
    print(f"{a.ukol}: rozsah rozšířen o snímky {r['snimky'][0]}–{r['snimky'][1]} ({a.duvod}). " + zprava(a.ukol))
    return 0


def cmd_ukaz(a):
    if not os.path.exists(cesta(a.ukol)):
        sys.exit(f"zadání {a.ukol} neexistuje")
    print(json.dumps(vysledek.nacti(cesta(a.ukol)), ensure_ascii=False, indent=1))
    print(zprava(a.ukol))
    return 0


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("novy"); s.add_argument("ukol"); s.add_argument("--otazka", required=True); s.add_argument("--hleda", required=True)
    s.add_argument("--osoba", action="append"); s.add_argument("--nezamenit", action="append"); s.add_argument("--svazek", required=True)
    s.add_argument("--portal", default="aron"); s.add_argument("--snimky", required=True); s.add_argument("--vratit", required=True)
    s.add_argument("--strop"); s.add_argument("--prepis", action="store_true")
    s = sp.add_parser("rozsir"); s.add_argument("ukol"); s.add_argument("--snimky", required=True); s.add_argument("--duvod", required=True)
    s.add_argument("--vratit")
    s = sp.add_parser("ukaz"); s.add_argument("ukol")
    a = ap.parse_args(argv)
    if not vysledek.UKOL.fullmatch(a.ukol):
        sys.exit("ID úkolu ve tvaru U-0042")
    return {"novy": cmd_novy, "rozsir": cmd_rozsir, "ukaz": cmd_ukaz}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
