#!/usr/bin/env python3
"""Podnět pro metodiku: bádací sezení pravidla ani nástroje nemění, jen sem zapíše, co se má ve skillu zlepšit
(analyza/navrh-optimalizace.md, E2 a E6). Připíše odrážku do data/poznamky_pro_skill.md, sekce „Nové“.

Použití (z kořene projektu):
  python3 -I tools/podnet.py "nástroj X odmítl Y; čekal jsem Z; obchvat byl W" [--dopad presnost|cena|oboji] [--kolikrat N]

Podnět je technický: co se stalo, čím se to projevilo, jaký byl obchvat. Žádné údaje o rodině – text se jménem nebo příjmením osoby
z data/osoby.py nástroj odmítne (poznámky se přenášejí do veřejného repozitáře skillu). Čísla úkolů a osob do podnětu také nepatří.
"""
import argparse
import datetime
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUBOR = os.path.join("data", "poznamky_pro_skill.md")
HLAVA = ("# Poznámky pro správce skillu „rodokmen“\n\nSem se zapisuje, co by se mělo ve skillu zlepšit: chyby nástrojů, nové archivy a postupy.\n"
         "Jen technické věci, žádné údaje o rodině.\n\n## Nové\n\n")


def bez_diakritiky(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.casefold()) if unicodedata.category(c) != "Mn")


def prijmeni():
    """Příjmení osob z data/osoby.py (bez diakritiky, aspoň 4 znaky); prázdné, když soubor není."""
    try:
        ns = {}
        with open(os.path.join(ROOT, "data", "osoby.py"), encoding="utf-8-sig") as f:
            exec(f.read(), ns)
    except Exception:
        return set()
    out = set()
    for o in list((ns.get("P") or {}).values()) + list((ns.get("RODINA") or {}).values()) + list(ns.get("SIDE") or []):
        slova = re.findall(r"[^\W\d_]{4,}", str(o.get("n", "")) if isinstance(o, dict) else "")
        if len(slova) > 1:
            out.update(bez_diakritiky(s) for s in slova[1:])   # křestní jména (Jan, Marie) by odmítala i běžná slova
    return out


def kmen(s):
    """Začátek příjmení, který přežije skloňování i přechýlení (vzorny → vzor, prikladova → prikla)."""
    return s[:max(4, len(s) - 4)]


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text"); ap.add_argument("--dopad", choices=("presnost", "cena", "oboji")); ap.add_argument("--kolikrat", type=int)
    a = ap.parse_args(argv)
    text = " ".join(a.text.split())
    if len(text) < 20:
        sys.exit("podnět: aspoň věta – co se stalo, čím se to projevilo, jaký byl obchvat")
    znama = {kmen(p) for p in prijmeni()}
    nalez = sorted({s for s in re.findall(r"[^\W\d_]{4,}", text) if s[0].isupper() and any(bez_diakritiky(s).startswith(k) for k in znama)})
    if nalez:
        sys.exit("ODMÍTNUTO: podnět obsahuje příjmení z rodokmenu (" + ", ".join(nalez) + "); poznámky pro skill jsou jen technické, "
                 "napiš to bez jmen (např. „osoba se stejným jménem v téže farnosti“)")
    if re.search(r"\bU-\d{4}\b", text):
        sys.exit("ODMÍTNUTO: podnět bez čísel úkolů (do skillu nepatří); popiš situaci obecně")
    p = os.path.join(ROOT, SOUBOR)
    try:
        with open(p, encoding="utf-8") as f:
            s = f.read()
    except OSError:
        s = HLAVA
    if "## Nové" not in s:
        s = s.rstrip("\n") + "\n\n## Nové\n\n"
    s = s.replace("(nic nového)\n", "")
    navic = "".join(x for x in (f" Dopad: {a.dopad}." if a.dopad else "", f" Výskytů: {a.kolikrat}." if a.kolikrat else ""))
    s = s.rstrip("\n") + ("\n" if s.rstrip("\n").endswith("## Nové") else "") + f"\n- {datetime.date.today().isoformat()}: {text}{navic}\n"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    os.replace(p + ".tmp", p)
    print(f"podnět zapsán do {SOUBOR.replace(os.sep, '/')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
