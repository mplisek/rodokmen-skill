#!/usr/bin/env python3
"""Commit dokončené práce bez agenta (analyza/navrh-optimalizace.md, etapa E2): přesně ty soubory, které zápis výsledku změnil, na větvi,
která je právě aktivní, s jednotnou zprávou. Nikdy nepushuje, nepřepíná větev, nepřidává nic navíc.

Použití (z kořene projektu):
  python3 -I tools/commit.py U-0101 [--vetev migrace-test] [--zprava "…"] [--nanecisto]
        soubory a zprávu vezme z historie úkolu (události „zapsano“ od tools/zapis_vysledku.py, které ještě nejsou v commitu)
  python3 -I tools/commit.py --soubory data/ukoly_na_noc.md,data/ukoly_historie.jsonl --zprava "Fronty: směrování nových úkolů"
        změny front bez výsledku čtení, role účastníků, opravný řádek deníku, hodnocení měření; jen soubory v data/ a mereni/
        a snímky rodinných dokumentů z data/dokumenty.json (zdroje/<img>.jpg, vyrezy/<img>.jpg, jak je uloží vyrez.py)

Pravidla: zpráva říká, co bylo zjištěno a kde, bez čísel úkolů a jmen agentů; --vetev (je-li zadána) se musí shodovat s aktivní větví,
jinak se necommituje; soubor beze změny se přeskočí; nic ke commitu = kód 1. Podpis (řádek Co-Authored-By) jednotně z data/rezim.json
→ "commit_podpis", jinak žádný.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fronta  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UKOL = re.compile(r"U-\d{4}")
PROCES = re.compile(r"(?i)\b(orchestr[aá]tor|researcher|verifier|fixer|committer|subagent|pomocník)\w*")


def git(*a, check=True):
    r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        sys.exit(f"git {' '.join(a[:2])} selhal: {(r.stderr or r.stdout).strip()}")
    return r


def bezpecna(p):
    p = p.replace("\\", "/")
    return bool(p) and not p.startswith(("/", "-")) and ".." not in p.split("/") and ":" not in p and not p.startswith("pracovni/")


def zmenene(soubory):
    r = git("status", "--porcelain", "--", *soubory)
    return sorted({radek[3:].strip().strip('"').split(" -> ")[-1] for radek in r.stdout.splitlines() if radek.strip()})


def z_historie(ukol):
    """Soubory a zpráva z událostí „zapsano“ úkolu (i jeho dřívějších částí)."""
    ud = [e for e in fronta.nacti_historii() if e.get("udalost") == "zapsano" and e.get("id") == ukol]
    return sorted({s for e in ud for s in e.get("soubory") or []}), (ud[-1].get("zprava") if ud else None)


def snimky_dokumentu():
    """zdroje/<img>.jpg a vyrezy/<img>.jpg dokumentů z data/dokumenty.json (vyrez.py je uloží tam, mimo data/)."""
    try:
        with open(os.path.join(ROOT, "data", "dokumenty.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return set()
    imgs = {x.get("img") for x in d if isinstance(x, dict)} if isinstance(d, list) else set()
    return {f"{s}/{i}.jpg" for i in imgs if isinstance(i, str) and re.fullmatch(r"[\w.-]+", i) for s in ("zdroje", "vyrezy")}


def podpis():
    try:
        with open(os.path.join(ROOT, "data", "rezim.json"), encoding="utf-8") as f:
            p = json.load(f).get("commit_podpis")
        return p if isinstance(p, str) and p.strip() else None
    except (OSError, ValueError):
        return None


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ukol", nargs="?"); ap.add_argument("--vetev"); ap.add_argument("--zprava"); ap.add_argument("--soubory")
    ap.add_argument("--nanecisto", action="store_true")
    a = ap.parse_args(argv)
    if a.ukol:
        if not UKOL.fullmatch(a.ukol):
            sys.exit("ID úkolu ve tvaru U-0042")
        soubory, zprava = z_historie(a.ukol)
        if not soubory:
            sys.exit(f"{a.ukol}: v historii není žádný zápis výsledku (tools/zapis_vysledku.py); není co commitovat")
        zprava = a.zprava or zprava
    else:
        soubory = [x.strip().replace("\\", "/") for x in (a.soubory or "").split(",") if x.strip()]
        zprava = a.zprava
        snimky = snimky_dokumentu()
        if not soubory or any(not (s.startswith(("data/", "mereni/")) or s in snimky) for s in soubory):
            sys.exit("bez úkolu: --soubory jen z data/ nebo mereni/, nebo snímek rodinného dokumentu z data/dokumenty.json "
                     "(zdroje/<img>.jpg, vyrezy/<img>.jpg); oddělené čárkou, s --zprava")
    if not zprava or not zprava.strip():
        sys.exit("chybí --zprava (co bylo zjištěno a kde)")
    if UKOL.search(zprava) or PROCES.search(zprava):
        sys.exit("ODMÍTNUTO: zpráva commitu je o výsledku, ne o postupu: bez čísel úkolů (U-…) a jmen agentů")
    spatne = [s for s in soubory if not bezpecna(s)]
    if spatne:
        sys.exit("ODMÍTNUTO: nepřípustná cesta " + ", ".join(spatne))
    vetev = git("branch", "--show-current").stdout.strip()
    if not vetev:
        sys.exit("ODMÍTNUTO: HEAD není na větvi; větev nepřepínám, rozhodne uživatel")
    if a.vetev and a.vetev != vetev:
        sys.exit(f"ODMÍTNUTO: aktivní větev je {vetev}, čekala se {a.vetev}; větev nepřepínám, rozhodne uživatel")
    ignor = [x for x in git("check-ignore", "--", *soubory, check=False).stdout.splitlines() if x.strip()]
    if ignor:   # git status je neukáže a commit by je tiše vynechal
        sys.exit("ODMÍTNUTO, nic se necommitlo: git tyto soubory ignoruje (.gitignore): " + ", ".join(ignor)
                 + "; o výjimce v .gitignore rozhodne uživatel, nebo patří do pracovni/")
    k = zmenene(soubory)
    if not k:
        print("není co commitovat: soubory jsou beze změny")
        return 1
    if a.nanecisto:
        print(f"větev {vetev}: {zprava}\n  " + "\n  ".join(k))
        return 0
    git("add", "--", *k)
    zpravy = ["-m", zprava.strip()] + (["-m", podpis()] if podpis() else [])
    git("commit", *zpravy, "--", *k)
    h = git("rev-parse", "--short", "HEAD").stdout.strip()
    print(f"commit {h} na větvi {vetev}: {zprava.strip()} ({len(k)} souborů)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
