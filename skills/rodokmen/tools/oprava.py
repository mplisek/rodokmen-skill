#!/usr/bin/env python3
"""Změny dat jedním voláním (opravy i doplnění, třeba z rodinných dokumentů): zápisy (data/zaznamy.json, jen úprava), místa
(data/mista.json, i nové), rodinné dokumenty (data/dokumenty.json, i nové), osoby v data/osoby.py (P i RODINA: pole, fakta
včetně bydliště, nová osoba) a otevřené otázky (ISSUES, nová i změna stavu).

Mění se ze souboru v pracovni/; nikdo nekopíruje data ručně. Nový zápis z matriky tudy nevzniká (ten jde přes
tools/nalez.py nebo tools/zapis.py), účastníci zápisu přes tools/ucastnici.py, svazky přes tools/svazky.py, začernění rodných čísel na
snímku dokumentu přes tools/vyrez.py --zacernit. Souhlas žijících a zveřejnění (souhlas, soukrome=false) určuje uživatel.
Zapisují se všechna data včetně žijících; co jde na web, omezuje až export (soukromí, začernění).

Použití (z kořene projektu):
  python3 -I tools/oprava.py vzor                                  tvar vstupu se všemi druhy změn
  python3 -I tools/oprava.py pracovni/oprava_<co>.json [--nanecisto]
      {"duvod": "…", "doklad": "…", "zmeny": [
        {"soubor": "zaznamy", "klic": "<klíč>", "pole": {"druh": "O"}},
        {"soubor": "mista", "klic": "<obec>", "nove": true, "pole": {"re": "…", "dotaz": "…", "lat": 49.9, "lon": 15.8}},
        {"soubor": "osoby", "klic": 8, "fakta_pridej": ["bydliště Lhota čp. 5 (1840–1870)"], "fakta_nahrad": [["starý", "nový"]]},
        {"soubor": "osoby", "skupina": "RODINA", "klic": "marie-vzorna-1840", "nove": true, "pole": {"n": "…", "otec": 8, "st": "fam"}},
        {"soubor": "dokumenty", "klic": "<img>", "nove": true, "pole": {"popis": "…", "osoby": [8, 9], "rc": [], "druh": "schema"}},
        {"soubor": "issues", "nove": true, "pole": {"k": 9, "otazka": "…", "stav": "otevřené", "text": "…"}}]}

Postup: (1) kontrola všech změn – důvod a doklad povinné, položka musí existovat (nebo „nove“), jen povolená pole a platné hodnoty
(druh N/O/Z/B/S/J, svazek z katalogu, souřadnice, stav osoby, osoby v otec/matka/osoby/rc existují, fakt k nahrazení existuje);
(2) zápis všech změn (formát souborů zůstane: tools/zapis.py, u osoby.py jen text dotčené položky – tools/osoby_upravy.py);
(3) tools/kontrola.py – přibude-li chyba, všechno se vrátí; (4) řádek do data/opravy.jsonl (co bylo, co je, důvod, doklad).
Pak vypíše, které soubory uložit (git add … && git commit). Web se tu nesestavuje: před nasazením ho ověří brána (tools/brana.py).
Kód 0 = opraveno nebo nic ke změně, 1 = odmítnuto nebo vráceno.
"""
import datetime
import json
import os
import re
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
SOUBORY = {"zaznamy": "data/zaznamy.json", "mista": "data/mista.json", "dokumenty": "data/dokumenty.json",
           "osoby": "data/osoby.py", "issues": "data/osoby.py"}
STAVY_OSOB = ("doc", "prob", "fam", "mh", "unk")
STAVY_OTAZEK = ("otevřené", "hypotéza", "vyřešeno")
POLE_OSOBY = {"P": ("n", "y", "st", "zap", "f", "note", "vyz", "r", "overeno", "sour"),
              "RODINA": ("n", "y", "sex", "otec", "matka", "partner", "v", "st", "zap", "f", "r", "note")}
