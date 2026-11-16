#!/usr/bin/env python3
"""Kontextový balíček pro agenta (Fáze C, Q-C3): nejmenší sada údajů, se kterou agent dokončí úkol o jedné osobě. Jen čte.

Použití: python3 -I tools/kontext.py --osoba N --tema identity,books [--limit 6000] [--rules SLOŽKA] [--data SLOŽKA]

Výstup (Markdown, stdout): záznam osoby z data/osoby.py, navázané zápisy (pole `r`), otevřené otázky osoby (ISSUES) a pravidla z vybraných
témat. Témata jsou názvy souborů ve složce pravidel (`skills/rodokmen-agents/rules/`). Stejný vstup dává stejný výstup (řazení podle
id). Nečte fronty ukoly_*.md ani veřejné otázky a nic nezapisuje. Překročí-li balíček --limit znaků, skončí chybou a nic nevypíše
(neořezává mlčky; zúžit se dá výběrem témat). Pravidla se hledají v --rules, jinak v $CLAUDE_PLUGIN_ROOT/skills/rodokmen-agents/rules,
jinak podle pracovni/.plugin_root (zapíše ho SessionStart hook pluginu),
jinak vedle skillu (…/skills/rodokmen-agents/rules).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python -I nepřidává složku skriptu do cesty

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
ZAKAZANE_VSTUPY = ("data/ukoly_*.md (fronty; úkoly dostáváš kartou, ne čtením)", "data/verejne_otazky.json",
                   "portály zakázané skriptům (viz tools/slusne.py, reference/portaly.md)", "data/ mimo tohoto balíčku")


def konec(text):
    print(f"kontext.py: {text}", file=sys.stderr)
    sys.exit(1)


def cesta_pravidel(arg):
    kandidati = [arg] if arg else []
    if not arg:
        if os.environ.get("CLAUDE_PLUGIN_ROOT"):
            kandidati.append(os.path.join(os.environ["CLAUDE_PLUGIN_ROOT"], "skills", "rodokmen-agents", "rules"))
        try:   # hooks/zapis_koren.py zapíše cestu pluginu při startu session (Bash nástroj CLAUDE_PLUGIN_ROOT nemá)
            with open(os.path.join(os.path.dirname(HERE), "pracovni", ".plugin_root"), encoding="utf-8") as f:
                kandidati.append(os.path.join(f.read().strip(), "skills", "rodokmen-agents", "rules"))
        except OSError:
            pass
        kandidati.append(os.path.join(os.path.dirname(os.path.dirname(HERE)), "rodokmen-agents", "rules"))
    for k in kandidati:
        if os.path.isdir(k):
            return k
    konec("složka pravidel nenalezena (zadej --rules nebo nastav CLAUDE_PLUGIN_ROOT)")


def temata(rules):
    return sorted(f[:-3] for f in os.listdir(rules) if f.endswith(".md"))


def bloky_pravidel(rules, tema):
    """[(id, text bloku)] pravidel jednoho tématu v pořadí podle id."""
    with open(os.path.join(rules, tema + ".md"), encoding="utf-8-sig") as f:
        text = f.read().replace("\r\n", "\n")
    out = []
    for m in re.finditer(r"(?ms)^## (R-[A-Z]+-\d{3})\n(.*?)(?=^## |\Z)", text):
        out.append((m.group(1), f"## {m.group(1)}\n{m.group(2).strip()}\n"))
    return sorted(out)


def nacti_osoby(data):
    cesta = os.path.join(data, "osoby.py")
    if not os.path.exists(cesta):
        konec(f"{cesta} neexistuje")
    ns = {}
    with open(cesta, encoding="utf-8-sig") as f:
        exec(f.read(), ns)
    try:   # zápis patří všem svým účastníkům (zaznamy.json → ucastnici), i když ho v `r` nemají
        import ucastnici
        ucastnici.dopln_r(ns, list(nacti_zaznamy(data).values()))
    except Exception:   # noqa: BLE001 – karta osoby musí jít sestavit i bez účastníků
        pass
    return ns


def nacti_zaznamy(data):
    cesta = os.path.join(data, "zaznamy.json")
    if not os.path.exists(cesta):
        return {}
    with open(cesta, encoding="utf-8-sig") as f:
        return {z["klic"]: z for z in json.load(f)}


def osoba_text(n, o):
    r = [f"## Person {n}: {o.get('n', '?')}", f"- years: {o.get('y', '')}", f"- confidence: {o.get('st', '')}"]
    for pole in ("sex", "otec", "matka", "partner"):
        if o.get(pole) not in (None, "", []):
            r.append(f"- {pole}: {o[pole]}")
    for radek in o.get("f", []):
        r.append(f"- fact: {radek}")
    if o.get("note"):
        r.append(f"- note: {o['note']}")
    return "\n".join(r)


def zapisy_text(o, zaznamy):
    r = ["## Linked records"]
    klice = sorted(o.get("r", []))
    if not klice:
        r.append("(none)")
    for k in klice:
        z = zaznamy.get(k)
        if not z:
            r.append(f"- {k}: (not in zaznamy.json)")
            continue
        r.append(f"- {k}: {z.get('nazev', '')} | {z.get('datum', '')} | book {z.get('svazek', '')}, image {z.get('snimek', '')}")
        if z.get("shrnuti"):
            r.append(f"  summary: {z['shrnuti']}")
    return "\n".join(r)


def otazky_text(n, issues):
    r = ["## Open questions of the person"]
    mine = [i for i in issues if i.get("k") == n and str(i.get("stav", "")).lower().startswith(("otev", "hypot"))]
    if not mine:
        r.append("(none)")
    for i in mine:
        r.append(f"- [{i.get('stav')}] {i.get('otazka', '')} {i.get('text', '')}".rstrip())
    return "\n".join(r)


def sestav(osoba, tema, rules, data):
    ns = nacti_osoby(data)
    P = ns.get("P", {})
    if osoba not in P:
        konec(f"osoba {osoba} není v data/osoby.py")
    platna = temata(rules)
    vybrana = sorted(set(t.strip() for t in tema.split(",") if t.strip()))
    if not vybrana:
        konec(f"chybí --tema; platná témata: {', '.join(platna)}")
    neznama = [t for t in vybrana if t not in platna]
    if neznama:
        konec(f"neznámé téma {', '.join(neznama)}; platná témata: {', '.join(platna)}")
    casti = [f"# Context package: person {osoba}", osoba_text(osoba, P[osoba]), zapisy_text(P[osoba], nacti_zaznamy(data)),
             otazky_text(osoba, ns.get("ISSUES", []))]
    pravidla = ["## Rules"]
    for t in vybrana:
        for _, blok in bloky_pravidel(rules, t):
            pravidla.append(blok)
    casti.append("\n".join(pravidla))
    casti.append("## Forbidden inputs\n" + "\n".join(f"- {z}" for z in ZAKAZANE_VSTUPY))
    return "\n\n".join(casti) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--osoba", type=int, required=True)
    ap.add_argument("--tema", default="")
    ap.add_argument("--limit", type=int, default=12000)
    ap.add_argument("--rules")
    ap.add_argument("--data", default=DATA)
    a = ap.parse_args(argv)
    text = sestav(a.osoba, a.tema, cesta_pravidel(a.rules), a.data)
    if len(text) > a.limit:
        konec(f"balíček má {len(text)} znaků a překračuje limit {a.limit}; zúž výběr témat nebo zvyš --limit")
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
