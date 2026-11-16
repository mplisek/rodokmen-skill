#!/usr/bin/env python3
"""Kontrakt mezi řídicím agentem, čtenářem a ověřovatelem (analyza/navrh-optimalizace.md, etapa E1). Tento soubor je jediný zdroj tvaru
zadání, nálezu a ověření: kontroluje je dřív, než se zaplatí další práce, a z nálezu dělá souhrn a porovnání dvou čtení. Jen čte.

Použití (z kořene projektu):
  python3 -I tools/vysledek.py over <soubor.json>        zkontroluje zadání, nález nebo ověření (podle pole "schema"); kód 1 a seznam chyb
  python3 -I tools/vysledek.py souhrn <U-0042|soubor>    krátký souhrn nálezu pro řídicího agenta (stav, co chybí, rozpory, rozsah, další krok)
  python3 -I tools/vysledek.py porovnej <U-0042> <čtení> porovná první čtení s ověřením naslepo po polích; kód 1 při neshodě
  python3 -I tools/vysledek.py vzor zadani|nalez|overeni|rozhodnuti   vyplněný příklad a výčty dovolených hodnot
  python3 -I tools/vysledek.py pripoj <U-0042> <část.json>  pokračování: další část nálezu (cast o 1 vyšší) připojí k nálezu úkolu; první část zůstává
  (souhrn a porovnej umí --json)

Soubory: zadání `pracovni/zadani/<úkol>.json`, nález `pracovni/vysledky/<úkol>.json`, ověření `pracovni/vysledky/<úkol>_overeni_<čtení>.json`.

Co kontrola hlídá navíc k tvaru: osoby jen klíčem z data/osoby.py (ne jménem); svazek jen klíčem z data/svazky.json (ne signaturou);
čtení jen v zadaném rozsahu; pramen musí hledanou roli vést (svazky.json → "pokryva": {"role": ["ženich"]}); „nenalezeno“ jen po dočtení
celého rozsahu; dosažený strop, nedostupný portál a nečitelný snímek jsou jiné stavy než „nenalezeno“.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

UKOL = re.compile(r"U-\d{4}")
STAVY = ("nalezeno", "částečně", "nečitelné", "nenalezeno", "nedostupné", "rozpočet", "vyvráceno", "chyba prostředí")
STAVY_BEHU = ("dočteno", "strop", "překážka")
BEZ_ROZSAHU = ("nedostupné", "chyba prostředí")          # u těchto stavů se nic nečetlo
TYPY_STRAN = ("titul", "rejstřík", "zápisy", "prázdná", "jiné")
KVALITY = ("dobrá", "slabá", "nečitelná")
ROLE = ("křtěnec", "otec", "matka", "ženich", "nevěsta", "zemřelý", "kmotr", "svědek", "jiné")
VEREJNE = ("zdroje/", "vyrezy/", "web/", "data/")        # sem čtenář nezapisuje

VZORY = {
    "zadani": {
        "schema": "zadani/1", "ukol": "U-0101", "otazka": "Najdi křest osoby 88 a přečti rodiče a kmotry.", "hleda_roli": "křtěnec",
        "osoby": [{"id": "88", "role": "křtěnec", "znaky": "* asi 1812, otec chalupník, Lhota čp. 5"}],
        "nezamenit_s": [{"id": "josef-vzorny-1809", "znaky": "* 1809, otec mlynář, Lhota čp. 12"}],
        "pramen": {"portal": "aron", "svazek": "0a1b2c3d"}, "rozsah": {"snimky": [40, 52]},
        "vratit": ["datum", "misto", "cp", "otec", "matka", "kmotri"], "strop": {"kroku": 12, "snimku": 12}},
    "nalez": {
        "schema": "nalez/1", "ukol": "U-0101", "cast": 1, "stav": "částečně", "stav_behu": "dočteno",
        "cteni": [{"id": "c1", "zdroj": {"portal": "aron", "svazek": "0a1b2c3d", "snimek": 46, "strana": "fol. 23v", "radek": 7},
                   "vyrez": "pracovni/vysledky/U-0101_vyrezy/c1_a.jpg",
                   "doslova": {"datum": "17. Martii 1812", "dite": "Josephus", "otec": "Joannes Wzorny chalupnik"},
                   "normalizace": {"datum": "1812-03-17", "dite": "Josef", "otec": "Jan Vzorný"},
                   "nejistota": {"otec": "příjmení na konci řádku"}, "chybi": ["kmotri"]}],
        "kandidati": [{"osoba": "88", "cteni": "c1", "pro": ["jméno", "rok", "čp. 5"], "proti": []}],
        "prohledano": [{"svazek": "0a1b2c3d", "snimky": [44, 46], "uplne": False}],
        "stranky": [{"portal": "aron", "svazek": "0a1b2c3d", "snimek": 46, "typ": "zápisy", "od": "1812-02", "do": "1812-04", "kvalita": "dobrá"}],
        "navrh_dalsiho_kroku": {"typ": "sousední strana", "snimek": 47, "duvod": "řádek 7 pokračuje vpravo (kmotři)"},
        "cerpani": {"kroku": 6, "snimku": 3}},
    "overeni": {
        "schema": "overeni/1", "ukol": "U-0101", "cteni": "c1", "vyrezy": ["pracovni/vysledky/U-0101_vyrezy/c1_a.jpg"],
        "doslova": {"datum": "17. Martii 1812", "dite": "Josephus", "otec": "Joannes Wzorny"},
        "nejistota": {"otec": "konec slova v hřbetu knihy"}, "necitelne": []},
}
VZORY["rozhodnuti"] = {
    "schema": "rozhodnuti/1", "ukol": "U-0101", "vysledek": "nalezeno", "dod_splneno": True, "uzavrit": True, "dukaz": ["c1"], "model": "sonnet",
    "denik": {"zdroj": "ARON, Lhota: kniha narozených 1800–1825, sn. 46", "hledano": "Křest Josefa Vzorného (88)",
              "nalez": "Křest 17. 3. 1812 ve Lhotě čp. 5, rodiče Jan a Anna.", "rozsah": "snímky 44–47", "osoby": ["88"], "overeno": True},
    "zaznam": {"klic": "lhota_krest_josef_vzorny_1812", "svazek": "0a1b2c3d", "snimek": 46, "druh": "N", "datum": "17. 3. 1812",
               "nazev": "Křest Josefa Vzorného, Lhota čp. 5", "shrnuti": "Rodiče Jan Vzorný, chalupník, a Anna.", "odkaz": "https://…",
               "ucastnici": [{"osoba": "88", "role": "křtěnec"}, {"jmeno": "Václav Ukázka", "role": "kmotr"}],
               "prepis": {"orig": "17. Martii 1812 …", "cs": "17. března 1812 …"}},
    "identita": {"osoba": "88", "proc": "jméno, rok, čp. 5 a povolání otce; jmenovec z čp. 12 má otce mlynáře", "vylouceno": ["josef-vzorny-1809"]},
    "tvrzeni": [{"typ": "narozeni", "osoby": ["88"], "jistota": "doc", "text": "* 17. 3. 1812 Lhota čp. 5", "dukaz": ["c1"]}],
    "navazujici": [{"text": "Kdo byl kmotr Václav Ukázka?", "os": ["88"], "typ": "kmotr"}],
    "hotovo": {"spotreba": "M"}}
VYSLEDKY_DENIKU = ("nalezeno", "vyvráceno", "nenalezeno", "částečně", "nečitelné")
DRUHY_ZAPISU = ("N", "O", "Z", "S")
TYPY_TVRZENI = ("narozeni", "umrti", "snatek", "rodic", "partner", "kmotr", "svedek", "totozny", "bydliste", "povolani", "jine")
JISTOTY = ("doc", "prob", "fam", "mh")
VYCTY = {"stav": STAVY, "stav_behu": STAVY_BEHU, "typ stránky": TYPY_STRAN, "kvalita": KVALITY, "role": ROLE, "typ tvrzení": TYPY_TVRZENI,
         "jistota": JISTOTY}


# ---------- data projektu ----------
def _json(*cesta):
    try:
        with open(os.path.join(ROOT, *cesta), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def zname_osoby():
    """Klíče osob jako texty, nebo None, když data/osoby.py není (pak se osoby nekontrolují)."""
    try:
        ns = {}
        with open(os.path.join(ROOT, "data", "osoby.py"), encoding="utf-8-sig") as f:
            exec(f.read(), ns)
    except Exception:
        return None
    return {str(k) for n in ("P", "RODINA", "SAME") for k in (ns.get(n) or {})}


def svazky():
    d = _json("data", "svazky.json")
    return d if isinstance(d, dict) else None


def podle_signatury(text, sv):
    """Klíče svazků, jejichž popis nese danou signaturu (pro nápovědu, když čtenář napíše signaturu místo klíče)."""
    t = re.escape(str(text).strip())
    return [k for k, v in (sv or {}).items() if re.search(rf"sign\.?:?\s*{t}(?![\w])", str(v.get("svazek", "")))]


def over_svazek(hodnota, kde, sv, ch):
    if not isinstance(hodnota, str) or not hodnota.strip():
        ch.append(f"{kde}: klíč svazku (text)")
        return
    if sv is None or hodnota in sv:
        return
    kand = podle_signatury(hodnota, sv)
    ch.append(f"{kde}: „{hodnota}“ není klíč svazku z data/svazky.json" + (
        f"; je to signatura, klíč je {' nebo '.join(kand)}" if kand else " (klíč je začátek ID svazku na portálu, např. 0a1b2c3d, ne signatura)"))


def over_osobu(hodnota, kde, zname, ch):
    if not isinstance(hodnota, (str, int)) or isinstance(hodnota, bool) or not str(hodnota).strip():
        ch.append(f"{kde}: klíč osoby")
    elif zname is not None and str(hodnota) not in zname:
        ch.append(f"{kde}: „{hodnota}“ není v data/osoby.py; uveď klíč osoby (číslo předka nebo zkratka z RODINA), ne jméno")


def rozpeti(x, kde, ch):
    if not (isinstance(x, list) and len(x) == 2 and all(isinstance(i, int) and not isinstance(i, bool) and i >= 1 for i in x) and x[0] <= x[1]):
        ch.append(f"{kde}: dvojice čísel snímků [od, do], např. [40, 52]")
        return None
    return x


def texty(d, kde, ch, povinne=False):
    if d is None and not povinne:
        return
    if not isinstance(d, dict) or (povinne and not d) or not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in d.items()):
        ch.append(f"{kde}: objekt pole → text" + (" (aspoň jedno pole)" if povinne else ""))


def cesta_zadani(ukol):
    return os.path.join(ROOT, "pracovni", "zadani", f"{ukol}.json")


def cesta_nalezu(ukol):
    return os.path.join(ROOT, "pracovni", "vysledky", f"{ukol}.json")


def cesta_overeni(ukol, cteni):
    return os.path.join(ROOT, "pracovni", "vysledky", f"{ukol}_overeni_{cteni}.json")


def cesty_overeni(ukol, cteni):
    """Všechna ověření naslepo jednoho čtení: `<úkol>_overeni_<čtení>.json` a dodatečná `<úkol>_overeni_<čtení>_<cokoli>.json`
    (třetí čtení z lepších výřezů, silnějším modelem)."""
    import glob
    zaklad = cesta_overeni(ukol, cteni)
    dalsi = sorted(glob.glob(os.path.join(ROOT, "pracovni", "vysledky", glob.escape(f"{ukol}_overeni_{cteni}_") + "*.json")))
    return ([zaklad] if os.path.exists(zaklad) else []) + dalsi


def nacti_overeni(ukol, cteni):
    """(cesty, dokumenty, kopie): ověření jednoho čtení; soubor se stejným obsahem jako dřívější (kopie pod jiným názvem) se
    nepočítá jako další čtení a vrátí se v „kopie“."""
    cesty, docs, kopie, videno = [], [], [], set()
    for p in cesty_overeni(ukol, cteni):
        d = nacti(p)
        klic = json.dumps(d, sort_keys=True, ensure_ascii=False)
        if klic in videno:
            kopie.append(os.path.basename(p))
            continue
        videno.add(klic)
        cesty.append(p)
        docs.append(d)
    return cesty, docs, kopie


def nacti(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except OSError:
        sys.exit(f"{path}: soubor nejde přečíst")
    except ValueError as e:
        sys.exit(f"{path}: není platný JSON ({e})")
    if not isinstance(d, dict):
        sys.exit(f"{path}: čeká se objekt")
    return d


# ---------- kontroly ----------
def pokryti(svazek, role, sv):
    """Věta, proč pramen hledanou roli nevede, nebo None."""
    vede = ((sv or {}).get(svazek) or {}).get("pokryva", {}).get("role")
    if isinstance(vede, list) and vede and role and role not in vede:
        return f"svazek {svazek} vede jen: {', '.join(vede)}; roli „{role}“ v něm hledat nelze (jiný pramen)"
    return None


def over_zadani(d):
    ch, zname, sv = [], zname_osoby(), svazky()
    if not (isinstance(d.get("ukol"), str) and UKOL.fullmatch(d["ukol"])):
        ch.append("ukol: ID úkolu ve tvaru U-0042")
    if not (isinstance(d.get("otazka"), str) and d["otazka"].strip()):
        ch.append("otazka: jedna věta, co se má zjistit")
    if d.get("hleda_roli") not in ROLE:
        ch.append(f"hleda_roli: {', '.join(ROLE)}")
    os_ = d.get("osoby")
    if not (isinstance(os_, list) and os_ and all(isinstance(o, dict) for o in os_)):
        ch.append("osoby: seznam {id, role, znaky}")
    else:
        for i, o in enumerate(os_):
            over_osobu(o.get("id"), f"osoby[{i}].id", zname, ch)
            if o.get("role") not in ROLE:
                ch.append(f"osoby[{i}].role: {', '.join(ROLE)}")
    for i, o in enumerate(d.get("nezamenit_s") or []):
        if not (isinstance(o, dict) and isinstance(o.get("znaky"), str) and o["znaky"].strip()):
            ch.append(f"nezamenit_s[{i}]: {{id, znaky}} – znaky, podle kterých se jmenovec pozná")
    pr = d.get("pramen")
    if not isinstance(pr, dict) or not isinstance(pr.get("portal"), str):
        ch.append("pramen: {portal, svazek}")
    else:
        over_svazek(pr.get("svazek"), "pramen.svazek", sv, ch)
        p = pokryti(pr.get("svazek"), d.get("hleda_roli"), sv)
        if p:
            ch.append("pramen: " + p)
    rozpeti((d.get("rozsah") or {}).get("snimky") if isinstance(d.get("rozsah"), dict) else None, "rozsah.snimky", ch)
    for i, r in enumerate(d.get("rozsireni") or []):
        rozpeti(r.get("snimky") if isinstance(r, dict) else None, f"rozsireni[{i}].snimky", ch)
    if not (isinstance(d.get("vratit"), list) and d["vratit"] and all(isinstance(x, str) and x for x in d["vratit"])):
        ch.append("vratit: seznam polí, která má čtenář přečíst")
    st = d.get("strop")
    if st is not None and not (isinstance(st, dict) and all(isinstance(st.get(k), int) and st[k] > 0 for k in ("kroku", "snimku"))):
        ch.append("strop: {kroku, snimku} kladná čísla")
    return ch


def dovoleny_rozsah(zadani):
    """Seznam [od, do] snímků svazku zadání včetně schválených rozšíření."""
    out = []
    for r in [zadani.get("rozsah") or {}] + list(zadani.get("rozsireni") or []):
        s = r.get("snimky") if isinstance(r, dict) else None
        if isinstance(s, list) and len(s) == 2:
            out.append(s)
    return out


def over_nalez(d, zadani=None):
    ch, zname, sv = [], zname_osoby(), svazky()
    if not (isinstance(d.get("ukol"), str) and UKOL.fullmatch(d["ukol"])):
        ch.append("ukol: ID úkolu ve tvaru U-0042")
    if not (isinstance(d.get("cast"), int) and d["cast"] >= 1):
        ch.append("cast: pořadí části od 1")
    stav, beh = d.get("stav"), d.get("stav_behu")
    if stav not in STAVY:
        ch.append(f"stav: {', '.join(STAVY)}")
    if beh not in STAVY_BEHU:
        ch.append(f"stav_behu: {', '.join(STAVY_BEHU)}")
    cteni, idc = d.get("cteni") or [], set()
    if not isinstance(cteni, list):
        ch.append("cteni: seznam čtení")
        cteni = []
    for i, c in enumerate(cteni):
        kde = f"cteni[{i}]"
        if not isinstance(c, dict):
            ch.append(f"{kde}: objekt")
            continue
        if not (isinstance(c.get("id"), str) and re.fullmatch(r"[a-z0-9]{1,8}", c["id"])) or c.get("id") in idc:
            ch.append(f"{kde}.id: krátké jedinečné označení (c1, c2, …)")
        idc.add(c.get("id"))
        z = c.get("zdroj")
        if not isinstance(z, dict) or not isinstance(z.get("portal"), str) or not (isinstance(z.get("snimek"), int) and z["snimek"] >= 1):
            ch.append(f"{kde}.zdroj: {{portal, svazek, snimek}} – snímek je číslo")
        else:
            over_svazek(z.get("svazek"), f"{kde}.zdroj.svazek", sv, ch)
        v = c.get("vyrez")
        if not (isinstance(v, str) and v.replace("\\", "/").startswith("pracovni/")) or str(v).replace("\\", "/").startswith(VEREJNE):
            ch.append(f"{kde}.vyrez: cesta k výřezu pod pracovni/ (ne do veřejných složek webu)")
        texty(c.get("doslova"), f"{kde}.doslova", ch, povinne=True)
        texty(c.get("normalizace"), f"{kde}.normalizace", ch)
        texty(c.get("nejistota"), f"{kde}.nejistota", ch)
        if c.get("chybi") is not None and not (isinstance(c["chybi"], list) and all(isinstance(x, str) for x in c["chybi"])):
            ch.append(f"{kde}.chybi: seznam polí, která se nepodařilo přečíst")
    for i, k in enumerate(d.get("kandidati") or []):
        if not isinstance(k, dict):
            ch.append(f"kandidati[{i}]: objekt")
            continue
        over_osobu(k.get("osoba"), f"kandidati[{i}].osoba", zname, ch)
        if k.get("cteni") not in idc:
            ch.append(f"kandidati[{i}].cteni: označení čtení z tohoto nálezu")
    proh = d.get("prohledano") or []
    if stav not in BEZ_ROZSAHU and not (isinstance(proh, list) and proh):
        ch.append("prohledano: co se opravdu přečetlo [{svazek, snimky: [od, do], uplne}] – i když se nic nenašlo")
    dovoleno = dovoleny_rozsah(zadani) if zadani else []
    svazek_zadani = ((zadani or {}).get("pramen") or {}).get("svazek")
    for i, p in enumerate(proh if isinstance(proh, list) else []):
        if not isinstance(p, dict) or not isinstance(p.get("uplne"), bool):
            ch.append(f"prohledano[{i}]: {{svazek, snimky: [od, do], uplne: true|false}}")
            continue
        over_svazek(p.get("svazek"), f"prohledano[{i}].svazek", sv, ch)
        s = rozpeti(p.get("snimky"), f"prohledano[{i}].snimky", ch)
        if s and dovoleno and p.get("svazek") == svazek_zadani and not any(a <= s[0] and s[1] <= b for a, b in dovoleno):
            ch.append(f"prohledano[{i}]: snímky {s[0]}–{s[1]} jsou mimo zadaný rozsah ({', '.join(f'{a}–{b}' for a, b in dovoleno)}); "
                      "rozšíření schvaluje řídicí agent – navrhni ho v navrh_dalsiho_kroku")
        if s and svazek_zadani and p.get("svazek") != svazek_zadani and zadani:
            ch.append(f"prohledano[{i}]: svazek {p.get('svazek')} není svazek zadání ({svazek_zadani}); jiný pramen navrhni v navrh_dalsiho_kroku")
    for i, s in enumerate(d.get("stranky") or []):
        if not isinstance(s, dict) or s.get("typ") not in TYPY_STRAN:
            ch.append(f"stranky[{i}].typ: {', '.join(TYPY_STRAN)}")
        elif s.get("kvalita", "dobrá") not in KVALITY:
            ch.append(f"stranky[{i}].kvalita: {', '.join(KVALITY)}")
        if isinstance(s, dict):
            over_svazek(s.get("svazek"), f"stranky[{i}].svazek", sv, ch)
            if not (isinstance(s.get("snimek"), int) and s["snimek"] >= 1):
                ch.append(f"stranky[{i}].snimek: číslo snímku")
    n = d.get("navrh_dalsiho_kroku")
    if n is not None and not (isinstance(n, dict) and isinstance(n.get("typ"), str) and isinstance(n.get("duvod"), str)):
        ch.append("navrh_dalsiho_kroku: {typ, duvod, …}")
    c = d.get("cerpani")
    if not (isinstance(c, dict) and all(isinstance(c.get(k), int) and c[k] >= 0 for k in ("kroku", "snimku"))):
        ch.append("cerpani: {kroku, snimku} – kolik kroků a snímků běh spotřeboval")
    # souvislosti stavů
    if stav == "nalezeno" and not cteni:
        ch.append("stav nalezeno: chybí čtení (cteni)")
    if stav == "částečně" and not (n or any(isinstance(x, dict) and x.get("chybi") for x in cteni)):
        ch.append("stav částečně: uveď, co chybí (cteni[].chybi) nebo kde pokračovat (navrh_dalsiho_kroku)")
    if stav == "nenalezeno":
        if beh != "dočteno":
            ch.append("stav nenalezeno jen po dočtení celého rozsahu; při dosaženém stropu je stav „rozpočet“, při překážce „nedostupné“ nebo „nečitelné“")
        if any(isinstance(p, dict) and p.get("uplne") is False for p in proh if isinstance(proh, list)):
            ch.append("stav nenalezeno: prohledano má uplne: false – rozsah není přečten celý, výsledek je „částečně“ nebo „rozpočet“")
        if zadani:
            p = pokryti(svazek_zadani, zadani.get("hleda_roli"), sv)
            if p:
                ch.append("stav nenalezeno: " + p)
    if zadani and d.get("ukol") != zadani.get("ukol"):
        ch.append(f"ukol: nález je pro {d.get('ukol')}, zadání pro {zadani.get('ukol')}")
    return ch


def over_overeni(d):
    ch = []
    if not (isinstance(d.get("ukol"), str) and UKOL.fullmatch(d["ukol"])):
        ch.append("ukol: ID úkolu ve tvaru U-0042")
    if not (isinstance(d.get("cteni"), str) and d["cteni"]):
        ch.append("cteni: označení čtení, které se ověřuje (c1)")
    if not (isinstance(d.get("vyrezy"), list) and d["vyrezy"] and all(isinstance(x, str) for x in d["vyrezy"])):
        ch.append("vyrezy: seznam výřezů, ze kterých se četlo")
    nec = d.get("necitelne") or []
    if not (isinstance(nec, list) and all(isinstance(x, str) for x in nec)):
        ch.append("necitelne: seznam polí, která nejdou přečíst")
    texty(d.get("doslova"), "doslova", ch, povinne=not nec)
    texty(d.get("nejistota"), "nejistota", ch)
    for zak in ("shoda", "neshoda", "vysledek", "osoba", "identita"):
        if zak in d:
            ch.append(f"{zak}: ověření vrací jen vlastní přepis; shodu vyhodnotí `vysledek.py porovnej`, identitu řídicí agent")
    return ch


def over_rozhodnuti(d):
    """Tvar rozhodnutí řídicího agenta; souvislosti s nálezem a daty hlídá tools/zapis_vysledku.py."""
    ch, zname, sv = [], zname_osoby(), svazky()
    if not (isinstance(d.get("ukol"), str) and UKOL.fullmatch(d["ukol"])):
        ch.append("ukol: ID úkolu ve tvaru U-0042")
    if d.get("vysledek") not in VYSLEDKY_DENIKU:
        ch.append(f"vysledek: {', '.join(VYSLEDKY_DENIKU)}")
    for pole in ("dod_splneno", "uzavrit"):
        if not isinstance(d.get(pole), bool):
            ch.append(f"{pole}: true nebo false (rozhoduje řídicí agent, ne čtenář)")
    dn = d.get("denik")
    if not isinstance(dn, dict) or not all(isinstance(dn.get(k), str) and dn[k].strip() for k in ("zdroj", "hledano")):
        ch.append("denik: {zdroj, hledano, nalez, rozsah, osoby, overeno} – zdroj a hledano jsou povinné")
    else:
        for i, o in enumerate(dn.get("osoby") or []):
            over_osobu(o, f"denik.osoby[{i}]", zname, ch)
        if not (dn.get("osoby") or []):
            ch.append("denik.osoby: aspoň jedna osoba klíčem (koho se hledání týká)")
    z = d.get("zaznam")
    if z is not None:
        if not isinstance(z, dict) or not all(isinstance(z.get(k), str) and z[k].strip() for k in ("klic", "datum", "nazev", "shrnuti")):
            ch.append("zaznam: {klic, svazek, snimek, druh, datum, nazev, shrnuti, odkaz[, prepis]}")
        else:
            over_svazek(z.get("svazek"), "zaznam.svazek", sv, ch)
            if not (isinstance(z.get("snimek"), int) and z["snimek"] >= 1):
                ch.append("zaznam.snimek: číslo snímku")
            if z.get("druh") not in DRUHY_ZAPISU:
                ch.append(f"zaznam.druh: {', '.join(DRUHY_ZAPISU)}")
            if not re.fullmatch(r"[a-z0-9_]+", z["klic"]):
                ch.append("zaznam.klic: malá písmena bez diakritiky, číslice a podtržítka")
            if z.get("prepis") is not None and not (isinstance(z["prepis"], dict) and z["prepis"].get("orig")):
                ch.append("zaznam.prepis: {orig, cs}")
            uc = z.get("ucastnici")
            if not (isinstance(uc, list) and any(isinstance(x, dict) and "osoba" in x for x in uc)):
                ch.append("zaznam.ucastnici: kdo v zápisu vystupuje a v jaké roli [{osoba, role}, {jmeno, role}] – aspoň jedna osoba z rodokmenu")
            else:
                for i, x in enumerate(uc):
                    if not isinstance(x, dict) or x.get("role") not in ROLE:
                        ch.append(f"zaznam.ucastnici[{i}].role: {', '.join(ROLE)}")
                    elif "osoba" in x:
                        over_osobu(x["osoba"], f"zaznam.ucastnici[{i}].osoba", zname, ch)
                    elif not (isinstance(x.get("jmeno"), str) and x["jmeno"].strip()):
                        ch.append(f"zaznam.ucastnici[{i}]: osoba (klíč), nebo jmeno (kdo v rodokmenu není)")
        if d.get("vysledek") != "nalezeno":
            ch.append("zaznam: nový zápis jen u výsledku nalezeno")
    idn = d.get("identita")
    if idn is not None:
        if not isinstance(idn, dict):
            ch.append("identita: {osoba, proc, vylouceno}")
        else:
            over_osobu(idn.get("osoba"), "identita.osoba", zname, ch)
    for i, t in enumerate(d.get("tvrzeni") or []):
        kde = f"tvrzeni[{i}]"
        if not isinstance(t, dict) or t.get("typ") not in TYPY_TVRZENI:
            ch.append(f"{kde}.typ: {', '.join(TYPY_TVRZENI)}")
            continue
        if t.get("jistota") not in JISTOTY:
            ch.append(f"{kde}.jistota: {', '.join(JISTOTY)}")
        if not (isinstance(t.get("osoby"), list) and t["osoby"]):
            ch.append(f"{kde}.osoby: aspoň jedna osoba klíčem (vztah má dvě)")
        else:
            for j, o in enumerate(t["osoby"]):
                over_osobu(o, f"{kde}.osoby[{j}]", zname, ch)
        if t.get("typ") in ("rodic", "partner", "kmotr", "svedek", "totozny") and len(t.get("osoby") or []) < 2 and not t.get("text"):
            ch.append(f"{kde}: vztah „{t['typ']}“ má dvě osoby (nebo druhou stranu popiš v text, když v rodokmenu není)")
        if t.get("nahrazuje") is not None and not (isinstance(t["nahrazuje"], str) and re.fullmatch(r"T-\d{4}", t["nahrazuje"])):
            ch.append(f"{kde}.nahrazuje: ID tvrzení ve tvaru T-0042")
    for i, n in enumerate(d.get("navazujici") or []):
        if not (isinstance(n, dict) and isinstance(n.get("text"), str) and n["text"].strip()):
            ch.append(f"navazujici[{i}]: {{text, os, typ}} – text otázky je povinný")
    if d.get("dukaz") is not None and not (isinstance(d["dukaz"], list) and all(isinstance(x, str) for x in d["dukaz"])):
        ch.append("dukaz: seznam označení čtení z nálezu (c1, …)")
    if d.get("zprava") is not None and (not isinstance(d["zprava"], str) or UKOL.search(d["zprava"])):
        ch.append("zprava: text commitu bez čísla úkolu (co bylo ověřeno a kde)")
    return ch


def over(d):
    sch = str(d.get("schema") or "")
    if sch == "rozhodnuti/1":
        return over_rozhodnuti(d)
    if sch == "zadani/1":
        return over_zadani(d)
    if sch == "nalez/1":
        z = cesta_zadani(str(d.get("ukol")))
        return over_nalez(d, nacti(z) if os.path.exists(z) else None)
    if sch == "overeni/1":
        return over_overeni(d)
    return ["schema: zadani/1, nalez/1, overeni/1 nebo rozhodnuti/1 (vzor: vysledek.py vzor nalez)"]


# ---------- souhrn a porovnání ----------
def souhrn(d):
    cteni = [c for c in d.get("cteni") or [] if isinstance(c, dict)]
    return {
        "ukol": d.get("ukol"), "cast": d.get("cast"), "stav": d.get("stav"), "stav_behu": d.get("stav_behu"),
        "cteni": [{"id": c.get("id"), "snimek": (c.get("zdroj") or {}).get("snimek"), "pole": sorted(c.get("doslova") or {}),
                   "chybi": c.get("chybi") or [], "nejistota": c.get("nejistota") or {}} for c in cteni],
        "kandidati": [{"osoba": str(k.get("osoba")), "cteni": k.get("cteni"), "pro": len(k.get("pro") or []), "proti": k.get("proti") or []}
                      for k in d.get("kandidati") or [] if isinstance(k, dict)],
        "prohledano": d.get("prohledano") or [], "navrh_dalsiho_kroku": d.get("navrh_dalsiho_kroku"), "cerpani": d.get("cerpani")}


def tisk_souhrnu(s, path):
    print(f"{s['ukol']} část {s['cast']}: {s['stav']} (běh: {s['stav_behu']})")
    for c in s["cteni"]:
        print(f"  čtení {c['id']}, snímek {c['snimek']}: {', '.join(c['pole'])}" + (f"; CHYBÍ {', '.join(c['chybi'])}" if c["chybi"] else ""))
        for k, v in c["nejistota"].items():
            print(f"    nejisté {k}: {v}")
    for k in s["kandidati"]:
        print(f"  kandidát osoba {k['osoba']} ({k['cteni']}): pro {k['pro']}" + (f", PROTI {'; '.join(k['proti'])}" if k["proti"] else ""))
    for p in s["prohledano"]:
        if isinstance(p, dict) and isinstance(p.get("snimky"), list) and len(p["snimky"]) == 2:
            print(f"  přečteno {p.get('svazek')} snímky {p['snimky'][0]}–{p['snimky'][1]}" + ("" if p.get("uplne") else " (NE celé)"))
    n = s["navrh_dalsiho_kroku"]
    if n:
        print("  návrh: " + ", ".join(f"{k} {v}" for k, v in n.items()))
    c = s["cerpani"] or {}
    print(f"  čerpání: {c.get('kroku', '?')} kroků, {c.get('snimku', '?')} snímků; soubor {path}")


def norm(t):
    return re.sub(r"[\s.,;:]+", " ", str(t)).strip().casefold()


# Měsíc v datu se porovnává jako měsíc, ne jako text: „Februar“ = „Febrr.“ = „Februarii“, „9ber“ = „Novembris“, „července“ = 7.
# Pořadí je důležité (července před června, Martii před Maii).
MESICE = ((r"(7|sept?)b(e)?r", 9), (r"(8|oct|okt)b(e)?r", 10), (r"9b(e)?r", 11), (r"(x|10|dec)b(e)?r", 12),
          (r"jan|ledn|leden", 1), (r"feb|únor|února", 2), (r"mart|marz|mär|břez", 3), (r"ma[ijy]|květ", 5), (r"apr|dub", 4),
          (r"červenc|července", 7), (r"jun|červen|června", 6), (r"jul", 7), (r"aug|srp", 8), (r"sep|září", 9),
          (r"oct|okt|říj|října", 10), (r"nov|listop", 11), (r"dec|dez|prosin", 12))


def _mesic(slovo):
    if not re.fullmatch(r"[^\W\d_]{3,}|(7|8|9|10|x)b(e)?r\w*", slovo):
        return slovo
    for vzor, cislo in MESICE:
        if re.match(vzor, slovo):
            return str(cislo)
    return slovo


def norm_pole(pole, t):
    """Normalizace pro porovnání čtení; u polí s datem navíc měsíc na číslo."""
    n = norm(t)
    return " ".join(_mesic(s) for s in n.split()) if "datum" in str(pole).casefold() else n


def porovnej(prvni, druhe):
    """První čtení × ověření naslepo, po polích."""
    a, b, nec = prvni.get("doslova") or {}, druhe.get("doslova") or {}, set(druhe.get("necitelne") or [])
    out = []
    for pole in sorted(set(a) | set(b) | nec):
        if pole in nec and pole not in b:
            vysl = "nečitelné při druhém čtení"
        elif pole not in b:
            vysl = "jen první čtení"
        elif pole not in a:
            vysl = "jen druhé čtení"
        else:
            vysl = "shoda" if norm_pole(pole, a[pole]) == norm_pole(pole, b[pole]) else "neshoda"
        out.append({"pole": pole, "vysledek": vysl, "prvni": a.get(pole), "druhe": b.get(pole)})
    return out


def vetsina(prvni, overeni):
    """Pole je ověřené, když hodnotu prvního čtení potvrdí většina všech čtení (první + ověření naslepo), aspoň dvě:
    při jednom ověření shoda obou, při dvou 2 ze 3, při 2 : 2 neověřeno (rozhodnutí uživatele 16. 11. 2026).
    Pole, které první čtení nemá, ověřené není. Vrací {pole: {"potvrzuje", "cteni", "overeno"}}."""
    a = prvni.get("doslova") or {}
    pole = set(a)
    for o in overeni:
        pole |= set(o.get("doslova") or {}) | set(o.get("necitelne") or [])
    cteni = 1 + len(overeni)
    out = {}
    for p in sorted(pole):
        potvrzuje = 0
        if p in a:
            potvrzuje = 1 + sum(1 for o in overeni if p in (o.get("doslova") or {}) and norm_pole(p, o["doslova"][p]) == norm_pole(p, a[p]))
        out[p] = {"potvrzuje": potvrzuje, "cteni": cteni, "overeno": potvrzuje >= 2 and 2 * potvrzuje > cteni}
    return out


# ---------- příkazy ----------
def cmd_over(a):
    d = nacti(a.soubor)
    ch = over(d)
    if ch:
        print(f"{a.soubor}: {len(ch)} chyb, soubor se nepřijímá:")
        for c in ch:
            print("  " + c)
        return 1
    print(f"{a.soubor}: v pořádku ({d['schema']})")
    return 0


def cmd_souhrn(a):
    path = cesta_nalezu(a.co) if UKOL.fullmatch(a.co) else a.co
    d = nacti(path)
    if d.get("schema") != "nalez/1":
        sys.exit(f"{path}: není nález (schema nalez/1)")
    s = souhrn(d)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    else:
        tisk_souhrnu(s, os.path.relpath(path, ROOT) if os.path.isabs(path) else path)
    return 0


def cmd_porovnej(a):
    nalez = nacti(cesta_nalezu(a.ukol))
    prvni = next((c for c in nalez.get("cteni") or [] if isinstance(c, dict) and c.get("id") == a.cteni), None)
    if prvni is None:
        sys.exit(f"{a.ukol}: čtení {a.cteni} v nálezu není")
    cesty, docs, kopie = nacti_overeni(a.ukol, a.cteni)
    if not cesty:
        sys.exit(f"{a.ukol}: čtení {a.cteni} nemá ověření ({os.path.relpath(cesta_overeni(a.ukol, a.cteni), ROOT)})")
    if kopie and not a.json:
        print(f"POZOR: {', '.join(kopie)} je kopie dřívějšího ověření (stejný obsah), jako další čtení se nepočítá; kopii smaž")
    overeni, dokumenty = [], []
    for p, druhe in zip(cesty, docs):
        ch = over_overeni(druhe)
        if ch:
            sys.exit(f"{os.path.basename(p)} má chyby (vysledek.py over):\n  " + "\n  ".join(ch))
        radky = porovnej(prvni, druhe)
        overeni.append({"soubor": os.path.basename(p), "shoda": all(r["vysledek"] == "shoda" for r in radky), "pole": radky})
        dokumenty.append(druhe)
    vet = vetsina(prvni, dokumenty)
    shoda = all(v["overeno"] for v in vet.values())
    if a.json:
        print(json.dumps({"ukol": a.ukol, "cteni": a.cteni, "shoda": shoda, "pole": overeni[0]["pole"], "overeni": overeni, "vetsina": vet, "kopie": kopie},
                         ensure_ascii=False, indent=1))
        return 0 if shoda else 1
    if len(overeni) == 1:
        print(f"{a.ukol} čtení {a.cteni}: " + ("obě čtení se shodují" if shoda else "čtení se NEshodují – tvrzení nejvýš prob, oba přepisy zůstávají"))
    else:
        print(f"{a.ukol} čtení {a.cteni}: {len(overeni) + 1} čtení; " + ("každé pole potvrdila většina čtení (ověřeno)" if shoda
              else "některé pole většina nepotvrdila – tvrzení nejvýš prob, všechny přepisy zůstávají"))
        for p, v in vet.items():
            print(f"  {p}: {v['potvrzuje']} z {v['cteni']}" + ("" if v["overeno"] else " – NEOVĚŘENO"))
    for o in overeni:
        if len(overeni) > 1:
            print(f"  {o['soubor'][len(a.ukol) + 9:-5]}: " + ("shoda" if o["shoda"] else "neshoda"))
        for r in o["pole"]:
            print(("    " if len(overeni) > 1 else "  ") + f"{r['pole']}: {r['vysledek']}"
                  + ("" if r["vysledek"] == "shoda" else f" | první: {r['prvni']} | ověření: {r['druhe']}"))
    return 0 if shoda else 1


def spoj(stary, novy):
    """Další část nálezu téhož úkolu: čtení se doplní (stejné označení = totéž čtení, pole se sloučí), rozsah a stránky přibudou,
    stav, návrh a pořadí části jsou z nové části, čerpání se sčítá. Nic z první části se neztratí."""
    out = dict(stary)
    cteni = {c["id"]: dict(c) for c in stary.get("cteni") or []}
    for c in novy.get("cteni") or []:
        if c["id"] in cteni:
            puv = cteni[c["id"]]
            for pole in ("doslova", "normalizace", "nejistota"):
                if c.get(pole) or puv.get(pole):
                    puv[pole] = {**(puv.get(pole) or {}), **(c.get(pole) or {})}
            puv["chybi"] = list(c.get("chybi") or [])
            puv.setdefault("dalsi_vyrezy", []).append(c.get("vyrez"))
            puv.setdefault("dalsi_zdroje", []).append(c.get("zdroj"))
        else:
            cteni[c["id"]] = dict(c)
    out["cteni"] = list(cteni.values())
    for pole in ("kandidati", "prohledano", "stranky"):
        out[pole] = list(stary.get(pole) or []) + [x for x in novy.get(pole) or [] if x not in (stary.get(pole) or [])]
    for pole in ("stav", "stav_behu", "cast"):
        out[pole] = novy.get(pole)
    out["navrh_dalsiho_kroku"] = novy.get("navrh_dalsiho_kroku")
    a, b = stary.get("cerpani") or {}, novy.get("cerpani") or {}
    out["cerpani"] = {k: int(a.get(k, 0)) + int(b.get(k, 0)) for k in ("kroku", "snimku")}
    return out


def cmd_pripoj(a):
    cil = cesta_nalezu(a.ukol)
    stary, novy = nacti(cil), nacti(a.cast)
    zp = cesta_zadani(a.ukol)
    zadani = nacti(zp) if os.path.exists(zp) else None
    ch = over_nalez(novy, zadani)
    if novy.get("ukol") != a.ukol:
        ch.append(f"ukol: část je pro {novy.get('ukol')}, ne pro {a.ukol}")
    if isinstance(novy.get("cast"), int) and isinstance(stary.get("cast"), int) and novy["cast"] != stary["cast"] + 1:
        ch.append(f"cast: nález má část {stary['cast']}, další je {stary['cast'] + 1} (je {novy['cast']})")
    if not ch:
        spojeny = spoj(stary, novy)
        ch = over_nalez(spojeny, zadani)
    if ch:
        print(f"{a.cast}: {len(ch)} chyb, část se nepřipojila:")
        for c in ch:
            print("  " + c)
        return 1
    tmp = cil + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(spojeny, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, cil)
    print(f"{a.ukol}: část {spojeny['cast']} připojena, stav {spojeny['stav']}")
    return 0


def cmd_vzor(a):
    print(json.dumps(VZORY[a.co], ensure_ascii=False, indent=1))
    print("\nDovolené hodnoty: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in VYCTY.items()))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("over"); s.add_argument("soubor")
    s = sp.add_parser("souhrn"); s.add_argument("co"); s.add_argument("--json", action="store_true")
    s = sp.add_parser("porovnej"); s.add_argument("ukol"); s.add_argument("cteni"); s.add_argument("--json", action="store_true")
    s = sp.add_parser("vzor"); s.add_argument("co", choices=sorted(VZORY))
    s = sp.add_parser("pripoj"); s.add_argument("ukol"); s.add_argument("cast")
    a = ap.parse_args(argv)
    return {"over": cmd_over, "souhrn": cmd_souhrn, "porovnej": cmd_porovnej, "vzor": cmd_vzor, "pripoj": cmd_pripoj}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
