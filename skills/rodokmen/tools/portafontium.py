#!/usr/bin/env python3
"""Matriky SOA Plzeň na portálu Porta fontium (portafontium.eu) bez prohlížeče.

Použití (z kořene projektu `python3 -I tools/portafontium.py …`, na Windows `python -I -X utf8 tools/portafontium.py …`):
  portafontium.py fara <fara>                -> knihy fary: kniha | obce | roky a druhy (* N, oo O, + Z, i index) | popis
                                                <fara> = část adresy římskokatolické fary, např. „dolni-bela“
                                                (https://www.portafontium.eu/contents/register/soap-pn/cirkev-rimskokatolicka/dolni-bela);
                                                obec → fara nástroj nehledá – faru zjisti na portálu (vyhledávání matrik, pole Místo)
  portafontium.py info <kniha>               -> popis knihy (signatura, druh, text desky…) a počet snímků
                                                <kniha> = část adresy knihy, např. „dolni-bela-17“
  portafontium.py snimek <kniha> <snímek> <vystup.jpg> [nahled] [x0,y0,x1,y1]
                                             -> snímek v plném rozlišení (IIIF, jeden požadavek); „nahled“ = 1/4;
                                                x0,y0,x1,y1 = jen výřez (zlomky 0..1)
  portafontium.py link <kniha> <snímek>      -> trvalý odkaz na snímek (pole „odkaz“ v zaznamy.json)
  portafontium.py svazek <kniha>             -> zapíše svazek do data/svazky.json (klíč pf_<kniha>)
Snímek = pořadové číslo náhledu v prohlížeči portálu (1, 2, 3…). Stránky knih se ukládají do pracovni/.cache_pf/.
Ber ohled na server: stahuj jen snímky, které čteš.
"""
import html, http.client, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

BASE = "https://www.portafontium.eu"
ARCHIV = "soap-pn"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "pracovni", ".cache_pf")
UA = {"User-Agent": "Mozilla/5.0 (rodokmen)"}   # bez prohlížečového User-Agentu portál vrací 403


def get(url, binary=False):
    url = url if url.startswith("http") else BASE + url
    err = None
    for attempt in range(4):
        if attempt:
            time.sleep(2 * attempt)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                sys.exit(f"Porta fontium: stránka nenalezena (404): {url}")
            if e.code < 500:   # 4xx se opakováním nespraví
                sys.exit(f"Porta fontium odmítl požadavek ({e.code}): {url}")
            err = e
        except (OSError, http.client.HTTPException) as e:   # i useknutý přenos (IncompleteRead)
            err = e
    sys.exit(f"Porta fontium neodpovídá ({err}): {url}")


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def kniha_page(kniha):
    kniha = kniha.strip("/").split("/")[-1]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, kniha + ".html")
    if os.path.exists(path):
        return kniha, open(path, encoding="utf-8").read()
    page = get(f"/register/{ARCHIV}/{kniha}")
    if "data-iip-path" in page:   # kešuj jen opravdovou stránku knihy se snímky
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
    return kniha, page


def info(kniha):
    kniha, page = kniha_page(kniha)
    fields = {}
    for m in re.finditer(r'<div class="field-label">(.*?)</div>\s*<div class="field-items">(.*?)</div>\s*</div>', page, re.S):
        lab, val = text(m.group(1)).rstrip(":"), text(m.group(2))
        if val and lab not in fields:
            fields[lab] = val
    scans = re.findall(r'data-iip-path="([^"]+)"', page)
    links = re.findall(r'href="(/iipimage/\d+/[^"]+)"', page)
    return kniha, fields, scans, links


def scan(kniha, n):
    kniha, fields, scans, links = info(kniha)
    if not str(n).isdigit():
        sys.exit(f"číslo snímku musí být celé číslo od 1 (zadáno „{n}“)")
    n = int(n)
    if not 1 <= n <= len(scans):
        sys.exit(f"{kniha}: snímek {n} neexistuje (kniha má {len(scans)} snímků)")
    return kniha, fields, scans[n - 1], (links[n - 1] if n - 1 < len(links) else "")


