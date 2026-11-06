#!/usr/bin/env python3
"""Přístupy k webu (data/web.json → „pristupy“) a pohled na rodokmen od jiné výchozí osoby.

Každý přístup má vlastní odpověď na přihlašovací otázku a volitelně výchozí osoby („koren“). Přístup bez kořene vidí
všechno (jako dosud). Přístup s kořenem vidí jen předky výchozích osob a jejich příbuzné (potomky předků a partnery);
web se pro něj sestaví zvlášť, takže ostatní větve na serveru vůbec nejsou (export_web.py --pristup, scripts/build.mjs).

    "prihlaseni": {"otazka": "…", "odpoved": "…"},             ← tahle odpověď vidí všechno (přístup „vse“)
    "pristupy": [
      {"nazev": "Plíškovi", "odpoved": "…", "koren": [1]},
      {"nazev": "Rodina Jany", "odpoved": "…", "koren": ["jana-nova"], "texty": false}
    ]
koren: čísla předků z P nebo zkratky z RODINA; první určuje číslování (vějíř, rody, předci), další se přidají jako
příbuzní s vlastní stránkou a vějířem. texty: true = i příběh, zajímavosti, deník a „Co hledáme“ (jinak skryté –
píšou o celé rodině). poznamky: true = tlačítko „Připomínka“ na stránkách a přehled /poznamky/ (jen Netlify;
přístup vidí jen poznámky ze svého přístupu, „vse“ všechny). Volitelně „nazev_webu“ a „uvod“ (jako ve web.json) jen pro tento přístup a „rody“ – názvy rodů
nového stromu {"8": ["Dvořákové", "popis"], …}; bez nich se vezmou z LINES, nebo z příjmení pradědečka / prababičky.
Předci partnerů (rodiče manžela sestry…) v pohledu nejsou – jen partner sám.
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


def nacti_pristupy(cfg):
    """Seznam přístupů [{id, nazev, odpoved, koren, texty, …}], nebo None, když web.json „pristupy“ nemá.
    Přístup „vse“ = prihlaseni.odpoved (vidí všechno). Chyby v nastavení ukončí export se srozumitelnou hláškou."""
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
        poz = cfg["poznamky"] if "poznamky" in cfg else any(p.get("poznamky") for p in seznam)   # správce vidí přehled
        out.append(dict(id="vse", nazev="všechno", odpoved=login["odpoved"], koren=[], texty=True, poznamky=bool(poz)))
    for i, p in enumerate(seznam, 1):
        pid = _slug(p.get("nazev", "")) or f"pristup-{i}"
        if pid in ("vse", "_p") or any(x["id"] == pid for x in out):
            raise SystemExit(f"CHYBA: web.json → pristupy: název „{p.get('nazev')}“ se opakuje nebo je vyhrazený – zvol jiný.")
        if not norm_odpoved(p.get("odpoved", "")):
            raise SystemExit(f"CHYBA: web.json → pristupy „{p.get('nazev', pid)}“ nemá odpověď (odpoved).")
        koren = p.get("koren") or []
        if not isinstance(koren, list) or not all(isinstance(k, (int, str)) and not isinstance(k, bool) for k in koren):
            raise SystemExit(f"CHYBA: web.json → pristupy „{p.get('nazev', pid)}“: koren musí být seznam čísel předků nebo zkratek z RODINA.")
        out.append(dict(p, id=pid, koren=koren, texty=bool(p.get("texty")) or not koren, poznamky=bool(p.get("poznamky"))))
    odpovedi = [norm_odpoved(p["odpoved"]) for p in out]
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

    # 3) potomci všech viditelných předků (sourozenci předků, jejich děti…) a 4) partneři
    vsichni = [k for k in P if norm(k) == k] + list(R)
    deti = {}
    for ref in vsichni:
        for r in rodice(ref):
            if r is not None:
                deti.setdefault(r, []).append(ref)
    vidi = predci | dalsi
    zas = list(vidi)
    while zas:
        for d in deti.get(zas.pop(), []):
            if d not in vidi:
                vidi.add(d)
                zas.append(d)
    partneri = []
    for pr in ns["PARTNERI"]:
        partneri.append((norm(pr.get("a")), norm(pr.get("b"))))
    for oid, o in R.items():
        partneri += [(oid, norm(v)) for v in o.get("partner", [])]
    for ref in vsichni:
        f, m = rodice(ref)
        if ref in vidi and f is not None and m is not None:
            partneri.append((f, m))
    for a, b in partneri:
        if a is not None and b is not None and (a in vidi) != (b in vidi):
            vidi.add(b if a in vidi else a)

    # 5) nové klíče a nové RODINA (zástupci „otec neuveden“ mimo strom předků nejsou osoby – vynechat)
    vidi = {ref for ref in vidi if ref in predci or not _zastupce(osoba(ref))}
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
    nove["_zapisy"] = ({r for p in list(nove_p.values()) + list(nove_r.values()) for r in p.get("r", [])}
                       | {r for s in side for r in s.get("r", [])})
    return nove, prevod
