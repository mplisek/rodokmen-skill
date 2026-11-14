#!/usr/bin/env python3
"""Zpráva o novinkách v originále (Fáze C, Q-C2, 4.4 návrhu). Nástroj údržby repozitáře skillu, do projektů se nekopíruje.

Použití: python3 -I scripts/sync_report.py [--repo SLOŽKA] [--upstream REF] [--json]
Čte jen lokální git (nejdřív `git fetch upstream`; síť ani GitHub API skript nepoužívá). Vypíše: verzi originálu a forku, nové commity
`HEAD..upstream/main`, dotčené soubory, překryv (soubory změněné od společného předka i v originále, i ve forku) a pravidla z `rules/`,
jejichž zdrojový oddíl se v originále změnil (k přezkoumání, viz pravidla.py). Nic nesloučí, nic nepushne a do originálu nezapisuje.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pravidla  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZRCADLO = "skills/rodokmen"
RULES = "skills/rodokmen-agents/rules"
UPSTREAM = "refs/remotes/upstream/main"


def git(repo, *a, check=True):
    r = subprocess.run(["git", "-c", "core.quotepath=false", *a], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        sys.exit(f"git {' '.join(a)} selhal: {r.stderr.strip()}")
    return r.stdout if r.returncode == 0 else None


def verze(repo, ref):
    t = git(repo, "show", f"{ref}:{ZRCADLO}/VERZE", check=False)
    return t.strip() if t else None


def radky(text):
    return [x for x in (text or "").split("\n") if x]


def dotcena_pravidla(repo, upstream):
    rules = os.path.join(repo, RULES)
    if not os.path.isdir(rules):
        return []
    pr, _ = pravidla.nacti_pravidla(rules)
    zdroje = pravidla.nacti_zdroje(rules)
    out = []
    for rid, p in sorted(pr.items()):
        zdroj = p.get("source", "")
        if not zdroj or zdroj == "fork" or rid not in zdroje:
            continue
        soubor, _, nadpis = zdroj.partition("#")
        text = git(repo, "show", f"{upstream}:{ZRCADLO}/{soubor}", check=False)
        if text is None:
            out.append(rid)
            continue
        text = text.replace("\r\n", "\n")
        if nadpis:
            s = pravidla.sekce(text, nadpis)
            ted = pravidla.otisk(s) if s is not None else None
        else:
            ted = pravidla.otisk(text)
        if ted != zdroje[rid].get("checked"):
            out.append(rid)
    return out


def sestav(repo, upstream):
    if git(repo, "rev-parse", "--verify", "--quiet", upstream + "^{commit}", check=False) is None:
        sys.exit(f"Chybí {upstream}: přidej remote `upstream` (sarsonj/rodokmen-skill) a spusť `git fetch upstream`.")
    zaklad = git(repo, "merge-base", "HEAD", upstream).strip()
    commity = []
    for r in radky(git(repo, "log", "--reverse", "--format=%H%x1f%s", f"HEAD..{upstream}")):
        sha, _, predmet = r.partition("\x1f")
        commity.append({"sha": sha[:9], "predmet": predmet})
    soubory = radky(git(repo, "diff", "--name-only", zaklad, upstream))
    nase = set(radky(git(repo, "diff", "--name-only", zaklad, "HEAD")))
    return {"verze_originalu": verze(repo, upstream), "verze_forku": verze(repo, "HEAD"), "commity": commity, "soubory": soubory,
            "prekryv": sorted(set(soubory) & nase), "dotcena_pravidla": dotcena_pravidla(repo, upstream)}


def vypis(d):
    print(f"Verze originálu: {d['verze_originalu']}   verze forku: {d['verze_forku']}")
    print(f"\nNové commity v originále ({len(d['commity'])}):")
    for c in d["commity"]:
        print(f"  {c['sha']}  {c['predmet']}")
    print(f"\nDotčené soubory ({len(d['soubory'])}):")
    for s in d["soubory"]:
        print(f"  {s}{'   ← překryv s forkem' if s in d['prekryv'] else ''}")
    print(f"\nPravidla k přezkoumání ({len(d['dotcena_pravidla'])}): {', '.join(d['dotcena_pravidla']) or '–'}")
    if d["commity"]:
        print("\nDál: u každé položky rozhodni převzít / upravit / vynechat; slučuje se `git merge upstream/main`, pak `pravidla.py overit`.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--upstream", default=UPSTREAM)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    d = sestav(a.repo, a.upstream)
    print(json.dumps(d, ensure_ascii=False, indent=1)) if a.json else vypis(d)


if __name__ == "__main__":
    main()
