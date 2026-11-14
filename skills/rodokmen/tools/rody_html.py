"""Společné pomůcky pro práci s textem hotových stránek: průchod textovými uzly mimo odkazy, nadpisy, skripty a hotové
značky rodů, načtení rodů z dat verze webu. Používá je znackuj_rody.py a kontrola_webu.py (Fáze B, ADR 0004). Nic nestahuje."""
import json
import os
import re

# Prvky, jejichž text se při značkování nemění: odkaz (značka už je odkaz), nadpis stránky, skripty, styly, formuláře, titulek.
SKIP_ZNACKOVANI = frozenset({"a", "script", "style", "title", "textarea", "option", "select", "button", "h1", "noscript", "template"})
SKIP_JEN_KOD = frozenset({"script", "style", "noscript", "template"})
ZNACKA_OTEVRENI = re.compile(r"<span\b[^>]*\bclass=\"[^\"]*\brod-znak\b[^\"]*\"", re.I)
TOKENY = re.compile(r"(<!--.*?-->|<[^>]+>)", re.S)
NAZEV_TAGU = re.compile(r"<(/?)\s*([a-zA-Z][\w:-]*)")


def nacti_rody(cesta):
    """[{k, slug, name, color}] z data verze webu (web/src/data/site.json), nejdelší názvy první."""
    with open(cesta, encoding="utf-8-sig") as f:
        lines = json.load(f).get("lines") or {}
    rody = [dict(k=l.get("k"), slug=l.get("slug") or s, name=l["name"], color=l.get("color", "")) for s, l in lines.items()
            if l.get("name")]
    return sorted(rody, key=lambda r: -len(r["name"]))


def regex_nazvu(rody):
    if not rody:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(r["name"]) for r in rody) + r")(?!\w)")


def projdi(html, fn_text, skip=SKIP_ZNACKOVANI, preskoc_znacku=True):
    """Vrátí html, v němž je každý textový uzel mimo přeskakované prvky nahrazen fn_text(text)."""
    out, pocty, znacka = [], {}, 0
    for i, cast in enumerate(TOKENY.split(html)):
        if i % 2:   # značka nebo komentář
            out.append(cast)
            if cast.startswith("<!--"):
                continue
            m = NAZEV_TAGU.match(cast)
            if not m:
                continue
            zavirani, nazev = bool(m.group(1)), m.group(2).lower()
            if preskoc_znacku and nazev == "span":
                if znacka:
                    znacka += -1 if zavirani else (0 if cast.rstrip().endswith("/>") else 1)
                elif not zavirani and ZNACKA_OTEVRENI.match(cast):
                    znacka = 1
            if nazev in skip and not cast.rstrip().endswith("/>"):
                pocty[nazev] = max(0, pocty.get(nazev, 0) + (-1 if zavirani else 1))
        else:
            preskocit = znacka or any(pocty.get(n, 0) for n in skip)
            out.append(cast if preskocit or not cast.strip() else fn_text(cast))
    return "".join(out)


def html_soubory(slozka):
    for koren, _, soubory in os.walk(slozka):
        for f in sorted(soubory):
            if f.lower().endswith(".html"):
                yield os.path.join(koren, f)


def cti(cesta):
    with open(cesta, encoding="utf-8", newline="") as f:
        return f.read()
