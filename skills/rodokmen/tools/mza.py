#!/usr/bin/env python3
"""Hledání matrik MZA Brno (Acta Publica, www.mza.cz/actapublica).

Použití (z kořene projektu):
  mza.py hledat "Obec" [slovo ...] [--stran N]
        -> knihy, které obsahují obec (české, německé i historické jméno). Další slova zúží výsledek (musí být v řádku
           všechna): „Hustopeče 1850“ = jen knihy, jejichž rozsah N/O/Z zahrnuje rok 1850; „Lhota Prostějov“ = jen knihy,
           ve kterých je Prostějov v původci či obcích. --stran N = nejvýš N stran výsledků po 20 knihách (výchozí 5,
           u „Lhota“ jich je přes 30). Výpis: id | č. knihy | původce (typ) | N | O | Z (v závorce rejstřík) | obcí N: obce | snímků
  mza.py puvodce "Farnost" [typ]
        -> knihy podle původce (farnosti); typ = římskokatolická, evangelická, civilní… (část názvu typu původce)
Skriptem jen hledání knih (MZA od 2. 11. 2026 nepovoluje stahování skriptem). Detail knihy, odkaz na snímek i snímky
otevři v prohlížeči (reference/portaly.md, MZA Brno); tools/slusne.py ostatní adresy MZA stejně zastaví.
Výpis: id | č. knihy | ... ; <id> je interní číslo knihy z odkazu `…/matrika/detail/<id>` (první sloupec výpisu).
Ber ohled na server. Podmínky užití: https://www.mza.cz/actapublica/page/view/podminky-uziti-sluzeb
"""
import html, http.cookiejar, os, re, sys, time, unicodedata, urllib.parse, urllib.request
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://www.mza.cz/actapublica/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cj = http.cookiejar.CookieJar()
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))
_op.addheaders = [("User-Agent", "Mozilla/5.0 (rodokmen)")]


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import slusne  # noqa: E402 – brzda proti zablokování archivem (společný limit dotazů, tools/slusne.py)


def get(url, binary=False):
    err = None
    for attempt in range(4):
        try:
            with _op.open(url, timeout=60) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except OSError as e:   # i HTTPError (404 u neexistující dlaždice) – volající si ho umí odchytit
            err = e
            if getattr(e, "code", 0) in (403, 404):
                break
            time.sleep(2 * (attempt + 1))
    raise err


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def radky(page):
    """Řádky tabulky „Nalezené matriky“ -> slovníky."""
    out = []
    for tr in re.findall(r"<tr>\s*<td class=\"clickable\".*?</tr>", page, re.S):
        m = re.search(r"matrika/detail/(\d+)", tr)
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not m or len(tds) < 7:
            continue
        bid = m.group(1)
        pv = re.sub(r"<a .*?</a>", "", tds[1], flags=re.S)   # tlačítko s poznámkou o původci
        parts = [text(x) for x in re.split(r"<br\s*/?>", pv)]
        poz = re.search(r'data-content="([^"]*)"', tds[1])
        obce = re.search(r'data-content="([^"]*)"', tds[5])
        names = re.findall(r"<strong>(.*?)</strong>", html.unescape(obce.group(1))) if obce else []

        def rok(td):   # „1621 - 1679 <br> index - “
            a = [text(x) for x in re.split(r"<br\s*/?>", td)]
            return a[0], (a[1] if len(a) > 1 else "")
        out.append({"id": bid, "kniha": text(tds[0]), "puvodce": parts[0], "typ": parts[1] if len(parts) > 1 else "",
                    "poznamka": text(html.unescape(poz.group(1))) if poz else "",
                    "N": rok(tds[2]), "O": rok(tds[3]), "Z": rok(tds[4]),
                    "obce": names, "obce_plne": text(html.unescape(obce.group(1))) if obce else "",
                    "snimku": text(tds[6])})
    return out


def vypis(r):
    def u(k):
        a, i = r[k]
        return f"{k} {a.replace(' - ', '–')}" + (f" (rejstřík {i.replace(' - ', '–')})" if i.strip(" -") else "")
    obce = r["obce_plne"] or ", ".join(r["obce"])
    print(f"{r['id']} | č. {r['kniha']} | {r['puvodce']} ({r['typ']}) | {u('N')} | {u('O')} | {u('Z')} | "
          f"obcí {len(r['obce'])}: {obce[:260]} | {r['snimku']} snímků")


