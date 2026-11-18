#!/usr/bin/env python3
"""Zápis jednoho nálezu z matriky jedním příkazem: snímek → výřez → rámeček → zápis s účastníky + přepis → odkazy u osob → deník.

Podle návrhu z originálu (sarsonj/rodokmen-skill#187, nalez.py), napojeno na deník forku (data/denik.jsonl, tools/denik.py)
a na účastníky zápisu (tools/ucastnici.py; tak se zápis přiřadí i osobám z RODINA). Dřív 6–7 samostatných příkazů, na které
se zapomínalo (přepis, rámeček, odkaz u osoby, deník) a výřez jednou vznikl ze zmenšeného snímku.

Použití (z kořene projektu):
  nalez.py nahled <vstup.json>   stáhne snímek v plném rozlišení, udělá výřez a rámeček a vypíše kontrolní obrázek; data
                                 nemění (zdroje/, vyrezy/ a zvyrazneni.json přepíše – tak se ladí souřadnice)
  nalez.py zapis  <vstup.json>   totéž a zapíše zápis, přepis, odkazy u osob a řádek deníku – všechno, nebo nic
      --prepsat   zápis se stejným klíčem už existuje a má se nahradit (jinak nástroj skončí)

Vstup (napiš ho nástrojem Write do pracovni/; jména a čísla jsou smyšlená):
{
  "klic":     "lhota_krest_josef_vzorny_1812",            klíč zápisu (malá písmena, obec_druh_jmeno_rok)
  "apu":      "<celé apu_id svazku v ARONu>", "snimek": 40,  ARON: svazek i odkaz doplní nástroj sám
      … nebo jiný archiv: "obraz": "pracovni/x.jpg", "svazek": "<klíč v data/svazky.json>", "odkaz": "https://…", "snimek": 40
  "vyrez":    [0, 0.25, 0.75, 0.40],                       zlomky celé stránky (velkoryse: hlavička sloupců, okraje)
  "kontrast": false,                                       vybledlý zápis
  "ramecek":  [[0, 0.30, 1, 0.62]],                        zlomky VÝŘEZU – kde přesně je čtený zápis
  "ramecek_pozn": "zápis č. 7",
  "zaznam":   {"druh": "N|O|Z|S", "datum": "17. 3. 1812", "nazev": "Křest Josefa (1812)", "shrnuti": "…",
               "ucastnici": [{"osoba": "8", "role": "křtěnec"}, {"osoba": "marie-vzorna", "role": "kmotr"}]},
  "prepis":   {"orig": "…", "cs": "…"},
  "osoby":    [8],                                         nepovinné: odkaz `r` u osob v P (číslo) nebo SIDE (část jména)
  "denik":    {"datum": "2026-11-18", "zdroj_typ": "archiv", "zdroj": "ARON, N Lhota 1800–1825", "rozsah": "sn. 38–45",
               "hledano": "křest Josefa Vzorného", "vysledek": "nalezeno", "nalez": "…", "citace": "…", "osoby": ["8"],
               "overeno": false}
}
Zápis musí patřit aspoň jedné osobě: přes „ucastnici“ (doporučeno, i RODINA) nebo „osoby“. Fakta osob se tu nezapisují –
`tools/oprava.py`. Po „zapis“ spusť `tools/kontrola.py` a VŽDY si prohlédni kontrolní obrázek rámečku.
"""
import ast
import json
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)   # -I nepřidává složku skriptu
import denik  # noqa: E402
import ucastnici  # noqa: E402
import zaznamy_store as store  # noqa: E402

PRAC = os.path.join(ROOT, "pracovni", "nalez")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
DRUHY = {"N", "O", "Z", "S"}
ZALOHA = ("zaznamy.json", "prepisy.json", "svazky.json", "zvyrazneni.json", "osoby.py", "denik.jsonl")


class Odmitnuto(Exception):
    pass


