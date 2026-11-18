#!/usr/bin/env python3
"""Skutečná spotřeba sezení Claude Code nad projektem: kolik stálo hlavní vlákno a kolik pomocníci podle role (měření pro
analyza/navrh-optimalizace.md, etapa E7). Jen čte záznamy sezení, nic nezapisuje a nevypisuje text zadání ani odpovědí.

Použití:
  python3 -I tools/spotreba.py sezeni [--sezeni ID|posledni] [--od 2026-11-14T18:00] [--do …] [--json]
        tabulka: role a model, počet běhů, součet a medián „ekv“, medián startu, kroků a chyb nástrojů; hlavní vlákno; podíly
  python3 -I tools/spotreba.py ukol U-0045 [--sezeni ID|posledni] [--json]
        pomocníci, jejichž zadání nebo popis jmenuje daný úkol (hlavní vlákno se k úkolu přiřadit nedá)
  python3 -I tools/spotreba.py seznam
        sezení projektu od nejnovějšího (ID, poslední změna, velikost)

„ekv“ je vážené číslo pro srovnání běhů, ne účet: vstup + 1,25 × zápis cache + 0,1 × čtení cache + 5 × výstup. Sčítá modely
s různou cenou, proto tabulka uvádí model u každé role. Záznamy se hledají v ~/.claude/projects/<složka projektu>; jinou složku
zadá proměnná RODOKMEN_PREPISY.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
UKOL = re.compile(r"U-\d{4}")


def slozka_prepisu():
    if os.environ.get("RODOKMEN_PREPISY"):
        return os.environ["RODOKMEN_PREPISY"]
    return os.path.join(os.path.expanduser("~"), ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", ROOT))


def ekv(u):
    return (u.get("input_tokens", 0) + 1.25 * u.get("cache_creation_input_tokens", 0) + 0.1 * u.get("cache_read_input_tokens", 0)
            + 5 * u.get("output_tokens", 0))


def kontext(u):
    return u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)


def cas(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def mez(s):
    t = cas(s)
    if t is None:
        sys.exit(f"čas ve tvaru 2026-11-14T18:00 (je „{s}“)")
    return t if t.tzinfo else t.astimezone()


def cti(path, od=None, do=None, jen_hlavni=False):
    """Jeden záznam (hlavní vlákno nebo pomocník) → souhrn. Tah modelu se počítá jednou (podle id zprávy)."""
    tahy, poradi, ukoly, chyby, prvni_text = {}, [], set(), 0, True
    try:
        f = open(path, encoding="utf-8")
    except OSError:
        return None
    with f:
        for radek in f:
            try:
                d = json.loads(radek)
            except ValueError:
                continue
            if jen_hlavni and d.get("isSidechain"):
                continue
            t = cas(d.get("timestamp"))
            if t and ((od and t < od) or (do and t > do)):
                continue
            m = d.get("message") or {}
            if d.get("type") == "assistant":
                if m.get("id") not in tahy:
                    poradi.append(m.get("id"))
                    tahy[m.get("id")] = (m.get("usage") or {}, m.get("model") or "", t)
            elif d.get("type") == "user":
                c = m.get("content")
                if isinstance(c, str) and prvni_text and not jen_hlavni:   # zadání pomocníka: jen čísla úkolů, text se nikam nenese
                    ukoly.update(UKOL.findall(c))
                    prvni_text = False
                for b in c if isinstance(c, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                        chyby += 1
    us = [tahy[i] for i in poradi]
    if not us:
        return None
    modely = collections.Counter(x[1] for x in us)
    casy = [x[2] for x in us if x[2]]
    return {"tahu": len(us), "ekv": round(sum(ekv(x[0]) for x in us)), "start": kontext(us[0][0]),
            "kontext_max": max(kontext(x[0]) for x in us), "kontext_median": round(statistics.median(kontext(x[0]) for x in us)),
            "vstup": sum(x[0].get("input_tokens", 0) for x in us), "zapis_cache": sum(x[0].get("cache_creation_input_tokens", 0) for x in us),
            "cteni_cache": sum(x[0].get("cache_read_input_tokens", 0) for x in us), "vystup": sum(x[0].get("output_tokens", 0) for x in us),
            "model": modely.most_common(1)[0][0].replace("claude-", ""), "modelu": len(modely), "chyb": chyby, "ukoly": sorted(ukoly),
            "od": min(casy).isoformat() if casy else "", "do": max(casy).isoformat() if casy else ""}


def sezeni_soubory(slozka):
    return sorted(glob.glob(os.path.join(slozka, "*.jsonl")), key=os.path.getmtime, reverse=True)


def vyber_sezeni(slozka, kdo):
    soubory = sezeni_soubory(slozka)
    if not soubory:
        sys.exit(f"ve složce {slozka} není žádný záznam sezení (jinou složku zadá RODOKMEN_PREPISY)")
    if kdo in (None, "posledni"):
        return soubory[0]
    hit = [p for p in soubory if os.path.basename(p).startswith(kdo)]
    if len(hit) != 1:
        sys.exit(f"sezení „{kdo}“: " + ("nenalezeno" if not hit else "víc shod, zadej delší začátek ID") + " (spotreba.py seznam)")
    return hit[0]


def pomocnici(sezeni, od=None, do=None):
    out = []
    for p in sorted(glob.glob(os.path.join(sezeni[:-len(".jsonl")], "subagents", "agent-*.jsonl"))):
        r = cti(p, od, do)
        if not r:
            continue
        meta = {}
        try:
            with open(p[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            pass
        r["role"] = str(meta.get("agentType") or "?").split(":")[-1]
        r["ukoly"] = sorted(set(r["ukoly"]) | set(UKOL.findall(str(meta.get("description") or ""))))
        out.append(r)
    return out


def po_rolich(ps):
    g = collections.defaultdict(list)
    for r in ps:
        g[(r["role"], r["model"])].append(r)
    radky = []
    for (role, model), rs in sorted(g.items()):
        radky.append({"role": role, "model": model, "behu": len(rs), "ekv": sum(r["ekv"] for r in rs),
                      "ekv_median": round(statistics.median(r["ekv"] for r in rs)), "start_median": round(statistics.median(r["start"] for r in rs)),
                      "tahu_median": round(statistics.median(r["tahu"] for r in rs)), "chyb": sum(r["chyb"] for r in rs)})
    return radky


def tis(n):
    return f"{n / 1000:.0f}"


def cmd_sezeni(a):
    sez = vyber_sezeni(slozka_prepisu(), a.sezeni)
    od, do = (mez(a.od) if a.od else None), (mez(a.do) if a.do else None)
    hlavni = cti(sez, od, do, jen_hlavni=True) or {"ekv": 0, "tahu": 0, "kontext_median": 0, "kontext_max": 0, "model": "", "modelu": 0}
    radky = po_rolich(pomocnici(sez, od, do))
    celkem = hlavni["ekv"] + sum(r["ekv"] for r in radky)
    vysl = {"sezeni": os.path.basename(sez)[:-len(".jsonl")], "hlavni": hlavni, "pomocnici": radky, "ekv_celkem": celkem}
    if a.json:
        print(json.dumps(vysl, ensure_ascii=False, indent=1))
        return 0
    print(f"sezení {vysl['sezeni']}" + (f" od {a.od}" if a.od else "") + (f" do {a.do}" if a.do else ""))
    print("role | model | běhů | ekv tis. | medián ekv tis. | medián startu | medián tahů | chyb nástrojů | podíl")
    for r in radky:
        print(f"{r['role']} | {r['model']} | {r['behu']} | {tis(r['ekv'])} | {tis(r['ekv_median'])} | {r['start_median']} | {r['tahu_median']} | "
              f"{r['chyb']} | {100 * r['ekv'] / celkem if celkem else 0:.0f} %")
    print(f"hlavní vlákno | {hlavni['model']}" + (f" (+{hlavni['modelu'] - 1} další model)" if hlavni["modelu"] > 1 else "")
          + f" | {hlavni['tahu']} tahů | {tis(hlavni['ekv'])} | kontext medián {hlavni['kontext_median']}, max {hlavni['kontext_max']} | "
          f"{100 * hlavni['ekv'] / celkem if celkem else 0:.0f} %")
    print(f"celkem {tis(celkem)} tis. ekv, pomocníků {sum(r['behu'] for r in radky)}")
    if hlavni["modelu"] > 1:
        print("pozor: hlavní vlákno měnilo model; každá změna zahodí mezipaměť a celý kontext se platí znovu")
    return 0


def cmd_ukol(a):
    if not UKOL.fullmatch(a.id):
        sys.exit("ID úkolu ve tvaru U-0042")
    sez = vyber_sezeni(slozka_prepisu(), a.sezeni)
    ps = [r for r in pomocnici(sez) if a.id in r["ukoly"]]
    vysl = {"ukol": a.id, "behu": len(ps), "ekv": sum(r["ekv"] for r in ps), "pomocnici": po_rolich(ps)}
    if a.json:
        print(json.dumps(vysl, ensure_ascii=False, indent=1))
        return 0
    if not ps:
        print(f"{a.id}: žádný pomocník v sezení úkol nejmenuje (zadání musí obsahovat ID úkolu)")
        return 1
    print(f"{a.id}: {len(ps)} běhů pomocníků, {tis(vysl['ekv'])} tis. ekv (bez hlavního vlákna)")
    for r in vysl["pomocnici"]:
        print(f"  {r['role']} ({r['model']}): {r['behu']}×, {tis(r['ekv'])} tis. ekv")
    return 0


def cmd_seznam(a):
    for p in sezeni_soubory(slozka_prepisu()):
        print(f"{os.path.basename(p)[:-len('.jsonl')]} | {datetime.datetime.fromtimestamp(os.path.getmtime(p)):%Y-%m-%d %H:%M} | "
              f"{os.path.getsize(p) / 1e6:.1f} MB")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("sezeni"); s.add_argument("--sezeni"); s.add_argument("--od"); s.add_argument("--do"); s.add_argument("--json", action="store_true")
    s = sp.add_parser("ukol"); s.add_argument("id"); s.add_argument("--sezeni"); s.add_argument("--json", action="store_true")
    sp.add_parser("seznam")
    a = ap.parse_args(argv)
    return {"sezeni": cmd_sezeni, "ukol": cmd_ukol, "seznam": cmd_seznam}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
