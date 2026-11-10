#!/usr/bin/env python3
"""Přístupy k webu (data/web.json → „pristupy“) a pohled na rodokmen od jiné výchozí osoby.

Každý přístup má odpověď na přihlašovací otázku, osobní odkazy, nebo obojí, a volitelně výchozí osoby („koren“).
Přístup bez kořene vidí všechno (jako dosud). Přístup s kořenem vidí jen svou rozšířenou linii; web se pro něj
sestaví zvlášť, takže ostatní větve na serveru vůbec nejsou (export_web.py --pristup, scripts/build.mjs).
- přímá linie = výchozí osoby + jejich předci (stránky Statistiky, Rody, Mapa, Časová osa, Strom, Předci),
- rozšířená linie = přímá + potomci všech osob přímé linie (sourozenci výchozích osob i předků s větvemi)
  + u každé z nich partner a rodiče partnera (dál ne),
- vlastní větev = výchozí osoby + jejich potomci + partneři (rozsah práva „soukrome“).

    "prihlaseni": {"otazka": "…", "odpoved": "…"},             ← tahle odpověď vidí všechno (přístup „vse“)
    "pristupy": [
      {"nazev": "Plíškovi", "odpoved": "…", "koren": [1], "prava": {"soukrome": true, "texty": true, "poznamky": true}},
      {"nazev": "Rodina Jany", "koren": ["jana-nova"], "odkazy": [{"id": "p1", "jmeno": "Jana", "otisk": "<sha256>"}]}
    ]
koren: čísla předků z P nebo zkratky z RODINA; první určuje číslování (vějíř, rody, předci, statistiky), další se
přidají (sjednocení). prava (nevyplněné = false): texty = i texty bez vazby na osobu nebo rod (příběh, deník…),
poznamky = tlačítko „Připomínka“ a přehled /poznamky/ (jen Netlify), soukrome = soukromé údaje vlastní větve.
Starší zápis „texty“ / „poznamky“ přímo v přístupu platí jako v prava. odkazy = osobní odkazy (tools/pozvanky.py). Volitelně „nazev_webu“ a „uvod“ (jako ve web.json) jen pro tento přístup a „rody“ – názvy rodů
nového stromu {"8": ["Dvořákové", "popis"], …}; bez nich se vezmou z LINES, nebo z příjmení pradědečka / prababičky.
Rodiče partnera v pohledu jsou (odkud pochází), sourozenci a další předci partnera ne.
"""
import re
import unicodedata


def _slug(text):
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def norm_odpoved(text):
    """Stejná normalizace jako export_web.norm_answer a prihlaseni.html."""
    t = unicodedata.normalize("NFD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", t)


PRAVA = ("soukrome", "texty", "poznamky")


def _prava(p, vse=False):
    """prava přístupu (nevyplněné = false); starší „texty“ / „poznamky“ přímo v přístupu platí jako v prava."""
    if vse:
        return {k: True for k in PRAVA}
    pr = p.get("prava") if isinstance(p.get("prava"), dict) else {}
    return {k: bool(pr.get(k, p.get(k, False))) for k in PRAVA}


def odkazy_pristupu(p, nazev="?"):
    """Platné osobní odkazy přístupu [{id, jmeno, otisk, …}]; zrušené („zruseno“) se přeskočí."""
    seznam = p.get("odkazy") or []
    if not isinstance(seznam, list) or not all(isinstance(o, dict) for o in seznam):
        raise SystemExit(f"CHYBA: web.json → pristupy „{nazev}“: odkazy musí být seznam záznamů s id a otiskem.")
    platne = []
    for o in seznam:
        if "zruseno" in o:
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(o.get("otisk", ""))):
            raise SystemExit(f"CHYBA: web.json → pristupy „{nazev}“: odkaz {o.get('id', '?')} má neplatný otisk "
                             f"(nový: python3 -I tools/pozvanky.py nova {o.get('id', '<id>')}).")
        platne.append(o)
    return platne


