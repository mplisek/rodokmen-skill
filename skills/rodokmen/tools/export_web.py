#!/usr/bin/env python3
"""Export dat rodokmenu (data/*) do webu ve složce web/.

Čte data/osoby.py, data/zaznamy.json, data/svazky.json, data/prepisy.json, data/zvyrazneni.json,
data/mista.json, data/web.json, data/dokumenty.json, data/pozvanky.json a markdownové poznámky. Zapisuje
web/src/data/site.json, web/src/generated/*, web/public/{img,zdroje}, web/public/prihlaseni.html,
web/nginx.conf a web/netlify/edge-functions/brana.js.

Spouští se z web/ příkazem `npm run data` (nebo přímo `python3 -I tools/export_web.py`, na Windows `python -I -X utf8 …`).
"""
import datetime, glob, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, unicodedata
import concurrent.futures as cf
if __name__ == "__main__" and sys.argv[1:2] in (["-h"], ["--help"]):   # nápověda místo pádu (ne při importu z kontrola.py)
    sys.exit(__doc__.strip())
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
# Obrázky pro web se při exportu zmenší a překódují (méně přenesených dat – na Netlify se platí za GB). Upravené verze
# se ukládají do pracovni/.web_obrazky/, aby je další export (i každý přístup zvlášť) nemusel kódovat znovu.
WEB_OBRAZKY = os.path.join(ROOT, "pracovni", ".web_obrazky")
UPRAVA_OBRAZKU = "1: img max 1400 px (s plným rozlišením) q80, zdroje q82, progresivní JPEG bez metadat"   # změna = vše znovu
JPEG_WEB = ["+profile", "!icc,*", "+set", "comment", "-interlace", "JPEG", "-sampling-factor", "4:2:0"]

LINE_COLORS = {8: "#EFB45F", 9: "#F09A78", 10: "#E58AA6", 11: "#B99AE0",
               12: "#86B8E8", 13: "#6FCBB9", 14: "#9CD17A", 15: "#D3D46A"}
STATUS = {"doc": "doloženo matrikou", "prob": "pravděpodobné", "fam": "údaj od rodiny",
          "mh": "jen z cizího rodokmenu", "unk": "neznámé"}
SIDE_KIND = {"bratr": "sib", "sestra": "sib", "manžel": "spouse", "manželka": "spouse", "syn": "child", "dcera": "child"}
SIB_STATUS = {"hotovo": "done", "částečně": "partial"}
KINDS = {"N": "křest / narození", "O": "sňatek", "Z": "úmrtí", "B": "biřmování", "S": "soupis obyvatel", "J": "jiný pramen"}


def druh_zapisu(z):
    """(druh události, jen rejstřík?) – rejstřík není druh, ale forma: položka rejstříku křtů je křest jen bez
    podrobností. Starší data mají druh „I“: událost se pozná z klíče nebo názvu (křtů/narozených, oddaných, zemřelých)."""
    druh, index = z.get("druh", "J"), bool(z.get("rejstrik"))
    if druh == "I":
        index, t = True, (z.get("klic", "") + " " + z.get("nazev", "")).lower()
        druh = ("Z" if re.search(r"zem[řr]|[úu]mrt|umrti|poh[řr]", t) else "O" if re.search(r"odda|s[ňn]at|snatek", t)
                else "N" if re.search(r"k[řr]t|naroz|krest", t) else "J")   # úmrtí dřív: „mrtvě narozené dítě“
    return (druh if druh in KINDS else "J"), index


