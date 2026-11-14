#!/usr/bin/env python3
"""Mapa knihy: co které snímky svazku pokrývají (písmena rejstříku, roky, čísla zápisů), aby se z archivu stahovalo jen to, co je potřeba.

Mapa je jen RADA, kam jít (z dvou známých bodů odhadne snímek hledaného písmene nebo roku, jako při hledání ve slovníku). Nikdy
neuzavře hledání: „není tam“ vyžaduje přečíst stránky, které cíl ohraničují (R-NEG-001); pořadí v rejstřících a číslech zápisů nemusí být přísné.
Obsahuje jen navigační údaje o stránce (typ, od–do, kvalita, kdo a čím četl), žádné přepisy a jména lidí, proto je společná pro všechny projekty
na počítači: `rodokmen_mapy/<portál>/<svazek>.jsonl` vedle mezipaměti snímků (mimo její úklid; jen přidávání, poslední čtení snímku platí).

Použití (z kořene projektu):
  mapa.py hledej <portál> <svazek> (--pismeno F | --rok 1856 | --cislo 107) [--celkem N]
      -> JSON {stav: zname | odhad | mezera | nesouhlas | nezname, snimek, zdola, shora, precti, poznamka}; kód 1 = mapa o svazku nic neví
  mapa.py zapis <vysledek.json>      údaje o stránkách z výsledkového souboru čtenáře: {"model": …, "stranky": [{portal, svazek, snimek, typ, od, do, …}]}
  mapa.py stav <portál> <svazek>     kolik snímků mapa zná a kolik má popsaných
  mapa.py snimek <portál> <svazek> <n> [--zdroj cache|pracovni|prohlizec]    identita snímku (že ho máme), bez popisu obsahu
  mapa.py naplnit-z-pracovni [--slozka pracovni/aron]    identita snímků ze stažených svazků (název <apu8>_<signatura>/…_<pořadí>_sign-…)
  mapa.py naplnit-z-cache            identita snímků eBadatelny z mezipaměti (názvy ebadatelna/<druh>/<xid>/snNNNN.jpg)
Složku změní proměnná RODOKMEN_MAPY. Portál a svazek jsou jména bez lomítek (např. aron 03066862, první znaky apu).
"""
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cache  # noqa: E402 – kořen mezipaměti (mapa leží vedle ní, ne uvnitř)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPY = ("titul", "rejstřík", "zápisy", "prázdná", "jiné")
KVALITY = ("dobrá", "slabá", "nečitelná")
ZDROJE = ("cache", "pracovni", "prohlizec")
JMENO = re.compile(r"[\w.-]+")
ABECEDA = ["a", "b", "c", "č", "d", "e", "f", "g", "h", "ch", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "ř", "s", "š", "t", "u", "v", "w",
           "x", "y", "z", "ž"]


def koren():
    return os.environ.get("RODOKMEN_MAPY") or os.path.join(os.path.dirname(cache.KOREN), "rodokmen_mapy")


def _jmeno(x, co):
    if not isinstance(x, str) or not JMENO.fullmatch(x) or x.startswith(".."):
        raise ValueError(f"{co}: jméno bez lomítek a mezer (písmena, číslice, tečka, pomlčka, podtržítko)")
    return x


def cesta(portal, svazek):
    return os.path.join(koren(), _jmeno(portal, "portal"), _jmeno(svazek, "svazek") + ".jsonl")


def _pripoj(portal, svazek, udalost):
    p = cesta(portal, svazek)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(dict(cas=time.strftime("%Y-%m-%dT%H:%M:%S"), **udalost), ensure_ascii=False) + "\n")


def nacti(portal, svazek):
    """{snímek: popis}: události po sobě; poslední popis snímku platí, identita (zdroj) zůstává."""
    p = cesta(portal, svazek)
    out = {}
    try:
        with open(p, encoding="utf-8") as f:
            radky = f.read().splitlines()
    except OSError:
        return out
    for r in radky:
        try:
            e = json.loads(r)
        except ValueError:
            continue
        sn = e.get("sn")
        if not isinstance(sn, int):
            continue
        d = out.setdefault(sn, {"sn": sn})
        if e.get("udalost") == "snimek":
            d["zdroj"] = e.get("zdroj", d.get("zdroj"))
        elif e.get("udalost") == "strana":
            d.update({k: e[k] for k in ("typ", "od", "do", "sloupce", "kvalita", "kdo", "nastroj", "cas") if k in e})
    return out