def nacti_pristupy(cfg):
    """Seznam přístupů [{id, nazev, odpoved, odkazy, koren, prava, texty, poznamky, …}], nebo None, když web.json
    „pristupy“ nemá. Přístup „vse“ = prihlaseni.odpoved (správce: vidí všechno, má všechna práva). Přístup potřebuje
    odpověď, osobní odkaz, nebo obojí. Chyby v nastavení ukončí export se srozumitelnou hláškou."""
    seznam = cfg.get("pristupy")
    if not seznam:
        return None
    if not isinstance(seznam, list) or not all(isinstance(p, dict) for p in seznam):
        raise SystemExit("CHYBA: web.json → pristupy musí být seznam {\"nazev\": …, \"odpoved\": …, \"koren\": [...]}.")
    login = cfg.get("prihlaseni") or {}
    if login.get("otevreny"):
        raise SystemExit("CHYBA: web.json – otevřený web (prihlaseni.otevreny) a přístupy (pristupy) nejdou dohromady.")
    out = []
    if norm_odpoved(login.get("odpoved", "")):
        poz = cfg["poznamky"] if "poznamky" in cfg else any(_prava(p)["poznamky"] for p in seznam)   # správce vidí přehled
        out.append(dict(id="vse", nazev="všechno", odpoved=login["odpoved"], odkazy=[], koren=[], texty=True,
                        poznamky=bool(poz), prava=dict(_prava({}, vse=True), poznamky=bool(poz))))
    for i, p in enumerate(seznam, 1):
        pid = _slug(p.get("nazev", "")) or f"pristup-{i}"
        if pid in ("vse", "_p") or any(x["id"] == pid for x in out):
            raise SystemExit(f"CHYBA: web.json → pristupy: název „{p.get('nazev')}“ se opakuje nebo je vyhrazený – zvol jiný.")
        odkazy = odkazy_pristupu(p, p.get("nazev", pid))
        if not norm_odpoved(p.get("odpoved", "")) and not odkazy:
            raise SystemExit(f"CHYBA: web.json → pristupy „{p.get('nazev', pid)}“ nemá odpověď (odpoved) ani osobní "
                             f"odkaz (odkazy) – nikdo by se na něj nedostal.")
        koren = p.get("koren") or []
        if not isinstance(koren, list) or not all(isinstance(k, (int, str)) and not isinstance(k, bool) for k in koren):
            raise SystemExit(f"CHYBA: web.json → pristupy „{p.get('nazev', pid)}“: koren musí být seznam čísel předků nebo zkratek z RODINA.")
        prava = _prava(p)
        if not koren:   # přístup bez kořene vidí všechno, i texty (jako dosud)
            prava["texty"] = True
        out.append(dict(p, id=pid, koren=koren, odkazy=odkazy, prava=prava, texty=prava["texty"], poznamky=prava["poznamky"]))
    otisky = [o["otisk"] for p in out for o in p.get("odkazy") or []]
    if len(set(otisky)) != len(otisky):
        raise SystemExit("CHYBA: web.json – stejný osobní odkaz (otisk) je u dvou přístupů; každý odkaz patří jen k jednomu.")
    odpovedi = [norm_odpoved(p.get("odpoved", "")) for p in out if norm_odpoved(p.get("odpoved", ""))]
    if len(set(odpovedi)) != len(odpovedi):
        raise SystemExit("CHYBA: web.json – dva přístupy mají stejnou odpověď; každý přístup potřebuje jinou.")
    return out


def _zastupce(o):
    """„otec neuveden“ apod. – místo v rodokmenu, ne osoba (stejně jako export_web.placeholder)."""
    return (o.get("n") or "").startswith(("otec neuveden", "matka neuvedena")) or o.get("n") in ("", "?")


