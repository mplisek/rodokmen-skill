#!/usr/bin/env python3
"""Přehled přístupů k webu: kdo co vidí (web.json → pristupy, tools/pohled.py). Nic nemění, nic nestahuje.

  python3 -I tools/pristupy.py              souhrn za každý přístup: vstup, práva, počty osob, dokumenty
  python3 -I tools/pristupy.py <id>         navíc seznam osob přístupu (přímá linie / rozšířená / vlastní větev)
  (Windows: python -I -X utf8 …)

Pomůcka k testům na testovacím webu: u každého přístupu je vidět, koho jeho verze webu obsahuje.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
from pohled import nacti_pristupy, pohled  # noqa: E402
from export_web import zijici, ocisti_osobu, skryt_osobu, rc_zverejnit, dokument_pro_pristup  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def nacti():
    ns = {}
    exec(open(os.path.join(DATA, "osoby.py"), encoding="utf-8").read(), ns)
    for k, v in (("P", {}), ("SIDE", []), ("LINES", {}), ("ISSUES", []), ("HYPOTEZY", []), ("SAME", {}),
                 ("RODINA", {}), ("PARTNERI", [])):
        ns.setdefault(k, v)
    cfg = json.load(open(os.path.join(DATA, "web.json"), encoding="utf-8"))
    path = os.path.join(DATA, "dokumenty.json")
    docs = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    return ns, cfg, docs


def main(argv):
    ns, cfg, docs = nacti()
    pristupy = nacti_pristupy(cfg)
    if not pristupy:
        print("web.json nemá přístupy (pristupy) – celý web vidí každý přihlášený.")
        return 0
    detail = argv[0] if argv else None
    if detail and detail not in {p["id"] for p in pristupy}:
        sys.exit(f"Přístup „{detail}“ není (jsou: {', '.join(p['id'] for p in pristupy)}).")
    for p in pristupy:
        if detail and p["id"] != detail:
            continue
        vstup = ", ".join(x for x in ("odpověď" if p.get("odpoved") else "", f"odkazy {len(p.get('odkazy') or [])}"
                                      if p.get("odkazy") else "") if x) or "–"
        prava = ", ".join(k for k, v in p["prava"].items() if v) or "žádná"
        print(f"\n== {p['id']} ({p['nazev']}) – vstup: {vstup}; práva: {prava}")
        if not p["koren"]:
            print("   bez kořene: vidí celý rodokmen" + (" včetně žijících a soukromých údajů (správce)" if p["id"] == "vse" else ""))
            continue
        nove, prevod = pohled(ns, p["koren"], p["texty"], p.get("rody"))
        zpet = {v: k for k, v in prevod.items()}
        linie, vlastni = nove["_linie"], nove["_vlastni"]

        def jmeno(nk):
            o = nove["P"].get(nk) if isinstance(nk, int) else nove["RODINA"].get(nk)
            return f"{o.get('n')} {o.get('y', '')}".strip() if o else str(nk)
        prima = [k for k, v in linie.items() if v == "prima"]
        rozs = [k for k, v in linie.items() if v == "rozsirena"]
        print(f"   osob: {len(linie)} (přímá linie {len(prima)}, rozšířená {len(rozs)}, vlastní větev {len(vlastni)})")

        def osoba(nk):
            return (nove["P"].get(nk) if isinstance(nk, int) else nove["RODINA"].get(nk)) or {}
        def smi(nk):
            return p["prava"]["soukrome"] and nk in vlastni
        ocistene = {nk: ocisti_osobu(osoba(nk), smi(nk)) for nk in linie}   # stejně jako export_web.py
        zive = [nk for nk, o in ocistene.items() if zijici(o.get("y"), o.get("note"), o.get("f", []))]
        plne = [nk for nk in zive if not skryt_osobu(ocistene[nk], smi(nk))]
        rucne = [nk for nk, o in ocistene.items() if nk not in zive and skryt_osobu(o, smi(nk))]
        print(f"   žijících: {len(zive)}, s plnými údaji (právo soukrome + vlastní větev + souhlas): {len(plne)}"
              + (f" – {', '.join(jmeno(nk) for nk in plne)}" if plne else ""))
        if rucne:
            print(f"   soukromé (soukrome=True), jen jméno a roky: {', '.join(jmeno(nk) for nk in rucne)}")
        najdi = lambda r: ns["P"].get(r) if isinstance(r, int) else ns["RODINA"].get(r)   # noqa: E731
        dok = [d["img"] for d in docs if rc_zverejnit(d, docs, najdi, ns["SAME"])
               and dokument_pro_pristup(d, p["id"], lambda r: r in prevod, ns["SAME"])]   # bez soukromí osob (export)
        print(f"   dokumenty: {len(dok)} z {len(docs)} (RČ a výběr přístupů; doklady se skrytými žijícími export ještě vynechá)")
        if detail:
            for nadpis, seznam in (("Přímá linie", prima), ("Rozšířená linie", rozs), ("Vlastní větev", sorted(vlastni, key=str))):
                print(f"   -- {nadpis}:")
                for nk in sorted(seznam, key=str):
                    print(f"      {jmeno(nk)}")
            for d in dok:
                print(f"   dokument: {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
