#!/usr/bin/env python3
"""Kontrola dodržování metodiky ze záznamů sezení Claude Code (analyza/zjednoduseni-badani.md, 10.7). Jen čte; nic neblokuje
a nevypisuje text zadání ani odpovědí – jen nástroj, čas a krátký výřez příkazu nebo cesty.

Použití (z kořene projektu):
  python3 -I tools/dodrzovani.py [--sezeni ID|posledni|vse] [--json]
      kód 0 = bez porušení, 1 = porušení nalezena (upozornění kód nemění)

Hlídá (hlavní vlákno i pomocníky):
  zapis_dat        Edit/Write přímo do data/*.json, data/denik.jsonl, data/osoby.py (mimo nalez.py, zapis.py, oprava.py, denik.py),
                   `sed -i` nebo přesměrování `>` do těchto souborů
  sit_mimo_brzdu   curl, wget, Invoke-WebRequest na web archivu (seznam brzdy a známé archivy) bez tools/slusne.py
  pomocnik_data    pomocník (subagent) zapisuje do data/ – ručně nebo zapisujícím nástrojem
  nasazeni_brana   nasazení (npm run nasadit…, wrangler deploy) bez předchozího tools/brana.py v témže sezení
  denik (upozornění)  sezení stahovalo snímky z archivu, ale nezapsalo žádný řádek deníku (denik.py pridej, nalez.py zapis)
Nekontroluje: `doc` bez ověření (čtení pevných polí, tools/cteni.py) a čtení ze zmenšeného snímku – to ukáže až deník a data.
Záznamy se hledají jako u tools/spotreba.py (~/.claude/projects/<složka projektu>, jinde RODOKMEN_PREPISY).
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import spotreba  # noqa: E402
try:
    import slusne  # noqa: E402 – weby, které brzda zná (limity a zákazy)
    _BRZDA = set(slusne.LIMITY) | set(slusne.ZAKAZ)
except Exception:   # noqa: BLE001
    _BRZDA = set()

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA = re.compile(r"(?:^|[\\/])data[\\/](?:(?:zaznamy|svazky|prepisy|dokumenty|mista|zvyrazneni|verejne_otazky)\.json|denik\.jsonl|osoby\.py|opravy\.jsonl)\b")
ZAPIS_NASTROJ = re.compile(r"tools[\\/](?:nalez\.py\s+zapis|zapis\.py|oprava\.py|denik\.py\s+pridej|svazky\.py\s+pridej|otazky\.py\s+(?:pridej|uprav|potvrd|smaz|ze-souboru))")
SOUBORY_DAT = r"(?:(?:zaznamy|svazky|prepisy|dokumenty|mista|zvyrazneni|verejne_otazky)\.json|denik\.jsonl|osoby\.py|opravy\.jsonl)\b"
# sed -i nad datovým souborem, nebo přesměrování přímo do něj (cíl > je ten soubor, ne text dál v příkazu)
SED_PRESMEROVANI = re.compile(r"(?:\bsed\s+-\w*i\b[^|;&]*?|>{1,2}\s*[\"']?)(?:[^\s\"'|;&<>]*[\\/])?data[\\/]" + SOUBORY_DAT)
ARCHIVY = _BRZDA | {"mza.cz", "archives.cz", "portafontium.eu", "digi.nacr.cz", "soapraha.cz", "ahmp.cz", "matricula-online.eu", "soalitomerice.cz", "vychodoceskearchivy.cz", "ceskearchivy.cz", "nacr.cz",
                    "onb.ac.at", "kramerius.mzk.cz", "ndk.cz", "holocaust.cz", "arolsen-archives.org", "pamatnik-terezin.cz",
                    "encyklopedie.brna.cz", "familysearch.org"}
HOST = re.compile(r"https?://([^/\s\"':]+)", re.I)
SIT = re.compile(r"\b(?:curl|wget|Invoke-WebRequest|iwr)\b", re.I)
STAZENI = re.compile(r"tools[\\/](?:aron_img\.py\s+[0-9a-f-]{36}\s+\d|portafontium\.py\s+snimek|litomerice\.py\s+snimek|soal_zoomify\.py|ahmp_scan\.py)")
DENIK = re.compile(r"tools[\\/](?:denik\.py\s+pridej|nalez\.py\s+zapis)")
NASAZENI = re.compile(r"npm\s+run\s+nasadit|wrangler(?:@\S+)?\s+deploy|netlify(?:-cli)?(?:@\S+)?\s+deploy", re.I)
BRANA = re.compile(r"tools[\\/]brana\.py")


def archiv(host):
    h = host.lower()
    return any(h == a or h.endswith("." + a) for a in ARCHIVY)


def kratce(s, n=110):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n] + "…"


def udalosti(path):
    """(čas, nástroj, vstup) ze záznamu, v pořadí."""
    out = []
    try:
        f = open(path, encoding="utf-8")
    except OSError:
        return out
    with f:
        for radek in f:
            try:
                d = json.loads(radek)
            except ValueError:
                continue
            m = d.get("message") or {}
            if d.get("type") != "assistant" or not isinstance(m.get("content"), list):
                continue
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    out.append((d.get("timestamp") or "", b.get("name") or "", b.get("input") or {}))
    return out


def zkontroluj(eventy, pomocnik):
    nalezy, stazeni, denik, brana = [], 0, 0, False
    for cas, nastroj, vstup in eventy:
        cesta = str(vstup.get("file_path") or vstup.get("notebook_path") or "")
        prikaz = str(vstup.get("command") or "").split("\n", 1)[0]   # první řádek: obsah heredocu není příkaz
        if nastroj in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            if DATA.search(cesta) or (pomocnik and re.search(r"(?:^|[\\/])data[\\/]", cesta)):
                druh = "pomocnik_data" if pomocnik else "zapis_dat"
                nalezy.append({"druh": druh, "cas": cas, "nastroj": nastroj, "co": kratce(cesta)})
            continue
        if nastroj not in ("Bash", "PowerShell", "Monitor") or not prikaz:
            continue
        if SED_PRESMEROVANI.search(prikaz):
            nalezy.append({"druh": "pomocnik_data" if pomocnik else "zapis_dat", "cas": cas, "nastroj": nastroj, "co": kratce(prikaz)})
        elif pomocnik and ZAPIS_NASTROJ.search(prikaz):
            nalezy.append({"druh": "pomocnik_data", "cas": cas, "nastroj": nastroj, "co": kratce(prikaz)})
        if SIT.search(prikaz) and "slusne.py" not in prikaz and any(archiv(h) for h in HOST.findall(prikaz)):
            nalezy.append({"druh": "sit_mimo_brzdu", "cas": cas, "nastroj": nastroj, "co": kratce(prikaz)})
        if BRANA.search(prikaz):
            brana = True
        if NASAZENI.search(prikaz) and not brana:
            nalezy.append({"druh": "nasazeni_brana", "cas": cas, "nastroj": nastroj, "co": kratce(prikaz)})
        stazeni += len(STAZENI.findall(prikaz))
        denik += len(DENIK.findall(prikaz))
    return nalezy, stazeni, denik


def sezeni_k_rozboru(slozka, kdo):
    if kdo == "vse":
        return spotreba.sezeni_soubory(slozka)
    return [spotreba.vyber_sezeni(slozka, kdo)]


def rozbor(sezeni):
    nalezy, stazeni, denik = zkontroluj(udalosti(sezeni), pomocnik=False)
    for p in sorted(glob.glob(os.path.join(sezeni[:-len(".jsonl")], "subagents", "agent-*.jsonl"))):
        n, s, d = zkontroluj(udalosti(p), pomocnik=True)
        nalezy += n
        stazeni += s
        denik += d
    upozorneni = []
    if stazeni and not denik:
        upozorneni.append({"druh": "denik", "co": f"stažení snímků {stazeni}×, řádků deníku 0"})
    return {"sezeni": os.path.basename(sezeni)[:8], "porušení": nalezy, "upozornění": upozorneni,
            "stazeni": stazeni, "zapisy_deniku": denik}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sezeni", default="posledni")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    slozka = spotreba.slozka_prepisu()
    if not spotreba.sezeni_soubory(slozka):
        print(f"ve složce {slozka} není žádný záznam sezení (jinou složku zadá RODOKMEN_PREPISY)")
        return 0
    vysledky = [rozbor(s) for s in sezeni_k_rozboru(slozka, a.sezeni)]
    if a.json:
        print(json.dumps(vysledky, ensure_ascii=False, indent=1))
    else:
        for v in vysledky:
            print(f"sezení {v['sezeni']}: porušení {len(v['porušení'])}, upozornění {len(v['upozornění'])} "
                  f"(stažení {v['stazeni']}, řádků deníku {v['zapisy_deniku']})")
            for n in v["porušení"]:
                print(f"  PORUŠENÍ {n['druh']} {n['cas'][:19]} {n['nastroj']}: {n['co']}")
            for n in v["upozornění"]:
                print(f"  upozornění {n['druh']}: {n['co']}")
        print("nekontroluje se: doc bez ověření pevných polí, čtení ze zmenšeného snímku")
    return 1 if any(v["porušení"] for v in vysledky) else 0


if __name__ == "__main__":
    sys.exit(main())
