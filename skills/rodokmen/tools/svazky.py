#!/usr/bin/env python3
"""Svazek do katalogu data/svazky.json ze souboru v pracovni/, bez sítě.

Portálové nástroje zapisují svazek samy (`aron_img.py <apu> svazek`, `litomerice.py svazek …`, `portafontium.py svazek …`). Na portály,
kam skript nesmí (ZAKAZ v tools/slusne.py: eBadatelna, SOA Třeboň, MZA…), jiná cesta není: čtenář v prohlížeči opíše údaje o svazku do
souboru v pracovni/ a badatel ho zapíše tímto nástrojem. Bez svazku v katalogu nejde sestavit zadání čtení (tools/zadani.py).

Použití (z kořene projektu):
  python3 -I tools/svazky.py pridej pracovni/svazek_<klic>.json [--doplnit]
        {"klic": "ebad_14312", "archiv": "…", "portal": "eBadatelna", "svazek": "Obec 36, O 1855–1943", "url": "https://…",
         "snimku": 101, "popis": "lokality", "roky": "1855–1943", "pokryva": {"role": ["ženich", "nevěsta", "svědek"]}}
        nový svazek (klíč ještě v katalogu není); s --doplnit jen přidá nebo změní uvedená pole existujícího svazku
  python3 -I tools/svazky.py ukaz <klic>

Kontrola před zápisem: klíč [a-z0-9_], u nového svazku povinné archiv, portal, svazek, url (https); snimku kladné číslo; role v „pokryva“
jen z kontraktu (tools/vysledek.py ROLE); žádná jiná pole (údaje o osobách do katalogu nepatří). Při chybě se nic nezapíše.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vysledek  # noqa: E402
import zapis  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLIC = re.compile(r"[a-z0-9][a-z0-9_]{1,39}")
POVINNE = ("archiv", "portal", "svazek", "url")
TEXTY = ("archiv", "portal", "svazek", "url", "popis", "roky")
POLE = set(TEXTY) | {"snimku", "pokryva"}


def katalog():
    p = os.path.join(ROOT, "data", "svazky.json")
    try:
        with open(p, encoding="utf-8-sig") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def over(d, doplnit, existuje):
    """Seznam chyb (prázdný = v pořádku)."""
    ch = []
    klic = d.get("klic")
    if not (isinstance(klic, str) and KLIC.fullmatch(klic)):
        ch.append("klic: malá písmena bez diakritiky, číslice a podtržítko (např. ebad_14312)")
    if existuje and not doplnit:
        ch.append(f"svazek {klic} už je v katalogu; jen doplnit pole: --doplnit")
    if doplnit and not existuje:
        ch.append(f"svazek {klic} v katalogu není; --doplnit jen u existujícího")
    nezname = sorted(set(d) - POLE - {"klic"})
    if nezname:
        ch.append("neznámá pole: " + ", ".join(nezname) + " (údaje o osobách do katalogu nepatří)")
    if not doplnit:
        ch += [f"chybí {k}" for k in POVINNE if not d.get(k)]
    for k in TEXTY:
        if k in d and not (isinstance(d[k], str) and d[k].strip() and len(d[k]) <= 300):
            ch.append(f"{k}: neprázdný text nejvýš 300 znaků")
    if isinstance(d.get("url"), str) and not d["url"].startswith("https://"):
        ch.append("url: jen https://")
    if "snimku" in d and not (isinstance(d["snimku"], int) and not isinstance(d["snimku"], bool) and d["snimku"] > 0):
        ch.append("snimku: kladné celé číslo")
    if "pokryva" in d:
        p = d["pokryva"]
        role = p.get("role") if isinstance(p, dict) else None
        if not (isinstance(p, dict) and set(p) == {"role"} and isinstance(role, list) and role):
            ch.append('pokryva: {"role": [ … ]}')
        else:
            spatne = [r for r in role if r not in vysledek.ROLE]
            if spatne:
                ch.append(f"pokryva.role: {', '.join(map(str, spatne))} není role kontraktu ({', '.join(vysledek.ROLE)})")
    return ch


def v_pracovni(cesta):
    plna = os.path.normcase(os.path.abspath(cesta))
    return plna.startswith(os.path.normcase(os.path.join(ROOT, "pracovni")) + os.sep)


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = sys.argv[1:] if argv is None else argv
    if a[:1] == ["ukaz"] and len(a) == 2:
        z = katalog().get(a[1])
        if z is None:
            print(f"svazek {a[1]} v katalogu není")
            return 1
        print(json.dumps(z, ensure_ascii=False, indent=1))
        return 0
    if not (a[:1] == ["pridej"] and len(a) in (2, 3) and (len(a) == 2 or a[2] == "--doplnit")):
        print(__doc__)
        return 2
    cesta, doplnit = os.path.join(ROOT, a[1]) if not os.path.isabs(a[1]) else a[1], len(a) == 3
    if not v_pracovni(cesta):
        print("ODMÍTNUTO: vstup jen ze souboru v pracovni/")
        return 1
    try:
        with open(cesta, encoding="utf-8-sig") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        print(f"ODMÍTNUTO: {a[1]} nejde přečíst jako JSON ({e})")
        return 1
    if not isinstance(d, dict):
        print("ODMÍTNUTO: vstup je jeden objekt JSON")
        return 1
    ch = over(d, doplnit, d.get("klic") in katalog())
    if ch:
        print("ODMÍTNUTO, nic se nezapsalo:\n- " + "\n- ".join(ch))
        return 1
    klic = d["klic"]
    zaznam = {k: v for k, v in d.items() if k != "klic"}
    zapis.zapis("svazky", klic, zaznam, sloucit=doplnit)
    print(f"{klic}: {'doplněno' if doplnit else 'zapsáno'} do data/svazky.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
