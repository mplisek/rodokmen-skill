#!/usr/bin/env python3
"""Vytěží rodinný strom (GEDCOM .ged z MyHeritage, Geni, FamilySearch…) pro rodokmen.

Použití (z kořene projektu):
  python3 -I tools/ged_import.py dokumenty/strom.ged                 -> seznam osob (id | jméno | narození)
  python3 -I tools/ged_import.py dokumenty/strom.ged "Jméno Příjmení" -> předci této osoby s Kekulého čísly
                                                                        (1 = ona, 2 = otec, 3 = matka…), všechny
                                                                        události, poznámky a FRONTA ZÁPISŮ k vyhledání
  … "Jméno Příjmení" --osoby   -> totéž jako kostra pro data/osoby.py (stav "fam", ke kontrole a doplnění)

Fronta zápisů: u každého předka nejmladší známá událost s místem (úmrtí, pak sňatek, pak narození) –
úmrtní a oddací zápisy uvádějí datum a místo narození i rodiče, proto se hledá od nejmladšího zápisu.
E-maily a adresy ze stromu se nevypisují.
"""
import datetime, re, sys
from collections import defaultdict

EVENTS = {"BIRT": "*", "CHR": "* (křest)", "DEAT": "†", "BURI": "† (pohřeb)", "MARR": "×"}
MONTHS = {m: i for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), 1)}


def read(path):
    raw = open(path, "rb").read().decode("utf-8", "replace").lstrip("﻿")   # MyHeritage občas rozsekne znak na hranici CONC
    recs, cur, stack = {}, None, []
    for line in raw.splitlines():
        m = re.match(r"\s*(\d+)\s+(@[^@]+@\s+)?(\S+)\s?(.*)$", line)
        if not m:
            continue
        lvl, xref, tag, val = int(m.group(1)), (m.group(2) or "").strip(), m.group(3), m.group(4)
        if lvl == 0:
            cur = {"_id": xref, "_type": tag, "_sub": []} if xref else None
            if cur:
                recs[xref] = cur
            stack = [cur]
            continue
        if cur is None:
            continue
        stack = stack[:lvl]
        parent = stack[-1] if stack else cur
        if tag in ("CONC", "CONT") and parent is not None:
            parent["val"] = parent.get("val", "") + ("\n" if tag == "CONT" else "") + val
            stack.append(parent)
            continue
        node = {"tag": tag, "val": val, "_sub": []}
        parent["_sub"].append(node)
        stack.append(node)
    return recs


def sub(node, tag):
    return [n for n in node["_sub"] if n["tag"] == tag]


def first(node, tag, default=""):
    s = sub(node, tag)
    return s[0].get("val", "").strip() if s else default


def cz_date(d):
    """'14 FEB 1890' -> '14. 2. 1890', 'ABT 1850' -> 'asi 1850'."""
    d = d.strip()
    pre = ""
    for k, v in (("ABT", "asi "), ("EST", "asi "), ("CAL", "asi "), ("BEF", "před "), ("AFT", "po "), ("BET", "mezi ")):
        if d.startswith(k):
            pre, d = v, d[len(k):].strip()
    d = d.replace(" AND ", " a ")
    def one(m):
        day, mon, yr = m.group(1), m.group(2), m.group(3)
        return f"{day + '. ' if day else ''}{str(MONTHS[mon]) + '. ' if mon else ''}{yr}"
    d = re.sub(r"(?:(\d{1,2}) )?(?:(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) )?(\d{3,4})", one, d)
    return pre + d


def year(d):
    m = re.search(r"\d{4}", d or "")
    return int(m.group()) if m else None


def name(ind):
    n = first(ind, "NAME").replace("/", "").strip()
    return re.sub(r"\s+", " ", n) or "(beze jména)"


def events(ind, recs):
    out = []
    for n in ind["_sub"]:
        if n["tag"] in EVENTS:
            d, p = first(n, "DATE"), first(n, "PLAC")
            extra = first(n, "CAUS")
            out.append((n["tag"], cz_date(d) if d else "", p, extra))
    for fam_id in [n["val"] for n in sub(ind, "FAMS")]:
        fam = recs.get(fam_id.strip())
        if not fam:
            continue
        spouse = [recs.get(n["val"].strip()) for n in fam["_sub"] if n["tag"] in ("HUSB", "WIFE") and n["val"].strip() != ind["_id"]]
        for m in sub(fam, "MARR"):
            d, p = first(m, "DATE"), first(m, "PLAC")
            out.append(("MARR", cz_date(d) if d else "", p, name(spouse[0]) if spouse and spouse[0] else ""))
    return out


