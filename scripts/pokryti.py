#!/usr/bin/env python3
"""Kontrola pokrytí testy (Fáze D, Q-D2, Q-D3, Q-D5). Nástroj údržby repozitáře skillu, do projektů se nekopíruje.

Použití: python3 -I scripts/pokryti.py [--repo SLOŽKA] [--json]

Čtyři kontroly:
  nástroje  každý skills/rodokmen/tools/*.py je zmíněn v nějakém tests/**/test_*.py, nebo je v tests/e2e/vyjimky.json s důvodem
            ({"nastroj.py": "důvod"}, aspoň 10 znaků); výjimka pro neexistující nástroj je chyba
  stránky   každá trasa z template/web/src/pages (soubor .astro; [x] → *, index → složka) je v tests/e2e/stranky.json
            ([{"vzor": "/osoba/*", "test": "test_jmeno"}]) a ten test existuje; záznam neexistující trasy je chyba
  jazyk     anglická vrstva (skills/rodokmen-agents, agents) je anglicky (jazyk.py); bez ní „preskoceno“
  pravidla  pravidla mají platné otisky zdrojů (pravidla.py overit); bez nich „preskoceno“
Jen hlásí: nic nezapisuje a nezakládá úkoly (ty zakládá orchestrátor z JSONu přes fronta.py). Kód 0 = vše pokryto, 1 = nepokryto.
"""
import argparse
import json
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MIN_DUVOD = 10


def cti_json(cesta, vychozi):
    if not os.path.isfile(cesta):
        return vychozi
    with open(cesta, encoding="utf-8-sig") as f:
        return json.load(f)


def texty_testu(*slozky):
    """{jméno testu: text} ze všech test_*.py ve složkách (včetně podsložek, jako repozitářové tests/)."""
    out = {}
    for slozka in slozky:
        for koren, _, soubory in os.walk(slozka):
            for j in sorted(soubory):
                if j.startswith("test_") and j.endswith(".py"):
                    with open(os.path.join(koren, j), encoding="utf-8-sig", errors="replace") as f:
                        out[j[:-3]] = f.read()
    return out


def kontrola_nastroju(skill, testy, vyjimky):
    nastroje = sorted(f for f in os.listdir(os.path.join(skill, "tools")) if f.endswith(".py")) if os.path.isdir(os.path.join(skill, "tools")) else []
    texty = "\n".join(testy.values())
    bez_testu, zpravy = [], []
    for n in nastroje:
        stem = n[:-3]
        if re.search(r"(?<![\w])" + re.escape(stem) + r"(?![\w])", texty):
            continue
        duvod = str(vyjimky.get(n, "")).strip()
        if len(duvod) >= MIN_DUVOD:
            continue
        bez_testu.append(n)
        zpravy.append(f"nástroj {n} nemá test (zmínku v tests/**/test_*.py nebo výjimku s důvodem v tests/e2e/vyjimky.json)")
    for n in sorted(set(vyjimky) - set(nastroje)):
        zpravy.append(f"výjimka {n} v vyjimky.json: nástroj neexistuje")
    for n, duvod in sorted(vyjimky.items()):
        if n in nastroje and len(str(duvod).strip()) < MIN_DUVOD:
            zpravy.append(f"výjimka {n} v vyjimky.json nemá důvod (aspoň {MIN_DUVOD} znaků)")
    return bez_testu, zpravy


def trasy(stranky):
    out = set()
    for koren, _, soubory in os.walk(stranky):
        for j in soubory:
            if not j.endswith(".astro"):
                continue
            rel = os.path.relpath(os.path.join(koren, j[:-6]), stranky).replace("\\", "/")
            casti = [re.sub(r"\[[^\]]*\]", "*", c) for c in rel.split("/")]
            if casti[-1] == "index":
                casti = casti[:-1]
                out.add("/" + "/".join(casti) + ("/" if casti else ""))
            else:
                out.add("/" + "/".join(casti))
    return out


def kontrola_stranek(skill, testy, zaznamy):
    existuji = trasy(os.path.join(skill, "template", "web", "src", "pages"))
    zname = {z.get("vzor"): z.get("test") for z in zaznamy if isinstance(z, dict)}
    bez, zpravy = sorted(existuji - set(zname)), []
    zpravy += [f"trasa {t} nemá záznam v tests/e2e/stranky.json" for t in bez]
    for vzor, test in sorted(zname.items(), key=lambda x: str(x[0])):
        if vzor not in existuji:
            zpravy.append(f"záznam {vzor} v stranky.json: taková trasa neexistuje")
        elif test not in testy:
            zpravy.append(f"záznam {vzor}: test {test} neexistuje (tests/{test}.py)")
    return bez, zpravy


def spust(repo, skript, *args):
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(HERE, skript), *args], cwd=repo, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode == 0, "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])


def sestav(repo):
    skill = os.path.join(repo, "skills", "rodokmen")
    testy_slozka = os.path.join(skill, "tests")
    testy = texty_testu(testy_slozka, os.path.join(repo, "tests"))
    e2e = os.path.join(testy_slozka, "e2e")
    nepokryto = []
    nastroje, z = kontrola_nastroju(skill, testy, cti_json(os.path.join(e2e, "vyjimky.json"), {}))
    nepokryto += z
    stranky, z = kontrola_stranek(skill, testy, cti_json(os.path.join(e2e, "stranky.json"), []))
    nepokryto += z
    vrstva = [p for p in (os.path.join(repo, "skills", "rodokmen-agents"), os.path.join(repo, "agents")) if os.path.isdir(p)]
    jazyk = pravidla = "preskoceno"
    if vrstva:
        ok, vystup = spust(repo, "jazyk.py", *vrstva)
        jazyk = "ok" if ok else "chyba"
        if not ok:
            nepokryto.append("jazyk: anglická vrstva není anglicky\n  " + vystup.replace("\n", "\n  "))
    rules = os.path.join(repo, "skills", "rodokmen-agents", "rules")
    if os.path.isdir(rules):
        ok, vystup = spust(repo, "pravidla.py", "overit", "--rules", rules, "--zrcadlo", skill)
        pravidla = "ok" if ok else "chyba"
        if not ok:
            nepokryto.append("pravidla: " + vystup.replace("\n", "\n  "))
    return {"nastroje": nastroje, "stranky": stranky, "jazyk": jazyk, "pravidla": pravidla, "nepokryto": nepokryto}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    d = sestav(a.repo)
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        print(f"nástroje bez testu: {len(d['nastroje'])}   trasy bez záznamu: {len(d['stranky'])}   jazyk: {d['jazyk']}   pravidla: {d['pravidla']}")
        for z in d["nepokryto"]:
            print("NEPOKRYTO:", z)
        print("pokryto" if not d["nepokryto"] else f"nepokryto: {len(d['nepokryto'])} položek")
    return 1 if d["nepokryto"] else 0


if __name__ == "__main__":
    sys.exit(main())