def nastroj(*args, vystup=False):
    """Spustí jiný nástroj z tools/ stejným Pythonem; při chybě vyhodí Odmitnuto s jeho hláškou."""
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(TOOLS, args[0]), *map(str, args[1:])],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise Odmitnuto(f"{args[0]} skončil chybou:\n{(r.stderr or r.stdout).strip()}")
    if not vystup and r.stdout.strip():
        print("  " + r.stdout.strip().splitlines()[-1])
    return r.stdout


def jload(nazev, vychozi):
    p = os.path.join(ROOT, "data", nazev)
    return json.load(open(p, encoding="utf-8-sig")) if os.path.exists(p) else vychozi


def ctverice(v, co):
    if not (isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v)
            and 0 <= v[0] < v[2] <= 1 and 0 <= v[1] < v[3] <= 1):
        raise Odmitnuto(f"{co}: čekám [x0, y0, x1, y1] jako zlomky 0..1 (x0 < x1, y0 < y1), dostal jsem {v}.")


def nacti_osoby():
    src = open(os.path.join(ROOT, "data", "osoby.py"), encoding="utf-8-sig").read()
    ns = {}
    try:
        ast.parse(src)
        exec(compile(src, "data/osoby.py", "exec"), ns)
    except Exception as e:   # noqa: BLE001
        raise Odmitnuto(f"data/osoby.py nejde načíst ({e}) – oprav ho nejdřív.")
    return ns


def over_osobu_pro_odkaz(cil, ns):
    """Stejná pravidla jako zapis.py odkaz: číslo z P, nebo jednoznačná část jména z SIDE."""
    if isinstance(cil, int) or (isinstance(cil, str) and cil.isdigit()):
        if int(cil) not in ns.get("P", {}):
            raise Odmitnuto(f"osoby: {cil} v P (data/osoby.py) není.")
        return
    shody = [s.get("n") for s in ns.get("SIDE", []) if str(cil).lower() in str(s.get("n", "")).lower()]
    if len(shody) != 1:
        raise Odmitnuto(f"osoby: bočního příbuzného „{cil}“ " + ("v SIDE není (osoby z RODINA patří do zaznam.ucastnici)." if not shody
                        else "je víc: " + "; ".join(shody) + " – napiš delší část jména."))


def radek_deniku(d, zaznamy):
    """Řádek deníku stejně jako denik.py pridej; kontrola předem, nic nezapisuje."""
    if not isinstance(d, dict):
        raise Odmitnuto("denik: objekt (datum, zdroj_typ, zdroj, hledano, vysledek, …)")
    z = {"id": max([x["id"] for x in zaznamy], default=0) + 1, "datum": d.get("datum"),
         "zdroj": {"typ": d.get("zdroj_typ"), "text": d.get("zdroj")}, "rozsah": d.get("rozsah") or "",
         "hledano": d.get("hledano"), "vysledek": d.get("vysledek")}
    if d.get("overeno"):
        z["overeno"] = True
    for pole in ("nalez", "citace", "poznamka", "odkaz"):
        if d.get(pole):
            z[pole] = d[pole]
    if d.get("osoby"):
        z["osoby"] = [str(x) for x in d["osoby"]]
    verze = denik.verze_nastroje()
    if verze:
        z["nastroj"] = verze
    ch = denik.over_zaznam(z, {x["id"] for x in zaznamy}) + denik.over_osoby(z.get("osoby", []))
    if ch:
        raise Odmitnuto("denik: " + "; ".join(ch))
    return z