def parents(ind, recs):
    for n in sub(ind, "FAMC"):
        fam = recs.get(n["val"].strip())
        if fam:
            h, w = first(fam, "HUSB"), first(fam, "WIFE")
            return recs.get(h), recs.get(w)
    return None, None


def find(recs, query):
    q = query.lower().split()
    hits = [r for r in recs.values() if r["_type"] == "INDI" and all(w in name(r).lower() for w in q)]
    if not hits:
        sys.exit(f"Osoba „{query}“ ve stromu není. Spusť bez jména pro seznam osob.")
    if len(hits) > 1:
        print("Víc osob odpovídá, použij id místo jména:", file=sys.stderr)
        for h in hits:
            print(f"  {h['_id']} | {name(h)}", file=sys.stderr)
        sys.exit(1)
    return hits[0]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    recs = read(sys.argv[1])
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    as_py = "--osoby" in sys.argv
    if not args:
        for r in recs.values():
            if r["_type"] == "INDI":
                b = next((e for e in events(r, recs) if e[0] == "BIRT"), None)
                print(f"{r['_id']} | {name(r)} | {('* ' + b[1] + ' ' + b[2]).strip() if b and (b[1] or b[2]) else ''}")
        return
    start = recs.get(args[0]) or find(recs, args[0])
    tree, todo = {1: start}, [1]
    while todo:
        k = todo.pop(0)
        f, m = parents(tree[k], recs)
        for kk, p in ((2 * k, f), (2 * k + 1, m)):
            if p:
                tree[kk] = p
                todo.append(kk)
    queue = []
    if as_py:
        print("P = {")
    for k in sorted(tree):
        ind = tree[k]
        ev = events(ind, recs)
        facts = []
        for tag, d, p, extra in ev:
            if tag == "MARR":
                facts.append(" ".join(x for x in ("×", d, p, extra) if x))
            elif d or p:   # příčinu úmrtí jen do výpisu, ne do kostry dat (zdravotní údaj)
                facts.append(" ".join(x for x in (EVENTS[tag], d, p) if x) + (f" ({extra})" if extra and not as_py else ""))
        facts += [first(n, "OCCU") or n.get("val", "") for n in sub(ind, "OCCU")]
        notes = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", n.get("val", ""))).strip() for n in sub(ind, "NOTE")]
        notes = [n for n in notes if n]
        b = next((year(d) for t, d, p, x in ev if t == "BIRT"), None)
        dd = next((year(d) for t, d, p, x in ev if t == "DEAT"), None)
        y = f"{b}–{dd}" if b and dd else (f"* {b}" if b else (f"† {dd}" if dd else ""))
        if as_py:
            note = " ".join(notes)   # !r = platný Python i pro uvozovky a „\“ ve jménech a poznámkách (osoby.py se spouští přes exec)
            print(f' {k}: dict(n={name(ind)!r}, y={y!r}, st="fam", f={facts!r}, r=[]' + (f', note={note[:300]!r}' if note else "") + "),")
        else:
            print(f"\n{k} | {name(ind)} | {y}")
            for f in facts:
                print("   ", f)
            for n in notes:
                print("    pozn.:", n.replace("\n", " ")[:600])
        dated = [(t, d, p) for t, d, p, x in ev if p or d]
        for pref in ("DEAT", "BURI", "MARR", "BIRT", "CHR"):
            hit = [e for e in dated if e[0] == pref and e[2]]
            if hit:
                t, d, p = max(hit, key=lambda e: year(e[1]) or 0)
                queue.append((k, name(ind), {"DEAT": "úmrtí", "BURI": "úmrtí", "MARR": "sňatek"}.get(t, "narození"), d, p))
                break
    if as_py:
        print("}")
        return
    print("\nFRONTA ZÁPISŮ (nejmladší známá událost s místem; lhůty pro archiv: narození 100, sňatky 75, úmrtí 30 let):")
    now = datetime.date.today().year
    for k, n, what, d, p in queue:
        y = year(d)
        limit = {"úmrtí": 30, "sňatek": 75}.get(what, 100)
        where = "" if not y else ("  → matriky online" if now - y > limit else "  → zatím jen matriční úřad (lhůta)")
        print(f"  {k:>4} {n}: {what} {d} {p}".rstrip() + where)


if __name__ == "__main__":
    main()