def snimek(kniha, n, out, nahled=False, crop=None):
    kniha, _, path, link = scan(kniha, n)
    region = "full"
    if crop:
        x0, y0, x1, y1 = crop
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            sys.exit("výřez x0,y0,x1,y1 musí být zlomky 0–1 a x0 < x1, y0 < y1")
        region = "pct:" + ",".join(f"{v * 100:.3f}" for v in (x0, y0, x1 - x0, y1 - y0))
    size = "pct:25" if nahled else "full"
    data = get(f"/fcgi-bin/iipsrv.fcgi?IIIF={urllib.parse.quote(path)}/{region}/{size}/0/default.jpg", binary=True)
    if not data.startswith(b"\xff\xd8"):
        sys.exit("Porta fontium nevrátil obrázek JPEG (zkus to později)")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    print(out, f"{len(data) // 1024} kB", "odkaz:", BASE + link)


def fara(slug):
    slug = slug.strip("/").split("/")[-1]
    # „Mýto“ → „myto“, „Dolní Bělá“ → „dolni-bela“ (adresa fary na portálu je bez diakritiky)
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode().lower().replace(" ", "-")
    url = f"/contents/register/{ARCHIV}/cirkev-rimskokatolicka/{slug}"
    out, n = [], 0
    while True:   # seznam knih je po 40 na stránku
        page = get(url + (f"?page={n}" if n else ""))
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
            m = re.search(r'href="/register/[^/]+/([^"]+)"[^>]*>([^<]+)</a>', row)
            if not m:
                continue
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            out.append((m.group(1), [c for c in cells if c and c != ">"]))
        n += 1
        if f'{slug}?page={n}"' not in page:
            return out


def zkrat(s, n=300):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " …"


def svazek(kniha):
    kniha, fields, scans, _ = info(kniha)
    path = os.path.join(ROOT, "data", "svazky.json")
    d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    sig = fields.get("Signatura", kniha)
    popis = "; ".join(x for x in (fields.get("Místo", ""), fields.get("Text desky", "")) if x)
    d[f"pf_{kniha}"] = {"archiv": "SOA Plzeň – Sbírka matrik západních Čech", "portal": "Porta fontium",
                        "svazek": f"{sig}, {fields.get('Typ', '')}".strip(", "), "popis": popis[:300],
                        "snimku": len(scans), "url": f"{BASE}/register/{ARCHIV}/{kniha}"}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"pf_{kniha} ->", d[f"pf_{kniha}"]["svazek"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "fara" and len(a) > 1:
        knihy = fara(a[1])
        if not knihy:
            sys.exit(f"Fara „{a[1]}“ nenalezena nebo nemá knihy – zkontroluj část adresy (např. dolni-bela).")
        for k, c in knihy:
            print(k, "|", " | ".join(zkrat(x) for x in c[1:]))
    elif a[0] == "info" and len(a) > 1:
        k, f, s, _ = info(a[1])
        for lab, val in f.items():
            print(f"{lab}: {val}")
        print("snímků:", len(s))
    elif a[0] == "snimek" and len(a) > 3:
        rest = a[4:]
        try:
            crop = next((tuple(float(v) for v in x.split(",")) for x in rest if x.count(",") == 3), None)
        except ValueError:
            sys.exit("výřez zadej jako čtyři čísla x0,y0,x1,y1 (zlomky 0–1)")
        snimek(a[1], a[2], a[3], "nahled" in rest, crop)
    elif a[0] == "link" and len(a) > 2:
        print(BASE + scan(a[1], a[2])[3])
    elif a[0] == "svazek" and len(a) > 1:
        svazek(a[1])
    else:
        sys.exit(__doc__)
