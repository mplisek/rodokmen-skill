#!/usr/bin/env python3
"""Kontrola anonymity před pushem do veřejného repozitáře (Fáze E, ADR 0008). Nástroj údržby repozitáře skillu, do projektů se nekopíruje.

Údaje z projektu (jména, příjmení, čísla osob a úkolů) se snadno dostanou do příkladů, testů nebo zpráv commitů. Skript hledá řetězce
z **lokálního seznamu** `.anonymita-seznam` (je v .gitignore, nepatří do gitu – sám by jména prozradil) a prochází **všechny přidané řádky
a zprávy všech commitů, které se budou pushovat**, ne jen výsledný stav: chytí i jméno, které je v pozdějším commitu už odstraněné, ale
zůstalo v historii. **Nikdy nic nepřepisuje ani nemění historii**; o tom, co s nálezem, rozhoduje uživatel.

Použití (z repozitáře): python3 -I scripts/anonymita.py <příkaz>
  pred-pushem [--vuci origin/main] [--seznam SOUBOR]   zkontroluje commity vuci..HEAD (kód 1 při shodě)
  pre-push [--vuci REF] [--seznam SOUBOR]               pro git hook: rozsah čte ze stdin (řádky „<ref> <sha> <vzdálený ref> <sha>“)
  nainstaluj                                            nastaví core.hooksPath na .githooks (hook pre-push); spouští uživatel
  navrhni-z-projektu <složka projektu> [--do SOUBOR]    kandidáti na seznam z data/osoby.py projektu (na stdout, do repozitáře nic)

Seznam: jeden řetězec na řádek (bez ohledu na velikost písmen a diakritiku; „Novák“ najde i „Novákové“), `re:<výraz>` je regulární
výraz, `!cesta/` vyjme soubory pod cestou, `#` je komentář. Vzor formátu: .anonymita-seznam.priklad. Bez seznamu skript jen varuje.
"""
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