def zapis_stranu(s, kdo="", nastroj=""):
    """Popis stránky z čtení; ValueError při špatném tvaru."""
    if not isinstance(s, dict):
        raise ValueError("strana: objekt")
    portal, svazek = _jmeno(s.get("portal"), "portal"), _jmeno(s.get("svazek"), "svazek")
    sn = s.get("snimek")
    if not isinstance(sn, int) or isinstance(sn, bool) or sn < 1:
        raise ValueError("snimek: celé číslo od 1")
    if s.get("typ") not in TYPY:
        raise ValueError(f"typ: {', '.join(TYPY)}")
    if s.get("kvalita", "dobrá") not in KVALITY:
        raise ValueError(f"kvalita: {', '.join(KVALITY)}")
    for pole in ("od", "do"):
        if pole in s and not (isinstance(s[pole], str) and len(s[pole]) <= 40):
            raise ValueError(f"{pole}: text do 40 znaků")
    ud = {"udalost": "strana", "sn": sn, "typ": s["typ"], "kvalita": s.get("kvalita", "dobrá"), "kdo": str(kdo)[:60], "nastroj": str(nastroj)[:60]}
    for pole in ("od", "do"):
        if s.get(pole):
            ud[pole] = s[pole]
    if isinstance(s.get("sloupce"), list):
        ud["sloupce"] = [str(x)[:30] for x in s["sloupce"]][:12]
    _pripoj(portal, svazek, ud)


def snimek(portal, svazek, n, zdroj="cache"):
    """Identita snímku (že ho máme), bez popisu obsahu; opakovaný zápis téhož zdroje se přeskočí."""
    if zdroj not in ZDROJE:
        raise ValueError(f"zdroj: {', '.join(ZDROJE)}")
    if not isinstance(n, int) or n < 1:
        raise ValueError("snimek: celé číslo od 1")
    if nacti(portal, svazek).get(n, {}).get("zdroj") == zdroj:
        return
    _pripoj(portal, svazek, {"udalost": "snimek", "sn": n, "zdroj": zdroj})


def snimek_bezpecne(portal, svazek, n, zdroj="cache"):
    """Pro nástroje, které stahují: identita nikdy nezastaví práci."""
    try:
        snimek(portal, svazek, n, zdroj)
    except Exception:   # noqa: BLE001
        pass


# ---------- klíče pro hledání ----------
def _pismena(t):
    t = unicodedata.normalize("NFC", (t or "").strip().casefold())
    out, i = [], 0
    while i < len(t):
        if t.startswith("ch", i):
            out.append(ABECEDA.index("ch"))
            i += 2
            continue
        c = t[i]
        if c not in ABECEDA:
            c = unicodedata.normalize("NFD", c)[0]
        if c in ABECEDA:
            out.append(ABECEDA.index(c))
        i += 1
    return out


def klic_pismeno(t):
    """Číselný klíč slova podle české abecedy (ch za h), do šesti písmen; pro odhad polohy v abecedním rejstříku."""
    p = _pismena(t)
    if not p:
        return None
    k = float(p[0])
    for i, x in enumerate(p[1:7], 1):
        k += x / (len(ABECEDA) ** i)
    return k


def klic_cislo(t):
    m = re.search(r"\d+", str(t or ""))
    return float(m.group(0)) if m else None