def jload(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_people():
    ns = {}
    exec(open(os.path.join(DATA, "osoby.py"), encoding="utf-8-sig").read(), ns)
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
            key=key, kind=druh_zapisu(z)[0], index=druh_zapisu(z)[1], date=z.get("datum", ""), title=z.get("nazev", key),
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


def hvezdicky_narozeni(md):
    """„* 1890“ (narozen) uprostřed řádku markdown bere jako začátek kurzívy – uvnitř tučného „**Jan (* 1890):**“
    pak rozbije formát. Hvězdičku před číslem (ne na začátku řádku, ne u **) ošetří zpětným lomítkem."""
    return re.sub(r"(?m)(?<!^)(?<![*\\])\*(?!\*)(?= ?\d)", r"\\*", md)


STAVY_OTAZEK = ("otevřené", "hypotéza", "vyřešeno")


def rody_osoby(ref, R, _videno=None):
    """Rody (8–15), ke kterým osoba patří: předek k ≥ 8 svému rodu, bližší předek (1–7) rodům, které z něj vycházejí,
    osoba z RODINA rodům svých rodičů (bez rodičů rodům partnera). Podle toho se rodinné dokumenty ukážou u příběhu rodu."""
    if isinstance(ref, bool) or ref is None:
        return set()
    if isinstance(ref, int):
        g = gen(ref)
        return {ref >> (g - 3)} if g >= 3 else {r for r in range(8, 16) if r >> (3 - g) == ref}
    videno = _videno if _videno is not None else set()
    if ref in videno or ref not in R:
        return set()
    videno.add(ref)
    o = R[ref]
    out = set().union(*(rody_osoby(o.get(x), R, videno) for x in ("otec", "matka")))
    return out or set().union(set(), *(rody_osoby(p, R, videno) for p in o.get("partner", [])))


def stranky_s_daty(site, generovane, texty):
    """Které stránky mají v této verzi webu data (menu ukáže jen je): stránka → True/False."""
    lide = site["people"].values()
    predci = [p for p in lide if not p.get("extra") and p["k"] > 1]
    domy_path = os.path.join(WEB, "src", "data", "domy.json")
    try:
        domy = bool(json.load(open(domy_path, encoding="utf-8")).get("domy")) if os.path.exists(domy_path) else False
    except ValueError:
        domy = False
    return dict(
        pribeh=bool(site["config"].get("maPribeh")), zajimavosti=generovane.get("zajimavosti.md", False),
        statistiky=bool(predci), osobnosti=bool(predci), rody=bool(site["lines"]), mapa=bool(site["places"]),
        domy=domy, vejir=bool(predci), osa=bool(site.get("timeline")), strom=len(site["people"]) > 1, predci=bool(predci),
        zapisy=bool(site["records"]), dokumenty=bool(site["docs"]),
        hledame=bool([i for i in site["issues"] if i.get("stav") != "vyřešeno"]) or generovane.get("otazky.md", False)
        or generovane.get("dotazy.md", False),
        poznamky=bool(site["config"].get("poznamky")))


def text_pro_misto(text):
    """Údaj osoby bez poznámek, podle kterých by se osoba přiřadila k obci, kde nežila: text v závorkách
    („(kniha narozených Libice 727)“, „(Libice nad Doubravou)“, „(rok potvrzuje náhrobek v Libici)“) a okres
    („okres Kutná Hora“, „okr. Havlíčkův Brod“); u sňatku původ partnera, u „rodiče …“ celý údaj."""
    for _ in range(2):   # i vnořené závorky
        text = re.sub(r"\([^()]*\)", " ", text)
    if text.lstrip().startswith("×"):   # sňatek: místo svatby ano, původ partnera („× Marie Tesařová z Chlumu“) ne
        text = re.sub(r"\s(?:z|ze)\s.*$", " ", text)
    if re.match(r"\s*rodiče\b", text):   # „rodiče podle schématu: … ze Stružince“ – obec rodičů, ne osoby
        return ""
    return re.sub(r"\b(?:okres|okr\.|okresu|okresní)\s+\w+(?:\s+(?:Brod|Hora|Mýto|Králové|Labem|Boleslav|Kostelec|Město|Ves))?", " ", text)


def issue_rows(issues, slug_of, rod_of):
    """ISSUES pro stránku „Co hledáme“. Položka je dict(k=<číslo předka nebo zkratka z RODINA>, otazka="…",
    stav="otevřené|hypotéza|vyřešeno", text="…"), nebo starší dvojice (otázka, „Otevřené: …“ / „Hypotéza: …“ /
    „Vyřešeno: …“). slug_of(k) → stránka osoby, rod_of(k) → slug rodu (nebo None)."""
    out = []
    for i in issues:
        if isinstance(i, dict):
            d = dict(i)
        elif isinstance(i, str):
            d = dict(otazka=i)
        else:
            d = dict(otazka=i[0], text=i[1] if len(i) > 1 else "")
        text, stav = (d.get("text") or "").strip(), (d.get("stav") or "").strip().lower()
        m = re.match(r"(Vyřešeno|Hypotéza|Otevřené)\s*:\s*", text, re.I)
        if m:   # stav na začátku textu (starší tvar)
            stav, text = stav or m.group(1).lower(), text[m.end():]
        k = d.get("k")
        out.append(dict(title=d.get("otazka") or "", text=text, stav=stav if stav in STAVY_OTAZEK else "otevřené",
                        person=slug_of(k) if k is not None else None, rod=rod_of(k) if k is not None else None))
    return out


def _bez_diakritiky(t):
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def rod_nadpisu(nadpis, lines):
    """Rod (dict z lines), ke kterému patří nadpis oddílu („Plíškové (Horní Vestec)“, „Culkovi“), nebo None."""
    slova = re.findall(r"\w+", _bez_diakritiky(nadpis))
    for l in sorted(lines.values(), key=lambda l: l["k"]):
        jmeno = re.findall(r"\w+", _bez_diakritiky(l["name"]))
        if jmeno and slova and slova[0][:5] == jmeno[0][:5]:   # stejný kmen příjmení: Culkové / Culkovi
            return l
    return None


def podle_rodu(md, lines):
    """Markdown s oddíly „## <rod>“: oddíly rodů seřadí podle čísla rodu (8–15), ostatní (dokumenty doma, obecné)
    nechá na začátku v původním pořadí. Úvod před prvním oddílem zůstane nahoře."""
    casti = re.split(r"(?m)^(?=## )", md)
    uvod, oddily = ("", casti) if casti[0].startswith("## ") else (casti[0], casti[1:])
    rod = lambda o: rod_nadpisu(o.splitlines()[0][3:], lines)
    ostatni = [o for o in oddily if not rod(o)]
    rody = sorted((o for o in oddily if rod(o)), key=lambda o: rod(o)["k"])
    return uvod + "".join(o if o.endswith("\n") else o + "\n" for o in ostatni + rody)


def story_frontmatter(path, slug, require_rod=True):
    """Načte omezené skalární frontmatter pro příběhy bez další Python závislosti."""
    text = open(path, encoding="utf-8-sig").read()
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
    if not match:
        sys.exit(f"CHYBA: {path}: chybí YAML frontmatter.")
    fields = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.fullmatch(r"(title|lead|rod|rody):\s*(.*?)\s*", line)
        if not item:
            sys.exit(f"CHYBA: {path}: očekávám pouze skalární pole title, lead, rod a rody.")
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
    rody = [int(x) for x in re.findall(r"\d+", fields.get("rody", ""))]   # rody: 8, 10 – zakladatelé rodů (víc rodů)
    if "rody" in fields and not rody:
        sys.exit(f"CHYBA: {path}: rody má být seznam čísel osob (zakladatelů rodů), např. „rody: 8, 10“.")
    for key in ("title", "lead"):   # rod nepovinný: příběh bez rodu = obecný text (jen s právem texty)
        if key not in fields:
            sys.exit(f"CHYBA: {path}: ve frontmatter chybí pole {key}.")
    if not fields["title"].strip():
        sys.exit(f"CHYBA: {path}: title nesmí být prázdný.")
    rod = fields.get("rod") or (str(rody[0]) if rody else None)
    if require_rod and fields.get("rod") is not None and not re.fullmatch(r"(?:[8-9]|1[0-5])", fields["rod"]):
        sys.exit(f"CHYBA: {path}: rod musí být číslo 8 až 15.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        sys.exit(f"CHYBA: {path}: název souboru musí být bezpečný slug z malých písmen, číslic a pomlček.")
    return dict(slug=slug, title=fields["title"], lead=fields["lead"],
                rod=int(rod) if require_rod and rod else None, zakladatele=rody or ([int(rod)] if require_rod and rod else []), text=text)


RODY_KOMENTAR = re.compile(r"<!--\s*rody?\s*:\s*([\d,\s]+?)\s*-->")


def zakladatele_v_textu(text):
    """Čísla zakladatelů rodů z komentáře <!-- rody: 8, 10 --> v textu."""
    return [int(x) for m in RODY_KOMENTAR.finditer(text) for x in re.findall(r"\d+", m.group(1))]


def oddily_md(md):
    """Markdown → (úvod před prvním oddílem „## “, [oddíly včetně nadpisu])."""
    casti = re.split(r"(?m)^(?=## )", md)
    return ("", casti) if casti[0].startswith("## ") else (casti[0], casti[1:])


def polozky_oddilu(telo):
    """Tělo oddílu → bloky: odrážka („- “/„* “) i s odsazeným pokračováním, jinak jednotlivé řádky."""
    bloky, prazdny = [], False
    for radek in telo.splitlines(keepends=True):
        nova = re.match(r"\s{0,3}[-*] ", radek)
        if bloky and bloky[-1][0] == "odrazka" and not nova and not radek.startswith("#") and (
                not radek.strip()                                   # prázdný řádek: odrážka může pokračovat
                or radek[:1] in (" ", "\t")                         # odsazené pokračování (i za prázdným řádkem)
                or not prazdny):                                    # líné pokračování hned pod odrážkou
            bloky[-1][1] += radek
        else:
            bloky.append(["odrazka" if nova else "radek", radek])
        prazdny = not radek.strip()
    return bloky



def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def norm_answer(text):
    """Stejná normalizace jako v prihlaseni.html: bez diakritiky, malá písmena, jen a-z0-9.
    Kdyby z odpovědi nezbylo nic (např. „***“ nebo azbuka), použije se malými písmeny bez mezer – jinak by byla prázdná."""
    t = unicodedata.normalize("NFD", str(text))   # číselná odpověď (1926) je v JSON číslo
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
    # „1889 – před 1936“ → „1889–před 1936“ (ne „1889–?“, horní odhad úmrtí se neztratí), „1849 (?)“ → „1849?“
    second = ("před " if "před" in tail else ("po " if re.search(r"\bpo\b", tail) else "") +
              ("≈" if re.search(r"(asi|≈)", tail) else "")) + ys[-1] + ("?" if "(?)" in tail else "")
    return f"{approx}{ys[0]}–{second}"


HRANICE_ZIJICI = datetime.date.today().year - 100   # stejná hranice jako u citlivých údajů v kontrola.py
ZIJICI_POZN = "Žijící – údaje jen základní."
SOUKROME_POZN = "Údaje jsou soukromé."
SOUKROMY_UDAJ = "(soukromé)"   # údaj osoby „(soukromé) …“ vidí jen ten, kdo smí soukromé údaje dané osoby


def soukromy_udaj(f):
    return isinstance(f, str) and f.lstrip().lower().startswith(SOUKROMY_UDAJ)


def bez_znacky(f):
    return f.lstrip()[len(SOUKROMY_UDAJ):].lstrip() if soukromy_udaj(f) else f


def ma_souhlas(o):
    """Souhlas žijící osoby se zveřejněním jejích údajů (zadání kap. 7): souhlas={"kdo": …, "datum": …, "rozsah": [...]}
    s datem; rozsah, je-li uvedený, musí obsahovat „udaje“."""
    sh = o.get("souhlas")
    if not isinstance(sh, dict) or not str(sh.get("datum") or "").strip() or not str(sh.get("kdo") or "").strip():
        return False
    rozsah = sh.get("rozsah")
    return rozsah is None or "udaje" in rozsah


def souhlas_doklady(o):
    """Souhlas i s doklady (rozsah vynechaný = vše)."""
    return ma_souhlas(o) and (o["souhlas"].get("rozsah") is None or "doklady" in o["souhlas"]["rozsah"])


def rc_zverejnit(d, docs, osoba, same=None):
    """Doklad s rodnými čísly (pole rc = osoby, jejichž RČ na něm je) jde na web, až je každá z nich doloženě mrtvá
    (dokument s "druh": "umrtni_list" a touto osobou) nebo má RČ v obrázku začerněné (pole zacerneno, vyrez.py --zacernit).
    osoba(ref) → záznam z osoby.py nebo None; reference v původním číslování (same = aliasy SAME)."""
    kan = lambda r: (same or {}).get(r, r) if isinstance(r, int) else r   # noqa: E731
    zacerneno = {kan(r) for r in d.get("zacerneno") or []}
    for r in map(kan, d.get("rc") or []):
        if r in zacerneno:
            continue
        o = osoba(r)
        mrtva = o is not None and not zijici(o.get("y"), o.get("note"), o.get("f", []))
        if not (mrtva and any(x.get("druh") == "umrtni_list" and r in {kan(y) for y in x.get("osoby", [])} for x in docs)):
            return False
    return True


def dokument_pro_pristup(d, pid, viditelne, same=None):
    """Doklad ve verzi webu přístupu pid: jen když ho správce přidělil (pole pristupy), nebo – bez výběru – když přístup
    vidí všechny osoby na dokladu (jinak by obrázek prozradil cizí větev). viditelne(ref) v původním číslování."""
    if "pristupy" in d:
        return pid in (d.get("pristupy") or [])
    kan = lambda r: (same or {}).get(r, r) if isinstance(r, int) else r   # noqa: E731
    return all(viditelne(kan(r)) for r in d.get("osoby", []))


def ocisti_osobu(o, smi):
    """Osoba bez údajů „(soukromé) …“, které daný přístup nesmí (smi = smí soukromé údaje této osoby); povolené bez značky."""
    f = o.get("f", [])
    if not any(soukromy_udaj(x) for x in f):
        return o
    return dict(o, f=[bez_znacky(x) for x in f if not soukromy_udaj(x) or smi])


def skryt_osobu(o, smi, spravce=False):
    """Osoba (už očištěná ocisti_osobu) jen jménem a roky: žijící bez práva / vlastní větve / souhlasu, nebo ručně
    soukrome=True a nesmí. Správce (přístup vse ve webu s přístupy) vidí vše."""
    if spravce:
        return False
    if zijici(o.get("y"), o.get("note"), o.get("f", [])):
        return not (smi and ma_souhlas(o))
    return bool(o.get("soukrome")) and not smi


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


# Na mapu jen obce, kde osoba sama žila. Údaje zmiňují i cizí obce: faru („fara Prčice“), okres, přívlastek
# („Chlum u Hořic“), rodnou obec matky („roz. Nováková z Bašnic“, „a Juliany z Hovězí“, „a Rosiny, dcery sedláka
# z Hovězí“) a u muže obec nevěsty („× 1758 Hořice Kateřina z Bašnic“). U ženy obec muže zůstává – po svatbě
# obvykle žila u něj. Nejisté jméno „(?)“ vzor nepřeruší („a Marie Josífkové (?) z Humpolce“).
MISTO_CIZI = re.compile(r"(?:\bu|\bfara|\bokres|\boddíl|\bsňatků|\brodu z)\s+$")
_Q = r"(?:\s*\(\?\))?"
RODINA = re.compile(r"\b(?:roz\.|rozen[áéý]|rodem)\s+[^,;()]*(?:\(\?\)[^,;()]*)?"
                    rf"|\ba\s+[A-ZČŘŠŽÚ]\w+(?:\s+[A-ZČŘŠŽÚ]\w+)?{_Q}(?:\s+roz\.\s+\w+{_Q})?\s+ze?\s+[^,;()]+"
                    rf"|\ba\s+[A-ZČŘŠŽÚ]\w+{_Q},\s+dcery\b[^;]*?\bze?\s+[^,;()]+")


def vlastni_text(fakty, muz):
    """Údaje osoby bez rodných obcí matky (a u muže bez obce nevěsty) – z toho se hledají obce na mapu."""
    out = []
    for f in fakty:
        f = RODINA.sub("", f)
        if muz:
            f = re.sub(r"×.*", lambda m: re.sub(r"\bze?\s+[^,;()]+", "", m.group()), f)
        out.append(f)
    return " ".join(out)


def zil_v(text, rx):
    """Obec `rx` je ve vlastním textu osoby jinde než za „fara“, „okres“, „u“ (Chlum u Hořic)…"""
    return any(not MISTO_CIZI.search(text[:m.start()]) for m in rx.finditer(text))


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


def timeline_data(P, SAME, slugs, people, line_of, skryti=None):
    """Časová osa: řádky v pořadí otec – dítě – matka, události jako intervaly v desetinných letech, varování."""
    dnes = datetime.date.today()

    def ev(d):
        if d is None:
            return None
        return {"from": None if d.od == chronologie.MIN else round(chronologie.rok(d.od), 3),
                "to": None if d.do == chronologie.MAX else round(chronologie.rok(d.do), 3), "text": d.text}
    # Soukromí: u žijících (viz skryj() v main) jen rok narození, bez data sňatku a bez varování o jejich datech
    if skryti is None:
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
        if k in skryti and b:   # jen rok – ani from/to nesmí prozradit den
            rok_b = int(b["from"]) if b["from"] is not None else None
            b.update({"from": rok_b, "to": rok_b, "text": str(rok_b) if rok_b is not None else ""})
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
from pohled import nacti_pristupy, pohled, _slug as slug_pristupu   # noqa: E402 – přístupy k webu a pohled od jiné výchozí osoby (tools/pohled.py)


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
    subprocess.run(cmd + JPEG_WEB + ["-quality", "82", dst], check=True)
    return True


def obrazek_pro_web(src, dst, sub, zmensit):
    """Obrázek do webu: img (na stránce) nejvýš 1400 px, když je k němu plné rozlišení (`zmensit`), jinak jen překódovat;
    zdroje (proklik v plném rozlišení) bez zmenšení. Bez ImageMagicku, nebo když by byl výsledek větší, kopie originálu."""
    m = magick_bin()
    if not m:
        shutil.copy2(src, dst)
        return
    cmd = [m, src] + (["-resize", "1400x1400>"] if zmensit else []) + JPEG_WEB + ["-quality", "80" if sub == "img" else "82", dst]
    if subprocess.run(cmd, capture_output=True).returncode or not os.path.exists(dst) \
            or os.path.getsize(dst) >= os.path.getsize(src):
        shutil.copy2(src, dst)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def poznamky_files(otisky, klice=None):
    """Funkce Netlify /api/poznamky (netlify/functions/poznamky.mjs) s otisky přístupů, které smí poznámky číst a psát,
    a s otisky klíčů z osobních odkazů (`klice`, otisk klíče → přístup). Když je nemá žádný, funkce se smaže
    (na webu pak není ani tlačítko)."""
    klice = klice or {}
    out = os.path.join(WEB, "netlify", "functions", "poznamky.mjs")
    if not any(v["poznamky"] for v in list(otisky.values()) + list(klice.values())):
        if os.path.exists(out):
            os.remove(out)
        return
    tpl = os.path.join(WEB, "netlify", "poznamky.sablona.mjs")
    if not os.path.exists(tpl):
        sys.exit("CHYBA: web/ nemá šablonu poznámek. " + AKTUALIZUJTE)
    text = open(tpl, encoding="utf-8-sig").read()
    if klice and "{{KLICE}}" not in text:
        sys.exit("CHYBA: šablona poznámek ve web/ ještě neumí osobní odkazy. " + AKTUALIZUJTE)
    write(out, text.replace("{{PRISTUPY}}", json.dumps(otisky, indent=2)).replace("{{KLICE}}", json.dumps(klice, indent=2, sort_keys=True)))


AKTUALIZUJTE = "Aktualizujte projekt: python3 -I <skill>/tools/novy_projekt.py <složka projektu>"


def _odkazy_web(cfg):
    """Osobní odkazy přístupů z web.json (pristupy[].odkazy): [(záznam, id přístupu)], jen platné (bez „zruseno“)."""
    out = []
    for i, p in enumerate((cfg or {}).get("pristupy") or [], 1):
        if isinstance(p, dict):
            pid = slug_pristupu(p.get("nazev") or "") or f"pristup-{i}"   # stejné id jako tools/pohled.py
            out += [(o, pid) for o in p.get("odkazy") or [] if isinstance(o, dict) and "zruseno" not in o and o.get("otisk")]
    return out


def load_otisky(cfg=None):
    """Otisky klíčů osobních odkazů z web.json (pristupy[].odkazy) a starší data/pozvanky.json; klíče se nikam neukládají."""
    otisky = [o["otisk"] for o, _ in _odkazy_web(cfg)]
    for z in jload("pozvanky.json", []):
        if "zruseno" in z:   # zrušený odkaz: záznam zůstává jen kvůli id
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(z.get("otisk", ""))):
            sys.exit(f"CHYBA: v data/pozvanky.json má odkaz {z.get('id', '?')} neplatný otisk. "
                     f"Vytvořte mu nový: python3 -I tools/pozvanky.py nova {z.get('id', '<id>')}")
        otisky.append(z["otisk"])
    return otisky


def load_klice(cfg=None):
    """Platné osobní odkazy: otisk klíče → {"id": "p1", "pristup": <id přístupu nebo None = celý web>}
    – z web.json (pristupy[].odkazy) i ze staršího data/pozvanky.json."""
    klice = {z["otisk"]: dict(id=z.get("id", "?"), pristup=z.get("pristup"))
             for z in jload("pozvanky.json", []) if "zruseno" not in z and z.get("otisk")}
    klice.update({o["otisk"]: dict(id=o.get("id", "?"), pristup=pid) for o, pid in _odkazy_web(cfg)})
    return klice


def ma_pozvanky(cfg=None):
    """Má projekt osobní odkazy zavedené (web.json nebo data/pozvanky.json s aspoň jedním záznamem, i zrušeným)?"""
    return bool(jload("pozvanky.json", [])) or any(isinstance(p, dict) and p.get("odkazy") for p in (cfg or {}).get("pristupy") or [])


def section(tpl, name, keep):
    """Část šablony mezi <!--name--> a <!--/name-->: buď nechá (bez značek), nebo vyřízne."""
    pattern = rf"<!--{name}-->\n?(.*?)<!--/{name}-->\n?"
    return re.sub(pattern, (lambda m: m.group(1)) if keep else "", tpl, flags=re.S)


def link_hint(contact):
    """Věta pro přihlašovací stránku, jak získat nový osobní odkaz. `jmeno` je ve 3. pádě („Petrovi“)."""
    who, email = html.escape(contact.get("jmeno") or ""), html.escape(contact.get("email") or "")
    if email:
        link = f'<a href="mailto:{email}">{email}</a>'
        return f"Napište {who} na {link}, pošle vám nový." if who else f"Napište na {link}, pošleme vám nový."
    return f"Řekněte si o nový {who}." if who else "Řekněte si o nový tomu, kdo vám o webu řekl."


def login_files(cfg, otisky, odkazy=None, pristupy=None, klice=None):
    """Přihlašovací brána: rodinná otázka, osobní odkazy (tools/pozvanky.py), nebo obojí. Na serveru je jen otisk
    odpovědi (SHA-256, stejný spočítá přihlašovací stránka a uloží do cookie) a otisky klíčů z odkazů – samotná
    odpověď ani klíče se nikam neukládají. nginx (Docker/CapRover) otisk klíče spočítat neumí, pustí jen otázku.
    `odkazy` = projekt má osobní odkazy zavedené (i když jsou všechny zrušené: pak brána nepustí nikoho, ne každého).
    S přístupy (web.json → pristupy, fork) brána podle otisku odpovědi nebo klíče pošle jen verzi webu pro ten přístup
    (dist/_p/<id>/); osobní odkaz patří k přístupu z pozvanky.json („pristup“, bez něj „vse“ = celý web).
    `klice` = load_klice() (u kterého odkazu jaký přístup). Vrací True, když je brána zapnutá."""
    odkazy = bool(otisky) if odkazy is None else bool(odkazy or otisky)
    klice = klice if klice is not None else {o: dict(id="?", pristup=None) for o in otisky}
    login = cfg.get("prihlaseni") or {}
    answer = norm_answer(str(login.get("odpoved", "")))   # i číslo („1923“ bez uvozovek)
    tpl = open(os.path.join(WEB, "prihlaseni.sablona.html"), encoding="utf-8-sig").read()
    if "rodokmen:" not in tpl:   # stará šablona (do 0.4.0) ukládá do cookie odpověď – s novou bránou by se nikdo nepřihlásil
        sys.exit("CHYBA: web/ má starou šablonu přihlášení. " + AKTUALIZUJTE)
    gate_tpl = open(os.path.join(WEB, "netlify", "brana.sablona.js"), encoding="utf-8-sig").read()
    if odkazy and ("<!--odkazy-->" not in tpl or "{{OTISKY}}" not in gate_tpl):
        sys.exit("CHYBA: šablona přihlášení ve web/ ještě neumí osobní odkazy (data/pozvanky.json). " + AKTUALIZUJTE)
    contact = cfg.get("kontakt") or {}
    hint = ""
    if contact.get("email"):
        hint = (f'Neznáte odpověď? Napište {html.escape(contact.get("jmeno") or "")} na '
                f'<a href="mailto:{html.escape(contact["email"])}">{html.escape(contact["email"])}</a>.')
    # otázka, jen když na ni má kdo odpovědět (správce nebo přístup s odpovědí); bez otázky i odkazů stránka jako dřív
    question = bool(answer) or any(norm_answer(p.get("odpoved", "") or "") for p in pristupy or []) or not odkazy
    tpl = section(section(section(tpl, "odkaz", bool(otisky)), "otazka", question), "odkazy", not question)
    page = (tpl.replace("{{NAZEV}}", html.escape(cfg.get("nazev", "Rodokmen")))
               .replace("{{UVOD}}", html.escape(login.get("uvod", "Tenhle web je jen pro rodinu a příbuzné.")))
               .replace("{{OTAZKA}}", html.escape(login.get("otazka", "Odpověď na rodinnou otázku")))
               .replace("{{NAPOVEDA}}", hint)
               .replace("{{KDO}}", html.escape(contact.get("kdo") or "správce rodokmenu"))
               .replace("{{NAPOVEDA_ODKAZ}}", link_hint(contact)))
    write(os.path.join(WEB, "public", "prihlaseni.html"), page)

    edge = os.path.join(WEB, "netlify", "edge-functions", "brana.js")
    if pristupy:
        sablony = [os.path.join(WEB, "netlify", "brana.pristupy.sablona.js"), os.path.join(WEB, "nginx.pristupy.sablona.conf")]
        if not all(os.path.exists(x) for x in sablony):
            sys.exit("CHYBA: web/ nemá šablony brány pro přístupy. " + AKTUALIZUJTE)
        brana_p = open(sablony[0], encoding="utf-8-sig").read()
        if odkazy and "{{KLICE}}" not in brana_p:
            sys.exit("CHYBA: brána pro přístupy ve web/ ještě neumí osobní odkazy (data/pozvanky.json). " + AKTUALIZUJTE)
        odpovedi = {hashlib.sha256(("rodokmen:" + norm_answer(p["odpoved"])).encode()).hexdigest(): p["id"]
                    for p in pristupy if norm_answer(p.get("odpoved", "") or "")}   # přístup jen s odkazy nemá odpověď
        ids = {p["id"]: p for p in pristupy}
        klice_p = {}
        for o in otisky:
            k = klice.get(o) or dict(id="?", pristup=None)
            pid = k["pristup"] or "vse"
            if pid not in ids:
                sys.exit(f"CHYBA: osobní odkaz {k['id']} patří k přístupu „{pid}“, který ve web.json → pristupy není "
                         f"(jsou: {', '.join(ids)}). Změňte ho: python3 -I tools/pozvanky.py pristup {k['id']} <přístup>")
            klice_p[o] = pid
        poznamky_files({h: dict(id=i, poznamky=ids[i]["poznamky"]) for h, i in odpovedi.items()},
                       {o: dict(id=i, poznamky=ids[i]["poznamky"]) for o, i in klice_p.items()})
        write(edge, brana_p.replace("{{PRISTUPY}}", json.dumps(odpovedi, indent=2))
                           .replace("{{KLICE}}", json.dumps(klice_p, indent=2, sort_keys=True)))
        mapa = "\n".join(f'  "{h}" "{i}";' for h, i in odpovedi.items())
        write(os.path.join(WEB, "nginx.conf"), open(sablony[1], encoding="utf-8-sig").read().replace("{{PRISTUPY}}", mapa))
        if odkazy:
            print("POZOR: nginx.conf (Docker/CapRover) osobní odkazy neumí – pustí jen přes odpovědi přístupů. "
                  "Osobní odkazy fungují na Netlify (npm run nasadit).")
        cloudflare_files(cfg, "", False, "přístupy")
        return True
    for k in klice.values():
        if k["pristup"] not in (None, "vse"):
            print(f"POZOR: osobní odkaz {k['id']} patří k přístupu „{k['pristup']}“, ale web.json přístupy nemá – pustí na celý web.")
    gated = bool(answer or odkazy) and login.get("otevreny") is not True   # jen JSON true otevře web, ne "true", 1 ani "ano"
    digest = hashlib.sha256(("rodokmen:" + answer).encode()).hexdigest() if answer else ""
    if gated:
        write(edge, gate_tpl.replace("{{HASH}}", digest).replace("{{OTISKY}}", json.dumps(sorted(otisky))))
        poz = dict(id="vse", poznamky=bool(cfg.get("poznamky")))
        poznamky_files({digest: poz} if digest else {}, {o: poz for o in otisky})
        nginx_map = f'  "{digest}" 1;' if digest else ""   # default 0 (nepustit) je v šabloně
        if odkazy and not otisky and not digest:
            print("POZOR: všechny osobní odkazy jsou zrušené a otázka není nastavená – na web se nedostane nikdo.")
        if odkazy:
            print("POZOR: nginx.conf (Docker/CapRover) osobní odkazy neumí – "
                  + ("pustí jen přes rodinnou otázku." if digest else "nepustí nikoho.")
                  + " Osobní odkazy fungují na Netlify (npm run nasadit).")
    else:   # bez přihlášení – web je otevřený
        poznamky_files({})   # poznámky jen pro přihlášené
        nginx_map = "  default 1;"
        if os.path.exists(edge):
            os.remove(edge)
    nginx_tpl = open(os.path.join(WEB, "nginx.sablona.conf"), encoding="utf-8-sig").read()
    pred, _, za = nginx_tpl.replace("{{ODPOVED}}", nginx_map).partition("map $cookie_rodokmen")
    mapa, _, zbytek = za.partition("}")   # jen mapa $cookie_rodokmen, jiné mapy v šabloně zůstanou, jak jsou
    if not gated:   # default 0 ze šablony nahradí default 1
        mapa = re.sub(r"^[ \t]*default[ \t]+0;[ \t]*(#.*)?\n", "", mapa, flags=re.M)
    nginx = pred + "map $cookie_rodokmen" + mapa + "}" + zbytek
    if not za or re.findall(r"^[ \t]*default[ \t]+(\S+);", mapa, flags=re.M) != ["0" if gated else "1"]:
        sys.exit("CHYBA: web/nginx.sablona.conf má v mapě $cookie_rodokmen jiný default než jediné „default 0;“. "
                 + AKTUALIZUJTE)
    write(os.path.join(WEB, "nginx.conf"), nginx)
    cloudflare_files(cfg, digest, not gated, "osobní odkazy" if odkazy else "")
    return gated


def deploy_error(cfg, otisky, odkazy=False):
    """Text chyby, když by nasazený web byl otevřený komukoli bez výslovného prihlaseni.otevreny: true; jinak None."""
    login = cfg.get("prihlaseni") or {}
    if norm_answer(login.get("odpoved", "")) or otisky or odkazy or login.get("otevreny") is True:
        return None
    return ("CHYBA: v data/web.json není odpověď na přihlašovací otázku a v data/pozvanky.json žádný osobní odkaz – "
            "web by byl otevřený komukoli.\n"
            "Nastavte prihlaseni.odpoved, nebo přidejte odkaz: python3 -I tools/pozvanky.py pridej \"Jméno\". "
            "Otevřený web jen výslovně (když to opravdu chcete) přes prihlaseni.otevreny: true.")


def cloudflare_files(cfg, digest, otevreny, duvod_ne=""):
    """Brána pro Cloudflare (web/cloudflare/worker.js) a web/wrangler.jsonc pro `npm run nasadit-cloudflare`.
    `otevreny` = web bez přihlášení. Brána pro Cloudflare umí jen jednu rodinnou otázku: s přístupy nebo osobními odkazy
    (`duvod_ne`) se nevyrobí a nasazení na Cloudflare skončí chybou – jinak by pustila jen jednu odpověď, nebo (bez otázky)
    dokonce web otevřela. Přístupy, odkazy a poznámky jsou zatím jen na Netlify."""
    tpl = os.path.join(WEB, "cloudflare", "worker.sablona.js")
    if duvod_ne:
        for f in (os.path.join(WEB, "cloudflare", "worker.js"), os.path.join(WEB, "wrangler.jsonc")):
            if os.path.exists(f):
                os.remove(f)
        if cfg.get("cloudflare"):
            print(f"POZOR: Cloudflare (npm run nasadit-cloudflare) zatím neumí {duvod_ne} – nasazuj na Netlify (npm run nasadit).")
        return
    if not os.path.exists(tpl):
        return
    # Adresa https://<web>.<nazev>.workers.dev: cloudflare.nazev = subdoména účtu (jedna na účet, zakládá ji
    # nasadit_cloudflare.mjs), cloudflare.web = název webu na účtu (výchozí „rodokmen“; druhý projekt na stejném
    # účtu musí mít jiný, jinak by první web přepsal).
    cf = cfg.get("cloudflare") or {}
    for pole, priklad in (("nazev", "novakovi"), ("web", "rodokmen-dvorakovi")):
        hodnota = (cf.get(pole) or "").strip()
        if hodnota and not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?", hodnota):
            sys.exit(f"CHYBA: cloudflare.{pole} v data/web.json „{hodnota}“ nejde použít – jen malá písmena bez diakritiky, "
                     f"číslice a pomlčky (nejvýš 50 znaků), např. „{priklad}“.")
    web_nazev = (cf.get("web") or "").strip() or "rodokmen"
    worker = (open(tpl, encoding="utf-8-sig").read().replace("{{HASH}}", digest)
              .replace("{{OTEVRENY}}", "true" if otevreny else "false"))
    write(os.path.join(WEB, "cloudflare", "worker.js"), worker)
    wrangler = {
        "name": web_nazev,
        "main": "cloudflare/worker.js",
        "compatibility_date": "2026-10-01",
        "workers_dev": True,      # adresa https://<web>.<subdoména>.workers.dev
        "preview_urls": False,    # bez zvláštních adres pro jednotlivé verze
        "assets": {"directory": "./dist", "binding": "ASSETS", "run_worker_first": True,
                   "not_found_handling": "404-page"},
    }
    write(os.path.join(WEB, "wrangler.jsonc"),
          "// Vyrábí tools/export_web.py – ručně neupravovat. Nasazení: npm run nasadit-cloudflare.\n"
          + json.dumps(wrangler, ensure_ascii=False, indent=2) + "\n")


def main():
    ns = ns_spravce = load_people()
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
    lines_spravce = dict(ns["LINES"])   # rody v rodokmenu správce: na ně (zakladatelé, adresy /rod/…) odkazují texty
    if pristup and pristup["koren"]:
        ns, prevod = pohled(ns, pristup["koren"], texty, pristup.get("rody"))
        cfg = dict(cfg, nazev=pristup.get("nazev_webu", cfg.get("nazev")))
        # úvod = společný (web.json uvod, jen s právem texty) a za ním vlastní text přístupu (pristupy[].uvod)
        spolecny = dict(cfg.get("uvod") or {}) if texty else {}
        vlastni = dict(pristup.get("uvod") or {})
        uvod = dict(spolecny, **{k: v for k, v in vlastni.items() if k != "odstavce"})
        uvod["odstavce"] = list(spolecny.get("odstavce") or []) + list(vlastni.get("odstavce") or [])
        if uvod.get("nadpis") or uvod["odstavce"]:
            cfg["uvod"] = uvod
        else:
            cfg.pop("uvod", None)
    # Soukromí osob (zadání kap. 4, 7): o žijících jen jméno a rok narození. Plné údaje jen tomu, kdo má právo soukrome
    # (správce ho má), u osoby z vlastní větve přístupu (správce: všichni) a se zapsaným souhlasem (pole souhlas).
    # Ručně: soukrome=True u osoby (i zemřelé – jen jméno a roky) a údaj „(soukromé) …“ – obojí jen pro toho, kdo smí
    # soukromé údaje dané osoby (právo soukrome + vlastní větev).
    # Správce = přístup vse ve webu s přístupy (jeho odpověď zná jen správce): vidí vše, i žijící bez souhlasu.
    # Web bez přístupů čte celá rodina pod jednou odpovědí – tam platí souhlas jako u ostatních.
    spravce = bool(pristup) and pristup["id"] == "vse"
    pravo_soukrome = pristup["prava"]["soukrome"] if pristup else True
    vlastni_set = ns.get("_vlastni")

    def smi_soukrome(ref):
        return pravo_soukrome and (vlastni_set is None or ref in vlastni_set)

    kanon = lambda k: ns["SAME"].get(k, k) if isinstance(k, int) else k   # noqa: E731
    ns = dict(ns, P={k: ocisti_osobu(o, smi_soukrome(kanon(k))) for k, o in ns["P"].items()},
              RODINA={oid: ocisti_osobu(o, smi_soukrome(oid)) for oid, o in ns["RODINA"].items()})
    skryti_p = {k for k, o in ns["P"].items() if k not in ns["SAME"] and skryt_osobu(o, smi_soukrome(k), spravce)}
    skryti_p |= {kanon(a) for a, o in ns["P"].items() if a in ns["SAME"] and o.get("soukrome") and not smi_soukrome(kanon(a))
                 and not spravce}
    skryti_r = {oid for oid, o in ns["RODINA"].items() if skryt_osobu(o, smi_soukrome(oid), spravce)}
    # doklady: osoba skrytá, nebo viditelná žijící bez souhlasu s doklady → doklad s ní se neukáže (soukromý)
    bez_dokladu = skryti_p | skryti_r | {
        r for r, o in list(ns["P"].items()) + list(ns["RODINA"].items())
        if r not in ns["SAME"] and zijici(o.get("y"), o.get("note"), o.get("f", [])) and not souhlas_doklady(o)
        and not spravce}

    skryte_side = set()   # zápisy bočních příbuzných, kteří se neukážou

    def side_zaznam(s):   # boční příbuzný (SIDE): u skryté osoby nic, žijící jen jménem, „(soukromé) …“ podle osoby
        if kanon(s.get("k")) in skryti_p:
            skryte_side.update(s.get("r", []))
            return None
        t = s.get("t", "")
        if soukromy_udaj(t):
            t = bez_znacky(t) if smi_soukrome(kanon(s.get("k"))) else ""
        if zijici(s.get("y"), t) and not spravce:
            skryte_side.update(s.get("r", []))
            return dict(s, t="", r=[])
        return dict(s, t=t)
    ns["SIDE"] = [x for x in map(side_zaznam, ns["SIDE"]) if x is not None]
    skryte_zapisy = {r for k, o in ns["P"].items() if kanon(k) in skryti_p for r in o.get("r", [])} | \
        {r for oid in skryti_r for r in ns["RODINA"][oid].get("r", [])} | skryte_side
    pozn_skryti = lambda o: ZIJICI_POZN if zijici(o.get("y"), o.get("note"), o.get("f", [])) else SOUKROME_POZN
    P, LINES, SIDE, ISSUES = ns["P"], ns["LINES"], ns["SIDE"], ns["ISSUES"]
    SAME = ns["SAME"]                       # alias Kekulé → kanonické Kekulé (předek v rodokmenu vícekrát)
    # web.json "puvodni_jmena": true → jméno osoby v původních tvarech ze zápisů (pole zap v osoby.py, „Nowakin / Nováková“);
    # jinak dnešní podoba n. Adresa stránky (slug) je vždy podle n.
    puvodni = lambda p: " / ".join(p["zap"]) if cfg.get("puvodni_jmena") and p.get("zap") else p["n"]
    otisky, odkazy = load_otisky(cfg_puvodni), ma_pozvanky(cfg_puvodni)
    if "--nasazeni" in sys.argv and not pristupy and deploy_error(cfg, otisky, odkazy):
        sys.exit(deploy_error(cfg, otisky, odkazy))
    docs_cfg = jload("dokumenty.json", [])
    # Doklady (zadání kap. 7): s rodným číslem až po úmrtním listu nebo začernění (pro všechny, i správce); ve verzi
    # přístupu jen přidělené (pristupy) nebo s osobami, které přístup vidí celé; soukrome jen tomu, kdo smí.
    najdi = lambda r: ns_spravce["P"].get(r) if isinstance(r, int) else ns_spravce["RODINA"].get(r)   # noqa: E731
    bez_rc = [d["img"] for d in docs_cfg if not rc_zverejnit(d, docs_cfg, najdi, puvodni_same)]
    if bez_rc:
        print(f"doklady s rodným číslem žijícího (bez úmrtního listu / začernění) se nezveřejní: {', '.join(bez_rc)}")
    docs_cfg = [d for d in docs_cfg if d["img"] not in bez_rc]
    if pristup and pristup["koren"]:
        docs_cfg = [d for d in docs_cfg if dokument_pro_pristup(d, pristup["id"], lambda r: r in prevod, puvodni_same)]
    docs_cfg = [d for d in docs_cfg if not d.get("soukrome") or all(
        smi_soukrome(prevod.get(puvodni_same.get(o, o) if isinstance(o, int) else o) if prevod is not None else o)
        for o in d.get("osoby", []))]
    recs = {r["key"]: r for r in record_rows()}
    if prevod is not None:   # jen zápisy a dokumenty viditelných osob
        recs = {k: v for k, v in recs.items() if k in ns["_zapisy"]}
        docs_cfg = [dict(d, osoby=[prevod[o] for o in (puvodni_same.get(x, x) if isinstance(x, int) else x
                                                       for x in d.get("osoby", [])) if o in prevod]) for d in docs_cfg]
        docs_cfg = [d for d in docs_cfg if d["osoby"]]
    recs = {k: v for k, v in recs.items() if k not in skryte_zapisy}   # zápisy skrytých osob (i sdílený sňatek) ne
    docs_cfg = [d for d in docs_cfg if not any(kanon(o) in bez_dokladu for o in d.get("osoby", []))]

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
    for a, c in list(SAME.items()):
        if c not in slugs:   # hlavní osoba je zástupná (bez jména) nebo chybí – alias nemá kam ukazovat
            print(f"POZOR: SAME {a} -> {c} – osoba {c} je zástupná nebo chybí, alias vynechávám (oprav data/osoby.py)")
            del SAME[a]
            continue
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
            side=[dict(name=s["n"], text=s.get("t", ""), records=[r for r in s.get("r", []) if r in recs], rel=s.get("v") or "příbuzný",
                       years=years(s.get("y")), kind=SIDE_KIND.get((s.get("v") or "").lower(), "other")) for s in SIDE if s["k"] == k],
            sibStatus=SIB_STATUS.get(p.get("sour"), "none"),
            docs=[dict(img=d["img"], caption=d.get("popis", "")) for d in docs_cfg if k in d.get("osoby", [])],
            children=[slugs[c] for c in [k // 2] + [a // 2 for a in aliases_of.get(k, [])] if k > 1 and c in slugs],
            also=[dict(k=a, rel=relation(a), line=line_of(a), child=slugs.get(a // 2)) for a in aliases_of.get(k, [])],
        )
        if aliases_of.get(k):
            for a in aliases_of[k]:
                people[slugs[k]]["records"] = list(dict.fromkeys(people[slugs[k]]["records"] + [r for r in P.get(a, {}).get("r", []) if r in recs]))
            people[slugs[k]]["facts"] = [f for f in people[slugs[k]]["facts"] if not f.startswith("TÁŽ OSOBA")]

    # Soukromí: žijící (a narození v posledních 100 letech bez známého úmrtí) jen jménem, rokem narození a vazbami –
    # bez míst, dat, poznámek a zápisů. Na mapu, do Domů ani do Statistik se tak nedostanou (počítají se z faktů).
    def skryj(p, pozn=ZIJICI_POZN):
        p["facts"], p["records"], p["note"], p["docs"], p["side"] = [], [], pozn, [], []
        p["vyz"], p["skryto"] = "", True
    skryto = 0
    for k, p in P.items():
        if k in slugs and k in skryti_p:
            skryj(people[slugs[k]], pozn_skryti(p))
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
        if oid in skryti_r:
            others[-1].update(facts=[], records=[], note=pozn_skryti(o))
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
            side=[], sibStatus="none", docs=[dict(img=d["img"], caption=d.get("popis", "")) for d in docs_cfg if oid in d.get("osoby", [])],
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
        if any(people[x]["note"] in (ZIJICI_POZN, SOUKROME_POZN) for x in (a, b)):
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
        surname = ((P[m]["n"].split() or [""])[-1] if m in P else "").strip("()?")
        mfacts = [x for x in fakta(f)["facts"] + fakta(m)["facts"] if x.startswith("×")]
        marriage = [x for x in mfacts if surname and surname[:5] in x] or mfacts
        if SAME.get(f, f) in skryti_p or SAME.get(m, m) in skryti_p:
            marriage = []   # sňatek skryté osoby (žijící, soukromá) ani z údajů manžela
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
        ls = slugify(name)
        if ls in lines:   # dva rody stejného jména (např. Novákové z obou stran) – jinak by jeden tiše zmizel
            print(f"POZOR: rody {lines[ls]['k']} a {k} mají stejný název „{name}“ – rozliš je v LINES (data/osoby.py)")
            ls = f"{ls}-{k}"
        lines[ls] = dict(k=k, slug=ls, name=name, desc=desc, color=LINE_COLORS[k],
                                    root=slugs.get(k), people=[p["slug"] for _, p in members],
                                    gens={p["slug"]: gen(kk) for kk, p in members})
    lines = {s: l for s, l in lines.items() if l["root"]}
    rod_k = {l["k"]: l for l in lines.values()}
    # rody správce (adresa /rod/<slug>/ a název v nadpisech) → číslo rodu správce = zakladatel
    rody_spravce, videno_s = {}, set()
    for k_, (jm, _) in sorted(lines_spravce.items()):
        ls_ = slugify(jm)
        ls_ = f"{ls_}-{k_}" if ls_ in videno_s else ls_
        videno_s.add(ls_)
        rody_spravce[ls_] = dict(k=k_, slug=ls_, name=jm)

    def rody_zakladatelu(zakladatele):
        """Zakladatelé rodů (čísla osob z rodokmenu správce) → (vidí přístup obsah?, čísla rodů přístupu 8–15).
        Vidí, když je některý zakladatel v přímé linii přístupu (kořen nebo předek)."""
        vidi, out = False, set()
        for z in zakladatele:
            z = puvodni_same.get(z, z)
            n = z if prevod is None else prevod.get(z)
            if prevod is None and z not in P:
                vidi = True   # celý web: obsah zůstane, jen bez znaku rodu
                continue
            if isinstance(n, int):
                vidi = True
                r = n >> (gen(n) - 3) if n >= 8 else n
                while r < 8:   # bližší předek přístupu: jeho rod pokračuje po otci (otec otce…)
                    r *= 2
                if r in rod_k:
                    out.add(r)
            elif n is not None and (ns.get("_linie") or {}).get(n) == "prima":
                vidi = True   # předek dalšího kořene: obsah ano, rod prvního kořene žádný
        return vidi, sorted(out)

    def znak_rodu(k):
        l = rod_k.get(k)
        return (f'<span class="rod-znak"><span class="dot" style="background:{l["color"]}"></span>'
                f'<a href="/rod/{l["slug"]}/">{html.escape(l["name"])}</a></span>') if l else ""

    def prepis_odkazy_rodu(md):
        """Odkazy /rod/<slug správce>/ → rod přístupu; rod, který přístup nemá, jen jako text."""
        def nahrad(m):
            l = rody_spravce.get(m.group(2))
            if not l or prevod is None:
                return m.group(0)
            vidi, rr = rody_zakladatelu([l["k"]])
            text = rod_k[rr[0]]["name"] if vidi and rr and m.group(1).strip() == l["name"] else m.group(1)   # název rodu správce → přístupu
            return f"[{text}](/rod/{rod_k[rr[0]]['slug']}/)" if vidi and rr else text
        return re.sub(r"\[([^\]]*)\]\(/rod/([^/)\s]+)/?\)", nahrad, md)

    def prepis_frontmatter_rodu(text, rod):
        m = re.match(r"\A(---\r?\n)(.*?)(\r?\n---)", text, re.S)
        if not m:
            return text
        fm = [x for x in m.group(2).splitlines() if not re.match(r"(rod|rody):", x)]
        if rod:
            fm.append(f"rod: {rod}")
        return m.group(1) + "\n".join(fm) + m.group(3) + text[m.end():]

    def filtr_zajimavosti(md):
        """Oddíly zajímavostí: bez rodu vidí všichni; s rodem (řádek „Rod: [..](/rod/<slug>/)“ nebo <!-- rody: 8 -->)
        jen přístup se zakladatelem v přímé linii – řádek Rod se přepíše na rody přístupu. Úvod jen s právem texty."""
        uvod, oddily = oddily_md(md)
        out = uvod if texty else ""
        for o in oddily:
            rod_radek = re.search(r"(?m)^Rod:\s*(.*)$", o)
            zakl = zakladatele_v_textu(o)
            if rod_radek:
                zakl += [rody_spravce[x]["k"] for x in re.findall(r"/rod/([^/)\s]+)", rod_radek.group(1)) if x in rody_spravce]
            if not zakl and not rod_radek:
                out += o
                continue
            if not zakl:   # řádek Rod: bez platného odkazu na rod (překlep, chybí odkaz)
                print(f"POZOR: zajímavost „{o.splitlines()[0][3:].strip()}“: řádek Rod: neodkazuje na rod (/rod/<slug>/ "
                      "z LINES)" + (" – v přístupu se neukáže" if prevod is not None else ""))
                if prevod is None:
                    out += o
                continue
            vidi, rr = rody_zakladatelu(zakl)
            if not vidi:
                continue
            znaky = " ".join(znak_rodu(k) for k in rr)
            if rod_radek:
                o = o[:rod_radek.start()] + (f"Rod: {znaky}" if znaky else "") + o[rod_radek.end():]
            elif znaky:
                hlava, _, telo = o.partition("\n")
                o = f"{hlava}\n\n{znaky}\n{telo}"
            out += o
        return out

    def filtr_oddilu(md, razeni_rodu):
        """Otázky pro rodinu / prameny: oddíl „## <rod správce>“ jen přístupu se zakladatelem v přímé linii (nadpis = rod
        přístupu), odrážka s <!-- rody: N --> podle zakladatele; oddíly a odrážky bez rodu jen s právem texty."""
        uvod, oddily = oddily_md(md)
        ostatni, rodove = [], []
        for o in oddily:
            hlava, _, telo = o.partition("\n")
            l = rod_nadpisu(hlava[3:], rody_spravce)
            vidi_oddil, rr = rody_zakladatelu([l["k"]]) if l else (texty, [])
            if l and not vidi_oddil:
                continue
            zbyle = []
            for druh, blok in polozky_oddilu(telo):
                zakl = zakladatele_v_textu(blok)
                if zakl:
                    if rody_zakladatelu(zakl)[0]:
                        zbyle.append(blok)
                elif vidi_oddil:
                    zbyle.append(blok)
            if not any(b.strip() and not RODY_KOMENTAR.fullmatch(b.strip()) for b in zbyle):
                continue
            if l and rr:
                hlava = "## " + " ".join(znak_rodu(k) for k in rr)
            cast = hlava + "\n" + "".join(zbyle)
            (rodove if l and rr and razeni_rodu else ostatni).append((rr[0] if rr else 0, cast))
        rodove.sort(key=lambda x: x[0])
        return (uvod if texty else "") + "".join(c if c.endswith("\n") else c + "\n" for _, c in ostatni + rodove)

    # názvy rodů přístupu: bez nich web použije odvozené (příjmení) – správce je má doplnit (pristupy[].rody)
    if pristup and pristup["koren"] and pristup["koren"][0] != 1:
        chybi = [f"{l['k']} ({l['name']})" for l in sorted(lines.values(), key=lambda l: l["k"])
                 if str(l["k"]) not in (pristup.get("rody") or {})]
        if chybi:
            print(f"POZOR: přístup {pristup['id']}: rody {', '.join(chybi)} nemají název ve web.json → "
                  f"pristupy[].rody (názvy z pohledu této větve, např. \"8\": [\"Plíškové\", \"popis\"])")
    for p in people.values():
        p["lineSlug"] = next((l["slug"] for l in lines.values() if l["k"] == p["line"]), None)

    # předci dalších výchozích osob přístupu (v RODINA, linie „prima“) patří na mapu taky – sjednocení kořenů
    prima_extra = {rslug[o] for o, l in (ns.get("_linie") or {}).items() if l == "prima" and isinstance(o, str) and o in rslug}
    places = []
    for name, e in jload("mista.json", {}).items():
        if "lat" not in e:
            continue
        rx = re.compile(e.get("re") or re.escape(name))
        hits = [p for p in people.values() if (not p.get("extra") or p["slug"] in prima_extra) and zil_v(vlastni_text([text_pro_misto(f) for f in p["facts"]], p["sex"] == "M"), rx)]
        byline = {}
        for p in sorted(hits, key=lambda p: p["k"]):
            byline.setdefault(p["line"] or 0, []).append(p["slug"])
        if e.get("hypoteza"):   # hypotéza = text; u přístupu jen s právem texty a jen v rodu, který přístup má
            rod_h = e.get("rod", 0)
            if pristup and not texty:
                continue
            if prevod is not None:
                rod_h = prevod.get(rod_h) if isinstance(rod_h, int) else None
                if not isinstance(rod_h, int) or not 8 <= rod_h <= 15:
                    continue
            byline = {rod_h: []}
        if not byline:
            continue
        yrs = [int(y) for p in hits for y in re.findall(r"\b1[4-9]\d\d\b", p["y"] or "")]
        slug = slugify(name)
        timeline = [] if e.get("hypoteza") else [
            dict(slug=p["slug"], line=p["line"] or 0, life=life(p["y"]), events=[place_event(f) for f in p["facts"] if rx.search(text_pro_misto(f))])
            for p in hits]
        for p in hits + [p for p in people.values() if p.get("extra") and any(rx.search(text_pro_misto(f)) for f in p["facts"])]:
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
        legacy_text = open(legacy_story, encoding="utf-8-sig").read()
        legacy_match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", legacy_text, re.S)
        legacy_fields = {}
        if legacy_match:
            for line in legacy_match.group(1).splitlines():
                item = re.fullmatch(r"(title|lead):\s*(.*?)\s*", line)
                if item:
                    legacy_fields[item.group(1)] = item.group(2)
        rod_l = (cfg.get("pribeh") or {}).get("rod")
        rody_l = [int(x) for x in re.findall(r"\d+", re.search(r"(?m)^rody:(.*)$", legacy_match.group(1)).group(1))] \
            if legacy_match and re.search(r"(?m)^rody:(.*)$", legacy_match.group(1)) else []
        stories = [dict(slug="", title=legacy_fields.get("title", "Příběh"),
                        lead=legacy_fields.get("lead", ""), rod=rod_l,
                        zakladatele=rody_l or ([int(rod_l)] if isinstance(rod_l, int) or str(rod_l or "").isdigit() else []),
                        text=legacy_text)]
    # příběh s rodem vidí přístup se zakladatelem v přímé linii (i bez práva texty), příběh bez rodu jen s právem texty
    vidi_story = []
    for story in stories:
        vidi, rody_story = rody_zakladatelu(story.get("zakladatele") or [])
        if (vidi if story.get("zakladatele") else texty):
            story = dict(story, rody=rody_story, rod=rody_story[0] if rody_story else None)
            story["text"] = prepis_frontmatter_rodu(story["text"], story["rod"])
            vidi_story.append(story)
    stories = vidi_story
    multi_stories = multi_stories and bool(stories)
    has_story = bool(stories)
    public_cfg = {k: v for k, v in cfg.items() if k not in ("prihlaseni", "pristupy")}   # odpovědi nikdy na web
    # poznámky ke stránkám (tlačítko „Připomínka“, /poznamky/): podle přístupu, jinak web.json „poznamky“
    vse = next((p for p in pristupy or [] if p["id"] == "vse"), None)
    public_cfg["poznamky"] = bool(pristup["poznamky"] if pristup else vse["poznamky"] if vse else cfg.get("poznamky"))
    public_cfg["maPribeh"] = has_story
    if stories and isinstance(public_cfg.get("pribeh"), dict):
        public_cfg["pribeh"] = dict(public_cfg["pribeh"], rod=stories[0]["rod"])   # číslo rodu z pohledu přístupu
    # karty na úvodu: s rody (zakladatelé) jen přístupům, které je mají v přímé linii; ve výstupu slugy rodů přístupu
    karty = []
    for karta in public_cfg.get("zajimavosti_na_uvodu") or []:
        zakl = [int(x) for x in karta.get("rody") or [] if str(x).isdigit()] if isinstance(karta, dict) else []
        vidi, rody_karty = rody_zakladatelu(zakl)
        if not (vidi if zakl else texty):   # karta bez rodu = obecný text (jen s právem texty)
            continue
        karty.append(dict(karta, rody=[rod_k[k]["slug"] for k in rody_karty]) if zakl else karta)
    if "zajimavosti_na_uvodu" in public_cfg:
        public_cfg["zajimavosti_na_uvodu"] = karty
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

    rody_k = {l["k"]: l["slug"] for l in lines.values()}

    def slug_otazky(k):   # stránka osoby u otázky (číslo předka, i alias ze SAME, nebo zkratka z RODINA)
        k = SAME.get(k, k) if isinstance(k, int) else k
        return slugs.get(k) if isinstance(k, int) else rslug.get(k)

    def rod_otazky(k):    # rod (8–15) předka u otázky; u bližších předků a příbuzných z RODINA žádný
        k = SAME.get(k, k) if isinstance(k, int) else k
        return rody_k.get(line_of(k)) if isinstance(k, int) and k >= 8 else None

    # linie („prima“ = výchozí osoby a předci, „rozsirena“ = ostatní) a vlastní větev (tools/pohled.py); celý web
    # (správce, projekt bez přístupů): předci = přímá, RODINA = rozšířená, všichni ve vlastní větvi
    linie_ns, vlastni_ns = ns.get("_linie"), ns.get("_vlastni")
    oid_slug = {s_: o_ for o_, s_ in rslug.items()}
    for s_, p_ in people.items():
        ref_ = oid_slug.get(s_) if p_.get("extra") else p_["k"]
        p_["linie"] = (linie_ns or {}).get(ref_, "rozsirena" if p_.get("extra") else "prima") if linie_ns is not None \
            else ("rozsirena" if p_.get("extra") else "prima")
        p_["vlastni"] = (ref_ in vlastni_ns) if vlastni_ns is not None else True
    prava_pristupu = dict(pristup["prava"]) if pristup else dict(soukrome=True, texty=True, poznamky=bool(public_cfg.get("poznamky")))
    koreny_slugy = [slugs[1]]
    if pristup and prevod is not None:
        for k_ in pristup["koren"][1:]:
            n_ = prevod.get(puvodni_same.get(k_, k_) if isinstance(k_, int) else k_)   # k_ je v původním číslování
            s_ = slugs.get(n_) if isinstance(n_, int) else rslug.get(n_)
            if s_ and s_ not in koreny_slugy:
                koreny_slugy.append(s_)
    site_pristup = dict(id=pristup["id"] if pristup else "vse", nazev=pristup["nazev"] if pristup else "všechno",
                        koreny=koreny_slugy, prava=prava_pristupu)

    site = dict(config=public_cfg, pristup=site_pristup, places=places, root=slugs[1], aliases={a: slugs[a] for a in SAME}, people=people,
                families=families, others=others, records=records, lines=lines,
                issues=issue_rows(ISSUES, slug_otazky, rod_otazky), stats=stats, hypotheses=hypotheses,
                docs=[dict(img=d["img"], caption=d.get("popis", ""), people=[slugs.get(k) or rslug[k] for k in d.get("osoby", []) if k in slugs or k in rslug],
                           rods=sorted(set().union(set(), *(rody_osoby(SAME.get(k, k) if isinstance(k, int) else k, R) for k in d.get("osoby", [])))))
                      for d in docs_cfg if os.path.exists(os.path.join(VYREZY, d["img"] + ".jpg"))],
                timeline=timeline_data(P, SAME, slugs, people, line_of, {k for k in skryti_p if k in slugs}))

    generovane = {}
    for src, dst in (("archivni_dotazy.md", "dotazy.md"), ("otazky_pro_rodinu.md", "otazky.md"),
                     ("research_log.md", "denik.md"), ("zajimavosti.md", "zajimavosti.md")):
        path = os.path.join(DATA, src)
        text = open(path, encoding="utf-8-sig").read() if os.path.exists(path) else ""
        text = re.sub(r"^# .*\n", "", text, count=1)
        # rody (zakladatelé) se čtou z komentářů – filtrovat před jejich odstraněním
        if src == "zajimavosti.md":
            text = filtr_zajimavosti(text)
        elif src in ("otazky_pro_rodinu.md", "archivni_dotazy.md"):   # otázky podle rodů (8–15), obecné nahoře
            text = filtr_oddilu(text, src == "otazky_pro_rodinu.md")
        elif not texty:
            text = ""
        text = hvezdicky_narozeni(strip_comments(prepis_odkazy_rodu(text)))
        write(os.path.join(gen_dir, dst), text)
        generovane[dst] = bool(text.strip())
    site["stranky"] = stranky_s_daty(site, generovane, texty)
    write(os.path.join(WEB, "src", "data", "site.json"), json.dumps(site, ensure_ascii=False, indent=1))
    shutil.rmtree(os.path.join(gen_dir, "pribehy"), ignore_errors=True)
    if multi_stories:
        for story in stories:
            write(os.path.join(gen_dir, "pribehy", story["slug"] + ".md"), strip_comments(prepis_odkazy_rodu(story["text"])))
    write(os.path.join(gen_dir, "pribehy.json"), json.dumps(
        [{key: story.get(key) for key in ("slug", "title", "lead", "rod", "rody")} for story in stories if story["slug"]],
        ensure_ascii=False, indent=1))
    story = stories[0]["text"] if stories else "---\ntitle: Příběh\nlead: ''\n---\n"
    write(os.path.join(gen_dir, "pribeh.md"), strip_comments(prepis_odkazy_rodu(story)))

    gated = login_files(cfg_puvodni, otisky, odkazy, pristupy, load_klice(cfg_puvodni))
    question = bool(norm_answer((cfg_puvodni.get("prihlaseni") or {}).get("odpoved", ""))) or \
        any(norm_answer(p.get("odpoved", "") or "") for p in pristupy or [])
    login_state = (f"zapnuté (otázka {'ano' if question else 'ne'}, osobních odkazů {len(otisky)})" if gated
                   else "VYPNUTÉ (web je otevřený)")
    if pristupy and not pristup:   # jednou za sestavení (správcovská data na konci build.mjs)
        na_vse = sorted(z["id"] for z in load_klice(cfg_puvodni).values() if not z.get("pristup"))
        if na_vse:
            print(f"POZOR: osobní odkazy {', '.join(na_vse)} vedou na celý web (přístup vse = správce: vidí i žijící "
                  "a soukromé údaje). Příbuzným dej odkaz k přístupu: python3 -I tools/pozvanky.py pristup <id> <přístup>")

    copied = 0
    zv = os.path.join(DATA, "zvyrazneni.json")
    hl_mtime = os.path.getmtime(zv) if os.path.exists(zv) else 0
    for sub, src_dir in (("img", VYREZY), ("zdroje", ZDROJE)):
        dst_dir = os.path.join(WEB, "public", sub)
        cache_dir = os.path.join(WEB_OBRAZKY, sub)
        if pristup:   # web pro jeden přístup: jen jeho obrázky (ze sestavení jiného přístupu nic nezůstane)
            shutil.rmtree(dst_dir, ignore_errors=True)
        znacka = os.path.join(cache_dir, ".uprava")
        nova_uprava = not os.path.exists(znacka) or open(znacka, encoding="utf-8-sig").read() != UPRAVA_OBRAZKU
        if nova_uprava:   # jiné nastavení úpravy (nebo první export s úpravou): staré verze pryč
            shutil.rmtree(cache_dir, ignore_errors=True)
            shutil.rmtree(dst_dir, ignore_errors=True)
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)
        if nova_uprava:
            with open(znacka, "w", encoding="utf-8") as f:
                f.write(UPRAVA_OBRAZKU)
        for key in list(recs) + [d["img"] for d in docs_cfg] + ([cfg["uvod"]["foto"]] if cfg.get("uvod", {}).get("foto") else []):
            src = os.path.join(src_dir, key + ".jpg")
            dst = os.path.join(dst_dir, key + ".jpg")
            hotovy = os.path.join(cache_dir, key + ".jpg")   # upravená verze v pracovni/.web_obrazky/
            if not os.path.exists(src):
                continue
            boxes = hl.get(key, {}).get("boxes", [])
            stale = not os.path.exists(hotovy) or os.path.getmtime(src) > os.path.getmtime(hotovy) \
                or (sub == "zdroje" and boxes and hl_mtime > os.path.getmtime(hotovy))
            if stale:
                if not (sub == "zdroje" and boxes and draw_boxes(src, hotovy, boxes, os.path.join(VYREZY, key + ".jpg"))):
                    obrazek_pro_web(src, hotovy, sub, sub == "img" and os.path.exists(os.path.join(ZDROJE, key + ".jpg")))
                copied += 1
            if stale or not os.path.exists(dst) or os.path.getmtime(hotovy) > os.path.getmtime(dst):
                shutil.copy2(hotovy, dst)
    if pristup:
        print(f"přístup {pristup['id']} ({pristup['nazev']}): " + (f"výchozí osoba {people[slugs[1]]['name']}" if prevod is not None else "vše"))
    print(f"{len(people)} osob, {len(families)} rodin, {len(records)} zápisů, {len(lines)} rodů, {len(places)} míst; "
          f"zkopírováno {copied} obrázků; přihlášení {login_state}")
    if skryto:
        print(f"soukromí: {skryto} žijících (nebo narozených od {HRANICE_ZIJICI} bez známého úmrtí) jen se jménem a rokem narození")

    # odkazy v textech, které nikam nevedou (adresa osoby se změní třeba doplněním roku narození: jan-novak → jan-novak-1798)
    targets = dict(osoba=people, zdroj=recs, rod=lines, rodina=families)
    texts = {f: open(os.path.join(gen_dir, f), encoding="utf-8-sig").read()
             for f in ("pribeh.md", "zajimavosti.md", "otazky.md", "dotazy.md", "denik.md")}
    if multi_stories:
        texts.update({f"pribehy/{story['slug']}.md": open(os.path.join(gen_dir, "pribehy", story["slug"] + ".md"),
                                                          encoding="utf-8-sig").read() for story in stories})
    texts["web.json"] = json.dumps(public_cfg, ensure_ascii=False)   # jen to, co jde do site.json
    texts["osoby.py (hypotézy)"] = json.dumps(hypotheses, ensure_ascii=False)
    targets["pribehy"] = {story["slug"] for story in stories if story["slug"]}
    broken = [(f, m.group(0)) for f, t in texts.items()
              for m in re.finditer(r"/(osoba|zdroj|rod|rodina|pribehy)/([^/\s)\"'#?<>\]]+)", t)
              if m.group(2) not in targets[m.group(1)]]
    v_pristupu = bool(pristup) and bool(pristup["koren"])
    # cíl ve webu správce existuje (osoba podle jména, zápis) → jde o jinou větev / skrytou osobu, ne o překlep
    jmena_spravce = {slugify(o.get("n", "")) for o in list(ns_spravce["P"].values()) + list(ns_spravce["RODINA"].values())}
    zapisy_spravce = {r["key"] for r in record_rows()}

    def cizi(link):
        druh, cil = link.strip("/").split("/", 1)
        if druh == "osoba":
            return any(j and (cil == j or cil.startswith(j + "-")) for j in jmena_spravce)
        return druh in ("zdroj", "rodina") and (druh == "rodina" or cil in zapisy_spravce)
    broken_cizi = [(f, link) for f, link in broken if v_pristupu and cizi(link)]
    for f, link in dict.fromkeys(broken):
        if (f, link) in broken_cizi:
            print(f"CHYBA: přístup {pristup['id']}: odkaz {link}/ v {f} vede na stránku, kterou tento přístup nevidí "
                  "(jiná větev nebo skrytá osoba) – text by prozradil jméno; vyřaď ho pro tento přístup "
                  "(rod u zajímavosti / příběhu, <!-- rody: N --> u odrážky) nebo odkaz oprav")
        else:
            print(f"POZOR: nefunkční odkaz {link}/ v {f} – oprav ho (adresy stránek jsou ve web/src/data/site.json)")
    if broken_cizi:
        sys.exit(1)

    # stránky Statistiky a Domy se počítají z hotového site.json
    sys.path.insert(0, TOOLS)
    import statistiky, domy_export, stavby
    statistiky.main()
    domy_export.main()
    upoz, n_staveb = stavby.export(prevod=prevod, same=puvodni_same)   # data/stavby.py → web/src/data/stavby.json (u Domů: držitelé, obyvatelé, události)
    stavby.tisk_upozorneni(upoz)
    if n_staveb:
        print(f"stavby: {n_staveb} staveb s dějinami na stránce Domy")


if __name__ == "__main__":
    main()