POLE_DOKUMENTU = ("popis", "osoby", "druh", "rc", "pristupy", "soukrome", "rodiny", "autor", "datum", "soubory")
POVINNE_NOVE = {"mista": ("re", "dotaz", "lat", "lon"), "dokumenty": ("popis", "osoby", "rc"), "osoby": ("n",), "issues": ("k", "otazka", "stav")}
VZOR = {"duvod": "rodinné schéma potomků a úmrtní list", "doklad": "dokumenty/schema_novakovi.jpg, úmrtní list 1906 (sken od rodiny 15. 11.)",
        "zmeny": [{"soubor": "zaznamy", "klic": "<klíč zápisu>", "pole": {"druh": "O"}},
                  {"soubor": "mista", "klic": "<obec>", "pole": {"lat": 49.69, "lon": 15.81}},
                  {"soubor": "mista", "klic": "<nová obec>", "nove": True, "pole": {"re": "Lhot", "dotaz": "Lhota, okres Chrudim", "lat": 49.9, "lon": 15.8}},
                  {"soubor": "osoby", "klic": 8, "fakta_pridej": ["bydliště Lhota čp. 5 (1840–1870, podle rodinného schématu)"],
                   "fakta_nahrad": [["kovář", "kovář a hostinský"]], "pole": {"st": "fam"}},
                  {"soubor": "osoby", "skupina": "RODINA", "klic": "marie-vzorna-1840", "nove": True,
                   "pole": {"n": "Marie Vzorná", "y": "* 1840", "sex": "F", "otec": 8, "matka": 9, "st": "fam", "f": ["* 1840 Lhota"]}},
                  {"soubor": "dokumenty", "klic": "schema_novakovi", "nove": True,
                   "pole": {"popis": "Schéma potomků …", "osoby": [8, 9], "rc": [], "druh": "schema", "autor": "rodina", "datum": "1960"}},
                  {"soubor": "issues", "nove": True, "pole": {"k": 9, "otazka": "Kdy zemřela Anna?", "stav": "otevřené", "text": "…"}},
                  {"soubor": "issues", "klic": "<přesný text otázky>", "pole": {"stav": "vyřešeno"}}]}
HISTORIE = "data/opravy.jsonl"


def nacti(rel, vychozi):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vychozi


def polozky(soubor):
    if soubor in ("zaznamy", "dokumenty"):
        d = nacti(SOUBORY[soubor], [])
        k = "klic" if soubor == "zaznamy" else "img"
        return {z.get(k): z for z in d if isinstance(z, dict)} if isinstance(d, list) else {}
    d = nacti(SOUBORY[soubor], {})
    return d if isinstance(d, dict) else {}


def osoby_ns():
    import runpy
    try:
        return runpy.run_path(os.path.join(ROOT, "data", "osoby.py"))
    except Exception:   # noqa: BLE001
        return {}


def _seznam_textu(v, n=500):
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() and len(x) <= n for x in v)


