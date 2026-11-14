#!/usr/bin/env python3
"""Výzkumný deník jako strukturovaná data (data/denik.jsonl, jen přidávání). Tabulka na webu se z něj generuje.

Použití (z kořene projektu): python3 -I tools/denik.py <příkaz> …
  pridej --datum RRRR-MM-DD --zdroj-typ archiv|stopa|rodina|jiné --zdroj TEXT --hledano VĚTA
         --vysledek nalezeno|vyvráceno|nenalezeno|částečně|nečitelné [--overeno] [--rozsah TEXT]
         [--nalez VĚTA (do 400 znaků)] [--citace TEXT] [--poznamka TEXT] [--osoby a,b] [--odkaz KLÍČ] [--opravuje ID]
                              přidá záznam; chybný záznam se odmítne a soubor se nezmění. Oprava = nový záznam s --opravuje
  vykresli [--do SOUBOR]      tabulka v Markdownu (opravené a nedořešené záznamy se nevykreslí)
  over                        zkontroluje celý soubor (schéma, zakázané vzory, duplicity, odkazy na opravované)
  migruj [--zdroj SOUBOR] [--znovu]
                              převede dosavadní tabulku research_log.md na denik.jsonl, protokol k ruční kontrole
                              zapíše do pracovni/migrace_denik.md
  overit-migraci [--zdroj SOUBOR]
                              ověří, že každý řádek původní tabulky má záznam a původní text se doslova shoduje

Pravidla: reference/zapisy.md, ADR 0002. Zakázané v textech pro web: čísla úkolů, jména agentů a modelů, cesty, údaje
o procesu, opravy uvnitř textu, mezera před dvojtečkou, šipky.
"""
import argparse
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import zaznamy_store as store  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
LOG = os.path.join(DATA, "denik.jsonl")
STARY = os.path.join(DATA, "research_log.md")
PROTOKOL = os.path.join(ROOT, "pracovni", "migrace_denik.md")

TYPY_ZDROJE = ("archiv", "stopa", "rodina", "jiné")
VYSLEDKY = ("nalezeno", "vyvráceno", "nenalezeno", "částečně", "nečitelné")
ROZSAH_POVINNY = ("nenalezeno", "vyvráceno", "částečně", "nečitelné")   # negativní výsledek vždy s rozsahem
NALEZ_POVINNY = ("nalezeno", "vyvráceno")
VEREJNA_POLE = ("rozsah", "hledano", "nalez", "citace", "poznamka", "odkaz")
SLOUPCE = ("#", "datum", "zdroj", "rozsah", "hledáno", "výsledek", "nález", "citace", "odkaz")
MAX_HLEDANO, MAX_NALEZ = 160, 400


def over_zaznam(z, id_pred=()):
    """Seznam chyb jednoho záznamu. id_pred = id záznamů před ním (pro kontrolu --opravuje)."""
    chyby = []
    if not isinstance(z.get("id"), int) or isinstance(z.get("id"), bool) or z["id"] < 1:
        chyby.append("id: celé číslo od 1")
    if z.get("k_rucni_kontrole"):   # migrovaný záznam k ruční kontrole: stačí původní text, na web nejde
        if not z.get("puvodni"):
            chyby.append("puvodni: záznam k ruční kontrole musí nést původní text")
        return chyby
    if not store.je_datum(z.get("datum")):
        chyby.append("datum: tvar RRRR-MM-DD (skutečné datum)")
    zd = z.get("zdroj")
    if not isinstance(zd, dict) or zd.get("typ") not in TYPY_ZDROJE or not str(zd.get("text") or "").strip():
        chyby.append(f"zdroj: {{typ: {'|'.join(TYPY_ZDROJE)}, text}} – typ a text jsou povinné")
    vys = z.get("vysledek")
    if vys not in VYSLEDKY:
        chyby.append(f"vysledek: jedna z hodnot {', '.join(VYSLEDKY)}")
    hl = str(z.get("hledano") or "")
    if not hl.strip():
        chyby.append("hledano: povinné, jedna věta")
    elif len(hl) > MAX_HLEDANO:
        chyby.append(f"hledano: nejvýš {MAX_HLEDANO} znaků (je {len(hl)})")
    nal = str(z.get("nalez") or "")
    if len(nal) > MAX_NALEZ:
        chyby.append(f"nalez: nejvýš {MAX_NALEZ} znaků (je {len(nal)}); zbytek patří do poznamka")
    if vys in ROZSAH_POVINNY and not str(z.get("rozsah") or "").strip():
        chyby.append(f"rozsah: povinný u výsledku {vys} (co přesně se prošlo)")
    if vys in NALEZ_POVINNY and not nal.strip():
        chyby.append(f"nalez: povinný u výsledku {vys}")
    if "osoby" in z and not (isinstance(z["osoby"], list) and all(isinstance(x, str) for x in z["osoby"])):
        chyby.append("osoby: seznam klíčů osob")
    if z.get("opravuje") is not None and z["opravuje"] not in id_pred:
        chyby.append(f"opravuje: záznam {z['opravuje']} neexistuje")
    texty = [("zdroj", (zd or {}).get("text", "") if isinstance(zd, dict) else "")] + [(p, str(z.get(p) or "")) for p in VEREJNA_POLE]
    for pole, text in texty:
        for nazev, nalezeno in store.zakazane_vzory(text):
            chyby.append(f"{pole}: zakázaný vzor „{nazev}“: {nalezeno}")
    return chyby


