#!/usr/bin/env python3
"""Výřez zápisu ze staženého snímku stránky (z jakéhokoli portálu).

Použití:
  vyrez.py <snimek.jpg> <klic> [x0,y0,x1,y1] [--kontrast | --vylepsit]
      x0..y1 = oblast zápisu jako zlomky šířky a výšky stránky (0..1); bez nich se bere celá stránka.
      Uloží zdroje/<klic>.jpg (plné rozlišení) a vyrezy/<klic>.jpg (zmenšeno na max. 1800 px pro web).
      --kontrast = vybledlý zápis: šedá škála, papír vybělit a písmo ztmavit (obojí ve zdroje/ i vyrezy/).
      --vylepsit = silnější úprava, když nepomůže ani --kontrast: navíc místní vyrovnání kontrastu a doostření
      (na zkoušku nejdřív overit.py … --vylepsit).
      Oblast si zapamatuje v pracovni/vyrezy_oblasti.json – `ramecek.py <klic> --stranka …` pak bere
      souřadnice čteného místa na celé stránce (stejně jako tady a v overit.py) a sám je přepočítá na výřez.

  vyrez.py --zacernit <klic> x0,y0,x1,y1 [x0,y0,x1,y1 …] [--osoby 12,anna]
      Začerní oblasti (zlomky šířky a výšky obrázku – rodná čísla) ve zdroje/<klic>.jpg i vyrezy/<klic>.jpg.
      --osoby = čí rodná čísla to jsou (čísla z P, zkratky z RODINA): zapíše je u dokumentu do data/dokumenty.json
      → zacerneno; doklad pak smí na web i s RČ žijících (pole rc). Oblasti uloží do → zacerneni a každý další
      výřez téhož klíče je nakreslí znovu. Původní sken v dokumenty/ zůstane.

Výřez dělejte velkoryse: celý zápis včetně hlavičky sloupců, okrajových poznámek a podpisů.
Potřebuje ImageMagick (příkaz `magick`).
"""
import json, os, subprocess, sys
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Vybledlé snímky: nejsvětlejších 35 % pixelů (papír) do bílé, nejtmavší 2 % do černé. Řídí se rozložením jasu,
# takže funguje i vedle tmavých předtištěných linek (pevné -level by tam písmo skoro nezměnilo).
KONTRAST = ["-colorspace", "Gray", "-contrast-stretch", "2%x35%"]


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
from obraz import magick   # společný hledač ImageMagicku (tools/obraz.py)


def vylepseni(m):
    """Úprava vybledlého snímku (#37), stejná jako v overit.py. -clahe umí jen novější ImageMagick – bez něj zbytek."""
    clahe = subprocess.run([m, "-size", "8x8", "xc:gray", "-clahe", "25x25%+128+4", "null:"],
                           capture_output=True).returncode == 0
    return (["-colorspace", "Gray"] + (["-clahe", "25x25%+128+4"] if clahe else [])
            + ["-contrast-stretch", "1%x50%", "-level", "5%,70%", "-unsharp", "0x1.2+1.2+0.02"])


def _dokumenty():
    path = os.path.join(ROOT, "data", "dokumenty.json")
    return path, (json.load(open(path, encoding="utf-8")) if os.path.exists(path) else [])


def kresli_zacerneni(MAGICK, key, oblasti):
    """Černé obdélníky (zlomky obrázku) do zdroje/ i vyrezy/; metadata pryč (náhled v EXIF by RČ ukázal)."""
    hotovo = []
    for slozka in ("zdroje", "vyrezy"):
        f = os.path.join(ROOT, slozka, key + ".jpg")
        if not os.path.exists(f):
            continue
        w, h = (int(v) for v in subprocess.run([MAGICK, f, "-format", "%w %h", "info:"], capture_output=True, text=True,
                                                check=True).stdout.split())
        kresby = []
        for x0, y0, x1, y1 in oblasti:
            kresby += ["-draw", f"rectangle {int(x0 * w)},{int(y0 * h)} {round(x1 * w)},{round(y1 * h)}"]
        subprocess.run([MAGICK, f, "-fill", "black", *kresby, "+profile", "!icc,*", "-quality", "90", f], check=True)
        hotovo.append(f)
    return hotovo


