#!/usr/bin/env python3
"""Výřez zápisu ze staženého snímku stránky (z jakéhokoli portálu).

Použití:
  vyrez.py <snimek.jpg> <klic> [x0,y0,x1,y1]
      x0..y1 = oblast zápisu jako zlomky šířky a výšky stránky (0..1); bez nich se bere celá stránka.
      Uloží zdroje/<klic>.jpg (plné rozlišení) a vyrezy/<klic>.jpg (zmenšeno na max. 1800 px pro web).

Výřez dělejte velkoryse: celý zápis včetně hlavičky sloupců, okrajových poznámek a podpisů.
Potřebuje ImageMagick (příkaz `magick`).
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, key = sys.argv[1], sys.argv[2]
    full = os.path.join(ROOT, "zdroje", key + ".jpg")
    small = os.path.join(ROOT, "vyrezy", key + ".jpg")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    os.makedirs(os.path.dirname(small), exist_ok=True)
    cmd = ["magick", src, "-auto-orient"]   # fotky z mobilu: otočit podle EXIF (EXIF i s GPS pak smaže +profile, barevný profil ICC zůstane)
    if len(sys.argv) > 3:
        x0, y0, x1, y1 = (float(v) for v in sys.argv[3].split(","))
        w, h = (int(v) for v in subprocess.run(["magick", src + "[0]", "-auto-orient", "-format", "%w %h", "info:"],
                                                capture_output=True, text=True, check=True).stdout.split())
        cmd += ["-crop", f"{round((x1 - x0) * w)}x{round((y1 - y0) * h)}+{round(x0 * w)}+{round(y0 * h)}", "+repage"]
    subprocess.run(cmd + ["+profile", "!icc,*", "+set", "comment", "-quality", "90", full], check=True)
    subprocess.run(["magick", full, "-resize", "1800x1800>", "-quality", "85", small], check=True)
    print("uloženo:", full, "a", small)


if __name__ == "__main__":
    main()
