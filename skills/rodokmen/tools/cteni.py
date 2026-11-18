#!/usr/bin/env python3
"""Porovnání prvního a kontrolního čtení zápisu po pevných polích (reference/zapisy.md → Pevná pole pro kontrolní čtení).

Obě čtení vyplní tatáž pole podle druhu zápisu. Shoda pole po normalizaci = ověřeno; neshoda (i pole, které jedno čtení
nemá nebo nepřečetlo) = spor pro uživatele – nástroj ho připíše do dávky pracovni/sporna_cteni.json (klíč zápisu, výřez,
pole, obě čtení), ze které se udělá stránka s odpověďmi (SKILL.md → Spornou věc). Žádné třetí čtení. Nic v data/ nemění.

Použití (z kořene projektu):
  python3 -I tools/cteni.py vzor N|O|Z                         prázdný formulář čtení (křest, sňatek, úmrtí)
  python3 -I tools/cteni.py porovnej pracovni/cteni_<klic>_1.json pracovni/cteni_<klic>_2.json
      kód 0 = všechna pole se shodují (zápis smí být ověřený), 1 = spory zapsané do pracovni/sporna_cteni.json, 2 = chybný vstup
Vstup: {"klic": "<klíč zápisu>", "druh": "N", "vyrez": "vyrezy/<klíč>.jpg", "pole": {"datum_krtu": "…", …}, "necitelne": ["kmotri"]}

Normalizace: mezery a interpunkce, malá písmena, w = v, „č.“ = „čp.“; v datu měsíc slovem = číslem (i starý pravopis);
věk s jednotkou let = bez jednotky. Kratší přepis téhož pole (podmnožina slov) je spor, ne shoda.
"""
import json
import os
import re
import sys
import unicodedata

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPORY = os.path.join(ROOT, "pracovni", "sporna_cteni.json")

POLE = {
    "N": ("datum_narozeni", "datum_krtu", "dite", "otec_jmeno", "otec_stav", "otec_dum", "otec_obec", "matka_jmeno", "matka_rodne",
          "matka_otec", "kmotri"),
    "O": ("datum", "zenich_jmeno", "zenich_vek", "zenich_stav", "zenich_dum", "zenich_obec", "zenich_rodice", "nevesta_jmeno",
          "nevesta_vek", "nevesta_stav", "nevesta_dum", "nevesta_obec", "nevesta_rodice", "svedci"),
    "Z": ("datum_umrti", "datum_pohrbu", "jmeno", "stav", "dum", "obec", "vek", "pricina"),
}


def norm(t):
    return re.sub(r"[\s.,;:]+", " ", str(t)).strip().casefold().replace("w", "v")


