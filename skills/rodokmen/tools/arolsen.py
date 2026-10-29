#!/usr/bin/env python3
"""Arolsen Archives (collections.arolsen-archives.org): vězni a oběti nacismu, nucené práce, vysídlení – bez prohlížeče.

Dachau, Mauthausen, Osvětim (část), Buchenwald, Flossenbürg, Terezín, Gestapo, nuceně nasazení, DP (vysídlené osoby) po válce
a další – přes 30 milionů záznamů o osobách (kartotéky táborů, seznamy transportů, korespondence ITS).

Použití (z kořene projektu):
  arolsen.py hledat "Příjmení Jméno [rok]" [--max N] [--jazyk en|de]
        -> osoby: id | příjmení | jméno | rodné | narozen | místo narození | č. vězně | národnost | část archivu | odkaz
           Slova jsou spojená „a zároveň“ (každé musí být v záznamu); rok narození přidej jako další slovo („Magyar Ferenc 1923“).
           Hledá i hláskové varianty. Max. 1000 záznamů; výchozí výpis N = 40, řazeno podle příjmení.
  arolsen.py karta <id> <vystup.jpg>
        -> stáhne obrázek kartotéční karty / dokumentu (víc obrázků dostane příponu _2, _3…) a vypíše odkaz do archivu
Datum narození v databázi je v pořadí měsíc/den/rok – nástroj ho převádí na „den. měsíc. rok“.
POZOR: shoda jména není ztotožnění. Jména se píší i s chybami (Novák/Nowak/Novak); ověř datum a místo narození na kartě
a v rodině. Údaje o obětech jsou citlivé – na web jen se souhlasem rodiny (soukromi.md). Podmínky užití sbírky jsou na
https://arolsen-archives.org (údaje jen pro osobní, vědecké a genealogické účely). Neprocházej databázi hromadně.
"""
import http.cookiejar, json, os, random, re, string, sys, time, urllib.parse, urllib.request
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

API = "https://collections-server.arolsen-archives.org/ITS-WS.asmx/"
WEB = "https://collections.arolsen-archives.org/"
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))   # server drží dotaz v session
_op.addheaders = [("User-Agent", "Mozilla/5.0 (rodokmen)")]


def post(metoda, data):
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(API + metoda, data=json.dumps(data).encode(),
                                         headers={"Content-Type": "application/json; charset=utf-8", "Origin": WEB.rstrip("/"), "Referer": WEB})
            with _op.open(req, timeout=90) as r:
                return json.load(r)["d"]
        except OSError as e:
            err = e
            if getattr(e, "code", 0) in (400, 403, 404):
                break
            time.sleep(3 * (attempt + 1))
    raise err


def datum(s):
    m = re.fullmatch(r"(\d\d)/(\d\d)/(\d{4})", s or "")
    return f"{int(m.group(2))}. {int(m.group(1))}. {m.group(3)}" if m else (s or "")


def hledat(dotaz, maxn, jazyk):
    uid = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
    post("BuildQueryGlobalForAngular", {"uniqueId": uid, "lang": jazyk, "archiveIds": [], "strSearch": dotaz, "synSearch": True})
    celkem = post("GetCount", {"uniqueId": uid, "lang": jazyk, "searchType": "person", "useFilter": False})
    rows = post("GetPersonList", {"uniqueId": uid, "lang": jazyk, "rowNum": 0, "orderBy": "LastName", "orderType": "asc"})
    for r in rows[:maxn]:
        print(" | ".join([str(r["ObjId"]), r.get("LastName") or "-", r.get("FirstName") or "-", r.get("MaidenName") or "-", datum(r.get("Dob")) or "-",
                          r.get("PlaceBirth") or "-", r.get("PrisonerNumber") or "-", r.get("Nationality") or "-",
                          (r.get("Signature") or "")[:70], f"{WEB}{jazyk}/document/{r['ObjId']}"]))
    if not rows:
        print("Nic nenalezeno (zkus jiný pravopis, jen příjmení, nebo bez roku).", file=sys.stderr)
    elif int(celkem) > len(rows[:maxn]):
        print(f"… celkem {celkem} záznamů, zobrazeno {len(rows[:maxn])}; přidej křestní jméno nebo rok narození",
              file=sys.stderr)


def karta(objid, out):
    if not objid.isdigit():
        sys.exit("id je číslo z prvního sloupce výpisu `hledat`.")
    obrazky = post("GetFileByObj", {"objId": int(objid), "lang": "en"})
    if not obrazky:
        sys.exit("K záznamu není obrázek (jen údaj v kartotéce).")
    base, ext = os.path.splitext(out)
    for i, o in enumerate(obrazky, 1):
        url = o["image"].replace("\\\\", "//").replace("\\", "/")
        if urllib.parse.urlsplit(url).hostname != "collections-server.arolsen-archives.org":
            sys.exit(f"Neočekávaný server obrázku: {url[:80]}")
        cil = out if i == 1 else f"{base}_{i}{ext}"
        os.makedirs(os.path.dirname(os.path.abspath(cil)), exist_ok=True)
        req = urllib.request.Request(url, headers={"Referer": WEB, "User-Agent": "Mozilla/5.0 (rodokmen)"})
        with _op.open(req, timeout=90) as r, open(cil, "wb") as fh:
            fh.write(r.read())
        print(cil, "|", o.get("title", ""), "|", WEB + o.get("relatedLink", ""))
        time.sleep(0.5)


if __name__ == "__main__":
    a = sys.argv[1:]
    maxn, jazyk = 40, "en"
    for volba in ("--max", "--jazyk"):
        if volba in a:
            i = a.index(volba)
            if i + 1 >= len(a) or (volba == "--max" and not (a[i + 1].isdigit() and int(a[i + 1]) >= 1)) \
                    or (volba == "--jazyk" and a[i + 1] not in ("en", "de")):
                sys.exit(f"{volba}: neplatná hodnota (--max kladné číslo, --jazyk en|de).")
            maxn, jazyk = (int(a[i + 1]), jazyk) if volba == "--max" else (maxn, a[i + 1])
            del a[i:i + 2]
    if not a:
        sys.exit(__doc__)
    if a[0] == "hledat" and len(a) == 2 and a[1].strip():
        hledat(a[1], maxn, jazyk)
    elif a[0] == "karta" and len(a) == 3:
        karta(a[1], a[2])
    else:
        sys.exit(__doc__)