def over_osobu(z, kde, ns, zaznamy):
    """(chyby, plán) pro změnu osoby v P nebo RODINA."""
    ch = []
    skupina = z.get("skupina", "P")
    if skupina not in POLE_OSOBY:
        return [f"{kde}: skupina P nebo RODINA"], None
    klic, nove = z.get("klic"), bool(z.get("nove"))
    if skupina == "P" and not (isinstance(klic, int) and not isinstance(klic, bool) and klic >= 1):
        return [f"{kde}: osoba v P má klíč číslo (Kekulé)"], None
    if skupina == "RODINA" and not (isinstance(klic, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,60}", klic)):
        return [f"{kde}: osoba v RODINA má klíč zkratku (malá písmena, číslice, pomlčka)"], None
    stara = (ns.get(skupina) or {}).get(klic)
    if nove and stara is not None:
        return [f"{kde}: osoba {klic} už v {skupina} je (bez „nove“ se upravuje)"], None
    if not nove and stara is None:
        return [f"{kde}: osoba {klic} v {skupina} není (novou založ s \"nove\": true)"], None
    stara = dict(stara or {})
    pole = dict(z.get("pole") or {})
    nezname = sorted(set(z) - {"soubor", "skupina", "klic", "nove", "pole", "fakta_pridej", "fakta_nahrad"})
    if nezname:
        ch.append(f"{kde}: neznámá pole změny: {', '.join(nezname)}")
    osoby = set(ns.get("P") or {}) | set(ns.get("RODINA") or {})
    for p, v in pole.items():
        if p not in POLE_OSOBY[skupina]:
            ch.append(f"{kde}: pole osoby „{p}“ tudy měnit nejde (povolená: {', '.join(POLE_OSOBY[skupina])}; souhlas a soukromí určuje uživatel)")
        elif p in ("n", "y", "note", "vyz", "v", "sour") and not (isinstance(v, str) and len(v) <= 3000 and (v.strip() or p in ("y", "note"))):
            ch.append(f"{kde}: {p} je text")
        elif p == "st" and v not in STAVY_OSOB:
            ch.append(f"{kde}: st jen {', '.join(STAVY_OSOB)}")
        elif p == "sex" and v not in ("M", "F"):
            ch.append(f"{kde}: sex M nebo F")
        elif p in ("f", "zap") and not (isinstance(v, list) and (not v or _seznam_textu(v))):
            ch.append(f"{kde}: {p} je seznam textů")
        elif p == "r" and not (isinstance(v, list) and all(x in zaznamy for x in v)):
            ch.append(f"{kde}: r jen klíče zápisů z data/zaznamy.json")
        elif p in ("otec", "matka") and v not in osoby:
            ch.append(f"{kde}: {p} {v!r} není osoba v P ani RODINA")
        elif p == "partner" and not (isinstance(v, list) and all(x in osoby for x in v)):
            ch.append(f"{kde}: partner je seznam osob z P nebo RODINA")
        elif p == "overeno" and not (isinstance(v, dict) and all(isinstance(x, str) and x.strip() for x in v.values())):
            ch.append(f"{kde}: overeno je slovník {{pravidlo: důvod}}")
    fakta = list(pole.get("f", stara.get("f") or []))
    for par in z.get("fakta_nahrad") or []:
        if not (isinstance(par, list) and len(par) == 2 and all(isinstance(x, str) and x.strip() for x in par)):
            ch.append(f"{kde}: fakta_nahrad je seznam dvojic [starý fakt, nový fakt]")
        elif par[0] not in fakta:
            ch.append(f"{kde}: fakt „{par[0]}“ u osoby {klic} není (přesný text)")
        else:
            fakta[fakta.index(par[0])] = par[1]
    pridej = z.get("fakta_pridej") or []
    if not (isinstance(pridej, list) and (not pridej or _seznam_textu(pridej))):
        ch.append(f"{kde}: fakta_pridej je seznam textů")
    else:
        fakta += [x for x in pridej if x not in fakta]
    if z.get("fakta_nahrad") or pridej:
        pole["f"] = fakta
    if nove and not str(pole.get("n") or "").strip():
        ch.append(f"{kde}: nová osoba potřebuje n (jméno)")
    if not pole:
        ch.append(f"{kde}: žádná změna (pole, fakta_pridej nebo fakta_nahrad)")
    plan = {"soubor": "osoby", "skupina": skupina, "klic": klic, "akce": "nove" if nove else "uprav",
            "pole": {p: {"bylo": stara.get(p), "je": v} for p, v in pole.items()}}
    return ch, plan


def over_otazku(z, kde, ns):
    ch = []
    nove = bool(z.get("nove"))
    pole = dict(z.get("pole") or {})
    stare = None
    if not nove:
        stare = next((dict(i) for i in ns.get("ISSUES") or [] if isinstance(i, dict) and i.get("otazka") == z.get("klic")), None)
        if stare is None:
            return [f"{kde}: otázka „{z.get('klic')}“ v ISSUES není (klíč = přesný text otázky; novou s \"nove\": true)"], None
    osoby = set(ns.get("P") or {}) | set(ns.get("RODINA") or {})
    for p, v in pole.items():
        if p not in ("k", "otazka", "stav", "text"):
            ch.append(f"{kde}: pole otázky jen k, otazka, stav, text")
        elif p == "stav" and v not in STAVY_OTAZEK:
            ch.append(f"{kde}: stav jen {', '.join(STAVY_OTAZEK)}")
        elif p == "k" and v not in osoby:
            ch.append(f"{kde}: k {v!r} není osoba v P ani RODINA")
        elif p in ("otazka", "text") and not (isinstance(v, str) and v.strip() and len(v) <= 2000):
            ch.append(f"{kde}: {p} je neprázdný text")
    if nove:
        ch += [f"{kde}: nová otázka potřebuje {p}" for p in POVINNE_NOVE["issues"] if p not in pole]
    plan = {"soubor": "issues", "klic": z.get("klic") if not nove else pole.get("otazka"), "puvodni": None if nove else z.get("klic"),
            "akce": "nove" if nove else "uprav", "pole": {p: {"bylo": (stare or {}).get(p), "je": v} for p, v in pole.items()}}
    return ch, plan


def over_dokument(p, v, osoby):
    if p == "osoby":
        return None if isinstance(v, list) and v and all(x in osoby for x in v) else "osoby = seznam osob z P nebo RODINA"
    if p == "rc":
        return None if isinstance(v, list) and all(x in osoby for x in v) else "rc = seznam osob (čí rodné číslo je na dokladu; i prázdný)"
    if p == "soukrome":
        return None if v is True else "soukrome jen true (zveřejnění určuje uživatel)"
    if p in ("pristupy", "rodiny", "soubory"):
        return None if isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v) else f"{p} = seznam textů"
    return _text(3000 if p == "popis" else 200)(v)


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
    data = {s: polozky(s) for s in ("zaznamy", "mista", "dokumenty")}
    svazky = nacti("data/svazky.json", {})
    ns = osoby_ns() if any(isinstance(z, dict) and z.get("soubor") in ("osoby", "issues", "dokumenty") for z in zmeny) else {}
    osoby = set(ns.get("P") or {}) | set(ns.get("RODINA") or {})
    for i, z in enumerate(zmeny, 1):
        kde = f"změna {i}"
        if not isinstance(z, dict) or z.get("soubor") not in SOUBORY:
            ch.append(f"{kde}: soubor jen {', '.join(SOUBORY)}")
            continue
        s = z["soubor"]
        if s == "osoby":
            c, p = over_osobu(z, kde, ns, data["zaznamy"])
            ch += c
            plan += [p] if p else []
            continue
        if s == "issues":
            c, p = over_otazku(z, kde, ns)
            ch += c
            plan += [p] if p else []
            continue
        klic, pole, nove = z.get("klic"), z.get("pole"), bool(z.get("nove"))
        if s == "zaznamy" and nove:
            ch.append(f"{kde}: nový zápis jen přes tools/nalez.py (nebo tools/zapis.py)")
            continue
        if nove and klic in data[s]:
            ch.append(f"{kde}: {s} „{klic}“ už existuje (bez „nove“ se upravuje)")
            continue
        if not nove and klic not in data[s]:
            ch.append(f"{kde}: {s} „{klic}“ neexistuje" + ("" if s == "zaznamy" else " (nové s \"nove\": true)"))
            continue
        if not (isinstance(klic, str) and klic.strip()):
            ch.append(f"{kde}: klic je text")
            continue
        if not (isinstance(pole, dict) and pole):
            ch.append(f"{kde}: pole = objekt se změněnými poli")
            continue
        povolena = POLE_DOKUMENTU if s == "dokumenty" else POLE[s]
        stare = {}
        for p, v in pole.items():
            if p not in povolena:
                ch.append(f"{kde}: pole „{p}“ tudy měnit nejde (povolená: {', '.join(povolena)}"
                          + ("; začernění jen přes tools/vyrez.py --zacernit" if s == "dokumenty" else "") + ")")
                continue
            if s == "dokumenty":
                chyba = over_dokument(p, v, osoby)
            elif p == "svazek":
                chyba = None if v in svazky else "svazek z katalogu data/svazky.json (tools/svazky.py)"
            else:
                chyba = POLE[s][p](v)
            if chyba:
                ch.append(f"{kde} {s} „{klic}“ {p}: {chyba}")
            stare[p] = (data[s].get(klic) or {}).get(p)
        if nove:
            ch += [f"{kde}: nové {s} potřebuje {p}" for p in POVINNE_NOVE.get(s, ()) if p not in pole]
        plan.append({"soubor": s, "klic": klic, "akce": "nove" if nove else "uprav",
                     "pole": {p: {"bylo": stare.get(p), "je": v} for p, v in pole.items() if p in povolena}})
    return ch, plan


