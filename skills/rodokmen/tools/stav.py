#!/usr/bin/env python3
"""Stav bádání ze souborů, bez historie rozhovoru (analyza/navrh-optimalizace.md, etapa E2): čím začít nové sezení nebo pokračovat po
přerušení. Jen čte. Nahrazuje čtení front, deníku a data/osoby.py řídicím agentem.

Použití (z kořene projektu):
  python3 -I tools/stav.py [--json]

Vypíše: větev a neuložené změny, verzi nástrojů, počty úkolů po frontách, rozpočet okna, rozpracované úkoly (stav „probíhá“ nebo se
zadáním či nálezem bez zápisu) s posledním krokem a tím, co má následovat, nedokončené zápisy a počet úkolů k rozhodnutí.
"""
import datetime
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fronta  # noqa: E402
import vysledek  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*a):
    try:
        r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def cti(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def dalsi_krok(zadani, nalez, zapsano, overeni):
    """Co má následovat, odvozeno jen ze souborů."""
    if zadani and not nalez:
        return "čtenář ještě nevrátil nález (spustit nebo pokračovat podle zadání)"
    if not nalez:
        return "sestavit zadání (tools/zadani.py novy)"
    if nalez.get("schema") != "nalez/1":
        return ("výsledek ve starém tvaru (před kontraktem): přečíst a rozhodnout, nebo zadat čtení znovu (tools/zadani.py novy); "
                "zapis_vysledku.py ho nepřijme")
    stav = nalez.get("stav")
    if zapsano and zapsano.get("uzavreno"):
        return "zapsáno a uzavřeno; zbývá commit, pokud neproběhl (tools/commit.py)"
    if stav == "částečně":
        n = nalez.get("navrh_dalsiho_kroku") or {}
        return "pokračovat v témže úkolu: " + (", ".join(f"{k} {v}" for k, v in n.items()) or "doplnit chybějící pole") + " (zadani.py rozsir)"
    if stav == "rozpočet":
        return "strop dosažen před koncem rozsahu: schválit pokračování, nebo předat rozhodnutí; není to „nenalezeno“"
    if stav == "nedostupné":
        return "portál: fronta.py selhani; úkol zůstává otevřený"
    if stav == "nečitelné":
        return "jiný výřez nebo jiný pramen; není to „nenalezeno“"
    if stav == "chyba prostředí":
        return "podnět do data/poznamky_pro_skill.md; úkol se vrací neotevřený"
    if stav in ("nalezeno", "vyvráceno") and not overeni:
        return "ověřit naslepo (verifier), pak vysledek.py porovnej"
    if zapsano:
        return "zapsáno, úkol otevřený: rozhodnout o uzavření nebo dalším kroku"
    return "rozhodnout a zapsat (rozhodnutí → tools/zapis_vysledku.py)"


def sestav():
    dnes = datetime.date.today()
    data = {f: fronta.nacti(f)[1] for f in fronta.FRONTY}
    hist = fronta.nacti_historii()
    posledni, zapsano = {}, {}
    for e in hist:
        posledni[e.get("id")] = e
        if e.get("udalost") == "zapsano":
            zapsano[e.get("id")] = e
    fronty = {f: {"celkem": len(uk), "probiha": sum(u.stav == "probíhá" for u in uk),
                  "ceka": sum(u.stav == "čeká" and not fronta.pripraveny(u, dnes) for u in uk)} for f, uk in data.items() if uk}
    kde = {u.id: (f, u) for f, uk in data.items() for u in uk}
    ids = {u.id for uk in data.values() for u in uk if u.stav == "probíhá"}
    for p in glob.glob(os.path.join(ROOT, "pracovni", "zadani", "U-*.json")) + glob.glob(os.path.join(ROOT, "pracovni", "vysledky", "U-????.json")):
        i = os.path.basename(p)[:6]
        if i in kde:   # hotový úkol už ve frontě není; jeho soubory jsou jen historie
            ids.add(i)
    rozprac = []
    for i in sorted(ids):
        f, u = kde.get(i, (None, None))
        zadani, nalez = cti(vysledek.cesta_zadani(i)), cti(vysledek.cesta_nalezu(i))
        overeni = sorted(os.path.basename(p)[len(i) + 9:-5] for p in glob.glob(os.path.join(ROOT, "pracovni", "vysledky", f"{i}_overeni_*.json")))
        e = posledni.get(i) or {}
        rozsah = None
        if zadani:
            rozsah = [(zadani.get("rozsah") or {}).get("snimky")] + [r.get("snimky") for r in zadani.get("rozsireni") or []]
        dod = next((r[len("Definice hotového:"):].strip() for r in (u.text.splitlines() if u else []) if r.startswith("Definice hotového:")), "")
        rozprac.append({"ukol": i, "fronta": f, "stav_ukolu": u.stav if u else None, "dod": dod, "osoby": u.os if u else [],
                        "posledni_udalost": f"{e.get('udalost')} {e.get('cas')}" if e else "", "rozsah": rozsah,
                        "nalez": (({"stav": nalez.get("stav"), "cast": nalez.get("cast"), "cerpani": nalez.get("cerpani"),
                                    "chybi": sorted({x for c in nalez.get("cteni") or [] if isinstance(c, dict) for x in c.get("chybi") or []})}
                                   if nalez.get("schema") == "nalez/1" else {"stary_tvar": True})
                                  if nalez else None),
                        "overeni": overeni, "zapsano": bool(zapsano.get(i)),
                        "dalsi_krok": dalsi_krok(zadani, nalez, zapsano.get(i), overeni)})
    r = fronta.nacti_rezim()
    rozpocet = None
    try:
        m, konec = fronta.rezim_v(datetime.datetime.now(), r)
        cfg = fronta.rozpocet_cfg(r)
        rozpocet = {"okno": m, "spotreba": fronta.cti_spotrebu(konec.isoformat() if konec else ""), "limit": cfg["okno"].get(m)}
    except Exception:   # noqa: BLE001 – rozpočet je jen doplněk
        pass
    try:
        with open(os.path.join(ROOT, ".skill_verze"), encoding="utf-8") as fh:
            verze = fh.read().strip()
    except OSError:
        verze = ""
    return {"vetev": git("branch", "--show-current").strip(), "neulozene": len([x for x in git("status", "--porcelain").splitlines() if x.strip()]),
            "verze": verze, "fronty": fronty, "rozpocet": rozpocet, "rozpracovano": rozprac,
            "nedokoncene_zapisy": sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "pracovni", "zapis_*.rozpracovano"))),
            "k_rozhodnuti": len(data.get("rozhodnuti") or [])}


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    s = sestav()
    if "--json" in argv:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    print(f"větev {s['vetev'] or '?'}, neuložených změn {s['neulozene']}, nástroje {s['verze'] or '?'}")
    print("fronty: " + (", ".join(f"{f} {v['celkem']}" + (f" (probíhá {v['probiha']})" if v["probiha"] else "") + (f" (čeká {v['ceka']})" if v["ceka"] else "")
                                  for f, v in s["fronty"].items()) or "prázdné"))
    if s["rozpocet"]:
        r = s["rozpocet"]
        print(f"rozpočet okna {r['okno']}: {r['spotreba']}/{r['limit'] if r['limit'] is not None else 'bez limitu'}")
    if s["k_rozhodnuti"]:
        print(f"k rozhodnutí: {s['k_rozhodnuti']} (před předložením projít: fronta.py seznam rozhodnuti)")
    for z in s["nedokoncene_zapisy"]:
        print(f"NEDOKONČENÝ ZÁPIS: pracovni/{z} (zápis byl přerušen a soubory vráceny; spusť tools/zapis_vysledku.py znovu)")
    if not s["rozpracovano"]:
        print("rozpracováno: nic")
    for x in s["rozpracovano"]:
        print(f"{x['ukol']} ({x['fronta'] or 'mimo fronty'}, {x['stav_ukolu'] or '-'}), osoby {','.join(x['osoby']) or '-'}; hotovo, když: {x['dod'] or 'NEURČENO'}")
        casti = []
        if x["rozsah"]:
            casti.append("rozsah " + " + ".join(f"{a[0]}–{a[1]}" for a in x["rozsah"] if isinstance(a, list) and len(a) == 2))
        if x["nalez"] and x["nalez"].get("stary_tvar"):
            casti.append("výsledek ve starém tvaru")
        elif x["nalez"]:
            n = x["nalez"]
            casti.append(f"nález {n['stav']} (část {n['cast']})" + (f", chybí {', '.join(n['chybi'])}" if n["chybi"] else ""))
        if x["overeni"]:
            casti.append("ověřeno " + ", ".join(x["overeni"]))
        if x["posledni_udalost"]:
            casti.append("poslední " + x["posledni_udalost"])
        print("  " + "; ".join(casti) if casti else "  bez zadání")
        print("  dál: " + x["dalsi_krok"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
