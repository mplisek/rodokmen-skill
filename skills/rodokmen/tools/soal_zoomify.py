#!/usr/bin/env python3
"""Snímek matriky SOA Litoměřice (Zoomify) v plném rozlišení – bez prohlížeče a bez cookies.

Použití (z kořene projektu):
  soal_zoomify.py <cesta> <zmenseni> <vystup.jpg>
    cesta     = část adresy obrázku za „…/CZ-214000010/matriky/“ (konec typicky „….jpg“), vezmi ji jednou z prohlížeče:
                v digitální badatelně otevři snímek a v síťovém provozu najdi požadavek na
                https://images.soalitomerice.cz/ximage/matriky/zoomify/cz/archives/CZ-214000010/matriky/<cesta>/ImageProperties.xml
                (další snímky téže knihy mají stejnou cestu, liší se jen číslem obrázku)
    zmenseni  = 0 plné rozlišení (na čtení a výřez), 1 poloviční (na orientaci), 2 čtvrtinové
POZOR: aplikace digi.soalitomerice.cz po ~100 rychlých požadavcích zablokuje přístup na 30 minut. Prohlížečem jen najdi
knihu a cestu k obrázkům, snímky pak stahuj tímto nástrojem (obrázkový server neomezuje).
"""
import math, os, re, subprocess, sys, tempfile, time, urllib.request

BASE = "https://images.soalitomerice.cz/ximage/matriky/zoomify/cz/archives/CZ-214000010/matriky/"


def get(url):
    err = None
    for _ in range(3):
        try:
            return urllib.request.urlopen(url, timeout=30).read()
        except Exception as e:
            time.sleep(1)
            err = e
    raise err


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    base = BASE + sys.argv[1].strip("/")
    red, out = int(sys.argv[2]), sys.argv[3]
    x = get(base + "/ImageProperties.xml").decode()
    W, H, T = (int(re.search(fr'{k}="(\d+)"', x).group(1)) for k in ("WIDTH", "HEIGHT", "TILESIZE"))
    dims, w, h = [], W, H   # úrovně Zoomify od nejmenší po plné rozlišení
    while True:
        dims.append((w, h))
        if w <= T and h <= T:
            break
        w, h = (w + 1) // 2, (h + 1) // 2
    dims = dims[::-1]
    counts = [math.ceil(a / T) * math.ceil(b / T) for a, b in dims]
    L = len(dims) - 1 - red
    w, h = dims[L]
    nx, ny = math.ceil(w / T), math.ceil(h / T)
    start = sum(counts[:L])
    d = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(out)))
    files = []
    for y in range(ny):
        for xx in range(nx):
            g = (start + y * nx + xx) // 256
            f = os.path.join(d, f"{y:03d}_{xx:03d}.jpg")
            open(f, "wb").write(get(f"{base}/TileGroup{g}/{L}-{xx}-{y}.jpg"))
            files.append(f)
    tmp = os.path.abspath(out) + ".tmp.jpg"
    # krátká jména dlaždic (cwd=d): plné cesty by na Windows přesáhly limit délky příkazové řádky
    subprocess.run(["magick", "montage", *[os.path.basename(f) for f in files], "-tile", f"{nx}x{ny}", "-geometry", "+0+0",
                    "-gravity", "NorthWest", "-background", "white", tmp], check=True, cwd=d)
    subprocess.run(["magick", tmp, "-crop", f"{w}x{h}+0+0", "+repage", "-quality", "88", out], check=True)
    os.remove(tmp)
    for f in files:
        os.remove(f)
    os.rmdir(d)
    print(out, w, h)


if __name__ == "__main__":
    main()