def over(v, prepsat, zapis):
    """Všechno zkontrolovat dřív, než se cokoli stáhne nebo zapíše. Vrací připravený řádek deníku (nebo None)."""
    klic = v.get("klic", "")
    if not re.fullmatch(r"[a-z0-9_]+", str(klic)):
        raise Odmitnuto(f"Klíč „{klic}“: jen malá písmena bez diakritiky, číslice a podtržítka (obec_druh_jmeno_rok).")
    if "apu" in v:
        if not UUID.fullmatch(str(v["apu"])):
            raise Odmitnuto(f"apu „{v['apu']}“ není celé apu_id ARONu (8-4-4-4-12 znaků).")
        if not isinstance(v.get("snimek"), int):
            raise Odmitnuto("U ARONu chybí číslo snímku „snimek“ (celé číslo).")
    else:
        for f in ("obraz", "svazek", "odkaz"):
            if not v.get(f):
                raise Odmitnuto(f"Bez „apu“ (jiný archiv než ARON) potřebuji „obraz“, „svazek“ a „odkaz“ – chybí „{f}“.")
        if not os.path.exists(os.path.join(ROOT, v["obraz"])):
            raise Odmitnuto(f"Obraz {v['obraz']} neexistuje.")
        if v["svazek"] not in jload("svazky.json", {}):
            raise Odmitnuto(f"Svazek „{v['svazek']}“ není v data/svazky.json – zapiš ho nejdřív (zapis.py svazky nebo svazky.py).")
    if "vyrez" in v:
        ctverice(v["vyrez"], "vyrez")
    ramecky = v.get("ramecek") or []
    if not ramecky:
        raise Odmitnuto("Chybí „ramecek“ – seznam aspoň jednoho rámečku [[x0, y0, x1, y1]] ve zlomcích výřezu.")
    for r in ramecky:
        ctverice(r, "ramecek")
    if not zapis:
        return None
    z = v.get("zaznam") or {}
    for f in ("druh", "datum", "nazev", "shrnuti"):
        if not str(z.get(f) or "").strip():
            raise Odmitnuto(f"V „zaznam“ chybí „{f}“.")
    if z["druh"] not in DRUHY:
        raise Odmitnuto(f"druh „{z['druh']}“ musí být jeden z {', '.join(sorted(DRUHY))} (narození, oddaní, zemřelí, sčítání).")
    p = v.get("prepis") or {}
    if not (str(p.get("orig") or "").strip() and str(p.get("cs") or "").strip()):
        raise Odmitnuto("V „prepis“ chybí „orig“ (doslovný přepis) nebo „cs“ (překlad) – každý zápis má mít obojí.")
    if any(x.get("klic") == klic for x in jload("zaznamy.json", [])) and not prepsat:
        raise Odmitnuto(f"Zápis „{klic}“ už v data/zaznamy.json je. Chceš-li ho nahradit, přidej --prepsat.")
    ns = nacti_osoby()
    if z.get("ucastnici"):
        ch = ucastnici.over({"klic": klic, "ucastnici": z["ucastnici"]}, ns)
        if ch:
            raise Odmitnuto("zaznam.ucastnici: " + "; ".join(ch))
    osoby = v.get("osoby") or []
    if not osoby and not any(isinstance(u, dict) and u.get("osoba") is not None for u in z.get("ucastnici") or []):
        raise Odmitnuto("Zápis nepatří žádné osobě: doplň „zaznam.ucastnici“ (osoba a role) nebo „osoby“. "
                        "Zápis, který nikdo necituje, kontrola hlásí.")
    for o in osoby:
        over_osobu_pro_odkaz(o, ns)
    if v.get("denik") is None:
        return None
    zaznamy, chyby = denik.nacti_zaznamy()
    if chyby:
        raise Odmitnuto("data/denik.jsonl má chyby, nejdřív je oprav (denik.py over): " + "; ".join(chyby[:5]))
    return radek_deniku(v["denik"], zaznamy)


