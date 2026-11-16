#!/usr/bin/env python3
"""Oprava chybných údajů v datech jedním voláním: pole existujících zápisů (data/zaznamy.json) a míst (data/mista.json).

Badatel opravuje sám, ze souboru v pracovni/; nikdo nekopíruje data ručně. Nový zápis tudy nevzniká (ten jde jen přes
tools/zapis_vysledku.py), účastníci zápisu přes tools/ucastnici.py, svazky přes tools/svazky.py.

Použití (z kořene projektu):
  python3 -I tools/oprava.py pracovni/oprava_<co>.json [--nanecisto]
      {"duvod": "sňatek označený jako soupis", "doklad": "snímek 80, oddací zápis (výřez pracovni/…)",
       "zmeny": [{"soubor": "zaznamy", "klic": "<klíč zápisu>", "pole": {"druh": "O"}},
                 {"soubor": "mista", "klic": "Stružinec", "pole": {"lat": 49.69, "lon": 15.81, "dotaz": "…"}}]}

Postup: (1) kontrola všech změn – důvod a doklad povinné, zápis nebo místo musí existovat, jen povolená pole a platné hodnoty
(druh N/O/Z/B/S/J, svazek z katalogu, souřadnice v rozsahu); (2) zápis všech změn (formát souborů zůstane, tools/zapis.py);
(3) tools/kontrola.py – přibude-li chyba, všechno se vrátí; (4) řádek do data/opravy.jsonl (co bylo, co je, důvod, doklad).
Pak vypíše příkaz pro commit (tools/commit.py --soubory …). Web se tu nesestavuje: před nasazením ho ověří brána (tools/brana.py).
Kód 0 = opraveno nebo nic ke změně, 1 = odmítnuto nebo vráceno.
"""
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zapis  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRUHY = ("N", "O", "Z", "B", "S", "J")


def _text(n):
    return lambda v: None if isinstance(v, str) and v.strip() and len(v) <= n else f"neprázdný text nejvýš {n} znaků"


def _snimek(v):
    ok = (isinstance(v, int) and not isinstance(v, bool) and v > 0) or (isinstance(v, str) and v.strip() and len(v) <= 20)
    return None if ok else "číslo snímku (kladné číslo nebo krátký text)"


def _cislo(od, do):
    return lambda v: None if isinstance(v, (int, float)) and not isinstance(v, bool) and od <= v <= do else f"číslo od {od} do {do}"


POLE = {
    "zaznamy": {"druh": lambda v: None if v in DRUHY else f"jedno z {', '.join(DRUHY)}", "datum": _text(60), "nazev": _text(300),
                "shrnuti": _text(3000), "snimek": _snimek, "svazek": None, "odkaz": lambda v: None if isinstance(v, str) and
                v.startswith("https://") else "adresa https://", "rejstrik": lambda v: None if isinstance(v, bool) else "true nebo false"},
    "mista": {"re": _text(300), "dotaz": _text(300), "lat": _cislo(-90, 90), "lon": _cislo(-180, 180), "osm": _text(500)},
}
SOUBORY = {"zaznamy": "data/zaznamy.json", "mista": "data/mista.json"}
VZOR = {"duvod": "sňatek označený jako soupis obyvatel", "doklad": "snímek 80: oddací zápis, výřez pracovni/vysledky/…",
        "zmeny": [{"soubor": "zaznamy", "klic": "<klíč zápisu z data/zaznamy.json>", "pole": {"druh": "O"}},
                  {"soubor": "mista", "klic": "<název místa z data/mista.json>", "pole": {"lat": 49.69, "lon": 15.81}}]}
HISTORIE = "data/opravy.jsonl"


def nacti(rel, vychozi):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vychozi


def polozky(soubor):
    d = nacti(SOUBORY[soubor], [] if soubor == "zaznamy" else {})
    if soubor == "zaznamy":
        return {z.get("klic"): z for z in d if isinstance(z, dict)}
    return d if isinstance(d, dict) else {}