NULY = "0" * 40
JMENA = {"jan", "josef", "marie", "anna", "karel", "frantisek", "vaclav", "petr", "pavel", "eva", "jana", "jiri", "martin", "tomas",
         "katerina", "barbora", "magdalena", "alois", "antonin", "emilie", "frantiska", "jakub", "ludmila", "terezie", "vojtech", "matej",
         "johann", "maria", "franz", "joseph", "anton", "wenzel", "novak", "novakova"}


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def git(*a, cwd=None, check=True):
    r = subprocess.run(["git", "-c", "core.quotepath=false", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        sys.exit(f"git {' '.join(a)} selhal: {r.stderr.strip()}")
    return r.stdout


def koren():
    return git("rev-parse", "--show-toplevel").strip()


def nacti_seznam(cesta):
    """(vzory [(raw, regex)], vyjmuté cesty) nebo None, když seznam neexistuje."""
    if not os.path.isfile(cesta):
        return None
    vzory, vyjmout = [], []
    for radek in open(cesta, encoding="utf-8-sig").read().splitlines():
        r = radek.strip()
        if not r or r.startswith("#"):
            continue
        if r.startswith("!"):
            vyjmout.append(r[1:].strip().replace("\\", "/"))
        elif r.startswith("re:"):
            vzory.append(("re:***", re.compile(r[3:], re.I)))
        else:
            vzory.append((r[:3] + "***", re.compile(re.escape(norm(r)))))
    return vzory, vyjmout


def shoda(text, vzory):
    n = norm(text)
    return [raw for raw, rx in vzory if rx.search(n)]


def zmeny_commitu(sha):
    """[(soubor, číslo řádku, přidaný text)] z diffu jednoho commitu (bez kontextu)."""
    out, soubor, radek = [], None, 0
    for l in git("show", "--format=", "--unified=0", "--no-color", "--no-ext-diff", sha).split("\n"):
        if l.startswith("+++ "):
            soubor = l[6:] if l.startswith("+++ b/") else None
        elif l.startswith("@@"):
            m = re.search(r"\+(\d+)", l)
            radek = int(m.group(1)) if m else 0
        elif l.startswith("+") and not l.startswith("+++"):
            if soubor:
                out.append((soubor, radek, l[1:]))
            radek += 1
    return out


def vyjmuto(soubor, vyjmout):
    return any(soubor == v.rstrip("/") or soubor.startswith(v.rstrip("/") + "/") for v in vyjmout)


def zkontroluj(commity, seznam):
    nalezy = []
    vzory, vyjmout = seznam
    for sha in commity:
        kratce = sha[:7]
        zprava = git("log", "-1", "--format=%B", sha)
        for m in shoda(zprava, vzory):
            nalezy.append((kratce, "zpráva commitu", 0, m))
        for soubor, radek, text in zmeny_commitu(sha):
            if vyjmuto(soubor, vyjmout):
                continue
            for m in shoda(text, vzory):
                nalezy.append((kratce, soubor, radek, m))
    return nalezy


def vypis(nalezy, commitu):
    for kratce, soubor, radek, m in nalezy:
        kde = soubor if soubor == "zpráva commitu" else f"{soubor}:{radek}"
        print(f"CHYBA: commit {kratce}: {kde} obsahuje řetězec ze seznamu ({m})" if soubor != "zpráva commitu"
              else f"CHYBA: commit {kratce}: zpráva commitu obsahuje řetězec ze seznamu ({m})")
    if nalezy:
        print(f"anonymita: {len(nalezy)} nálezů v {commitu} commitech; nic neopravuji a historii nepřepisuji, o řešení rozhoduje uživatel "
              "(nový commit odstraní řetězec jen ze stavu, v historii zůstane)")
    else:
        print(f"anonymita: {commitu} commitů zkontrolováno, bez nálezu")


def seznam_cesta(a, kor):
    return a.seznam or os.path.join(kor, ".anonymita-seznam")


def rozsah(vuci, tip="HEAD"):
    if vuci and git("rev-parse", "--verify", "--quiet", vuci + "^{commit}", check=False).strip():
        return [c for c in git("rev-list", "--reverse", f"{vuci}..{tip}").split() if c]
    return [c for c in git("rev-list", "--reverse", tip).split() if c]


def cmd_pred_pushem(a):
    kor = koren()
    sez = nacti_seznam(seznam_cesta(a, kor))
    if sez is None:
        print(f"POZOR: seznam {seznam_cesta(a, kor)} neexistuje, kontrola anonymity neproběhla (vzor: .anonymita-seznam.priklad).")
        return 0
    commity = rozsah(a.vuci)
    nalezy = zkontroluj(commity, sez)
    vypis(nalezy, len(commity))
    return 1 if nalezy else 0


def cmd_pre_push(a):
    kor = koren()
    sez = nacti_seznam(seznam_cesta(a, kor))
    if sez is None:
        print(f"POZOR: seznam {seznam_cesta(a, kor)} neexistuje, kontrola anonymity neproběhla.", file=sys.stderr)
        return 0
    commity = []
    for radek in sys.stdin.read().splitlines():
        p = radek.split()
        if len(p) < 4 or p[1] == NULY:
            continue
        vzdaleny = p[3]
        if vzdaleny != NULY:
            commity += [c for c in git("rev-list", "--reverse", f"{vzdaleny}..{p[1]}", check=False).split() if c]
        else:
            commity += rozsah(a.vuci, p[1])
    commity = list(dict.fromkeys(commity))
    nalezy = zkontroluj(commity, sez)
    if nalezy:
        sys.stdout = sys.stderr
    vypis(nalezy, len(commity))
    return 1 if nalezy else 0


def cmd_nainstaluj(a):
    kor = koren()
    git("config", "core.hooksPath", ".githooks", cwd=kor)
    print("nastaveno core.hooksPath=.githooks (hook pre-push volá scripts/anonymita.py); vrátit: git config --unset core.hooksPath")
    return 0


def cmd_navrh(a):
    osoby = os.path.join(a.projekt, "data", "osoby.py")
    if not os.path.isfile(osoby):
        sys.exit(f"{osoby} neexistuje.")
    slova = Counter()
    for jmeno in re.findall(r"\bn=\"([^\"]+)\"", open(osoby, encoding="utf-8-sig").read()):
        for s in re.findall(r"[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][^\W\d_]{3,}", jmeno):
            if norm(s) not in JMENA:
                slova[s] += 1
    vystup = ["# Kandidáti na .anonymita-seznam z dat projektu (prořezat: ponechat jen to, co nesmí do veřejného repozitáře)"]
    vystup += [s for s, _ in sorted(slova.items(), key=lambda x: (-x[1], x[0]))]
    text = "\n".join(vystup) + "\n"
    if a.do:
        with open(a.do, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"zapsáno {len(slova)} kandidátů do {a.do}")
    else:
        sys.stdout.write(text)
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    import argparse
    ap = argparse.ArgumentParser(prog="anonymita.py", add_help=False)
    sub = ap.add_subparsers(dest="prikaz", required=True)
    for jmeno, fn in (("pred-pushem", cmd_pred_pushem), ("pre-push", cmd_pre_push)):
        p = sub.add_parser(jmeno)
        p.add_argument("--vuci", default="origin/main")
        p.add_argument("--seznam")
        p.set_defaults(fn=fn)
    sub.add_parser("nainstaluj").set_defaults(fn=cmd_nainstaluj)
    p = sub.add_parser("navrhni-z-projektu")
    p.add_argument("projekt")
    p.add_argument("--do")
    p.set_defaults(fn=cmd_navrh)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