def bez_diakritiky(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


# pořadí je důležité (července před června, Martii před Maii)
MESICE = ((r"(7|sept?)b(e)?r", 9), (r"(8|oct|okt)b(e)?r", 10), (r"9b(e)?r", 11), (r"(x|10|dec)b(e)?r", 12),
          (r"jan|ledn|leden", 1), (r"feb|únor|února", 2), (r"mart|marz|mär|břez", 3), (r"ma[ijy]|květ", 5), (r"apr|dub", 4),
          (r"červenc|července", 7), (r"jun|červen|června", 6), (r"jul", 7), (r"aug|srp", 8), (r"sep|září", 9),
          (r"oct|okt|říj|října", 10), (r"nov|listop", 11), (r"dec|dez|prosin", 12))


def _mesic(slovo):
    if not re.fullmatch(r"[^\W\d_]{3,}|(7|8|9|10|x)b(e)?r\w*", slovo):
        return slovo
    holy = bez_diakritiky(slovo)
    for vzor, cislo in MESICE:
        if re.match(vzor, slovo) or re.match(bez_diakritiky(vzor), holy):
            return str(cislo)
    return slovo


def norm_pole(pole, t):
    n = re.sub(r"(?<!\w)(?:čp|č p|č|cp|c p)(?=\s+\d)", "č", norm(t))
    if pole.endswith("vek"):
        n = re.sub(r"(?<!\w)(\d+) (?:let|léta|roků|roku|rok|r|jahre?|jahr|ann(?:orum|os|i)?)(?!\w)", r"\1", n)
        n = re.sub(r"(?<!\w)(?:annorum|annos|anni|ann|aetatis) (\d+)(?!\w)", r"\1", n)
    if pole.startswith("datum") or re.search(r"(?<!\d)1[5-9]\d\d(?!\d)", n):
        n = " ".join(_mesic(s) for s in n.split())
    return n


def nacti(cesta):
    try:
        with open(cesta, encoding="utf-8-sig") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError(f"{cesta}: {e}")
    if not isinstance(d, dict) or d.get("druh") not in POLE:
        raise ValueError(f"{cesta}: chybí „druh“ (N, O nebo Z)")
    if not re.fullmatch(r"[a-z0-9_]+", str(d.get("klic", ""))):
        raise ValueError(f"{cesta}: chybí „klic“ zápisu")
    pole = d.get("pole") or {}
    nec = d.get("necitelne") or []
    cizi = sorted(set(pole) - set(POLE[d["druh"]]) | set(nec) - set(POLE[d["druh"]]))
    if cizi:
        raise ValueError(f"{cesta}: pole {', '.join(cizi)} nejsou pevná pole druhu {d['druh']} ({', '.join(POLE[d['druh']])})")
    return d


def porovnej(a, b):
    """[(pole, vysledek, a, b)] pro pole, která má aspoň jedno čtení; vysledek „shoda“, nebo popis sporu."""
    if (a["klic"], a["druh"]) != (b["klic"], b["druh"]):
        raise ValueError("čtení nejsou ke stejnému zápisu a druhu")
    pa, pb = a.get("pole") or {}, b.get("pole") or {}
    na, nb = set(a.get("necitelne") or []), set(b.get("necitelne") or [])
    out = []
    for p in POLE[a["druh"]]:
        if p not in pa and p not in pb and p not in na and p not in nb:
            continue
        va, vb = pa.get(p), pb.get(p)
        if p in na or p in nb or va is None or vb is None:
            vysl = "nečitelné nebo jen v jednom čtení"
        elif norm_pole(p, va) == norm_pole(p, vb):
            vysl = "shoda"
        else:
            vysl = "neshoda"
        out.append((p, vysl, va, vb))
    return out


def zapis_spory(a, radky):
    try:
        with open(SPORY, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = []
    znam = {(s.get("klic"), s.get("pole")) for s in d}
    nove = 0
    for p, vysl, va, vb in radky:
        if vysl != "shoda" and (a["klic"], p) not in znam:
            d.append({"klic": a["klic"], "vyrez": a.get("vyrez") or f"vyrezy/{a['klic']}.jpg", "pole": p, "spor": vysl,
                      "moznosti": [x for x in (va, vb) if x is not None], "navrh": None})
            nove += 1
    os.makedirs(os.path.dirname(SPORY), exist_ok=True)
    tmp = SPORY + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SPORY)
    return nove


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if a[:1] == ["vzor"] and len(a) == 2 and a[1] in POLE:
        print(json.dumps({"klic": "<klíč zápisu>", "druh": a[1], "vyrez": "vyrezy/<klíč>.jpg",
                          "pole": {p: "" for p in POLE[a[1]]}, "necitelne": []}, ensure_ascii=False, indent=1))
        return 0
    if a[:1] != ["porovnej"] or len(a) != 3:
        print(__doc__)
        return 2
    try:
        x, y = nacti(a[1]), nacti(a[2])
        radky = porovnej(x, y)
    except ValueError as e:
        print(f"CHYBA: {e}")
        return 2
    for p, vysl, va, vb in radky:
        print(f"  {p}: {vysl}" + ("" if vysl == "shoda" else f" | první: {va} | kontrolní: {vb}"))
    if all(v == "shoda" for _, v, _, _ in radky) and radky:
        print(f"{x['klic']}: všechna pole se shodují – zápis je ověřený")
        return 0
    if not radky:
        print("CHYBA: žádné pole k porovnání")
        return 2
    nove = zapis_spory(x, radky)
    print(f"{x['klic']}: spor v {sum(v != 'shoda' for _, v, _, _ in radky)} polích, do pracovni/sporna_cteni.json přidáno {nove} – "
          "rozhodne uživatel (SKILL.md → Spornou věc), do té doby prob")
    return 1


if __name__ == "__main__":
    sys.exit(main())