def hledej(portal, svazek, pismeno=None, rok=None, cislo=None, celkem=None):
    """Nejlepší další snímek pro písmeno, rok nebo číslo podle známých stránek svazku. Jen rada."""
    if pismeno is not None:
        cil, f = klic_pismeno(pismeno), klic_pismeno
    else:
        cil, f = float(rok if rok is not None else cislo), klic_cislo
    m = nacti(portal, svazek)
    body = []
    for sn, d in sorted(m.items()):
        if d.get("typ") in ("rejstřík", "zápisy") and d.get("od") and d.get("do"):
            od, do = f(d["od"]), f(d["do"])
            if od is not None and do is not None:
                body.append((sn, min(od, do), max(od, do)))
    nota = "rada, ne důkaz: hledání se uzavře až čtením stránek, které cíl ohraničují (R-NEG-001)"
    for sn, od, do in body:
        if od <= cil <= do:
            return {"stav": "zname", "snimek": sn, "poznamka": f"snímek {sn} už je popsaný a cíl pokrývá; {nota}"}
    dole = [b for b in body if b[2] < cil]
    nahore = [b for b in body if b[1] > cil]
    L = max(dole, key=lambda b: b[2]) if dole else None
    U = min(nahore, key=lambda b: b[1]) if nahore else None
    if L and U:
        if U[0] <= L[0]:
            return {"stav": "nesouhlas", "precti": sorted({L[0], U[0]}), "poznamka": "pořadí snímků neodpovídá hodnotám – přečti okolí; " + nota}
        if U[0] - L[0] <= 1:
            return {"stav": "mezera", "precti": [L[0], U[0]], "poznamka": "mezi snímky " + f"{L[0]} a {U[0]} nic není – cíl je na jednom z nich; " + nota}
        zlomek = (cil - L[2]) / (U[1] - L[2]) if U[1] != L[2] else 0.5
        sn = max(L[0] + 1, min(U[0] - 1, L[0] + round((U[0] - L[0]) * zlomek)))
        return {"stav": "odhad", "snimek": sn, "zdola": L[0], "shora": U[0], "poznamka": nota}
    if L:
        sn = min(celkem, L[0] + max(1, (celkem - L[0]) // 2)) if celkem else L[0] + 10
        return {"stav": "odhad", "snimek": sn, "zdola": L[0], "poznamka": "známe jen začátek; " + nota}
    if U:
        return {"stav": "odhad", "snimek": max(1, U[0] - max(1, U[0] // 2)), "shora": U[0], "poznamka": "známe jen konec; " + nota}
    return {"stav": "nezname", "snimek": (celkem // 2) if celkem else 1,
            "poznamka": "mapa o svazku nic neví: začni titulem (snímek 1) nebo půlením svazku a výsledek zapiš (mapa.py zapis)"}


def stav(portal, svazek):
    m = nacti(portal, svazek)
    return {"portal": portal, "svazek": svazek, "snimku": len(m), "popsano": len([d for d in m.values() if d.get("typ")]),
            "zdroje": sorted({d.get("zdroj") for d in m.values() if d.get("zdroj")})}


def _celkem(svazek):
    try:
        with open(os.path.join(ROOT, "data", "svazky.json"), encoding="utf-8-sig") as f:
            return int(json.load(f).get(svazek, {}).get("snimku") or 0) or None
    except (OSError, ValueError, AttributeError):
        return None


def naplnit_z_pracovni(slozka):
    n = 0
    if not os.path.isdir(slozka):
        return n
    for jmeno in sorted(os.listdir(slozka)):
        m = re.fullmatch(r"([0-9a-f]{8})_(.+)", jmeno)
        sv = os.path.join(slozka, jmeno)
        if not (m and os.path.isdir(sv)):
            continue
        for f in sorted(os.listdir(sv)):
            c = re.search(r"_(\d{3,5})_sign", f) or re.search(r"_(\d{4,5})(?:\.\w+)?$", f)
            if c:
                snimek("aron", m.group(1), int(c.group(1)), "pracovni")
                n += 1
    return n


def naplnit_z_cache():
    n = 0
    zaklad = os.path.join(cache.KOREN, "ebadatelna")
    for druh in sorted(os.listdir(zaklad)) if os.path.isdir(zaklad) else []:
        for xid in sorted(os.listdir(os.path.join(zaklad, druh))):
            for f in sorted(os.listdir(os.path.join(zaklad, druh, xid))):
                c = re.fullmatch(r"sn(\d{4})\.jpg", f)
                if c:
                    snimek("ebadatelna", f"{druh}-{xid}", int(c.group(1)), "cache")
                    n += 1
    return n


def _arg(a, nazev, vychozi=None):
    return a[a.index(nazev) + 1] if nazev in a and a.index(nazev) + 1 < len(a) else vychozi


def main(argv=None):
    a = sys.argv[1:] if argv is None else list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    try:
        if a[0] == "hledej":
            portal, svazek = a[1], a[2]
            kw = {"pismeno": _arg(a, "--pismeno")}
            if _arg(a, "--rok"):
                kw["rok"] = int(_arg(a, "--rok"))
            if _arg(a, "--cislo"):
                kw["cislo"] = int(_arg(a, "--cislo"))
            if kw["pismeno"] is None and "rok" not in kw and "cislo" not in kw:
                print("hledej: --pismeno, --rok nebo --cislo", file=sys.stderr)
                return 2
            kw["celkem"] = int(_arg(a, "--celkem") or 0) or _celkem(svazek)
            r = hledej(portal, svazek, **kw)
            print(json.dumps(r, ensure_ascii=False))
            return 1 if r["stav"] == "nezname" else 0
        if a[0] == "zapis":
            with open(a[1], encoding="utf-8-sig") as f:
                d = json.load(f)
            for s in d.get("stranky") or []:
                zapis_stranu(s, kdo=d.get("model", "neznámý"), nastroj=d.get("nastroj", ""))
            print(f"zapsáno {len(d.get('stranky') or [])} stránek")
            return 0
        if a[0] == "stav":
            print(json.dumps(stav(a[1], a[2]), ensure_ascii=False))
            return 0
        if a[0] == "snimek":
            snimek(a[1], a[2], int(a[3]), _arg(a, "--zdroj", "cache"))
            return 0
        if a[0] == "naplnit-z-pracovni":
            print(f"identita {naplnit_z_pracovni(_arg(a, '--slozka', os.path.join(ROOT, 'pracovni', 'aron')))} snímků")
            return 0
        if a[0] == "naplnit-z-cache":
            print(f"identita {naplnit_z_cache()} snímků")
            return 0
    except (ValueError, IndexError, OSError) as e:
        print(f"mapa: {e}", file=sys.stderr)
        return 2
    print(f"neznámý příkaz {a[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
