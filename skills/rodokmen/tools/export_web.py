#!/usr/bin/env python3
"""Export dat rodokmenu (data/*) do webu ve složce web/.

Čte data/osoby.py, data/zaznamy.json, data/svazky.json, data/prepisy.json, data/zvyrazneni.json,
data/mista.json, data/web.json, data/dokumenty.json a markdownové poznámky. Zapisuje
web/src/data/site.json, web/src/generated/*, web/public/{img,zdroje}, web/public/prihlaseni.html,
web/nginx.conf a web/netlify/edge-functions/brana.js.

Spouští se z web/ příkazem `npm run data` (nebo přímo `python3 -I tools/export_web.py`, na Windows `python -I -X utf8 …`).
"""
import datetime, glob, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, unicodedata
import concurrent.futures as cf
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python -I nepřidává složku skriptu do cesty
import chronologie  # noqa: E402 – data a pravidla časové osy (tools/chronologie.py)

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DATA = os.path.join(ROOT, "data")
WEB = os.path.join(ROOT, "web")
VYREZY = os.path.join(ROOT, "vyrezy")      # výřezy zápisů a dokumentů (asi 1800 px) – zobrazují se na webu
ZDROJE = os.path.join(ROOT, "zdroje")      # tytéž výřezy v plném rozlišení (proklik)

LINE_COLORS = {8: "#EFB45F", 9: "#F09A78", 10: "#E58AA6", 11: "#B99AE0",
               12: "#86B8E8", 13: "#6FCBB9", 14: "#9CD17A", 15: "#D3D46A"}
STATUS = {"doc": "doloženo matrikou", "prob": "pravděpodobné", "fam": "údaj od rodiny",
          "mh": "jen z cizího rodokmenu", "unk": "neznámé"}
SIDE_KIND = {"bratr": "sib", "sestra": "sib", "manžel": "spouse", "manželka": "spouse", "syn": "child", "dcera": "child"}
SIB_STATUS = {"hotovo": "done", "částečně": "partial"}
KINDS = {"N": "křest / narození", "O": "sňatek", "Z": "úmrtí", "I": "rejstřík", "S": "sčítání lidu", "J": "jiný pramen"}