def vysledky(url, stran):
    nalez, videno = [], set()
    for p in range(1, stran + 1):
        page = get(url + ("" if p == 1 else f"&page={p}"))
        rows = radky(page)
        if p == 1 and not rows and "matrika/detail/" in page:
            sys.exit("Výsledky se nepodařilo přečíst (portál změnil stránku?). Hledej na portálu v prohlížeči.")
        nove = [r for r in rows if r["id"] not in videno]
        if not nove:
            break
        videno |= {r["id"] for r in nove}
        nalez += nove
        if f"page={p + 1}" not in page:
            break
        time.sleep(0.5)
    return nalez


def holy(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(c))


def shoda(r, w):
    """Čtyřmístné číslo = rok uvnitř některého z rozsahů N/O/Z; jinak slovo (bez diakritiky) v textu řádku."""
    if re.fullmatch(r"\d{4}", w):   # i jednoletý rozsah („1850“) a otevřený („1850 -“)
        return any(int(a) <= int(w) <= int(b or (9999 if pom else a)) for k in ("N", "O", "Z")
                   for a, pom, b in re.findall(r"(\d{4})(\s*-\s*(?=\d{4}|$|,))?(?:(\d{4}))?", r[k][0]))
    hodnoty = [r["kniha"], r["puvodce"], r["typ"], r["poznamka"], r["obce_plne"]]
    return holy(w) in holy(" ".join(hodnoty))


def hledat(args, stran):
    if not args:
        sys.exit(__doc__)
    nalez = vysledky(f"{BASE}matrika/hledani_obec?typ=obec&search_by_obec={urllib.parse.quote(args[0])}", stran)
    shody = [r for r in nalez if all(shoda(r, w) for w in args[1:])]
    for r in shody:
        vypis(r)
    if not shody:
        print(f"Nic nenalezeno (prohlédnuto {len(nalez)} knih). Zkus jiný tvar jména (německý, bez přívlastku) nebo méně slov.",
              file=sys.stderr)
    if len(nalez) >= 20 * stran:
        print(f"… možná je výsledků víc (načteno {stran} stran); zúžit jde dalším slovem (farnost, okres, rok) nebo --stran", file=sys.stderr)


def puvodce(nazev, typ, stran=5):
    typy = {t: i for i, t in re.findall(r'<option value="(\d+)"[^>]*>(.*?)</option>',
                                       get(BASE + "matrika/hledani_puvodce"))}
    tid = ""
    if typ:
        shody = [i for t, i in typy.items() if typ.lower() in html.unescape(t).lower()]
        if len(shody) != 1:
            sys.exit(f"Typ původce „{typ}“ neodpovídá právě jednomu z: " + "; ".join(html.unescape(t) for t in typy))
        tid = shody[0]
    url = (f"{BASE}matrika/hledani_puvodce?typ_puvodce_id={tid}&search_by_puvodce={urllib.parse.quote(nazev)}")
    nalez = vysledky(url, stran)
    for r in nalez:
        vypis(r)
    if not nalez:
        print("Nic nenalezeno (původce se hledá podle začátku názvu; zkus kratší název nebo jiný typ).", file=sys.stderr)
    elif len(nalez) >= 20 * stran:
        print(f"… možná je výsledků víc (načteno {stran} stran); zúžit jde typem původce nebo přesnějším názvem, víc dá --stran", file=sys.stderr)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    stran = 5
    if "--stran" in a:
        i = a.index("--stran")
        if i + 1 >= len(a) or not a[i + 1].isdigit() or int(a[i + 1]) < 1:
            sys.exit("--stran chce kladné číslo (kolik stran výsledků načíst).")
        stran = int(a[i + 1])
        del a[i:i + 2]
    if not a:
        sys.exit(__doc__)
    if a[0] == "hledat":
        hledat(a[1:], stran)
    elif a[0] == "puvodce" and len(a) >= 2:
        puvodce(a[1], a[2] if len(a) > 2 else "", stran)
    else:
        sys.exit(__doc__)