def obrazky(v):
    klic = v["klic"]
    os.makedirs(PRAC, exist_ok=True)
    if "apu" in v:
        obraz = os.path.join(PRAC, f"{v['apu'][:8]}_{v['snimek']:04d}.jpg")
        print(f"1/3 snímek {v['snimek']} z ARONu v plném rozlišení …")
        nastroj("aron_img.py", v["apu"], v["snimek"], 0, obraz)
    else:
        obraz = os.path.join(ROOT, v["obraz"])
    print("2/3 výřez …")
    args = ["vyrez.py", obraz, klic]
    if "vyrez" in v:
        args.append(",".join(str(x) for x in v["vyrez"]))
    if v.get("kontrast"):
        args.append("--kontrast")
    nastroj(*args)
    print("3/3 rámeček …")
    args = ["ramecek.py", klic, *(",".join(str(x) for x in r) for r in v["ramecek"])]
    if v.get("ramecek_pozn"):
        args += ["--pozn", v["ramecek_pozn"]]
    nastroj(*args, vystup=True)
    return os.path.join(ROOT, "pracovni", f"ramecek_{klic}.jpg")


def zapis_json(soubor, klic, obj, prepsat):
    p = os.path.join(PRAC, f"{klic}.{soubor}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    nastroj("zapis.py", soubor, klic, p, *(["--prepsat"] if prepsat else []))


def data(v, radek, prepsat):
    klic = v["klic"]
    if "apu" in v:
        svazek = v["apu"][:8]
        if svazek not in jload("svazky.json", {}):
            print("svazek …")
            nastroj("aron_img.py", v["apu"], "svazek")
        odkaz = nastroj("aron_img.py", v["apu"], "link", v["snimek"], vystup=True).strip().splitlines()[-1]
    else:
        svazek, odkaz = v["svazek"], v["odkaz"]
    z = v["zaznam"]
    print("zápis, přepis …")
    obj = {"klic": klic, "svazek": svazek, "snimek": v.get("snimek", ""), "druh": z["druh"], "datum": z["datum"],
           "nazev": z["nazev"], "shrnuti": z["shrnuti"], "odkaz": odkaz}
    if z.get("ucastnici"):
        obj["ucastnici"] = z["ucastnici"]
    zapis_json("zaznamy", klic, obj, prepsat)
    zapis_json("prepisy", klic, {"orig": v["prepis"]["orig"], "cs": v["prepis"]["cs"]}, prepsat)
    for o in v.get("osoby") or []:
        print("odkaz u osoby …")
        nastroj("zapis.py", "odkaz", o, klic)
    if radek:
        with store.Zamek(denik.LOG):
            store.pridej_radek(denik.LOG, radek)
        print(f"  deník: záznam {radek['id']} uložen")


def zaloha():
    out = {}
    for n in ZALOHA:
        p = os.path.join(ROOT, "data", n)
        out[p] = open(p, "rb").read() if os.path.exists(p) else None
    return out


def obnov(stav):
    for p, obsah in stav.items():
        if obsah is None:
            if os.path.exists(p):
                os.remove(p)
        else:
            with open(p, "wb") as f:
                f.write(obsah)


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    prepsat = "--prepsat" in a
    a = [x for x in a if x != "--prepsat"]
    if len(a) != 2 or a[0] not in ("nahled", "zapis"):
        print(__doc__)
        return 2
    try:
        v = json.load(open(a[1], encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        print(f"Vstup {a[1]} není platný JSON: {e}")
        return 1
    zapis = a[0] == "zapis"
    try:
        radek = over(v, prepsat, zapis)
    except Odmitnuto as e:
        print(f"ODMÍTNUTO, nic se nestáhlo ani nezapsalo: {e}")
        return 1
    stav = zaloha()
    try:
        kontrolni = obrazky(v)
        if zapis:
            data(v, radek, prepsat)
    except Odmitnuto as e:
        obnov(stav)
        print(f"ZAPSÁNO NIC (data vrácena): {e}")
        return 1
    if zapis:
        print(f"Hotovo: {v['klic']}" + (f", deník {radek['id']}" if radek else
                                        " (řádek deníku nebyl ve vstupu – přidej ho přes tools/denik.py pridej)") + ".")
        print("Teď: python -I -X utf8 tools/kontrola.py; fakta osob přes tools/oprava.py")
    print(f"Prohlédni kontrolní obrázek rámečku: {kontrolni}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