def proved(plan):
    """Zapíše plán; SystemExit/ValueError = selhání (volající vrátí zálohu)."""
    import osoby_upravy
    cesta_osob = os.path.join(ROOT, "data", "osoby.py")
    text = None
    for z in plan:
        hodnoty = {p: v["je"] for p, v in z["pole"].items()}
        if z["soubor"] in ("zaznamy", "mista", "dokumenty"):
            zapis.zapis(z["soubor"], z["klic"], hodnoty, sloucit=z["akce"] == "uprav")
            continue
        if text is None:
            with open(cesta_osob, encoding="utf-8") as f:
                text = f.read()
        if z["soubor"] == "osoby":
            stara = osoby_upravy.nacti_osobu(text, z["skupina"], z["klic"]) or {}
            text = osoby_upravy.uloz_osobu(text, z["skupina"], z["klic"], {**stara, **hodnoty})
        else:
            stara = next((h for h, _ in osoby_upravy.otazky(text) if h.get("otazka") == z.get("puvodni")), {})
            text = osoby_upravy.uloz_otazku(text, z.get("puvodni"), {**stara, **hodnoty})
    if text is not None:
        compile(text, cesta_osob, "exec")   # pojistka: osoby.py musí zůstat platný Python
        with open(cesta_osob, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


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
        z["pole"] = {p: v for p, v in z["pole"].items() if v["bylo"] != v["je"] or z.get("akce") == "nove"}
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
    for rel in sorted(set(SOUBORY.values())) + [HISTORIE]:
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
        proved(plan)
    except (SystemExit, ValueError, SyntaxError) as e:
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
    print(f'uložit: git add {" ".join(soubory)} && git commit -m "Oprava: {o["duvod"].strip()[:80]}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
