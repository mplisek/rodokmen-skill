#!/usr/bin/env python3
"""Dějiny významných staveb a domů předků: kontrola dat, náměty z rodokmenu, export pro web (stránka Domy).

Použití (z kořene projektu):
  python3 -I tools/stavby.py kontrola            zkontroluje data/stavby.py (osoby, zápisy, stavy, soukromí)
  python3 -I tools/stavby.py kandidati [--vse]   z data/osoby.py navrhne domy, které stojí za záznam (řemesla, opakované adresy)
  python3 -I tools/stavby.py export              zapíše web/src/data/stavby.json (volá ho tools/export_web.py)

Data: data/stavby.py (formát v reference/stavby.md). Poloha domu zůstává v data/domy/ (výstup skillu stare-adresy);
stavba na ni odkazuje klíčem `dum`. Údaje o žijících lidech a o dnešních majitelích na web nejdou.
"""
import json
import os
import re
import runpy
import sys
import unicodedata

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
from soubory import zapis_json  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAVBY = os.path.join(ROOT, "data", "stavby.py")
ADRESY = os.path.join(ROOT, "data", "domy", "adresy.json")
OUT = os.path.join(ROOT, "web", "src", "data", "stavby.json")
SITE = os.path.join(ROOT, "web", "src", "data", "site.json")

STAVY = {"doc", "lit", "prob", "fam", "unk"}
TYPY = {"dum": "dům", "statek": "statek", "chalupa": "chalupa", "hostinec": "hostinec", "mlyn": "mlýn",
        "kovarna": "kovárna", "rychta": "rychta", "fara": "fara", "skola": "škola", "panstvi": "panství, zámek",
        "kostel": "kostel", "kaple": "kaple", "jine": "jiná stavba"}
ROK_SOUKROMI = 1950   # držitel domu po tomto roce jen se souhlasem (pole `souhlas`)

# řemeslo / postavení → typ stavby; podle nich kandidati navrhuje domy
ROLE_TYP = [
    ("hostinec", r"hostinsk|hospodsk|výčepn|krčmář"),
    ("mlyn", r"mlyn|mlynář"),
    ("kovarna", r"kovář"),
    ("rychta", r"rychtář|starosta|purkmistr"),
    ("fara", r"farář|kaplan|děkan|varhaník"),
    ("skola", r"učitel|řídící"),
    ("panstvi", r"panský|zahradník|správce|důchodní|hajný|vrchní|ovčák|kočí"),
]
ROLE_RX = [(t, re.compile(rx, re.I)) for t, rx in ROLE_TYP]
OBEC_CP = re.compile(r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:[ -](?:[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+|u|nad|pod))?)\s+čp\.\s?(\d+)")


