#!/usr/bin/env python3
"""Kontrola konzistence dat rodokmenu. Spouštějte po každé větší změně a před stavbou webu.

Použití: kontrola.py
Vypíše CHYBY (rozbijí web nebo jsou věcně špatně) a UPOZORNĚNÍ (něco chybí, doplnit).
Hlídá i časovou návaznost narození, sňatků a úmrtí (pravidla v tools/chronologie.py, stejná jako na webu).
Návratový kód 1, pokud jsou chyby.
"""
import datetime, json, os, re, sys, unicodedata
if sys.argv[1:2] in (["-h"], ["--help"]):   # nápověda místo pádu
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python -I nepřidává složku skriptu do cesty
import chronologie  # noqa: E402 – pravidla časové návaznosti (tools/chronologie.py)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:   # stejná pravidla jako mapa na webu
    from export_web import text_pro_misto, vlastni_text, zil_v
except ImportError:   # projekt se starším nebo místně upraveným export_web.py: obce ze všech údajů jako dřív
    def text_pro_misto(text): return text   # noqa: E704
    def vlastni_text(fakty, muz): return " ".join(fakty)   # noqa: E704
    def zil_v(text, rx): return bool(rx.search(text))   # noqa: E704

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def jload(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8-sig")) if os.path.exists(p) else default


def research_log_stats(path):
    """Count numbered research-log rows and return duplicate identifiers."""
    identifier_re = re.compile(r"^\|\s*(\d+|[A-Za-z][A-Za-z0-9]*-\d+)\s*\|")
    seen, duplicates = {}, set()
    rows = 0
    if not os.path.exists(path):
        return rows, []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            match = identifier_re.match(line)
            if not match:
                continue
            rows += 1
            identifier = match.group(1)
            normalized = identifier.casefold()
            if normalized in seen:
                duplicates.add(seen[normalized])
            else:
                seen[normalized] = identifier
    return rows, sorted(duplicates, key=str.casefold)


# „otec Václava (72)“ = tato osoba je otcem osoby 72; „syn Jana Nováka (36)“ = je synem osoby 36.
_RODIC = re.compile(r"\b(otec|matka)\s+(\w+)[^()\"]{0,40}?\((\d+)\)", re.I)
_DITE = re.compile(r"\b(syn|dcera)\s+(\w+)[^()\"]{0,40}?\((\d+)\)", re.I)


def _stejne_jmeno(gen, jmeno):
    """Jméno v 2. pádě („Václava“, „Josefy“) patří ke křestnímu jménu („Václav“, „Josefa“)?"""
    a, b = gen.lower(), (jmeno.split() or [""])[0].lower()
    return len(a) >= 3 and len(b) >= 3 and a[:3] == b[:3]


def kekule(P, SAME=None):
    """Hlídá Kekulého čísla podle poznámek: rodiče osoby k jsou 2k a 2k+1, dítě je k // 2. Upozorní, když fakta
    nebo poznámka osoby zmiňují příbuzného s číslem v závorce, které tomu neodpovídá (předek dostal špatné číslo).
    Jen když osoba s tím číslem existuje a jméno sedí – číslo v závorce může být i rok nebo číslo domu.
    U předka, který je v rodokmenu víckrát (SAME), stačí, když sedí kterékoli z jeho čísel."""
    warn = []
    for k, p in sorted((k, p) for k, p in P.items() if isinstance(k, int) and k > 1):
        cisla = [k] + [a for a, c in (SAME or {}).items() if c == k and isinstance(a, int)]
        text = " ".join(p.get("f", [])) + " " + p.get("note", "")
        for rx, sedi in ((_RODIC, lambda n: any(c // 2 == n for c in cisla)),
                         (_DITE, lambda n: any(n // 2 == c for c in cisla))):
            for m in rx.finditer(text):
                n = int(m.group(3))
                if n not in P or sedi(n) or not _stejne_jmeno(m.group(2), P[n].get("n", "")):
                    continue
                spravne = (f"dítě má mít číslo {k // 2}" if rx is _RODIC
                           else f"rodiče mají čísla {2 * k} a {2 * k + 1}")
                warn.append(f"osoba {k} ({p.get('n')}): v poznámce „{m.group(0)}“, ale podle Kekulého čísla {spravne}"
                            " – má předek správné číslo? (rodiče osoby k jsou 2k a 2k+1)")
    return warn


_SLOVO = "[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽÄÖÜ][a-záčďéěíňóřšťúůýžäöüß]+"
OBEC_RE = re.compile(rf"(?:\b(?i:v|ve|z|ze|na|u)\s+|[*†×]\s*[\d.\s]*\d\s+)"
                     rf"((?:{_SLOVO[:-1]}*(?:[áéíý]|[éíý]m|[ýí]ch|ého|ou)\s+)?{_SLOVO})")   # „Nové Vsi“, „Vysokém Mýtě“


def slova_obce(fakty):
    """Slova z faktů, která vypadají jako obec (po „v/z/na/u“ nebo po datu u */†/×): ukáže, jestli chybí obec, nebo tvar."""
    return list(dict.fromkeys(OBEC_RE.findall(" ".join(fakty))))[:4]


def _md_bez_poznamek(name):
    path = os.path.join(DATA, name)
    return re.sub(r"<!--.*?-->", "", open(path, encoding="utf-8-sig").read(), flags=re.S) if os.path.exists(path) else ""


def co_hledame(ns, P, LINES):
    """Stránka „Co hledáme“: ISSUES (otevřené otázky), otazky_pro_rodinu.md (oddíly podle rodů) a archivni_dotazy.md
    (oddíly podle archivů). Hlídá tvar, data zápisu, zodpovězené otázky a rody bez LINES."""
    warn, R, SAME = [], ns.get("RODINA", {}), ns.get("SAME", {})
    for n, i in enumerate(ns.get("ISSUES", []), 1):
        if isinstance(i, dict):
            k = i.get("k")
            if not i.get("otazka"):
                warn.append(f"ISSUES {n}: chybí „otazka“")
            if i.get("stav", "otevřené") not in ("otevřené", "hypotéza", "vyřešeno"):
                warn.append(f"ISSUES {n}: stav „{i.get('stav')}“ – má být otevřené, hypotéza nebo vyřešeno")
            if k is not None and SAME.get(k, k) not in P and k not in R:
                warn.append(f"ISSUES {n} ({i.get('otazka', '')[:40]}): osoba k={k!r} není v P ani v RODINA")
            text = str(i.get("text", ""))
        elif isinstance(i, (tuple, list)):
            text = str(i[1]) if len(i) > 1 else ""
            if not re.match(r"(Vyřešeno|Hypotéza|Otevřené)\s*:", text):
                warn.append(f"ISSUES {n} ({str(i[0])[:40]}): převeď na dict(k=…, otazka=…, stav=…, text=…) – "
                            "web ji jinak neumí zařadit k rodu ani poznat stav (reference/data.md)")
        else:
            text = ""
        if len(text) > 400:
            warn.append(f"ISSUES {n}: text má {len(text)} znaků – na webu ho čte rodina, zkrať na pár vět "
                        "(signatury a snímky patří do research_log.md)")
    jmena = {k: v[0] for k, v in LINES.items()}
    kmen = lambda t: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower())[:5]
    for name, druh in (("otazky_pro_rodinu.md", "rod"), ("archivni_dotazy.md", "archiv")):
        md = _md_bez_poznamek(name)
        if not md:
            continue
        if re.search(r"\(zapsáno [^)]*\)|deník č\.", md):
            warn.append(f"{name}: datum zápisu nebo číslo deníku („zapsáno …“, „deník č.“) jde na web – smaž ho, "
                        "pořadí určuje rod nebo archiv, ne datum")
        if re.search(r"(?mi)^\s*(?:[-*]|\d+\.).*\b(ODPOVĚZENO|zodpovězeno|vyřešeno)\b", md):
            warn.append(f"{name}: obsahuje zodpovězenou položku – smaž ji, odpověď patří do udaje_od_rodiny.md "
                        "nebo research_log.md")
        nadpisy = re.findall(r"(?m)^## +(.+)$", md)
        if druh == "rod":
            nezname = [h for h in nadpisy if not any(kmen(h.split()[0]) == kmen(j.split()[0]) for j in jmena.values())
                       and not re.match(r"(?i)(dokumenty|obecn|celá rodina|ostatní)", h)]
            if nezname:
                warn.append(f"{name}: oddíl {', '.join(f'„{h}“' for h in nezname[:4])} není rod z LINES – web ho nezařadí; "
                            "oddíly = názvy rodů (8–15), nahoře „Dokumenty doma“ a „Obecně“")
        elif nadpisy:
            podle_osob = [h for h in nadpisy if not re.search(r"(?i)archiv|SOA|SOkA|AHMP|ZA |MZA|úřad|fara|muzeum|knihovn", h)]
            if podle_osob:
                warn.append(f"{name}: oddíl {', '.join(f'„{h}“' for h in podle_osob[:3])} nevypadá jako archiv ani úřad – "
                            "oddíly mají být podle archivů (SOA Zámrsk, Matriční úřad …), rod a osobu napiš do odrážky")
    return warn


def main():
    err, warn = [], []
    ns = {}
    try:
        exec(open(os.path.join(DATA, "osoby.py"), encoding="utf-8-sig").read(), ns)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"CHYBA: data/osoby.py nejde načíst: {e}")
    P, SIDE, LINES, SAME = ns.get("P", {}), ns.get("SIDE", []), ns.get("LINES", {}), ns.get("SAME", {})
    zaz = jload("zaznamy.json", [])
    svazky, prep, hl = jload("svazky.json", {}), jload("prepisy.json", {}), jload("zvyrazneni.json", {})
    keys = [z.get("klic") for z in zaz]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        err.append(f"zápisy se stejným klíčem: {sorted(dup)}")
    keys = set(keys)
    stare = [z.get("klic") for z in zaz if z.get("druh") == "I"]
    if stare:   # rejstřík není událost: druh = křest/sňatek/úmrtí, rejstrik: true
        warn.append(f"zaznamy.json: {len(stare)} zápisů má druh „I“ (např. {stare[0]}) – nastav druh události (N, O, Z) a "
                    "„rejstrik“: true (zapis.py zaznamy <klíč> - --sloucit; reference/data.md)")
    jine = sorted({z.get("druh") for z in zaz} - {"N", "O", "Z", "B", "S", "J", "I", None})
    if jine:
        warn.append(f"zaznamy.json: neznámý druh {', '.join(map(str, jine))} – platné jsou N, O, Z, B, S, J")

    if 1 not in P:
        err.append("chybí osoba 1 (výchozí osoba rodokmenu)")
    for k, p in P.items():
        if not isinstance(k, int) or k < 1:
            err.append(f"osoba {k!r}: číslo musí být kladné celé číslo")
            continue
        if k > 1 and k // 2 not in P and k not in SAME:
            warn.append(f"osoba {k} ({p.get('n')}): v rodokmenu chybí její dítě {k // 2} – je číslo správně?")
        st = p.get("st", "unk")
        if st not in ("doc", "prob", "fam", "mh", "unk"):
            err.append(f"osoba {k}: neznámý stav '{st}'")
        for r in p.get("r", []):
            if r not in keys:
                err.append(f"osoba {k} ({p.get('n')}) cituje neexistující zápis '{r}'")
        if st == "doc" and not p.get("r"):
            warn.append(f"osoba {k} ({p.get('n')}) je 'doc' (doloženo), ale necituje žádný zápis")
    for s in SIDE:
        if s.get("k") not in P:
            err.append(f"boční příbuzný '{s.get('n')}' patří k neexistující osobě {s.get('k')}")
        for r in s.get("r", []):
            if r not in keys:
                err.append(f"boční příbuzný '{s.get('n')}' cituje neexistující zápis '{r}'")
        if not (s.get("t") or "").strip():
            warn.append(f"boční příbuzný '{s.get('n')}' nemá text (t) – na webu bude jen jméno")
    R = ns.get("RODINA", {})
    PARTNERI = ns.get("PARTNERI", [])
    odkazy = ({v for o in R.values() for v in [o.get("otec"), o.get("matka"), *o.get("partner", [])] if isinstance(v, str)}
              | {v for pr in PARTNERI for v in (pr.get("a"), pr.get("b")) if isinstance(v, str)})
    for oid, o in R.items():
        kde = f"RODINA '{oid}' ({o.get('n')})"
        if o.get("sex") not in ("M", "F"):
            err.append(f"{kde}: chybí sex=\"M\" nebo \"F\"")
        if o.get("st", "fam") not in ("doc", "prob", "fam", "mh", "unk"):
            err.append(f"{kde}: neznámý stav '{o.get('st')}'")
        for pole in ("otec", "matka"):
            v = o.get(pole)
            if isinstance(v, str) and v not in R:
                err.append(f"{kde}: {pole} '{v}' není v RODINA")
            elif isinstance(v, int) and not isinstance(v, bool) and (v < 1 or v not in P and v not in SAME):
                err.append(f"{kde}: {pole} {v} – takový předek v P není (1 = výchozí osoba, u jejích dětí)")
        for v in o.get("partner", []):
            if isinstance(v, str) and v not in R or isinstance(v, int) and v not in P and v not in SAME:
                err.append(f"{kde}: partner {v!r} neexistuje")
        if not (o.get("otec") or o.get("matka") or o.get("partner")) and oid not in odkazy:
            warn.append(f"{kde}: není s nikým spojen (chybí otec, matka i partner) – na webu bude jen samostatná stránka; "
                        "nejistého příbuzného raději jako poznámku do SIDE")
        for r in o.get("r", []):
            if r not in keys:
                err.append(f"{kde} cituje neexistující zápis '{r}'")
    for pr in PARTNERI:
        for v in (pr.get("a"), pr.get("b")):
            if isinstance(v, str) and v not in R or isinstance(v, int) and v not in P and v not in SAME or v is None:
                err.append(f"PARTNERI {pr.get('a')!r} × {pr.get('b')!r}: osoba {v!r} neexistuje (číslo z P nebo klíč z RODINA)")
    warn += kekule(P, SAME)
    for a, c in SAME.items():
        if c not in P:
            err.append(f"SAME: {a} -> {c}, ale osoba {c} neexistuje")
        elif not P[c].get("n") or P[c]["n"] in ("?",) or P[c]["n"].startswith(("otec neuveden", "matka neuvedena")):
            err.append(f"SAME: {a} -> {c}, ale osoba {c} je zástupná (bez jména) – alias musí ukazovat na skutečnou osobu")
    for k in LINES:
        if k not in range(8, 16):
            err.append(f"LINES: rod {k} – rody mají čísla 8 až 15 (pradědečci a prababičky)")
    nazvy = {}
    for k, v in sorted(LINES.items()):
        nazvy.setdefault(str(v[0]).strip().lower(), []).append(k)
    for n, ks in nazvy.items():
        if len(ks) > 1:
            err.append(f"LINES: rody {', '.join(map(str, ks))} mají stejný název „{LINES[ks[0]][0]}“ – rozliš je "
                       "(např. „Novákové z Holic“ a „Novákové z Chrudimi“), web by je jinak nerozlišil")
    docs_k = [d for d in jload("dokumenty.json", []) if isinstance(d, dict)]
    from pohled import _slug as slug_pristupu   # stejné id přístupu jako export
    ids_pristupu = {"vse"} | {slug_pristupu(p.get("nazev") or "") or f"pristup-{i}"
                              for i, p in enumerate(jload("web.json", {}).get("pristupy") or [], 1) if isinstance(p, dict)}
    for d in docs_k:
        if not (d.get("popis") or "").strip():
            warn.append(f"dokument {d.get('img')} nemá popis – na webu bude bez popisku")
        # doklady s rodnými čísly (reference/soukromi.md): rc, zacerneno, pristupy
        for pole in ("rc", "zacerneno", "osoby"):
            for r in d.get(pole) or []:
                if not (r in P or r in R):
                    err.append(f"dokument {d.get('img')}: {pole} – osoba {r!r} není v P ani v RODINA")
        for pid in d.get("pristupy") or []:
            if pid not in ids_pristupu:
                err.append(f"dokument {d.get('img')}: pristupy – přístup „{pid}“ ve web.json není (jsou: {', '.join(sorted(ids_pristupu))})")
        if "rc" not in d and (d.get("druh") in ("rodny_list", "oddaci_list", "umrtni_list", "domovsky_list", "obcansky")
                              or re.search(r"rodn[ýé] list|oddací list|úmrtní list|rodné číslo|občansk", d.get("popis") or "", re.I)):
            warn.append(f"dokument {d.get('img')}: doklad – vyplň \"rc\": [osoby, jejichž rodné číslo na něm je] (i prázdný "
                        "seznam, když RČ nemá); doklad s RČ žijícího se zveřejní až po úmrtním listu nebo začernění "
                        "(vyrez.py --zacernit)")

    cited = ({r for p in list(P.values()) + list(R.values()) for r in p.get("r", [])} | {r for s in SIDE for r in s.get("r", [])}
             | {r for h in ns.get("HYPOTEZY", []) if isinstance(h, dict) for r in h.get("zaznamy", [])})
    for z in zaz:
        k = z.get("klic", "?")
        if "pricina_umrti" in z:
            cause = z["pricina_umrti"]
            if z.get("druh") != "Z" or not isinstance(cause, dict):
                err.append(f"zápis {k}: příčina úmrtí musí být objekt u zápisu druhu Z")
            else:
                stav = cause.get("stav")
                if stav not in ("uvedena", "necitelna", "nevyplnena", "bez_rubriky"):
                    err.append(f"zápis {k}: neznámý stav příčiny úmrtí '{stav}'")
                for f in ("puvodni", "cesky", "jistota", "poznamka"):
                    if f in cause and not isinstance(cause[f], str):
                        err.append(f"zápis {k}: příčina úmrtí – '{f}' musí být text")
                if stav == "uvedena" and not all(isinstance(cause.get(f), str) and cause[f].strip()
                                                 for f in ("puvodni", "cesky", "jistota")):
                    err.append(f"zápis {k}: uvedená příčina úmrtí potřebuje původní výraz, český překlad a jistotu")
                if "jistota" in cause and cause["jistota"] not in ("doc", "prob"):
                    err.append(f"zápis {k}: jistota čtení příčiny úmrtí musí být 'doc' nebo 'prob'")
                if stav in ("necitelna", "nevyplnena", "bez_rubriky") and cause.get("cesky"):
                    err.append(f"zápis {k}: příčina úmrtí ve stavu '{stav}' nemá mít český překlad")
                if stav in ("nevyplnena", "bez_rubriky") and cause.get("puvodni"):
                    err.append(f"zápis {k}: příčina úmrtí ve stavu '{stav}' nemá mít původní výraz")
        for f in ("klic", "druh", "datum", "nazev", "shrnuti"):
            if not z.get(f):
                err.append(f"zápis {k}: chybí pole '{f}'")
        if z.get("svazek") and z["svazek"] not in svazky:
            err.append(f"zápis {k}: svazek '{z['svazek']}' není v data/svazky.json")
        if z.get("ukazka"):   # vymyšlený zápis ukázkové rodiny – nemá snímek ani přepis
            continue
        sv = svazky.get(z.get("svazek", ""))
        if not z.get("odkaz") and not (sv or {}).get("url") and not (sv and not sv.get("portal")):
            # svazek bez „portal“ = doklad od rodiny nebo z badatelny, online odkaz nemá (#37)
            warn.append(f"zápis {k}: chybí odkaz na snímek (pole 'odkaz')")
        if not os.path.exists(os.path.join(ROOT, "vyrezy", k + ".jpg")):
            warn.append(f"zápis {k}: chybí výřez vyrezy/{k}.jpg")
        elif k not in hl:
            warn.append(f"zápis {k}: chybí rámeček (tools/ramecek.py)")
        if k not in prep:
            warn.append(f"zápis {k}: chybí přepis a překlad v data/prepisy.json")
        if k not in cited:
            warn.append(f"zápis {k}: necituje ho žádná osoba (doplnit do 'r' u osoby nebo bočního příbuzného)")
    for k, v in prep.items():   # web čte jen „orig“ a „cs“ – jiné pole (třeba „preklad“) by tiše chybělo (#74)
        if not isinstance(v, dict):
            err.append(f"přepis {k}: má být objekt {{\"orig\": …, \"cs\": …}}")
            continue
        jine = sorted(set(v) - {"orig", "cs"})
        if jine:
            warn.append(f"přepis {k}: pole {', '.join(jine)} web nezobrazí – přepis patří do „orig“, překlad do „cs“")
        for pole, co in (("orig", "přepis originálu"), ("cs", "český překlad")):
            if not str(v.get(pole) or "").strip():
                warn.append(f"přepis {k}: chybí {co} (pole „{pole}“) – na webu bude prázdný")

    znamy = [k for k in range(8, 16) if P.get(k, {}).get("st") in ("doc", "prob")]
    chybi = [f"{k} ({P[k].get('n', '?')})" for k in znamy if k not in LINES]
    if chybi:   # bez LINES web neukáže rody ani barvy ve vějíři
        warn.append(f"LINES: chybí rod pro {', '.join(chybi)}"
                    " – jakmile znáš pradědečky a prababičky (8–15), vyplň v data/osoby.py LINES (reference/data.md)")

    warn += co_hledame(ns, P, LINES)

    # Časová návaznost: stejná pravidla ukazuje web na stránce Časová osa; ověřený údaj se odškrtne polem overeno.
    for k in sorted(k for k in P if isinstance(k, int)):
        o = P[k].get("overeno")
        if o is None:
            continue
        if not isinstance(o, dict):
            warn.append(f"osoba {k}: overeno má být slovník {{\"pravidlo\": \"proč údaj platí\"}}")
            continue
        for x in o:
            if x not in chronologie.PRAVIDLA:
                warn.append(f"osoba {k}: overeno – neznámé pravidlo '{x}' (platná: {', '.join(chronologie.PRAVIDLA)})")
    for v in chronologie.kontrola(P, SAME):
        warn.append(f"časová návaznost u osoby {v.k}: {v.text} Pokud údaj platí, přidej k osobě {v.k} "
                    f"do overeno: \"{v.pravidlo}\": \"proč údaj platí\"")

    mista = jload("mista.json", {})
    vzory = []
    for n, e in mista.items():
        try:
            vzory += [re.compile(e.get("re") or re.escape(n))] if "lat" in e else []
        except re.error:   # špatný výraz hlásí kontrola míst níž
            pass
    # jméno ženy: rodné příjmení, ne „Marie Tesařová (Plíšková)“ (příjmení po sňatku je vidět u manžela)
    for kde, o in [(f"osoba {k}", p) for k, p in P.items()] + [(f"RODINA '{k}'", o) for k, o in ns.get("RODINA", {}).items()]:
        m = re.search(r"\((\w+(?:ová|á))\)\s*$", o.get("n", ""))
        if m:
            warn.append(f"{kde} ({o['n']}): v n je příjmení po sňatku „{m.group(1)}“ – piš jen rodné příjmení "
                        "(neznámé: „(příjmení neznámé)“); příjmení po sňatku je vidět u manžela")
    # soukromí osob (reference/soukromi.md): souhlas žijícího se zveřejněním, ruční „soukrome“, údaj „(soukromé) …“
    for kde, o in [(f"osoba {k}", p) for k, p in P.items()] + [(f"RODINA '{k}'", o) for k, o in ns.get("RODINA", {}).items()]:
        sh = o.get("souhlas")
        if sh is not None:
            if not isinstance(sh, dict) or not str(sh.get("kdo") or "").strip() or not str(sh.get("datum") or "").strip():
                err.append(f"{kde} ({o.get('n')}): souhlas musí mít kdo a datum – "
                           "souhlas={'kdo': 'Jméno', 'datum': 'RRRR-MM-DD', 'rozsah': ['udaje', 'doklady']}; jinak neplatí")
            elif not set(sh.get("rozsah") or []) <= {"udaje", "doklady"}:
                err.append(f"{kde} ({o.get('n')}): souhlas – rozsah zná jen 'udaje' a 'doklady'")
        if "soukrome" in o and not isinstance(o["soukrome"], bool):
            err.append(f"{kde} ({o.get('n')}): soukrome má být True nebo False")
        for f in o.get("f", []):
            if isinstance(f, str) and re.match(r"\s*\(soukrom", f, re.I) and not re.match(r"\s*\(soukromé\) \S", f, re.I):
                warn.append(f"{kde} ({o.get('n')}): soukromý údaj piš přesně „(soukromé) text“ – „{f[:40]}“ se jinak "
                            "ukáže všem")
    muz = lambda k, p: p.get("sex", "M") == "M" if k == 1 else k % 2 == 0   # noqa: E731
    bez_mista = [k for k, p in sorted(P.items()) if isinstance(k, int) and p.get("st") == "doc" and p.get("f")
                 and not any(zil_v(vlastni_text([text_pro_misto(f) for f in p["f"]], muz(k, p)), rx) for rx in vzory)]
    if bez_mista:   # mapa na webu ukáže jen obce z data/mista.json, kde osoba sama žila (ne obec matky, fara…)
        seznam = ", ".join(f"{k} {P[k].get('n', '?')}" + (f" [{', '.join(s)}]" if (s := slova_obce(P[k]["f"])) else "")
                           for k in bez_mista)   # všechny – ukázka tří schovala obce, které chyběly
        warn.append(f"mapa: {len(bez_mista)} doložených předků nemá v údajích žádnou svou obec z data/mista.json ({seznam})"
                    " – přidej jejich obce: tools/mista.py pridej \"Obec\", pak tools/mista.py")

    def kmeny(s):   # první 4 písmena slov bez diakritiky; text v závorce se nepočítá
        s = "".join(c for c in unicodedata.normalize("NFD", re.sub(r"\(.*?\)", "", s).lower())
                    if not unicodedata.combining(c))
        return {w[:4] for w in re.findall(r"[a-z]{3,}", s)}

    obce = []   # všechny platné výrazy obcí, i bez souřadnic (vzory výš jsou jen obce na mapě)
    for n, e in mista.items():
        try:
            obce.append(re.compile(e.get("re") or re.escape(n)))
        except re.error:
            pass

    def bez_obce(f):   # „× 1950 Holice Karel Hrubý“ → bez obce hned za datem (Holice ≠ Holický), jméno zůstane
        i = re.match(r"×[\s\d.,?/–-]*", f).end()
        for rx in obce:
            m = rx.match(f, i)
            if m and m.end() > i:
                return f[:i] + " " + f[re.compile(r"\w*").match(f, m.end()).end():]
        return f

    def neznamy(p):   # jako placeholder() v export_web.py
        return p.get("n", "").startswith(("otec neuveden", "matka neuvedena")) or p.get("n", "") in ("", "?")
    for k, p in P.items():   # sňatek „× Jméno“ má jmenovat partnera na sousedním čísle (k ^ 1, SAME vzít v úvahu)
        satky = [kmeny(bez_obce(f)) for f in p.get("f", []) if isinstance(f, str) and f.startswith("×")]
        satky = [s for s in satky if s]
        if not isinstance(k, int) or not satky:
            continue
        kandidati = {k ^ 1} | {a ^ 1 for a, c in SAME.items() if c == k and isinstance(a, int)}
        partneri = {sp for sp in {SAME.get(sp, sp) for sp in kandidati} if sp in P and not neznamy(P[sp])}
        if partneri and not any(kmeny(P[sp].get("n", "")) & s for sp in partneri for s in satky):
            sp = min(partneri)
            warn.append(f"osoba {k} ({p.get('n')}): žádný sňatek (×) nejmenuje partnera {sp} ({P[sp].get('n')})"
                        " – patří sňatek k této osobě, je číslo správně?")

    # Číslo domu v zápisu: za „čp.“, „č.“, „čís.“, „No“, „N.“, „N°“, „Nro“, „Nr.“, „Haus“, „domu“, v poli „[Dům] …“
    # nebo hned za obcí z mista.json („z Břilic 23“). Datum („5. 1. 1767“, „23. února“, „9. 9bris“), věk, rok
    # ani číslo zápisu, strany či snímku („zápis č. 23“) dům nedokládají.
    mesic = (r"ledna|února|března|dubna|května|června|července|srpna|září|října|listopadu|prosince|"
             r"jänner|januar|feber|februar|märz|april|mai|juni|juli|august|september|oktober|october|november|"
             r"dezember|december|januarii|februarii|martii|aprilis|maii|junii|julii|augusti|septembris|octobris|"
             r"novembris|decembris|[7-9x]bris|10bris|jan|feb|mär|apr|aug|sept?|okt|oct|nov|dez|dec")
    ne_datum = rf"(?!\d|\.\s*(?:\d|(?:{mesic})(?![^\W\d_])))"
    za_cislo = r"(\d+)" + ne_datum
    s_predponou = re.compile(r"(?<![^\W\d_])(?:čp|čís|č|nro|nr|no|n°|n|haus|dům|domu|domě)\.?\s*" + za_cislo, re.I)
    pole_domu = re.compile(r"\[[^\]\n]*(?:dům|domu|haus)[^\]\n]*\]([^\n|\[]*)", re.I)
    po_obci = re.compile(r"\w*,?\s+(\d{1,3})" + ne_datum, re.I)   # číslo hned za obcí, ne rok
    ne_dum = re.compile(r"(?<![^\W\d_])(?:zápis\w*|záznam\w*|stran\w*|str|list\w*|fol|folio|sním\w*|sn|pag)\.?\s*$",
                        re.I)

    def cisla_domu(t):   # každé pole zvlášť, aby se pole „[Dům]“ nepřelilo do dalšího textu
        cisla = {m.group(1) for m in s_predponou.finditer(t) if not ne_dum.search(t[max(0, m.start() - 12):m.start()])}
        cisla |= {c for v in pole_domu.findall(t) for c in re.findall(r"(?<!\d)" + za_cislo, v, re.I)}
        for rx in obce:   # výraz obce se jen hledá, do jiných výrazů se nevkládá (vlastní příznaky a skupiny)
            for m in rx.finditer(t):
                c = po_obci.match(t, m.end())
                if c and m.end() > m.start():
                    cisla.add(c.group(1))
        return cisla
    cisla_zaz = {z.get("klic"): cisla_domu(str(z.get("shrnuti", ""))) | cisla_domu(str(z.get("nazev", ""))) for z in zaz}
    ukazka_zaz = {z.get("klic") for z in zaz if z.get("ukazka")}
    zapisy_osoby = {}   # předek v rodokmenu dvakrát (SAME): zápisy hlavní osoby i všech aliasů
    for k, p in P.items():
        zapisy_osoby.setdefault(SAME.get(k, k), set()).update(p.get("r", []))
    for k, p in P.items():   # čp. z faktů má být v citovaném zápisu
        zapisy = zapisy_osoby.get(SAME.get(k, k), set())
        if p.get("st") != "doc" or not zapisy - ukazka_zaz:   # vymyšlené zápisy ukázky přepis nemají
            continue
        dolozena = set().union(*(cisla_zaz.get(r, set()) | cisla_domu(str(prep.get(r, {}).get("orig", "")))
                                 | cisla_domu(str(prep.get(r, {}).get("cs", ""))) for r in zapisy))
        fakta = [f for f in p.get("f", []) if isinstance(f, str)   # „(podle stromu)“, „(z vyprávění)“ = zdroj označený
                 and not re.search(r"\([^)]*\b(?:strom|vyprávění|rodin)", f, re.I)]
        for c in sorted(set(re.findall(r"čp\.\s*(\d+)", " ".join(fakta))) - dolozena, key=int):
            warn.append(f"osoba {k} ({p.get('n')}): čp. {c} není v žádném citovaném zápisu – ověřit, "
                        "nebo označit zdroj (strom, vyprávění)")

    for name, e in mista.items():
        if "lat" not in e:
            warn.append(f"místo {name}: nemá souřadnice (spusťte tools/mista.py)")
        try:
            re.compile(e.get("re") or "")
        except re.error as ex:
            err.append(f"místo {name}: špatný výraz '{e.get('re')}': {ex}")

    cfg = jload("web.json", {})
    # Chybějící přihlašovací otázku nehlásit pořád – ohlídá ji až nasazení (export_web.py --nasazeni).
    ukazka = ("Rodokmen Novákových", "(ukázka", "vymyšlená rodina", "kovárnu v Holicích čp. 112")
    if any(u in json.dumps(cfg, ensure_ascii=False) for u in ukazka) and "Novák" not in P.get(1, {}).get("n", ""):
        warn.append("web.json: jsou v něm ještě ukázkové texty (Novákovi) – nastav název, příběh a kontakt")

    # Citlivé věci, které jdou na web: ISSUES („Co hledáme“), poznámky a fakta osob, boční příbuzní, texty.
    citlive = re.compile(r"sebevra|vzal[a]? si život|oběsil|zastřelil[a]? se|utopil[a]? se|alkohol|vězen|kriminál|"
                         r"rozvod|rozvedl|psychiatr|léčebn|duševn|rakovin|nemanželsk|cizoložst|dluh|exekuc|interrupc|potrat", re.I)

    hranice = datetime.date.today().year - 100   # posledních ~100 let; staré matriční údaje (nemanželské dítě v 18. stol.) nevadí

    def recent(text):   # datum v závorce („Dovětek (3. 11. 2026)“) je datum zápisu poznámky, ne události
        text = re.sub(r"\(\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*\)", "", text)
        return any(int(y) >= hranice for y in re.findall(r"\b(19\d\d|20\d\d)\b", text))

    def popreno(text, m):   # „nejsou dluhy“, „bez dluhů“, „nebyl rozveden“ – slovo je popřené
        return re.search(r"(?:^|\s)(?:bez|žádn\w*|nejsou|nebyl\w*|neměl\w*|nemá\w*|není)\s+(?:\w+\s+)?$",
                         text[max(0, m.start() - 30):m.start()], re.I)
    schvaleno = [s for s in (cfg.get("citlive_schvaleno") if isinstance(cfg.get("citlive_schvaleno"), list) else [])
                 if isinstance(s, str) and len(s.strip()) >= 3]

    def schvalene(text, m):   # uživatel to na web pustil: v web.json „citlive_schvaleno“ je úryvek textu s tímto slovem
        for s in schvaleno:
            i = text.find(s)
            while i >= 0:
                if i <= m.start() and m.end() <= i + len(s):
                    return True
                i = text.find(s, i + 1)
        return False
    texty = [("ISSUES", i if isinstance(i, str) else " ".join(str(v) for v in (i.values() if isinstance(i, dict) else i)))
             for i in ns.get("ISSUES", [])]
    for k, p in P.items():
        text = " ".join(p.get("f", [])) + " " + p.get("note", "")
        roky = [int(y) for y in re.findall(r"\b1[5-9]\d\d|20\d\d\b", p.get("y", "") + " " + text)]
        texty.append((f"osoba {k}", text + (f" {hranice}" if roky and min(roky) >= 1870 or k < 8 else "")))
    texty += [(f"boční příbuzný {s.get('n')}", s.get("n", "") + " " + s.get("t", "")) for s in SIDE]
    texty += [(f"RODINA {oid}", " ".join(o.get("f", [])) + " " + o.get("note", "") + " " + o.get("y", "")) for oid, o in R.items()]
    for z in zaz:
        cause = z.get("pricina_umrti")
        if isinstance(cause, dict):
            text = " ".join(str(cause.get(f, "")) for f in ("puvodni", "cesky", "poznamka"))
            texty.append((f"příčina úmrtí {z.get('klic')}", text + " " + str(z.get("datum", ""))))
    for f in ("zajimavosti.md", "pribeh.md", "otazky_pro_rodinu.md", "archivni_dotazy.md"):
        path = os.path.join(DATA, f)
        if os.path.exists(path):
            obsah = open(path, encoding="utf-8-sig").read()
            texty += [(f, odst) for odst in re.split(r"\n\s*\n|\n(?=#)", obsah)]   # odstavce i oddíly „## …“
    story_dir = os.path.join(DATA, "pribehy")
    if os.path.isdir(story_dir):
        for name in sorted(os.listdir(story_dir)):
            if name.endswith(".md"):
                path = os.path.join(story_dir, name)
                obsah = open(path, encoding="utf-8-sig").read()
                texty += [(f"pribehy/{name}", odst) for odst in re.split(r"\n\s*\n|\n(?=#)", obsah)]
    # na web jdou i hypotézy (stránky rodů) a deník
    texty += [(f"hypotéza {h.get('nadpis', '')}", h.get("nadpis", "") + " " + h.get("text", ""))
              for h in ns.get("HYPOTEZY", []) if isinstance(h, dict)]
    log = os.path.join(DATA, "research_log.md")
    if os.path.exists(log):
        texty += [(f"deník ř. {l.split('|')[1].strip()}", l.split('|', 3)[3]) for l in open(log, encoding="utf-8-sig")
                  if re.match(r"^\| \d+ \|", l)]   # bez sloupců č. a datum (datum hledání není rok události)
    for kde, text in texty:
        denik = kde.startswith("deník")   # řádek deníku míchá roky z různých století – rozhoduje jen okolí nálezu
        if not denik and not recent(text):
            continue
        m = next((m for m in citlive.finditer(text) if not schvalene(text, m) and not popreno(text, m)
                  and (not denik or recent(text[max(0, m.start() - 80):m.end() + 80]))), None)
        if m:
            warn.append(f"CITLIVÉ ({kde}): „…{text[max(0, m.start() - 40):m.end() + 40].strip()}…“ – jde na web; "
                        f"zeptej se uživatele, jestli to tam smí být (reference/soukromi.md); když ano, "
                        f"přidej úryvek textu s tím slovem do web.json „citlive_schvaleno“")

    has_story = os.path.exists(os.path.join(DATA, "pribeh.md"))
    if os.path.isdir(story_dir):
        has_story = has_story or any(name.endswith(".md") for name in os.listdir(story_dir))
    if not has_story:
        hlavni = min(LINES) if LINES else 8   # bez LINES rod po meči (otec otce otce)
        jmeno = (LINES[hlavni][0] if LINES else
                 (P.get(8) or P.get(1) or {}).get("n", "").split()[-1:] or ["po meči"])
        jmeno = jmeno if isinstance(jmeno, str) else jmeno[0]
        n = max((k.bit_length() for k in P if isinstance(k, int) and k >= 8 and k >> (k.bit_length() - 4) == hlavni),
                default=0)
        if n >= 6:
            warn.append(f"rod {jmeno} má už {n} generací – je čas napsat příběh rodu "
                        f"(data/pribeh.md, reference/pribehy.md); koncept nejdřív ukaž uživateli v chatu")

    try:   # rodina jako graf (tools/graf.py): věk rodičů 2k a 2k+1, stejná osoba na dvou číslech bez SAME
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import graf
        # věk rodičů a úmrtí rodiče před narozením už hlídá chronologie.py (jde potlačit polem overeno); z graf.py jen dvojníci
        warn += [w for w in graf.predci(P, SAME) if "nejspíš tatáž jako" in w]
    except ImportError:
        pass

    # údaje o procesu (kdo práci udělal, jak se ověřilo, čísla úkolů) v textech pro web – pravidla: reference/zapisy.md
    proces = re.compile(r"pomocník|\bagent\w*|\bsonnet\b|\bClaude\b|(?:ověřen\w*|čten\w*|přečten\w*) (?:na|z) (?:snímk\w+|výřez\w+|výřezu)"
                        r"|\bvlna \d|\bN\d{1,2}[a-z]\b|\bU-\d{4}\b|čtyř oči|nečteno mnou|mnou ověřen", re.I)
    nalezy = []
    for k, o in P.items():
        for pole, text in [("f", x) for x in o.get("f", [])] + [("note", o.get("note", ""))]:
            for m in proces.finditer(text or ""):
                nalezy.append(f"osoba {k} ({pole}): „{m.group(0)}“")
    for z in zaz.values() if isinstance(zaz, dict) else zaz:
        for pole in ("nazev", "shrnuti"):
            for m in proces.finditer(z.get(pole, "") or ""):
                nalezy.append(f"zápis {z.get('klic', '?')} ({pole}): „{m.group(0)}“")
    if nalezy:
        warn.append(f"{len(nalezy)} výskytů údajů o procesu v textech pro web (kdo práci udělal, jak se ověřilo) – patří jen do front a deníku"
                    f" (reference/zapisy.md); seznam: kontrola.py --proces")
        if "--proces" in sys.argv:
            for n in nalezy:
                print("  proces:", n)

    log = os.path.join(DATA, "research_log.md")
    rows, duplicate_ids = research_log_stats(log)
    if duplicate_ids:
        err.append(f"deník obsahuje duplicitní identifikátory: {', '.join(duplicate_ids)}")
    print(f"{len(P)} osob, {len(zaz)} zápisů, {len(svazky)} svazků, {rows} řádků deníku")
    for e in err:
        print("CHYBA:", e)
    for w in warn:
        print("upozornění:", w)
    if not err and not warn:
        print("Vše v pořádku.")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