def zacernit(argv):
    """vyrez.py --zacernit <klic> oblasti… [--osoby a,b]: černé obdélníky přes rodná čísla ve zdroje/ i vyrezy/."""
    osoby = []
    if "--osoby" in argv:
        i = argv.index("--osoby")
        osoby = [int(x) if x.strip().isdigit() else x.strip() for x in (argv[i + 1:i + 2] or [""])[0].split(",") if x.strip()]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) < 2:
        sys.exit("Použití: vyrez.py --zacernit <klic> x0,y0,x1,y1 [x0,y0,x1,y1 …] [--osoby 12,anna]")
    key, oblasti = argv[0], []
    for a in argv[1:]:
        x0, y0, x1, y1 = (float(v) for v in a.split(","))
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            sys.exit(f"Oblast {a} musí být zlomky 0..1 obrázku (x0 < x1, y0 < y1).")
        oblasti.append((x0, y0, x1, y1))
    path, docs = _dokumenty()
    d = next((x for x in docs if isinstance(x, dict) and x.get("img") == key), None)
    if d is None:
        sys.exit(f"Dokument {key} v data/dokumenty.json není – nejdřív ho zapiš (oblasti začernění se ukládají k němu, "
                 "aby je nový výřez nesmazal).")
    hotovo = kresli_zacerneni(magick(), key, oblasti)
    if not hotovo:
        sys.exit(f"Obrázek {key}.jpg není ve zdroje/ ani vyrezy/ (nejdřív vyrez.py <sken> {key}).")
    d["zacerneni"] = [list(o) for o in dict.fromkeys(tuple(o) for o in list(d.get("zacerneni") or []) + oblasti)]
    if osoby:
        d["zacerneno"] = list(dict.fromkeys(list(d.get("zacerneno") or []) + osoby))
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as fh:   # celý soubor naráz
        json.dump(docs, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(path + ".tmp", path)
    print("začerněno:", ", ".join(hotovo) + (f"; zacerneno u dokumentu: {osoby}" if osoby else "")
          + " – zkontroluj obrázek, že rodné číslo není čitelné")


def main():
    if sys.argv[1:2] == ["--zacernit"]:
        return zacernit(sys.argv[2:])
    kontrast = "--kontrast" in sys.argv
    vylepsit = "--vylepsit" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--vylepsit", "--kontrast")]
    if len(args) < 2:
        sys.exit(__doc__)
    src, key = args[0], args[1]
    MAGICK = magick()
    full = os.path.join(ROOT, "zdroje", key + ".jpg")
    small = os.path.join(ROOT, "vyrezy", key + ".jpg")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    os.makedirs(os.path.dirname(small), exist_ok=True)
    oblast = [0, 0, 1, 1]
    cmd = [MAGICK, src, "-auto-orient"]   # fotky z mobilu: otočit podle EXIF (EXIF i s GPS pak smaže +profile, barevný profil ICC zůstane)
    if len(args) > 2:
        x0, y0, x1, y1 = (float(v) for v in args[2].split(","))
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):   # pixely by ImageMagick jen varoval a uložil celou stránku
            sys.exit(f"Oblast {args[2]} musí být zlomky 0..1 (x0 < x1, y0 < y1), ne pixely – "
                     "např. 0.1,0.25,0.9,0.6 = od 10 % do 90 % šířky a od 25 % do 60 % výšky.")
        w, h = (int(v) for v in subprocess.run([MAGICK, src + "[0]", "-auto-orient", "-format", "%w %h", "info:"],
                                                capture_output=True, text=True, check=True).stdout.split())
        cmd += ["-crop", f"{round((x1 - x0) * w)}x{round((y1 - y0) * h)}+{round(x0 * w)}+{round(y0 * h)}", "+repage"]
        oblast = [x0, y0, x1, y1]
    if vylepsit:
        cmd += vylepseni(MAGICK)
    elif kontrast:   # --vylepsit už kontrast obsahuje
        cmd += KONTRAST
    subprocess.run(cmd + ["+profile", "!icc,*", "+set", "comment", "-quality", "90", full], check=True)
    subprocess.run([MAGICK, full, "-resize", "1800x1800>", "-quality", "85", small], check=True)
    zapamatuj_oblast(key, oblast)
    _, docs = _dokumenty()   # začernění rodných čísel (vyrez.py --zacernit) nakreslit znovu
    d = next((x for x in docs if isinstance(x, dict) and x.get("img") == key and x.get("zacerneni")), None)
    if d:
        kresli_zacerneni(MAGICK, key, [tuple(o) for o in d["zacerneni"]])
        print("znovu začerněno:", len(d["zacerneni"]), "oblastí (data/dokumenty.json → zacerneni) – zkontroluj, že sedí")
    print("uloženo:", full, "a", small, "(zvýšený kontrast – poznamenej to v přepisu)" if kontrast or vylepsit else "")


def zapamatuj_oblast(key, oblast):
    """Oblast výřezu na stránce pro `ramecek.py --stranka` (pracovni/, na web nejde)."""
    path = os.path.join(ROOT, "pracovni", "vyrezy_oblasti.json")
    try:
        d = json.load(open(path, encoding="utf-8"))
        d = d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        d = {}
    d[key] = oblast
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