def bez_diakritiky(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def kmen(obec):
    """Hrubý kmen názvu obce (první 5 písmen bez diakritiky): sloučí „Křemenice“, „v Křemenici“, „Křemenic“."""
    return re.sub(r"[^a-z]", "", bez_diakritiky(obec))[:5]


def rok(text):
    """První čtyřčíslí v textu („asi 1840“, „před 1836“) jako číslo; None, když tam není."""
    m = re.search(r"\b(1[2-9]\d\d|20\d\d)\b", str(text or ""))
    return int(m.group(1)) if m else None


def nacti_data(root=ROOT):
    """(P, RODINA, stavby, issues) z data/osoby.py a data/stavby.py; chybějící soubor = prázdné."""
    d = runpy.run_path(os.path.join(root, "data", "osoby.py"))
    P, RODINA = d.get("P", {}), d.get("RODINA", d.get("X", {}))
    cesta = os.path.join(root, "data", "stavby.py")
    s = runpy.run_path(cesta) if os.path.exists(cesta) else {}
    return P, RODINA, s.get("D", {}), s.get("ISSUES", [])


def osoba(os_, P, RODINA):
    """Záznam osoby podle `os` (Kekulého číslo z P nebo klíč z RODINA), jinak None."""
    if isinstance(os_, int):
        return P.get(os_)
    if isinstance(os_, str):
        return RODINA.get(os_)
    return None


def zijici(o):
    """Žijící nebo možná žijící (stejné pravidlo jako u webu: export_web.zijici) – podrobnosti o nich nepatří na web."""
    if not o:
        return False
    from export_web import zijici as web_zijici
    return web_zijici(o.get("y"), o.get("note"), o.get("f", ()))


def _zaznamy_klice(root):
    p = os.path.join(root, "data", "zaznamy.json")
    if not os.path.exists(p):
        return None
    z = json.load(open(p, encoding="utf-8"))
    if isinstance(z, dict):
        return set(z)
    return {r.get("klic") or r.get("key") for r in z}


def _adresy_id(root):
    p = os.path.join(root, "data", "domy", "adresy.json")
    if not os.path.exists(p):
        return None
    return {a.get("id"): a for a in json.load(open(p, encoding="utf-8"))}


def zkontroluj(D, P, RODINA, zaznamy=None, adresy=None):
    """Seznam upozornění (úroveň, text). Úrovně: CHYBA (data nejdou použít), POZOR (zkontroluj), SOUKROMÍ (nejde na web)."""
    out = []

    def pridej(uroven, dum, text):
        out.append((uroven, f"{dum}: {text}"))

    videno_dum = {}
    for klic, s in D.items():
        for pole in ("nazev", "typ", "popis"):
            if not s.get(pole):
                pridej("CHYBA", klic, f"chybí pole {pole}")
        if s.get("typ") and s["typ"] not in TYPY:
            pridej("CHYBA", klic, f"neznámý typ „{s['typ']}“ (povolené: {', '.join(TYPY)})")
        if s.get("st") not in STAVY:
            pridej("CHYBA", klic, f"stav st musí být {'/'.join(sorted(STAVY))}, je „{s.get('st')}“")
        dum = s.get("dum")
        if not dum:
            pridej("POZOR", klic, "chybí `dum` (odkaz na adresu v data/domy/adresy.json) – dům se na mapě nespojí")
        else:
            if adresy is not None and dum not in adresy:
                pridej("POZOR", klic, f"dům „{dum}“ není v data/domy/adresy.json")
            if dum in videno_dum:
                pridej("POZOR", klic, f"stejný dům „{dum}“ má i stavba „{videno_dum[dum]}“")
            videno_dum[dum] = klic
        for kat in ("udalosti", "drzitele", "obyvatele"):
            for i, it in enumerate(s.get(kat, []), 1):
                kde = f"{kat}[{i}]"
                st = it.get("st")
                if st not in STAVY:
                    pridej("CHYBA", klic, f"{kde}: stav st musí být {'/'.join(sorted(STAVY))}, je „{st}“")
                if st == "doc" and not (it.get("r") or it.get("zdroj")):
                    pridej("CHYBA", klic, f"{kde}: stav doc vyžaduje r (zápis) nebo zdroj")
                if st == "lit" and not it.get("zdroj"):
                    pridej("CHYBA", klic, f"{kde}: stav lit vyžaduje zdroj (kniha, strana)")
                if st == "prob" and not (it.get("note") or it.get("r") or it.get("zdroj")):
                    pridej("POZOR", klic, f"{kde}: prob bez poznámky – napiš proč je to jen pravděpodobné")
                if zaznamy is not None:
                    for r in it.get("r", []):
                        if r not in zaznamy:
                            pridej("CHYBA", klic, f"{kde}: zápis „{r}“ není v data/zaznamy.json")
                if kat == "udalosti":
                    if not it.get("text"):
                        pridej("CHYBA", klic, f"{kde}: chybí text")
                    continue
                os_ = it.get("os")
                if os_ is None and not it.get("n"):
                    pridej("CHYBA", klic, f"{kde}: chybí osoba (os) i jméno (n)")
                o = None
                if os_ is not None:
                    o = osoba(os_, P, RODINA)
                    if o is None:
                        pridej("CHYBA", klic, f"{kde}: osoba {os_!r} není v osoby.py (P ani RODINA)")
                if zijici(o) and (it.get("f") or it.get("note") or (it.get("role") and kat == "drzitele")):
                    pridej("SOUKROMÍ", klic, f"{kde}: {o.get('n')} je žijící – jen jméno a role, bez podrobností")
                if kat == "drzitele":
                    for pole in ("od", "do"):
                        r = rok(it.get(pole))
                        if r and r > ROK_SOUKROMI and not it.get("souhlas"):
                            pridej("SOUKROMÍ", klic, f"{kde}: držitel po roce {ROK_SOUKROMI} jen se souhlasem (pole `souhlas`)")
                            break
    return out


def kandidati(P, RODINA, D, adresy=None, vse=False, jmena=None):
    """Domy zmíněné v osoby.py jako „Obec čp. N“, seřazené podle toho, jak moc stojí za záznam.

    Skóre = počet různých lidí v domě + 3 za řemeslo/postavení (hostinský, mlynář, rychtář, panský zahradník…).
    Domy, které už ve stavby.py jsou, se vynechají. Vrací seznam slovníků. `jmena` = základní tvary názvů obcí
    (z data/mista.json a adresy.json), aby se místo „Smiřic“ psalo „Smiřice“.
    """
    zaklad = {kmen(n): n for n in (jmena or [])}
    mam = {s.get("dum") for s in D.values()} | set(D)
    mam_km = set()   # i bez adresy.json: klíč „holice-112“ → (kmen „holic“, 112)
    for k in mam:
        m = re.match(r"^(.*)-(\d+)$", str(k or ""))
        if m:
            mam_km.add((kmen(m.group(1).replace("-", " ")), int(m.group(2))))
    ad = {}
    for aid, a in (adresy or {}).items():
        ad[(kmen(a.get("obec", "")), int(a.get("cp") or 0))] = aid
    domy = {}
    lidi = [(f"P{k}", p) for k, p in P.items()] + [(f"R:{k}", p) for k, p in RODINA.items()]
    for ident, p in lidi:
        if not isinstance(p, dict):
            continue
        for text in list(p.get("f", [])) + [p.get("note") or ""]:
            for m in OBEC_CP.finditer(text):
                obec, cp = m.group(1), int(m.group(2))
                d = domy.setdefault((kmen(obec), cp), dict(obec=obec, cp=cp, lide={}, role=set(), tvary={}))
                d["tvary"][obec] = d["tvary"].get(obec, 0) + 1
                d["lide"][ident] = p.get("n", ident)
                kus = text[max(0, m.start() - 90):m.end() + 90]
                for typ, rx in ROLE_RX:
                    if rx.search(kus) or rx.search(text if len(text) < 120 else ""):
                        d["role"].add(typ)
    out = []
    for (km, cp), d in domy.items():
        aid = ad.get((km, cp))
        if aid in mam or (km, cp) in mam_km:
            continue
        d["obec"] = zaklad.get(km) or max(d["tvary"], key=d["tvary"].get)
        d["adresa_id"] = aid
        d["skore"] = len(d["lide"]) + (3 if d["role"] else 0)
        if d["skore"] >= 3 or vse:
            out.append(d)
    out.sort(key=lambda d: (-d["skore"], d["obec"], d["cp"]))
    return out


def _soubory_webu(root):
    site = json.load(open(os.path.join(root, "web", "src", "data", "site.json"), encoding="utf-8"))
    people = site["people"]
    people = people if isinstance(people, dict) else {p["slug"]: p for p in people}
    by_k, by_key = {}, {}
    for p in people.values():
        k = p.get("k")
        if k not in (None, "", 0, "0"):
            by_k[int(k)] = p
        t = str(p.get("tree") or "")
        if t.startswith("o:"):
            by_key[t[2:]] = p
    recs = site["records"]
    recs = recs if isinstance(recs, dict) else {r["key"]: r for r in recs}
    return by_k, by_key, recs


def sestav_export(D, P, RODINA, by_k, by_key, recs):
    """Slovník dum → data stavby pro web: osoby přeložené na jména a adresy stránek, žijící bez podrobností, soukromé vynechané."""
    out = {}
    for klic, s in D.items():
        if s.get("verejne") is False or not s.get("dum"):
            continue

        def kdo(it):
            os_ = it.get("os")
            o = osoba(os_, P, RODINA)
            if isinstance(os_, int):
                web = by_k.get(os_)
            else:
                web = by_key.get(os_) if os_ else None
            jmeno = it.get("n") or (o or {}).get("n", "")
            return dict(name=jmeno, slug=(web or {}).get("slug"), zije=zijici(o))

        def zapisy(it):
            return [dict(key=r, title=recs[r].get("title", r), date=recs[r].get("date", "")) for r in it.get("r", []) if r in recs]

        udalosti = [dict(rok=u.get("rok", ""), text=u.get("text", ""), st=u.get("st"), zdroj=u.get("zdroj", ""),
                         note=u.get("note", ""), zapisy=zapisy(u)) for u in s.get("udalosti", [])]
        udalosti.sort(key=lambda u: rok(u["rok"]) or 9999)
        drzitele = []
        for h in s.get("drzitele", []):
            w = kdo(h)
            if rok(h.get("od")) and rok(h.get("od")) > ROK_SOUKROMI and not h.get("souhlas"):
                continue   # dnešní majitelé jen se souhlasem
            drzitele.append(dict(name=w["name"], slug=w["slug"], od=h.get("od", ""), do=h.get("do", ""), jak=h.get("jak", ""),
                                 st=h.get("st"), zdroj=h.get("zdroj", ""),
                                 note="" if w["zije"] else h.get("note", ""), zapisy=[] if w["zije"] else zapisy(h)))
        drzitele.sort(key=lambda h: rok(h["od"]) or rok(h["do"]) or 9999)
        obyvatele = []
        for h in s.get("obyvatele", []):
            w = kdo(h)
            obyvatele.append(dict(name=w["name"], slug=w["slug"], role=h.get("role", ""), st=h.get("st"),
                                  od=h.get("od", ""), do=h.get("do", ""),
                                  note="" if w["zije"] else h.get("note", ""), zapisy=[] if w["zije"] else zapisy(h)))
        out[s["dum"]] = dict(klic=klic, nazev=s.get("nazev", ""), typ=s.get("typ", "dum"), typ_text=TYPY.get(s.get("typ"), ""),
                             popis=s.get("popis", ""), st=s.get("st"), cisla=[list(c) for c in s.get("cisla", [])],
                             udalosti=udalosti, drzitele=drzitele, obyvatele=obyvatele, pamatka=s.get("pamatka"),
                             otevrene=list(s.get("otevrene", [])), note=s.get("note", ""))
    return out


def export(root=ROOT):
    """Zapíše web/src/data/stavby.json (vždy; bez data/stavby.py prázdné) a vrátí seznam upozornění."""
    out_path = os.path.join(root, "web", "src", "data", "stavby.json")
    if not os.path.exists(os.path.join(root, "data", "stavby.py")):
        zapis_json(out_path, {"stavby": {}}, indent=None)
        return [], 0
    P, RODINA, D, _ = nacti_data(root)
    upoz = zkontroluj(D, P, RODINA, _zaznamy_klice(root), _adresy_id(root))
    by_k, by_key, recs = _soubory_webu(root)
    stavby = sestav_export(D, P, RODINA, by_k, by_key, recs)
    zapis_json(out_path, {"stavby": stavby}, indent=None)
    dj = os.path.join(root, "web", "src", "data", "domy.json")
    if os.path.exists(dj):   # stavba se ukáže jen u domu, který je na stránce Domy (domy.geojson)
        na_strance = {d["id"] for d in json.load(open(dj, encoding="utf-8")).get("domy", [])}
        for dum in stavby:
            if dum not in na_strance:
                upoz.append(("POZOR", f"{stavby[dum]['klic']}: dům „{dum}“ není na stránce Domy – chybí v data/domy/domy.geojson "
                                      "(spusť stare-adresy mapa.py a výsledek dej do data/domy/)"))
    return upoz, len(stavby)


def tisk_upozorneni(upoz):
    for uroven, text in upoz:
        print(f"{uroven}: {text}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not os.path.exists(os.path.join(ROOT, "data", "STAV.md")):
        sys.exit(f"stavby.py: {ROOT} není složka projektu (chybí data/STAV.md). Spusť projektovou kopii z kořene projektu: "
                 "python3 -I tools/stavby.py …")
    prikaz = argv[0] if argv else ""
    if prikaz == "kontrola":
        P, RODINA, D, _ = nacti_data()
        if not D:
            print("data/stavby.py je prázdné nebo chybí – zatím žádná stavba. Návrhy: tools/stavby.py kandidati")
            return
        upoz = zkontroluj(D, P, RODINA, _zaznamy_klice(ROOT), _adresy_id(ROOT))
        tisk_upozorneni(upoz)
        print(f"Staveb: {len(D)}; upozornění: {len(upoz)}" + (" – bez chyb." if not any(u == 'CHYBA' for u, _ in upoz) else "."))
        sys.exit(1 if any(u == "CHYBA" for u, _ in upoz) else 0)
    elif prikaz == "kandidati":
        P, RODINA, D, _ = nacti_data()
        adresy = _adresy_id(ROOT)
        mp = os.path.join(ROOT, "data", "mista.json")
        jmena = [n for n in (json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}) if not re.search(r"\d", n)]
        jmena += [a.get("obec", "") for a in (adresy or {}).values()]
        kand = kandidati(P, RODINA, D, adresy, vse="--vse" in argv, jmena=jmena)
        if not kand:
            print("Žádné nové náměty (všechny domy se řemeslem nebo více lidmi už ve stavby.py jsou).")
            return
        print("Náměty na stavby (počet lidí v domě + řemeslo). Ověř v zápisech; vybrané doplň do data/stavby.py.\n")
        for d in kand:
            lide = ", ".join(sorted(d["lide"].values())[:5]) + (" …" if len(d["lide"]) > 5 else "")
            role = f" [{', '.join(sorted(TYPY[t] for t in d['role']))}]" if d["role"] else ""
            geo = f"adresa {d['adresa_id']}" if d["adresa_id"] else "není v data/domy/adresy.json – nejdřív geokódovat (stare-adresy)"
            print(f"{d['skore']:>3}  {d['obec']} čp. {d['cp']}{role}: {lide}\n       {geo}")
    elif prikaz == "export":
        upoz, n = export()
        tisk_upozorneni(upoz)
        print(f"stavby: {n} staveb → web/src/data/stavby.json" + (f"; upozornění: {len(upoz)}" if upoz else ""))
    else:
        print(__doc__)
        sys.exit(2 if prikaz else 0)


if __name__ == "__main__":
    main()
