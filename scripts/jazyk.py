#!/usr/bin/env python3
"""Kontrola jazyka anglické vrstvy (Fáze E, ADR 0005). Nástroj údržby repozitáře skillu, do projektů se nekopíruje.

Použití: python3 -I scripts/jazyk.py [soubor nebo složka …] [--prah 0.02]
Bez argumentů zkontroluje `skills/rodokmen-agents/`. Posoudí podíl českých znaků s diakritikou mezi písmeny souboru *.md; nad prahem
(výchozí 2 %) je soubor považovaný za český a skript skončí chybou (kód 1). Nepočítá se: frontmatter, bloky kódu, text v `…`, v uvozovkách
(„…“, “…”, "…") a řádky `source:` (odkaz na český nadpis zrcadla). Zrcadlo originálu (SKILL.md, reference/*.md) se nekontroluje.
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CESKE = set("áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ")


def ocisti(text):
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"(?m)^source:.*$", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"„[^“\n]*“|“[^”\n]*”|\"[^\"\n]*\"", "", text)
    return re.sub(r"\]\([^)]*\)", "]", text)


def podil(text):
    t = ocisti(text)
    pismena = sum(1 for c in t if c.isalpha())
    return (sum(1 for c in t if c in CESKE) / pismena) if pismena else 0.0


def soubory(cesta):
    if os.path.isdir(cesta):
        for koren, _, f in os.walk(cesta):
            for j in sorted(f):
                if j.lower().endswith(".md"):
                    yield os.path.join(koren, j)
    elif os.path.isfile(cesta):
        yield cesta


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    prah = 0.02
    if "--prah" in args:
        i = args.index("--prah")
        prah = float(args[i + 1])
        del args[i:i + 2]
    cile = args or [os.path.join(REPO, "skills", "rodokmen-agents")]
    chyby, n = [], 0
    for cil in cile:
        for s in soubory(cil):
            n += 1
            p = podil(open(s, encoding="utf-8-sig").read())
            if p > prah:
                chyby.append(f"{s}: podíl českých znaků {p * 100:.1f} % (práh {prah * 100:.1f} %) – tento soubor má být anglicky")
    for ch in chyby:
        print("CHYBA:", ch)
    print(f"jazyk: {n} souborů, {len(chyby)} chyb")
    sys.exit(1 if chyby else 0)


if __name__ == "__main__":
    main()