def nacti_zaznamy():
    """(záznamy, chyby) – chyby jsou řádky s číslem řádku; duplicity id a odkazy na opravované se kontrolují tady."""
    zaznamy, chyby, videna = [], [], set()
    for n, z, e in store.nacti(LOG):
        if e:
            chyby.append(f"řádek {n}: {e}")
            continue
        for ch in over_zaznam(z, videna):
            chyby.append(f"řádek {n} (id {z.get('id')}): {ch}")
        if z.get("id") in videna:
            chyby.append(f"řádek {n}: duplicitní id {z.get('id')}")
        videna.add(z.get("id"))
        zaznamy.append(z)
    return zaznamy, chyby


def vykresli(zaznamy):
    nahrazene = {z.get("opravuje") for z in zaznamy if z.get("opravuje") is not None}
    radky = ["| " + " | ".join(SLOUPCE) + " |", "|" + "---|" * len(SLOUPCE)]
    for z in sorted(zaznamy, key=lambda x: x.get("id", 0)):
        if z.get("id") in nahrazene or z.get("k_rucni_kontrole"):
            continue
        nalez = store.bunka(z.get("nalez"))
        if z.get("poznamka"):
            nalez = (nalez + " " if nalez else "") + "<details><summary>poznámka</summary>" + store.bunka(z["poznamka"]) + "</details>"
        vys = z["vysledek"] + (" (ověřeno)" if z.get("overeno") else "")
        bunky = [z["id"], z["datum"], z["zdroj"]["text"], z.get("rozsah"), z.get("hledano"), vys]
        radky.append("| " + " | ".join(store.bunka(b) for b in bunky) + " | " + nalez + " | " + store.bunka(z.get("citace"))
                     + " | " + store.bunka(z.get("odkaz")) + " |")
    return "\n".join(radky) + "\n"


def cmd_pridej(a):
    zaznamy, chyby = nacti_zaznamy()
    if chyby:
        sys.exit("denik.jsonl má chyby, nejdřív je oprav (denik.py over):\n  " + "\n  ".join(chyby[:10]))
    z = {"id": max([x["id"] for x in zaznamy], default=0) + 1, "datum": a.datum,
         "zdroj": {"typ": a.zdroj_typ, "text": a.zdroj}, "rozsah": a.rozsah or "", "hledano": a.hledano,
         "vysledek": a.vysledek}
    if a.overeno:
        z["overeno"] = True
    for pole in ("nalez", "citace", "poznamka", "odkaz"):
        if getattr(a, pole):
            z[pole] = getattr(a, pole)
    if a.osoby:
        z["osoby"] = [x.strip() for x in a.osoby.split(",") if x.strip()]
    if a.opravuje is not None:
        z["opravuje"] = a.opravuje
    ch = over_zaznam(z, {x["id"] for x in zaznamy})
    if ch:
        sys.exit("Záznam se neuložil:\n  " + "\n  ".join(ch))
    with store.Zamek(LOG):
        store.pridej_radek(LOG, z)
    print(f"deník: záznam {z['id']} uložen")


def cmd_vykresli(a):
    zaznamy, chyby = nacti_zaznamy()
    if chyby:
        sys.exit("denik.jsonl má chyby (denik.py over):\n  " + "\n  ".join(chyby[:10]))
    md = vykresli(zaznamy)
    if a.do:
        cil = os.path.join(ROOT, a.do)
        os.makedirs(os.path.dirname(cil), exist_ok=True)
        with open(cil, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        print(f"deník: tabulka zapsána do {a.do}")
    else:
        sys.stdout.write(md)


def cmd_over(a):
    zaznamy, chyby = nacti_zaznamy()
    if chyby:
        print("\n".join(chyby))
        sys.exit(f"denik.jsonl: {len(chyby)} chyb")
    print(f"denik.jsonl v pořádku ({len(zaznamy)} záznamů)")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    ap = argparse.ArgumentParser(prog="denik.py", add_help=False)
    sub = ap.add_subparsers(dest="prikaz", required=True)
    p = sub.add_parser("pridej")
    p.add_argument("--datum", required=True)
    p.add_argument("--zdroj-typ", dest="zdroj_typ", required=True)
    p.add_argument("--zdroj", required=True)
    p.add_argument("--hledano", required=True)
    p.add_argument("--vysledek", required=True)
    p.add_argument("--rozsah")
    p.add_argument("--nalez")
    p.add_argument("--citace")
    p.add_argument("--poznamka")
    p.add_argument("--osoby")
    p.add_argument("--odkaz")
    p.add_argument("--opravuje", type=int)
    p.add_argument("--overeno", action="store_true")
    p.set_defaults(fn=cmd_pridej)
    p = sub.add_parser("vykresli")
    p.add_argument("--do")
    p.set_defaults(fn=cmd_vykresli)
    p = sub.add_parser("over")
    p.set_defaults(fn=cmd_over)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