def over(o):
    """(chyby, změny se starými hodnotami)."""
    ch, plan = [], []
    for k in ("duvod", "doklad"):
        if not (isinstance(o.get(k), str) and o[k].strip()):
            ch.append(f"chybí {k} (proč se opravuje a čím je to doloženo)")
    zmeny = o.get("zmeny")
    if not (isinstance(zmeny, list) and zmeny):
        return ch + ["zmeny: seznam aspoň jedné změny"], plan
    nezname = sorted(set(o) - {"duvod", "doklad", "zmeny"})
    if nezname:
        ch.append("neznámá pole: " + ", ".join(nezname))
    data = {s: polozky(s) for s in SOUBORY}
    svazky = nacti("data/svazky.json", {})
    for i, z in enumerate(zmeny, 1):
        kde = f"změna {i}"
        if not isinstance(z, dict) or z.get("soubor") not in SOUBORY:
            ch.append(f"{kde}: soubor jen {' nebo '.join(SOUBORY)}")
            continue
        s, klic, pole = z["soubor"], z.get("klic"), z.get("pole")
        if klic not in data[s]:
            ch.append(f"{kde}: {s} „{klic}“ neexistuje (nový zápis jen přes tools/zapis_vysledku.py)")
            continue
        if not (isinstance(pole, dict) and pole):
            ch.append(f"{kde}: pole = objekt se změněnými poli")
            continue
        stare = {}
        for p, v in pole.items():
            if p not in POLE[s]:
                ch.append(f"{kde}: pole „{p}“ tudy měnit nejde (povolená: {', '.join(POLE[s])})")
                continue
            if p == "svazek":
                chyba = None if v in svazky else "svazek z katalogu data/svazky.json (tools/svazky.py)"
            else:
                chyba = POLE[s][p](v)
            if chyba:
                ch.append(f"{kde} {s} „{klic}“ {p}: {chyba}")
            stare[p] = data[s][klic].get(p)
        plan.append({"soubor": s, "klic": klic, "pole": {p: {"bylo": stare.get(p), "je": v} for p, v in pole.items() if p in POLE[s]}})
    return ch, plan


def chyby_kontroly():
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "tools", "kontrola.py")], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {x for x in (r.stdout + r.stderr).splitlines() if x.startswith("CHYBA:")}


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = sys.argv[1:] if argv is None else argv
    nanecisto = "--nanecisto" in a
    a = [x for x in a if x != "--nanecisto"]
    if a == ["vzor"]:
        print(json.dumps(VZOR, ensure_ascii=False, indent=1))
        return 0
    if len(a) != 1 or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if a in (["-h"], ["--help"]) else 2
    cesta = os.path.abspath(os.path.join(ROOT, a[0]))
    if not cesta.startswith(os.path.join(ROOT, "pracovni") + os.sep):
        print("ODMÍTNUTO: vstup jen ze souboru v pracovni/")
        return 1
    try:
        with open(cesta, encoding="utf-8-sig") as f:
            o = json.load(f)
    except (OSError, ValueError) as e:
        print(f"ODMÍTNUTO: {a[0]} nejde přečíst jako JSON ({e})")
        return 1
    if not isinstance(o, dict):
        print("ODMÍTNUTO: vstup je jeden objekt JSON")
        return 1
    ch, plan = over(o)
    if ch:
        print("ODMÍTNUTO, nic se nezměnilo:\n- " + "\n- ".join(ch))
        return 1
    for z in plan:   # beze změny se nezapisuje
        z["pole"] = {p: v for p, v in z["pole"].items() if v["bylo"] != v["je"]}
    plan = [z for z in plan if z["pole"]]
    if not plan:
        print("nic ke změně: data už mají uvedené hodnoty")
        return 0
    for z in plan:
        print(f"{z['soubor']} „{z['klic']}“: " + "; ".join(f"{p} {v['bylo']} → {v['je']}" for p, v in z["pole"].items()))
    if nanecisto:
        print("(nanečisto, nic nezapsáno)")
        return 0
    zaloha = {}
    for rel in list(SOUBORY.values()) + [HISTORIE]:
        p = os.path.join(ROOT, rel)
        zaloha[p] = open(p, "rb").read() if os.path.exists(p) else None

    def vrat(duvod):
        for p, obsah in zaloha.items():
            if obsah is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                with open(p, "wb") as f:
                    f.write(obsah)
        print(f"vráceno, nic se nezměnilo: {duvod}")
        return 1

    pred = chyby_kontroly()
    try:
        for z in plan:
            zapis.zapis(z["soubor"], z["klic"], {p: v["je"] for p, v in z["pole"].items()}, sloucit=True)
    except SystemExit as e:
        return vrat(f"zápis selhal ({e})")
    nove = sorted(chyby_kontroly() - pred)
    if nove:
        return vrat("po opravě hlásí kontrola dat nové chyby:\n  " + "\n  ".join(nove))
    zaznam = {"cas": datetime.datetime.now().isoformat(timespec="seconds"), "duvod": o["duvod"].strip(), "doklad": o["doklad"].strip(),
              "zmeny": plan}
    with open(os.path.join(ROOT, HISTORIE), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(zaznam, ensure_ascii=False) + "\n")
    soubory = sorted({SOUBORY[z["soubor"]] for z in plan}) + [HISTORIE]
    print(f"opraveno ({sum(len(z['pole']) for z in plan)} polí), kontrola dat bez nové chyby; historie {HISTORIE}")
    print(f'commit: python -I -X utf8 tools/commit.py --soubory {",".join(soubory)} --zprava "Oprava: {o["duvod"].strip()[:80]}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