def pohled(ns, koreny, texty=False, rody=None):
    """Data rodokmenu z pohledu výchozích osob `koreny` (první určuje číslování). Vrací (nové ns, převod), kde převod
    mapuje původní odkaz osoby (číslo z P nebo zkratka z RODINA) na nový (číslo v novém P nebo zkratka v novém RODINA)."""
    P, R, SAME = ns["P"], ns["RODINA"], ns["SAME"]

    def norm(ref):
        if isinstance(ref, bool) or ref is None:
            return None
        if isinstance(ref, int):
            ref = SAME.get(ref, ref)
            return ref if ref in P else None
        return ref if ref in R else None

    for k in koreny:
        if norm(k) is None:
            raise SystemExit(f"CHYBA: web.json → pristupy: výchozí osoba {k!r} není v P ani v RODINA (data/osoby.py).")

    def osoba(ref):
        return P[ref] if isinstance(ref, int) else R[ref]

    def rodice(ref):
        if isinstance(ref, int):
            return [norm(c) if c in P else None for c in (2 * ref, 2 * ref + 1)]
        return [norm(R[ref].get("otec")), norm(R[ref].get("matka"))]

    # 1) přečíslování od první výchozí osoby (Kekulé: otec 2n, matka 2n+1); opakovaný předek = SAME
    nove_p, kde, same = {}, {}, {}
    fronta = [(1, norm(koreny[0]))]
    while fronta:
        n, ref = fronta.pop(0)
        if ref in kde:
            same[n] = kde[ref]
            nove_p[n] = {k: v for k, v in osoba(ref).items() if k not in ("otec", "matka", "partner")}
            continue
        kde[ref] = n
        nove_p[n] = {k: v for k, v in osoba(ref).items() if k not in ("otec", "matka", "partner")}
        if n == 1 and isinstance(ref, int) and ref != 1:   # předek jako výchozí osoba: pohlaví podle čísla
            nove_p[n]["sex"] = "M" if ref % 2 == 0 else "F"
        for c, r in zip((2 * n, 2 * n + 1), rodice(ref)):
            if r is not None:
                fronta.append((c, r))
    predci = set(kde)

    # 2) další výchozí osoby a jejich předci (mimo první strom) = příbuzní s vlastní stránkou
    dalsi = set()
    for k in koreny[1:]:
        zas = [norm(k)]
        while zas:
            ref = zas.pop()
            if ref is None or ref in predci or ref in dalsi:
                continue
            dalsi.add(ref)
            zas += rodice(ref)

    # 3) přímá linie = výchozí osoby a jejich předci; k ní potomci všech jejích osob (sourozenci výchozích osob
    #    i předků a jejich větve až k žijícím)
    vsichni = [k for k in P if norm(k) == k] + list(R)
    deti = {}
    for ref in vsichni:
        for r in rodice(ref):
            if r is not None:
                deti.setdefault(r, []).append(ref)

    def potomci(od):
        out, zas = set(od), list(od)
        while zas:
            for d in deti.get(zas.pop(), []):
                if d not in out:
                    out.add(d)
                    zas.append(d)
        return out

    prima = predci | dalsi
    pokrevni = potomci(prima)
    # 4) partneři (PARTNERI, partner v RODINA, rodiče společného dítěte) a rodiče partnera – dál ne
    partner_of = {}
    pary = [(norm(pr.get("a")), norm(pr.get("b"))) for pr in ns["PARTNERI"]]
    for oid, o in R.items():
        pary += [(oid, norm(v)) for v in o.get("partner", [])]
    for ref in vsichni:
        f, mm = rodice(ref)
        if f is not None and mm is not None:
            pary.append((f, mm))
    for a, b in pary:
        if a is not None and b is not None and a != b:
            partner_of.setdefault(a, set()).add(b)
            partner_of.setdefault(b, set()).add(a)
    partneri_vidi = {b for a in pokrevni for b in partner_of.get(a, ())} - pokrevni
    rodice_partneru = {r for b in partneri_vidi for r in rodice(b) if r is not None} - pokrevni - partneri_vidi
    vidi = pokrevni | partneri_vidi | rodice_partneru
    vlastni_puv = potomci({norm(k) for k in koreny})
    vlastni_puv |= {b for a in vlastni_puv for b in partner_of.get(a, ())}

    # 5) nové klíče a nové RODINA (zástupci „otec neuveden“ mimo strom předků nejsou osoby – vynechat)
    vidi = {ref for ref in vidi if ref in predci or not _zastupce(osoba(ref))}
    prima &= vidi
    prevod = {ref: kde[ref] for ref in predci}
    for ref in vidi - predci:
        prevod[ref] = ref if isinstance(ref, str) else f"p{ref}"

    def m(ref):
        return prevod.get(norm(ref)) if norm(ref) is not None else None

    nove_r = {}
    for ref in sorted(vidi - predci, key=str):
        o = {k: v for k, v in osoba(ref).items() if k not in ("otec", "matka", "partner")}
        if isinstance(ref, int):
            o.setdefault("sex", P[1].get("sex", "M") if ref == 1 else ("M" if ref % 2 == 0 else "F"))
        f, mm = rodice(ref)
        if f is not None and m(f) is not None:
            o["otec"] = m(f)
        if mm is not None and m(mm) is not None:
            o["matka"] = m(mm)
        if isinstance(ref, str) and R[ref].get("partner"):
            o["partner"] = [m(v) for v in R[ref]["partner"] if m(v) is not None]
        nove_r[prevod[ref]] = o

    # 6) rody: čísla 8–15 nového stromu; název z „rody“ přístupu, z původních LINES, jinak příjmení předka
    lines = {}
    for n in range(8, 16):
        if n not in nove_p or n in same:
            continue
        ref = next(r for r, k in kde.items() if k == n)
        vlastni = (rody or {}).get(str(n))
        if vlastni:
            lines[n] = tuple(vlastni) if isinstance(vlastni, (list, tuple)) else (str(vlastni), "")
        elif isinstance(ref, int) and ref in ns["LINES"]:
            lines[n] = ns["LINES"][ref]
        else:
            prijmeni = (nove_p[n].get("n") or "").split()[-1:] or [""]
            lines[n] = (prijmeni[0].strip("()?,"), "")

    side = [dict(s, k=kde[norm(s["k"])]) for s in ns["SIDE"] if norm(s.get("k")) in kde]
    nove_partneri = [dict(pr, a=m(pr.get("a")), b=m(pr.get("b"))) for pr in ns["PARTNERI"]
                     if m(pr.get("a")) is not None and m(pr.get("b")) is not None]
    hypotezy = [dict(h, rod=kde[norm(h["rod"])]) for h in ns["HYPOTEZY"]
                if texty and isinstance(h, dict) and norm(h.get("rod")) in kde]
    # otázky s osobou (dict s k): jen ty, jejichž osoba v pohledu je, s jejím novým číslem; bez osoby zůstanou všechny
    s_osobou = lambda i: isinstance(i, dict) and i.get("k") is not None
    issues = [dict(i, k=m(i["k"])) if s_osobou(i) else i for i in ns["ISSUES"]
              if not s_osobou(i) or m(i["k"]) is not None] if texty else []
    nove = dict(ns, P=nove_p, RODINA=nove_r, SAME=same, LINES=lines, SIDE=side, PARTNERI=nove_partneri,
                ISSUES=issues, HYPOTEZY=hypotezy)
    # linie a vlastní větev v nových klíčích (export_web.py je přenese k osobám na web)
    nove["_linie"] = {prevod[r]: ("prima" if r in prima else "rozsirena") for r in vidi}
    nove["_vlastni"] = {prevod[r] for r in vlastni_puv & vidi}
    nove["_zapisy"] = ({r for p in list(nove_p.values()) + list(nove_r.values()) for r in p.get("r", [])}
                       | {r for s in side for r in s.get("r", [])})
    return nove, prevod