def jload(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_people():
    ns = {}
    exec(open(os.path.join(DATA, "osoby.py"), encoding="utf-8").read(), ns)
    for name, default in (("P", {}), ("SIDE", []), ("LINES", {}), ("ISSUES", []), ("HYPOTEZY", []), ("SAME", {}), ("RODINA", {}), ("PARTNERI", [])):
        ns.setdefault(name, default)
    return ns


def record_rows():
    svazky = jload("svazky.json", {})
    rows = []
    for z in jload("zaznamy.json", []):
        sv = svazky.get(z.get("svazek", ""), {})
        key = z["klic"]
        rows.append(dict(
            key=key, kind=z.get("druh", "J"), date=z.get("datum", ""), title=z.get("nazev", key),
            summary=z.get("shrnuti", ""), scan=z.get("snimek", ""), cause=z.get("pricina_umrti"),
            archive=sv.get("archiv", ""), volume=sv.get("svazek", ""), vdesc=sv.get("popis", ""),
            portal=sv.get("portal", "archivu"), url=z.get("odkaz") or sv.get("url", ""),
            img=os.path.exists(os.path.join(VYREZY, key + ".jpg")),
            full=os.path.exists(os.path.join(ZDROJE, key + ".jpg")),
        ))
    return rows


def strip_comments(md):
    """Poznámky <!-- … --> v markdownu jsou pro Clauda, ne pro web."""
    return re.sub(r"<!--.*?-->\n?", "", md, flags=re.S)


def story_frontmatter(path, slug, require_rod=True):
    """Načte omezené skalární frontmatter pro příběhy bez další Python závislosti."""
    text = open(path, encoding="utf-8").read()
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
    if not match:
        sys.exit(f"CHYBA: {path}: chybí YAML frontmatter.")
    fields = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.fullmatch(r"(title|lead|rod):\s*(.*?)\s*", line)
        if not item:
            sys.exit(f"CHYBA: {path}: očekávám pouze skalární pole title, lead a rod.")
        key, value = item.groups()
        if key in fields:
            sys.exit(f"CHYBA: {path}: pole {key} je uvedené vícekrát.")
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as ex:
                sys.exit(f"CHYBA: {path}: neplatná hodnota {key}: {ex}")
            if not isinstance(value, str):
                sys.exit(f"CHYBA: {path}: {key} musí být text.")
        elif value.startswith("'"):
            if len(value) < 2 or not value.endswith("'"):
                sys.exit(f"CHYBA: {path}: neuzavřená hodnota {key}.")
            value = value[1:-1].replace("''", "'")
        fields[key] = value
    for key in ("title", "lead") + (("rod",) if require_rod else ()):
        if key not in fields:
            sys.exit(f"CHYBA: {path}: ve frontmatter chybí pole {key}.")
    if not fields["title"].strip():
        sys.exit(f"CHYBA: {path}: title nesmí být prázdný.")
    rod = fields.get("rod")
    if require_rod and not re.fullmatch(r"(?:[8-9]|1[0-5])", rod or ""):
        sys.exit(f"CHYBA: {path}: rod musí být číslo 8 až 15.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        sys.exit(f"CHYBA: {path}: název souboru musí být bezpečný slug z malých písmen, číslic a pomlček.")
    return dict(slug=slug, title=fields["title"], lead=fields["lead"],
                rod=int(rod) if require_rod else None, text=text)


def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def norm_answer(text):
    """Stejná normalizace jako v prihlaseni.html: bez diakritiky, malá písmena, jen a-z0-9.
    Kdyby z odpovědi nezbylo nic (např. „***“ nebo azbuka), použije se malými písmeny bez mezer – jinak by byla prázdná."""
    t = unicodedata.normalize("NFD", text)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", t) or re.sub(r"\s+", "", t)


def life(y):
    """Roky narození a úmrtí pro časovou osu („1820–1886“ → (1820, 1886), „* 1955“ → (1955, None))."""
    y = (y or "").strip()
    ys = [int(v) for v in re.findall(r"\d{4}", y)]
    if not ys:
        return None, None
    if y.startswith("*"):
        return ys[0], None
    if y.startswith("†"):
        return None, ys[0]
    return ys[0], ys[1] if len(ys) > 1 else None


def place_event(fact):
    """Událost z údaje osoby: značka (* × † nebo ·), rok a text."""
    yr = re.search(r"\b1[4-9]\d\d\b|\b20[0-2]\d\b", fact)
    return dict(sign=fact[0] if fact[:1] in "*×†" else "·", year=int(yr.group()) if yr else None, text=fact)


def years(y):
    y = (y or "").strip()
    ys = re.findall(r"\d{4}", y)
    if not ys:
        return ""
    approx = "≈" if re.match(r"^(asi|≈)", y) else ""
    head, dash, tail = y.partition("–")
    if y.startswith(("?", "†")) or (dash and not re.search(r"\d", head)) or re.match(r"po\b", y):
        # neznámé narození: ukázat jen úmrtí („? – před 1743“ → „† před 1743“, „– po 1921“ → „žil 1921“)
        if re.search(r"\bpo\b", tail or y):
            return "žil " + ys[-1]
        return "† " + ("před " if "před" in y else "") + ys[-1]
    if y.startswith("*"):
        return "* " + ys[0]
    if len(ys) == 1:
        return approx + ys[0]
    second = "?" if "před" in tail else ("po " if re.search(r"\bpo\b", tail) else "") + \
        ("≈" if re.search(r"(asi|≈)", tail) else "") + ys[-1]
    return f"{approx}{ys[0]}–{second}"


HRANICE_ZIJICI = datetime.date.today().year - 100   # stejná hranice jako u citlivých údajů v kontrola.py
ZIJICI_POZN = "Žijící – údaje jen základní."


def zijici(y, note="", facts=()):
    """Žijící nebo možná žijící: v poznámce „žijící“, nebo narozen v posledních 100 letech bez známého úmrtí."""
    if re.search(r"\bžij[íi]c", (note or "").lower()):
        return True
    y = (y or "").strip()
    if y.startswith(("?", "†", "–", "-", "po ")) or "†" in y or any(str(f).lstrip().startswith("†") for f in facts):
        return False
    if re.search(r"[–-]\s*(asi\s+|≈\s*)?\d{4}", y):   # rok úmrtí známý („1892–1970“)
        return False
    ys = re.findall(r"\d{4}", y)
    return bool(ys) and int(ys[0]) >= HRANICE_ZIJICI


def gen(k):
    return k.bit_length() - 1


def relation(k):
    g, male = gen(k), (k % 2 == 0)
    if g == 0:
        return "výchozí osoba rodokmenu"
    if g == 1:
        return "otec" if male else "matka"
    base = "dědeček" if male else "babička"
    if g <= 5:
        return "pra" * (g - 2) + base
    return f"{'předek' if male else 'předkyně'} v {g}. generaci ({'pra' * (g - 2)}{base})"


def placeholder(p):
    return chronologie.zastupna(p)


def timeline_data(P, SAME, slugs, people, line_of):
    """Časová osa: řádky v pořadí otec – dítě – matka, události jako intervaly v desetinných letech, varování."""
    dnes = datetime.date.today()

    def ev(d):
        if d is None:
            return None
        return {"from": None if d.od == chronologie.MIN else round(chronologie.rok(d.od), 3),
                "to": None if d.do == chronologie.MAX else round(chronologie.rok(d.do), 3), "text": d.text}
    # Soukromí: u žijících (viz skryj() v main) jen rok narození, bez data sňatku a bez varování o jejich datech
    skryti = {k for k in slugs if k not in SAME and zijici(P[k].get("y"), P[k].get("note"), P[k].get("f", []))}
    warns = [v for v in chronologie.kontrola(P, SAME) if not ({v.k, *v.osoby} & skryti)]
    s_varovanim = {v.k for v in warns}
    ud = {k: chronologie.udalosti(P, k) for k in slugs if k not in SAME}
    rows = []
    for pos, k in chronologie.radky(P, SAME):
        if k not in ud:
            continue
        p, u = P[k], ud[k]
        b = ev(u["narozeni"])
        if k in skryti and b:
            b["text"] = str(int(b["from"])) if b["from"] is not None else ""
        manzel = {k, k ^ 1} & skryti if k > 1 else {k} & skryti   # sňatek rodičů žijícího: otec i matka (k ^ 1) mají stejný
        rows.append(dict(k=pos, slug=slugs[k], name=p["n"], line=line_of(pos), years=people[slugs[k]]["years"],
                         birth=b, marriage=None if manzel else ev(u["snatek"]), death=None if k in skryti else ev(u["umrti"]),
                         living=chronologie.zije(p, u, dnes),
                         uncertain=p.get("st") in ("prob", "mh") or any(d and d.approx for d in u.values()),
                         warn=k in s_varovanim))
    roky = [x for r in rows for e in (r["birth"], r["marriage"], r["death"]) if e for x in (e["from"], e["to"]) if x is not None]
    return {"from": int(min(roky)) // 10 * 10 if roky else dnes.year - 100, "to": dnes.year, "rows": rows,
            "warnings": [dict(k=v.k, slug=slugs[v.k], rule=v.pravidlo, text=v.text, maybe=v.mozna,
                              people=[slugs[x] for x in v.osoby if x in slugs]) for v in warns]}


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
from obraz import najdi_magick   # společný hledač ImageMagicku (tools/obraz.py)
from pohled import nacti_pristupy, pohled   # noqa: E402 – přístupy k webu a pohled od jiné výchozí osoby (tools/pohled.py)


def magick_bin():
    return najdi_magick()


def size(path):
    w, h = subprocess.run([magick_bin(), path + "[0]", "-format", "%w %h", "info:"],
                          capture_output=True, text=True, check=True).stdout.split()
    return int(w), int(h)


def draw_boxes(src, dst, boxes, small):
    """Kopie výřezu v plném rozlišení s nakreslenými rámečky (pokud má stejný poměr stran jako webový výřez,
    na kterém se rámečky měřily). Vrací False, pak se kopíruje bez rámečků."""
    if not os.path.exists(small) or not magick_bin():
        return False
    (W, H), (w, h) = size(src), size(small)
    if abs(W / H - w / h) > 0.015 * (w / h):
        return False
    sw = max(4, round(W / 450))
    cmd = [magick_bin(), src, "-fill", "none", "-stroke", "#d7302a", "-strokewidth", str(sw)]
    for x0, y0, x1, y1 in boxes:
        cmd += ["-draw", f"rectangle {x0 * W:.0f},{y0 * H:.0f},{x1 * W:.0f},{y1 * H:.0f}"]
    subprocess.run(cmd + ["-quality", "90", dst], check=True)
    return True


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def poznamky_files(otisky):
    """Funkce Netlify /api/poznamky (netlify/functions/poznamky.mjs) s otisky přístupů, které smí poznámky číst a psát.
    Když je nemá žádný, funkce se smaže (na webu pak není ani tlačítko)."""
    out = os.path.join(WEB, "netlify", "functions", "poznamky.mjs")
    if not any(v["poznamky"] for v in otisky.values()):
        if os.path.exists(out):
            os.remove(out)
        return
    tpl = os.path.join(WEB, "netlify", "poznamky.sablona.mjs")
    if not os.path.exists(tpl):
        sys.exit("CHYBA: web/ nemá šablonu poznámek. Aktualizujte projekt: python3 -I <skill>/tools/novy_projekt.py <složka projektu>")
    write(out, open(tpl, encoding="utf-8").read().replace("{{PRISTUPY}}", json.dumps(otisky, indent=2)))


def login_files(cfg, pristupy=None):
    """Přihlašovací brána: otázka na webu, na serveru (nginx i Netlify) jen otisk odpovědi (SHA-256).
    Stejný otisk spočítá přihlašovací stránka a uloží ho do cookie – samotná odpověď se nikam neukládá.
    S přístupy (web.json → pristupy) brána podle otisku pošle jen verzi webu pro ten přístup (dist/_p/<id>/)."""
    login = cfg.get("prihlaseni") or {}
    answer = norm_answer(login.get("odpoved", ""))
    tpl = open(os.path.join(WEB, "prihlaseni.sablona.html"), encoding="utf-8").read()
    if "rodokmen:" not in tpl:   # stará šablona (do 0.4.0) ukládá do cookie odpověď – s novou bránou by se nikdo nepřihlásil
        sys.exit("CHYBA: web/ má starou šablonu přihlášení. Aktualizujte projekt: python3 -I <skill>/tools/novy_projekt.py <složka projektu>")
    contact = cfg.get("kontakt") or {}
    hint = ""
    if contact.get("email"):
        hint = (f'Neznáte odpověď? Napište {html.escape(contact.get("jmeno", ""))} na '
                f'<a href="mailto:{html.escape(contact["email"])}">{html.escape(contact["email"])}</a>.')
    page = (tpl.replace("{{NAZEV}}", html.escape(cfg.get("nazev", "Rodokmen")))
               .replace("{{UVOD}}", html.escape(login.get("uvod", "Tenhle web je jen pro rodinu a příbuzné.")))
               .replace("{{OTAZKA}}", html.escape(login.get("otazka", "Odpověď na rodinnou otázku")))
               .replace("{{NAPOVEDA}}", hint))
    write(os.path.join(WEB, "public", "prihlaseni.html"), page)

    edge = os.path.join(WEB, "netlify", "edge-functions", "brana.js")
    if pristupy:
        sablony = [os.path.join(WEB, "netlify", "brana.pristupy.sablona.js"), os.path.join(WEB, "nginx.pristupy.sablona.conf")]
        if not all(os.path.exists(x) for x in sablony):
            sys.exit("CHYBA: web/ nemá šablony brány pro přístupy. Aktualizujte projekt: python3 -I <skill>/tools/novy_projekt.py <složka projektu>")
        otisky = {hashlib.sha256(("rodokmen:" + norm_answer(p["odpoved"])).encode()).hexdigest(): p["id"] for p in pristupy}
        poznamky_files({h: dict(id=p["id"], poznamky=p["poznamky"]) for h, p in
                        zip(otisky, pristupy)})
        write(edge, open(sablony[0], encoding="utf-8").read().replace("{{PRISTUPY}}", json.dumps(otisky, indent=2)))
        mapa = "\n".join(f'  "{h}" "{i}";' for h, i in otisky.items())
        write(os.path.join(WEB, "nginx.conf"), open(sablony[1], encoding="utf-8").read().replace("{{PRISTUPY}}", mapa))
        return True
    if answer:
        digest = hashlib.sha256(("rodokmen:" + answer).encode()).hexdigest()
        poznamky_files({digest: dict(id="vse", poznamky=bool(cfg.get("poznamky")))})
        nginx_map = f'  "{digest}" 1;'
        write(edge, open(os.path.join(WEB, "netlify", "brana.sablona.js"), encoding="utf-8").read().replace("{{HASH}}", digest))
    else:   # bez přihlášení – web je otevřený
        poznamky_files({})   # poznámky jen pro přihlášené
        nginx_map = "  default 1;"
        if os.path.exists(edge):
            os.remove(edge)
    nginx = open(os.path.join(WEB, "nginx.sablona.conf"), encoding="utf-8").read()
    if not answer:   # šablona už má „default 0;“ – druhý default nginx odmítne
        nginx = nginx.replace("  default 0;\n", "")
    nginx = nginx.replace("{{ODPOVED}}", nginx_map)
    write(os.path.join(WEB, "nginx.conf"), nginx)
    return bool(answer)


def main():
    ns = load_people()
    if 1 not in ns["P"]:
        sys.exit("V data/osoby.py chybí výchozí osoba (číslo 1).")
    cfg = cfg_puvodni = jload("web.json", {})
    # Přístupy (web.json → pristupy, tools/pohled.py): --seznam-pristupu vypíše jejich id pro scripts/build.mjs,
    # --pristup <id> exportuje web jen pro ten přístup – od jeho výchozí osoby, jen jeho větve.
    pristupy = nacti_pristupy(cfg)
    if "--seznam-pristupu" in sys.argv:
        print(json.dumps([p["id"] for p in pristupy or []]))
        return
    pristup, prevod = None, None
    if "--pristup" in sys.argv:
        pid = (sys.argv[sys.argv.index("--pristup") + 1:] or [""])[0]
        pristup = next((p for p in pristupy or [] if p["id"] == pid), None)
        if not pristup:
            sys.exit(f"CHYBA: přístup „{pid}“ není ve web.json → pristupy (jsou: {', '.join(p['id'] for p in pristupy or []) or 'žádné'}).")
    texty = not pristup or pristup["texty"]   # příběh, zajímavosti, deník, „Co hledáme“ (píšou o celé rodině)
    puvodni_same = ns["SAME"]
    if pristup and pristup["koren"]:
        ns, prevod = pohled(ns, pristup["koren"], texty, pristup.get("rody"))
        cfg = dict(cfg, nazev=pristup.get("nazev_webu", cfg.get("nazev")))
        if "uvod" in pristup:
            cfg["uvod"] = pristup["uvod"]
        elif not texty:
            cfg.pop("uvod", None)
        if not texty:
            cfg.pop("zajimavosti_na_uvodu", None)
    P, LINES, SIDE, ISSUES = ns["P"], ns["LINES"], ns["SIDE"], ns["ISSUES"]
    SAME = ns["SAME"]                       # alias Kekulé → kanonické Kekulé (předek v rodokmenu vícekrát)
    # web.json "puvodni_jmena": true → jméno osoby v původních tvarech ze zápisů (pole zap v osoby.py, „Nowakin / Nováková“);
    # jinak dnešní podoba n. Adresa stránky (slug) je vždy podle n.
    puvodni = lambda p: " / ".join(p["zap"]) if cfg.get("puvodni_jmena") and p.get("zap") else p["n"]
    login = cfg.get("prihlaseni") or {}
    if "--nasazeni" in sys.argv and not pristupy and not norm_answer(login.get("odpoved", "")) and not login.get("otevreny"):
        sys.exit("CHYBA: v data/web.json není odpověď na přihlašovací otázku – web by byl otevřený komukoli.\n"
                 "Nastavte prihlaseni.odpoved, nebo (jen když to opravdu chcete) prihlaseni.otevreny: true.")
    docs_cfg = jload("dokumenty.json", [])
    recs = {r["key"]: r for r in record_rows()}
    if prevod is not None:   # jen zápisy a dokumenty viditelných osob
        recs = {k: v for k, v in recs.items() if k in ns["_zapisy"]}
        docs_cfg = [dict(d, osoby=[prevod[o] for o in (puvodni_same.get(x, x) if isinstance(x, int) else x
                                                       for x in d.get("osoby", [])) if o in prevod]) for d in docs_cfg]
        docs_cfg = [d for d in docs_cfg if d["osoby"]]

    slugs, used = {}, set()
    for k in sorted(P):
        p = P[k]
        if placeholder(p) or k in SAME:
            continue
        yv = (p.get("y") or "").strip()
        ys = [] if yv.startswith(("?", "†")) else re.findall(r"\d{4}", yv)   # rok úmrtí do adresy nedávat
        s = slugify(p["n"] + (" " + ys[0] if ys else ""))
        if s in used or not s:
            s = f"{s}-{k}"
        used.add(s)
        slugs[k] = s
    for a, c in SAME.items():
        slugs[a] = slugs[c]
    aliases_of = {}
    for a, c in SAME.items():
        aliases_of.setdefault(c, []).append(a)

    def line_of(k):
        g = gen(k)
        return k >> (g - 3) if g >= 3 else None

    people = {}
    for k, p in sorted(P.items()):
        if k not in slugs or k in SAME:
            continue
        path, c = [], k
        while c >= 1:
            path.append(slugs.get(c))
            c //= 2
        people[slugs[k]] = dict(
            k=k, slug=slugs[k], name=puvodni(p), modern=p["n"], zap=p.get("zap", []), y=p.get("y", ""), years=years(p.get("y")), st=p.get("st", "unk"),
            status=STATUS.get(p.get("st"), ""), gen=gen(k), sex="M" if k == 1 and p.get("sex", "M") == "M" or k > 1 and k % 2 == 0 else "F",
            rel=relation(k), line=line_of(k), facts=p.get("f", []), note=p.get("note", ""), vyz=p.get("vyz", ""), records=[r for r in p.get("r", []) if r in recs],
            father=slugs.get(2 * k), mother=slugs.get(2 * k + 1),
            fatherUnknown=(2 * k in P and placeholder(P[2 * k])), motherUnknown=(2 * k + 1 in P and placeholder(P[2 * k + 1])),
            child=slugs.get(k // 2) if k > 1 else None, spouse=slugs.get(k ^ 1) if k > 1 else None,
            family=None, ownFamily=None, path=path,
            side=[dict(name=s["n"], text=s["t"], records=[r for r in s.get("r", []) if r in recs], rel=s.get("v") or "příbuzný",
                       years=years(s.get("y")), kind=SIDE_KIND.get((s.get("v") or "").lower(), "other")) for s in SIDE if s["k"] == k],
            sibStatus=SIB_STATUS.get(p.get("sour"), "none"),
            docs=[dict(img=d["img"], caption=d["popis"]) for d in docs_cfg if k in d.get("osoby", [])],
            children=[slugs[c] for c in [k // 2] + [a // 2 for a in aliases_of.get(k, [])] if k > 1 and c in slugs],
            also=[dict(k=a, rel=relation(a), line=line_of(a), child=slugs.get(a // 2)) for a in aliases_of.get(k, [])],
        )
        if aliases_of.get(k):
            for a in aliases_of[k]:
                people[slugs[k]]["records"] = list(dict.fromkeys(people[slugs[k]]["records"] + [r for r in P[a].get("r", []) if r in recs]))
            people[slugs[k]]["facts"] = [f for f in people[slugs[k]]["facts"] if not f.startswith("TÁŽ OSOBA")]

    # Soukromí: žijící (a narození v posledních 100 letech bez známého úmrtí) jen jménem, rokem narození a vazbami –
    # bez míst, dat, poznámek a zápisů. Na mapu, do Domů ani do Statistik se tak nedostanou (počítají se z faktů).
    def skryj(p):
        p["facts"], p["records"], p["note"] = [], [], ZIJICI_POZN
        p["vyz"] = ""
    skryto = 0
    for k, p in P.items():
        if k in slugs and k not in SAME and zijici(p.get("y"), p.get("note"), p.get("f", [])):
            skryj(people[slugs[k]])
            skryto += 1

    def fakta(k):   # fakta a zápisy osoby už po skrytí žijících (pro stránky rodin)
        return people[slugs[k]] if k in slugs and slugs[k] in people else {"facts": [], "records": []}

    # RODINA: osoby mimo přímou linii pro stromový graf. Odkazy: "k12" = přímý předek, "o:zkratka" = osoba z RODINA,
    # "?12" = neznámý předek na místě 12 (sourozenci se tak poznají i bez známých rodičů).
    R = ns["RODINA"]
    rslug = {}   # klíč z RODINA → adresa stránky osoby: jméno a první rok z y – u příbuzných bývá jen úmrtí
    for oid, o in R.items():   # (zemřelé dítě „† 1879“), rok je pak jediné, co stejnojmenné odliší
        yv = (o.get("y") or "").strip()
        ys = [] if yv.startswith("?") else re.findall(r"\d{4}", yv)
        s = slugify(o["n"] + (" " + ys[0] if ys else ""))
        if s in used or not s:
            s = f"{s}-{slugify(oid)}"
        used.add(s)
        rslug[oid] = s

    def ref(v):
        if isinstance(v, int):
            v = SAME.get(v, v)
            return f"k{v}" if v in slugs else f"?{v}"
        return f"o:{v}" if isinstance(v, str) and v in R else None

    others = []
    for oid, o in R.items():
        others.append(dict(id=f"o:{oid}", name=o["n"], y=o.get("y", ""), years=years(o.get("y")), sex=o.get("sex", ""),
                           st=o.get("st", ""), status=STATUS.get(o.get("st"), ""), father=ref(o.get("otec")),
                           mother=ref(o.get("matka")), partners=[x for x in map(ref, o.get("partner", [])) if x],
                           facts=o.get("f", []), note=o.get("note", ""), records=[r for r in o.get("r", []) if r in recs]))
        if zijici(o.get("y"), o.get("note"), o.get("f", [])):
            others[-1].update(facts=[], records=[], note=ZIJICI_POZN)
            skryto += 1
    # na stránce osoby a rodiny je ukázat jako příbuzné (dřív byli jen v SIDE)
    for pp in people.values():
        me, k = f"k{pp['k']}", pp["k"]
        birth = (ref(2 * k), ref(2 * k + 1))
        for o in others:
            if (o["father"], o["mother"]) == birth:
                rel = "bratr" if o["sex"] == "M" else "sestra"
            elif o["father"] == me or o["mother"] == me:
                rel = "syn" if o["sex"] == "M" else "dcera"
            elif me in o["partners"] or any(me in (c["father"], c["mother"]) and o["id"] in (c["father"], c["mother"]) for c in others):
                rel = "manžel" if o["sex"] == "M" else "manželka"
            elif birth[0] in (o["father"], o["mother"]) and not birth[0].startswith("?") or                     birth[1] in (o["father"], o["mother"]) and not birth[1].startswith("?"):
                rel = "nevlastní bratr" if o["sex"] == "M" else "nevlastní sestra"
            else:
                continue
            pp["side"].append(dict(name=o["name"], text=o["note"] or "; ".join(o["facts"]), records=o["records"], rel=rel,
                                   years=o["years"], kind=SIDE_KIND.get(rel, "other"), id=o["id"], slug=rslug[o["id"][2:]]))
            if not o.get("rel"):
                o["rel"] = f"{rel} osoby {pp['name']}"

    # RODINA dostane vlastní stránky (k=0, extra=True); děti, sourozenci a partneři se pak počítají u KAŽDÉ osoby
    # stejně – z toho, kdo je čí otec a matka. Neznámý předek na místě n je „?n“, aby se sourozenci poznali i bez něj.
    def pkey(v):
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, int):
            v = SAME.get(v, v)
            return slugs[v] if slugs.get(v) in people else f"?{v}"
        return rslug.get(v)

    for o in others:
        oid = o["id"][2:]
        s, src = rslug[oid], R[oid]
        o["slug"] = s
        people[s] = dict(
            k=0, slug=s, name=o["name"], modern=o["name"], zap=[], y=o["y"], years=o["years"], st=src.get("st", "fam"),
            status=o["status"], gen=0, sex=o["sex"], rel=src.get("v") or src.get("rel") or o.get("rel") or "příbuzný mimo přímou linii", line=None,
            facts=o["facts"], note=o["note"], vyz="", records=o["records"], father=None, mother=None,
            fatherUnknown=False, motherUnknown=False, child=None, spouse=None, family=None, ownFamily=None, path=[s],
            side=[], sibStatus="none", docs=[dict(img=d["img"], caption=d["popis"]) for d in docs_cfg if oid in d.get("osoby", [])],
            children=[], also=[], extra=True)
    rodice = {}   # slug → (klíč otce, klíč matky); klíč = slug nebo „?n“
    for k, p in P.items():
        if k in slugs and k not in SAME and slugs[k] in people:
            rodice[slugs[k]] = (pkey(2 * k), pkey(2 * k + 1))
    for oid, o in R.items():
        rodice[rslug[oid]] = (pkey(o.get("otec")), pkey(o.get("matka")))
    for s, (f_, m_) in rodice.items():
        if people[s].get("extra"):
            people[s]["father"] = f_ if f_ in people else None
            people[s]["mother"] = m_ if m_ in people else None
    for s, p in people.items():   # rodiče podle odkazů (ne podle čísla) – graf předků i u osob z RODINA
        p["parents"] = [x if x in people else None for x in rodice.get(s, (None, None))]
    by_parent = {}
    for s, par in rodice.items():
        for x in par:
            if x:
                by_parent.setdefault(x, []).append(s)

    def ykey(s):
        m_ = re.findall(r"\d{4}", people[s].get("y") or "")
        return (int(m_[0]) if m_ else 9999, people[s]["name"])

    for s, p in people.items():
        par = rodice.get(s, (None, None))
        p["kids"] = [dict(slug=c, other=next((x for x in rodice[c] if x != s and x in people), None), line=people[c]["k"] > 0)
                     for c in sorted(set(by_parent.get(s, [])), key=ykey)]
        sib = {c for x in par if x for c in by_parent.get(x, [])} - {s}
        p["siblings"] = [dict(slug=c, half=bool(all(par) and all(rodice[c]) and rodice[c] != par)) for c in sorted(sib, key=ykey)]
        p["partners"] = []

    def partneri(a, b, text=""):
        if not (a in people and b in people) or a == b:
            return
        if any(people[x]["note"] == ZIJICI_POZN for x in (a, b)):
            text = ""   # u žijících ani rok a místo sňatku
        for x, y_ in ((a, b), (b, a)):
            hit = next((z for z in people[x]["partners"] if z["slug"] == y_), None)
            if hit is None:
                people[x]["partners"].append(dict(slug=y_, text=text))
            elif text and not hit["text"]:
                hit["text"] = text
    for pr in ns["PARTNERI"]:   # dict(a=<číslo předka nebo klíč z RODINA>, b=…, rok=…, misto="…", konec="rozvod 1950")
        partneri(pkey(pr.get("a")), pkey(pr.get("b")), ", ".join(x for x in (
            f"sňatek {pr['rok']}" if pr.get("rok") else "", pr.get("misto", ""), pr.get("konec", "")) if x))
    for oid, o in R.items():
        for v in o.get("partner", []):
            partneri(rslug[oid], pkey(v))
    for s, (f_, m_) in rodice.items():   # společné dítě = partneři
        partneri(f_, m_)
    # vztah u vzdálenějších příbuzných: přes partnera, rodiče nebo dítě, který už vztah má („manžel osoby Marie Nováková“)
    VYCHOZI_REL = "příbuzný mimo přímou linii"
    for _ in range(3):
        for p in people.values():
            if not p.get("extra") or p["rel"] != VYCHOZI_REL:
                continue
            zena = p["sex"] == "F"
            kdo = next(((("manželka" if zena else "manžel"), x["slug"]) for x in p["partners"] if people[x["slug"]]["rel"] != VYCHOZI_REL), None)                 or next(((("dcera" if zena else "syn"), x) for x in (p["father"], p["mother"]) if x and people[x]["rel"] != VYCHOZI_REL), None)                 or next(((("matka" if zena else "otec"), c["slug"]) for c in p["kids"] if people[c["slug"]]["rel"] != VYCHOZI_REL), None)
            if kdo:
                p["rel"] = f"{kdo[0]} osoby {people[kdo[1]]['name']}"
    for p in people.values():   # příbuzní z RODINA mají vlastní stránku a jsou v Dětech / Sourozencích / Manželství
        p["side"] = [e for e in p["side"] if not e.get("slug")]
        p["tree"] = f"k{p['k']}" if not p.get("extra") else next(o["id"] for o in others if o["slug"] == p["slug"])
    # Další děti předka zapsané jen v SIDE (děti z RODINA už jsou v p["kids"]): u předka jako syn/dcera,
    # u jeho dítěte v linii jako bratr/sestra. Nevlastní sourozence vynechá – nevíme, po kterém rodiči jsou.
    for p in people.values():
        p["sideKids"] = []
        if p.get("extra"):
            continue
        for owner, kind in [(p["slug"], "child")] + [(c, "sib") for c in p["children"]]:
            for i, e in enumerate(people[owner]["side"]):
                if e["kind"] == kind and not any(x["name"] == e["name"] for x in p["sideKids"]):
                    p["sideKids"].append(dict(name=e["name"], years=e["years"], slug=owner, anchor=f"pribuzny-{i}"))

    families = {}
    for k in sorted(P):
        f, m = 2 * k, 2 * k + 1
        if k not in slugs or k in SAME or (f not in slugs and m not in slugs):
            continue
        fs, ms = slugs.get(f), slugs.get(m)
        fid = "-a-".join(x for x in (fs, ms) if x) if fs and ms else (fs or ms) + "-rodina"
        surname = (P[m]["n"].split()[-1] if m in P else "").strip("()?")
        mfacts = [x for x in fakta(f)["facts"] + fakta(m)["facts"] if x.startswith("×")]
        marriage = [x for x in mfacts if surname and surname[:5] in x] or mfacts
        frec = fakta(f)["records"] + fakta(m)["records"]
        child_rec = [r for r in fakta(k)["records"] if r in recs and recs[r]["kind"] == "N"]
        rlist = [r for r in dict.fromkeys(frec) if r in recs and recs[r]["kind"] == "O"] + child_rec
        if fid in families:   # stejný pár potkán dvakrát (předek v rodokmenu vícekrát) – jedna rodina, víc dětí
            fam = families[fid]
            fam["children"].append(slugs[k])
            fam["records"] = list(dict.fromkeys(fam["records"] + rlist))
            fam["side"] += people[slugs[k]]["side"]
        else:
            families[fid] = dict(id=fid, father=fs, mother=ms, fatherUnknown=f in P and placeholder(P[f]),
                                 child=slugs[k], children=[slugs[k]], marriage=marriage, records=rlist,
                                 line=line_of(f) if f in P else line_of(m), gen=gen(f), side=list(people[slugs[k]]["side"]))
        people[slugs[k]]["family"] = fid
        for x in (fs, ms):
            if x:
                people[x]["ownFamily"] = fid
    for fam in families.values():   # v rodině jsou všechny děti páru, i ty z RODINA (mají vlastní stránku)
        par = rodice[fam["child"]]
        deti = [c for c in by_parent.get(par[0] or par[1], []) if rodice.get(c) == par]
        fam["children"] = sorted(set(fam["children"]) | set(deti), key=ykey)
        fam["side"] = [e for e in fam["side"] if e.get("slug") not in fam["children"]]
        for c in deti:
            if people[c].get("extra"):
                people[c]["family"] = fam["id"]

    refs = {}
    for s, p in people.items():
        for r in p["records"] + [r for e in p["side"] if not e.get("slug") for r in e["records"]]:
            refs.setdefault(r, []).append(s)
    hl = jload("zvyrazneni.json", {})
    prep = jload("prepisy.json", {})
    records = []
    for key, r in recs.items():
        r = dict(r)
        r["boxes"] = hl.get(key, {}).get("boxes", [])
        tr = prep.get(key, {})
        r["orig"], r["cs"] = tr.get("orig", ""), tr.get("cs", "")
        r["kindName"] = KINDS.get(r["kind"], r["kind"])
        r["people"] = list(dict.fromkeys(refs.get(key, [])))
        records.append(r)

    lines = {}
    for k, (name, desc) in sorted(LINES.items()):
        if k not in LINE_COLORS:
            continue
        members = [(p["k"], p) for p in people.values() if p["line"] == k]
        members += [(a["k"], p) for p in people.values() for a in p["also"] if a["line"] == k]
        members.sort(key=lambda x: x[0])
        lines[slugify(name)] = dict(k=k, slug=slugify(name), name=name, desc=desc, color=LINE_COLORS[k],
                                    root=slugs.get(k), people=[p["slug"] for _, p in members],
                                    gens={p["slug"]: gen(kk) for kk, p in members})
    lines = {s: l for s, l in lines.items() if l["root"]}
    for p in people.values():
        p["lineSlug"] = next((l["slug"] for l in lines.values() if l["k"] == p["line"]), None)

    places = []
    for name, e in jload("mista.json", {}).items():
        if "lat" not in e:
            continue
        rx = re.compile(e.get("re") or re.escape(name))
        hits = [p for p in people.values() if not p.get("extra") and rx.search(" ".join(p["facts"]))]
        byline = {}
        for p in sorted(hits, key=lambda p: p["k"]):
            byline.setdefault(p["line"] or 0, []).append(p["slug"])
        if e.get("hypoteza"):
            byline = {e.get("rod", 0): []}
        if not byline:
            continue
        yrs = [int(y) for p in hits for y in re.findall(r"\b1[4-9]\d\d\b", p["y"] or "")]
        slug = slugify(name)
        timeline = [] if e.get("hypoteza") else [
            dict(slug=p["slug"], line=p["line"] or 0, life=life(p["y"]), events=[place_event(f) for f in p["facts"] if rx.search(f)])
            for p in hits]
        for p in hits + [p for p in people.values() if p.get("extra") and rx.search(" ".join(p["facts"]))]:
            p.setdefault("places", []).append(dict(slug=slug, name=name))   # příbuzní mimo linii: jen odkaz, mapa beze změny
        places.append(dict(name=name, slug=slug, lat=e["lat"], lon=e["lon"], lines=[dict(k=k, people=v) for k, v in sorted(byline.items())],
                           years=[min(yrs), max(yrs)] if yrs else None, hypothesis=bool(e.get("hypoteza")), timeline=timeline))

    known = [p for p in people.values() if p["k"] > 1]
    stats = dict(ancestors=len(known), documented=sum(p["st"] == "doc" for p in known), records=len(records),
                 generations=max(p["gen"] for p in people.values()) + 1,
                 updated=(lambda d: f"{d.day}. {d.month}. {d.year} {d.hour}:{d.minute:02d}")(datetime.datetime.now()))
    hypotheses = [dict(line=h.get("rod"), title=h.get("nadpis", "Hypotéza"), text=h.get("text", ""),
                       items=[dict(name=a, text=b) for a, b in h.get("polozky", [])],
                       records=[r for r in h.get("zaznamy", []) if r in recs]) for h in ns["HYPOTEZY"]]

    story_dir = os.path.join(DATA, "pribehy")
    story_files = sorted(
        os.path.join(story_dir, name) for name in os.listdir(story_dir)
        if name.endswith(".md")
    ) if os.path.isdir(story_dir) else []
    stories = [story_frontmatter(path, os.path.splitext(os.path.basename(path))[0])
               for path in story_files]
    multi_stories = bool(stories)
    configured_order = cfg.get("pribehy", [])
    if not isinstance(configured_order, list) or any(not isinstance(slug, str) for slug in configured_order):
        sys.exit("CHYBA: web.json → pribehy musí být seznam slugů příběhů.")
    if multi_stories:
        slugs_in_files = [story["slug"] for story in stories]
        if len(set(slugs_in_files)) != len(slugs_in_files):
            sys.exit("CHYBA: názvy souborů příběhů se po převodu na slug opakují.")
        if configured_order:
            if len(set(configured_order)) != len(configured_order) or set(configured_order) != set(slugs_in_files):
                sys.exit("CHYBA: web.json → pribehy musí obsahovat každý slug v data/pribehy/ právě jednou.")
            by_slug = {story["slug"]: story for story in stories}
            stories = [by_slug[slug] for slug in configured_order]
    elif configured_order:
        sys.exit("CHYBA: web.json → pribehy odkazuje na příběhy, ale data/pribehy/ neobsahuje žádné Markdown soubory.")
    legacy_story = os.path.join(DATA, "pribeh.md")
    if not multi_stories and os.path.exists(legacy_story):
        legacy_text = open(legacy_story, encoding="utf-8").read()
        legacy_match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", legacy_text, re.S)
        legacy_fields = {}
        if legacy_match:
            for line in legacy_match.group(1).splitlines():
                item = re.fullmatch(r"(title|lead):\s*(.*?)\s*", line)
                if item:
                    legacy_fields[item.group(1)] = item.group(2)
        stories = [dict(slug="", title=legacy_fields.get("title", "Příběh"),
                        lead=legacy_fields.get("lead", ""), rod=cfg.get("pribeh", {}).get("rod"),
                        text=legacy_text)]
    if not texty:
        stories, multi_stories = [], False
    has_story = bool(stories)
    public_cfg = {k: v for k, v in cfg.items() if k not in ("prihlaseni", "pristupy")}   # odpovědi nikdy na web
    # poznámky ke stránkám (tlačítko „Připomínka“, /poznamky/): podle přístupu, jinak web.json „poznamky“
    vse = next((p for p in pristupy or [] if p["id"] == "vse"), None)
    public_cfg["poznamky"] = bool(pristup["poznamky"] if pristup else vse["poznamky"] if vse else cfg.get("poznamky"))
    public_cfg["maPribeh"] = has_story
    public_cfg["maVicePribehu"] = multi_stories
    public_cfg["pribehy"] = [story["slug"] for story in stories] if multi_stories else []
    # Vějíře pro web: hlavní (výchozí osoba, /vejir/) a vějíř předků každé další osoby, která má aspoň jednoho známého
    # rodiče (/vejir/<adresa osoby>/). fan_hrefs.json: číslo předka nebo zkratka z RODINA → stránka osoby.
    gen_dir = os.path.join(WEB, "src", "generated")
    os.makedirs(gen_dir, exist_ok=True)
    hrefs = os.path.join(gen_dir, "fan_hrefs.json")
    with open(hrefs, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({**{str(k): f"/osoba/{s}/" for k, s in slugs.items()}, **{oid: f"/osoba/{s}/" for oid, s in rslug.items()}}, fh)
    for old in glob.glob(os.path.join(gen_dir, "fan_*.svg")):
        os.remove(old)
    for p in people.values():
        p["fan"] = None
    people[slugs[1]]["fan"] = "/vejir/"
    ukoly = [(os.path.join(gen_dir, "fan.svg"), None)]
    for k in sorted(P):
        if k > 1 and k in slugs and k not in SAME and slugs[k] in people and (2 * k in slugs or 2 * k + 1 in slugs):
            ukoly.append((os.path.join(gen_dir, f"fan_{slugs[k]}.svg"), k))
            people[slugs[k]]["fan"] = f"/vejir/{slugs[k]}/"
    for oid, o in R.items():
        if any(pkey(o.get(x)) in people for x in ("otec", "matka")):
            ukoly.append((os.path.join(gen_dir, f"fan_{rslug[oid]}.svg"), oid))
            people[rslug[oid]]["fan"] = f"/vejir/{rslug[oid]}/"
    env = None
    if prevod is not None:   # fan_chart.py čte osoby ze souboru – pro přístup jen jeho pohled
        fd, osoby_pohled = tempfile.mkstemp(prefix="rodokmen_pohled_", suffix=".py")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(f"{x} = {ns[x]!r}" for x in ("P", "RODINA", "LINES", "SAME")) + "\n")
        env = dict(os.environ, RODOKMEN_OSOBY=osoby_pohled)

    def vejir(ukol):
        out, koren = ukol
        subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(TOOLS, "fan_chart.py"), out, "--web", hrefs]
                       + (["--root", str(koren)] if koren is not None else []), check=True, capture_output=True, env=env)
    try:
        with cf.ThreadPoolExecutor(min(8, os.cpu_count() or 2)) as ex:   # každý vějíř je samostatný proces
            list(ex.map(vejir, ukoly))
    finally:
        if env:
            os.remove(env["RODOKMEN_OSOBY"])
    shutil.copyfile(os.path.join(gen_dir, "fan.svg"), os.path.join(gen_dir, f"fan_{slugs[1]}.svg"))   # i /vejir/<výchozí osoba>/

    site = dict(config=public_cfg, places=places, root=slugs[1], aliases={a: slugs[a] for a in SAME}, people=people,
                families=families, others=others, records=records, lines=lines,
                issues=[dict(title=i, text="") if isinstance(i, str) else dict(title=i[0], text=i[1]) for i in ISSUES], stats=stats, hypotheses=hypotheses,
                docs=[dict(img=d["img"], caption=d["popis"], people=[slugs.get(k) or rslug[k] for k in d.get("osoby", []) if k in slugs or k in rslug])
                      for d in docs_cfg if os.path.exists(os.path.join(VYREZY, d["img"] + ".jpg"))],
                timeline=timeline_data(P, SAME, slugs, people, line_of))

    write(os.path.join(WEB, "src", "data", "site.json"), json.dumps(site, ensure_ascii=False, indent=1))
    for src, dst in (("archivni_dotazy.md", "dotazy.md"), ("research_log.md", "denik.md"), ("zajimavosti.md", "zajimavosti.md")):
        path = os.path.join(DATA, src)
        text = open(path, encoding="utf-8").read() if os.path.exists(path) and texty else ""
        write(os.path.join(gen_dir, dst), strip_comments(re.sub(r"^# .*\n", "", text, count=1)))
    shutil.rmtree(os.path.join(gen_dir, "pribehy"), ignore_errors=True)
    if multi_stories:
        for story in stories:
            write(os.path.join(gen_dir, "pribehy", story["slug"] + ".md"), strip_comments(story["text"]))
    write(os.path.join(gen_dir, "pribehy.json"), json.dumps(
        [{key: story[key] for key in ("slug", "title", "lead", "rod")} for story in stories if story["slug"]],
        ensure_ascii=False, indent=1))
    story = stories[0]["text"] if stories else "---\ntitle: Příběh\nlead: ''\n---\n"
    write(os.path.join(gen_dir, "pribeh.md"), strip_comments(story))

    gated = login_files(cfg_puvodni, pristupy)

    copied = 0
    zv = os.path.join(DATA, "zvyrazneni.json")
    hl_mtime = os.path.getmtime(zv) if os.path.exists(zv) else 0
    for sub, src_dir in (("img", VYREZY), ("zdroje", ZDROJE)):
        dst_dir = os.path.join(WEB, "public", sub)
        if pristup:   # web pro jeden přístup: jen jeho obrázky (ze sestavení jiného přístupu nic nezůstane)
            shutil.rmtree(dst_dir, ignore_errors=True)
        os.makedirs(dst_dir, exist_ok=True)
        for key in list(recs) + [d["img"] for d in docs_cfg] + ([cfg["uvod"]["foto"]] if cfg.get("uvod", {}).get("foto") else []):
            src = os.path.join(src_dir, key + ".jpg")
            dst = os.path.join(dst_dir, key + ".jpg")
            if not os.path.exists(src):
                continue
            boxes = hl.get(key, {}).get("boxes", [])
            stale = not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst) \
                or (sub == "zdroje" and boxes and hl_mtime > os.path.getmtime(dst))
            if not stale:
                continue
            if sub == "zdroje" and boxes and draw_boxes(src, dst, boxes, os.path.join(VYREZY, key + ".jpg")):
                copied += 1
                continue
            shutil.copy2(src, dst)
            copied += 1
    if pristup:
        print(f"přístup {pristup['id']} ({pristup['nazev']}): " + (f"výchozí osoba {people[slugs[1]]['name']}" if prevod is not None else "vše"))
    print(f"{len(people)} osob, {len(families)} rodin, {len(records)} zápisů, {len(lines)} rodů, {len(places)} míst; "
          f"zkopírováno {copied} obrázků; přihlášení {'zapnuté' if gated else 'VYPNUTÉ (web je otevřený)'}")
    if skryto:
        print(f"soukromí: {skryto} žijících (nebo narozených od {HRANICE_ZIJICI} bez známého úmrtí) jen se jménem a rokem narození")

    # odkazy v textech, které nikam nevedou (adresa osoby se změní třeba doplněním roku narození: jan-novak → jan-novak-1798)
    targets = dict(osoba=people, zdroj=recs, rod=lines, rodina=families)
    texts = {f: open(os.path.join(gen_dir, f), encoding="utf-8").read() for f in ("pribeh.md", "zajimavosti.md")}
    if multi_stories:
        texts.update({f"pribehy/{story['slug']}.md": story["text"] for story in stories})
    texts["web.json"] = json.dumps(cfg, ensure_ascii=False)
    texts["osoby.py (hypotézy)"] = json.dumps(hypotheses, ensure_ascii=False)
    targets["pribehy"] = {story["slug"] for story in stories if story["slug"]}
    broken = [(f, m.group(0)) for f, t in texts.items()
              for m in re.finditer(r"/(osoba|zdroj|rod|rodina|pribehy)/([^/\s)\"'#?<>\]]+)", t)
              if m.group(2) not in targets[m.group(1)]]
    for f, link in dict.fromkeys(broken):
        print(f"POZOR: nefunkční odkaz {link}/ v {f} – oprav ho (adresy stránek jsou ve web/src/data/site.json)")

    # stránky Statistiky a Domy se počítají z hotového site.json
    sys.path.insert(0, TOOLS)
    import statistiky, domy_export, stavby
    statistiky.main()
    domy_export.main()
    upoz, n_staveb = stavby.export()   # data/stavby.py → web/src/data/stavby.json (u Domů: držitelé, obyvatelé, události)
    stavby.tisk_upozorneni(upoz)
    if n_staveb:
        print(f"stavby: {n_staveb} staveb s dějinami na stránce Domy")


if __name__ == "__main__":
    main()
