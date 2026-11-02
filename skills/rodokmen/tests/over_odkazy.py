#!/usr/bin/env python3
"""Ověří, že každý místní odkaz (href/src začínající „/“) v sestaveném webu vede na existující soubor.

Použití: python3 over_odkazy.py <web/dist>   → kód 1 a seznam, když nějaký odkaz nikam nevede (spouští ho CI).
"""
import collections
import os
import re
import sys

ODKAZ = re.compile(r'(?:href|src)="(/[^"#?]*)')


def main(dist):
    koren = os.path.abspath(dist)
    if os.name == "nt":   # dlouhé cesty (adresa zápisu bývá dlouhá) – Windows jinak končí na 260 znacích
        koren = "\\\\?\\" + koren
    spatne, priklad, pocet = collections.Counter(), {}, 0
    for slozka, _, soubory in os.walk(koren):
        if "pagefind" in slozka:
            continue
        for f in soubory:
            if not f.endswith(".html"):
                continue
            with open(os.path.join(slozka, f), encoding="utf-8", errors="replace") as fh:
                for h in ODKAZ.findall(fh.read()):
                    pocet += 1
                    cil = os.path.join(koren, *h.strip("/").split("/"))
                    if not (os.path.isfile(cil) or os.path.isfile(os.path.join(cil, "index.html"))):
                        spatne[h] += 1
                        priklad.setdefault(h, os.path.relpath(slozka, koren))
    print(f"odkazů {pocet}, nefunkčních cílů {len(spatne)}")
    for h, n in spatne.most_common(20):
        print(f"  {n}x {h}   (např. na stránce {priklad[h]})")
    return 1 if spatne or not pocet else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
