#!/usr/bin/env python3
"""Fronty úkolů (noční a víkendový režim): úkoly na noc, k rozhodnutí, k bádání, archivní dotazy, otázky pro rodinu.

Použití (z kořene projektu): python3 -I tools/fronta.py <příkaz> …
  seznam [fronta]                         vypíše úkoly (fronta: noc | rozhodnuti | badani | dotazy | rodina)
  pridej <fronta> --text T [--p P1] [--os 57,114] [--typ krest] [--cil krest:115] [--rodic U-0001] [--stav otevřeno]
                  [--zavisi U-0001,U-0002]
                                          nový úkol; tentýž úkol ve stejné frontě (shodný cíl, nebo stejný typ a stejné
                                          osoby) se NEZALOŽÍ, ale doplní (text, vyšší priorita); --nove sloučení zakáže
                                          u fronty rozhodnuti povinně --otazka T --moznosti "A) …; B) …" --vychozi T (a doporučeně --dukazy,
                                          --zkuseno, --doporuceni); bez nich se úkol odmítne (reference/nocni_rezim.md)
  smeruj <id> --do <fronta> --dod "…" [--cena S|M|L|XL] [--p P1]   router: úkol ze vstupu do cílové fronty (DOD povinná)
  rozdel <id> --cast FRONTA "text" "DOD" [os=1,2] [typ=…] [cena=S] [--cast …]   rozdělí úkol na části; má-li rodič víc osob, každá část
                                          uvede své (os=…), mlčky se nedědí
  zaparkuj <id> --do RRRR-MM-DD [--duvod T]                           stav:čeká do data
  selhani <id> --druh prechodna|zakaz --portal P [--kdy "RRRR-MM-DD HH:MM"]   opakování podle rezim.json, pak rozhodnutí za portál
  hotovo <id> [--denik 12,13] [--soubory a,b] [--spotreba S|M|L|XL] [--poznamka T]   zapíše do historie, co úkol vyřešilo
  historie [<id>]                                                     události úkolu (i dětí po rozdělení) z data/ukoly_historie.jsonl
  znovu --starsi-nez <verze> [--vysledek nečitelné,nenalezeno] [--zaloz]   neúspěšná čtení v deníku staršího nástroje; --zaloz založí úkoly
  plan [fronta]                                                       plán okna: pořadí, kumulativní váha, co je mimo rozpočet nebo čeká na schválení
  kalibrace                                                           odhady cen při směrování × skutečná spotřeba z historie
  cekajici [fronta]                                                   čekající úkoly seřazené podle data s důvodem (seznam je jen počítá; seznam --vse ukáže všechny)
  odeslano <id> --uzivatel "kdo" [--odpoved-do RRRR-MM-DD]            dotaz nebo otázka pro rodinu odeslána (jen na pokyn uživatele): stav čeká do odpovědi
  uprav <id> [--p P2] [--text T] [--stav odloženo] [--os …] [--cil …] [--zavisi …] [--pridat-text T] [--cena S] [--dod "…"]
  hotovo <id> | hotovo --cil krest:115    úkol smaže (jeho výsledek je v datech nebo v následných úkolech)
  presun <id> <fronta>                    přesune úkol do jiné fronty
  trid                                    setřídí všechny fronty (priorita, id)
  frontier [fronta]                       úkoly, jejichž závislosti (zavisi) jsou hotové – lze je přidělit
  prejmenuj                               přejmenuje staré soubory front (archivni_dotazy.md, otazky_pro_rodinu.md)
                                          na ukoly_dotazy_na_archivy.md a ukoly_na_rodinu.md
  kontrola                                formát hlaviček, duplicity, úkoly s už splněným cílem (v datech)
  rezim [--kdy "2026-11-12 23:50"]        aktuální režim (pracovni | noc | vikend) a konec okna
  dalsi <fronta> [--typ T]                další úkol ke zpracování (jen mimo pracovní dobu nebo s --vzdy); hlídá zámek
  zamek start <typ> | stop | stav         brzda: v jednom běhu buď bádání, nebo úprava skillu (nikdy obojí)

Úkol v souboru: hlavička `## U-0412 | P1 | os:57,114 | typ:křest | cíl:krest:115 | rodič:U-0398 | stav:otevřeno`
a pod ní volný text. Priorita P1 = odemyká chybějícího předka, P2 = mění „prob“ na „doc“, P3 = ověřuje rodinný údaj.
Pravidla: reference/nocni_rezim.md.
"""
import argparse
import datetime
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FRONTY = {"vstup": "ukoly_vstup.md", "noc": "ukoly_na_noc.md", "rozhodnuti": "ukoly_k_rozhodnuti.md", "badani": "ukoly_k_badani.md",
          "dotazy": "ukoly_dotazy_na_archivy.md", "rodina": "ukoly_na_rodinu.md"}
CENY = ("S", "M", "L", "XL")        # pásma ceny úkolu (rozpočet na noc, analyza/navrh-router-uloh.md kap. 5)
REZIMY_BEHU = ("noc", "vikend", "pracovni")
# Do 0.10.1-fork.2 se tyto dvě fronty jmenovaly takto. Dokud nový soubor neexistuje, čte a zapisuje se starý (prejmenuj to převede).
STARE_NAZVY = {"dotazy": "archivni_dotazy.md", "rodina": "otazky_pro_rodinu.md"}
# Soubory ukoly_* jsou vnitřní: export webu je nikdy nečte (ADR 0003). Veřejný text je v data/verejne_otazky.json (tools/otazky.py).
HLAVICKA = re.compile(r"^##+ (U-\d+)\s*\|(.*)$")
STAVY = ("otevřeno", "odloženo", "probíhá", "čeká")
TYPY_RUN = {"bádání": "badani", "skill": "skill", "test": "skill", "údržba": "skill"}   # typ úkolu → druh běhu (brzda)
VYCHOZI_REZIM = {"odpoved_dnu": 30, "pracovni_dny": [1, 2, 3, 4, 5], "pracovni_od": "06:00", "pracovni_do": "22:00", "svatky": [],
                 "pomocniku": 2, "dod": {},
                 # po přechodné chybě portálu: nejdřív za dvě noci, pak o víkendu, pak přes den; pak jedno rozhodnutí za portál
                 "opakovani": [{"rezim": "noc", "odstup_dnu": 2}, {"rezim": "vikend"}, {"rezim": "pracovni"}],
                 # rozpočet okna v pásmech ceny (váhy jsou odhad, kalibruje je `fronta.py kalibrace`); úkol od pásma `prah` výš potřebuje schválení člověka
                 "rozpocet": {"vahy": {"S": 1, "M": 3, "L": 8, "XL": 20}, "okno": {"noc": 24, "vikend": 60}, "prah": "XL"}}


# Úkol k rozhodnutí (reference/nocni_rezim.md, analyza/navrh-router-uloh.md kap. 2): rozhoduje člověk, ne stroj. Proto musí mít otázku, možnosti
# a výchozí postup (co se stane, když uživatel neodpoví); důkazy, co se zkusilo a doporučení se doporučují.
POVINNA_ROZHODNUTI = ("Otázka", "Možnosti", "Výchozí postup")
POLE_ROZHODNUTI = (("otazka", "Otázka"), ("moznosti", "Možnosti"), ("dukazy", "Důkazy"), ("zkuseno", "Zkoušeno"),
                   ("doporuceni", "Doporučení"), ("vychozi", "Výchozí postup"))
ZRUSENE_TYPY = ("skill", "test", "údržba")   # úkoly na úpravu skillu se ve frontách nevedou (S-010)
ZPRAVA_TYP = ("typ „{t}“ se ve frontách nevede: úkoly pro skill patří do data/poznamky_pro_skill.md (projekt) nebo do analyza/ukoly_na_skill.md "
              "(repozitář skillu)")
POLE_RADEK = re.compile(r"^\s*(Otázka|Možnosti|Důkazy|Zkoušeno|Doporučení|Výchozí postup)\s*:\s*(.*\S)\s*$")
PRACE = re.compile(r"^\s*(?:ověřit|zkontrolovat|porovnat|přečíst|potvrdit|prověřit|dohledat|zjistit)\b", re.I)


def pole_rozhodnuti(text):
    """{název pole: hodnota} z řádků „Otázka: …“ v textu úkolu."""
    out = {}
    for radek in (text or "").splitlines():
        m = POLE_RADEK.match(radek)
        if m:
            out.setdefault(m.group(1), m.group(2))
    return out


def chyby_rozhodnuti(text):
    """Seznam chybějících nebo špatných povinných polí úkolu k rozhodnutí (prázdný = v pořádku)."""
    pole, chyby = pole_rozhodnuti(text), []
    for p in POVINNA_ROZHODNUTI:
        if p not in pole:
            chyby.append(f"chybí pole „{p}“")
    if "Možnosti" in pole and len([x for x in re.split(r"\s*;\s*", pole["Možnosti"]) if x.strip()]) < 2:
        chyby.append("Možnosti: aspoň dvě, oddělené středníkem (A) …; B) …)")
    return chyby


def vypada_jako_prace(text):
    """Otázka začíná slovesem práce (ověřit, zkontrolovat, porovnat…): pravděpodobně to není rozhodnutí člověka."""
    prvni = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return bool(PRACE.match(pole_rozhodnuti(text).get("Otázka") or prvni))


def text_rozhodnuti(a):
    """Text úkolu z přepínačů --otazka, --moznosti … (jinak None)."""
    radky = [f"{nazev}: {getattr(a, attr)}" for attr, nazev in POLE_ROZHODNUTI if getattr(a, attr, None)]
    return "\n".join(radky) if radky else None


def vyzaduj_rozhodnuti(text):
    chyby = chyby_rozhodnuti(text)
    if chyby:
        sys.exit("ODMÍTNUTO: úkol k rozhodnutí potřebuje otázku, možnosti a výchozí postup (" + "; ".join(chyby) + "). "
                 "fronta.py pridej rozhodnuti --otazka … --moznosti \"A) …; B) …\" --vychozi … [--dukazy … --zkuseno … --doporuceni …]. "
                 "Věc, kterou jde vyřešit čtením nebo porovnáním dat, patří do fronty noc, badani nebo dotazy (reference/nocni_rezim.md).")
    if vypada_jako_prace(text):
        print("pozor: otázka vypadá jako práce (ověřit, zkontrolovat, porovnat…), ne jako rozhodnutí člověka – patří do noc, badani nebo dotazy?")


def cesta(f):
    nova = os.path.join(DATA, FRONTY[f])
    stara = os.path.join(DATA, STARE_NAZVY[f]) if f in STARE_NAZVY else None
    if stara and not os.path.exists(nova) and os.path.exists(stara):
        return stara
    return nova


def bez_diakritiky(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower()


class Ukol:
    def __init__(self, id_, p="P2", os_=None, typ="", cil="", rodic="", stav="otevřeno", text="", zavisi=None):
        self.id, self.p, self.os, self.typ, self.cil, self.rodic, self.stav, self.text = id_, p, list(os_ or []), typ, cil, rodic, stav, text
        self.zavisi = list(zavisi or [])
        self.cena, self.do, self.kdy, self.pokusu = "", "", "", 0   # router: pásmo ceny, čekání do data, režim běhu, počet selhání

    def hlavicka(self):
        pole = [self.id, self.p]
        if self.os:
            pole.append("os:" + ",".join(self.os))
        for k, v in (("typ", self.typ), ("cíl", self.cil), ("rodič", self.rodic), ("zavisi", ",".join(self.zavisi)), ("cena", self.cena),
                     ("kdy", self.kdy), ("do", self.do), ("pokusu", str(self.pokusu) if self.pokusu else "")):
            if v:
                pole.append(f"{k}:{v}")
        pole.append(f"stav:{self.stav}")
        return "## " + " | ".join(pole)

    def radky(self):
        return [self.hlavicka(), ""] + self.text.strip("\n").split("\n") + [""]


def parse_hlavicka(radek):
    m = HLAVICKA.match(radek)
    if not m:
        return None
    pole = [x.strip() for x in m.group(2).split("|")]
    u = Ukol(m.group(1))
    for x in pole:
        if re.fullmatch(r"P[1-9]", x):
            u.p = x
        elif ":" in x:
            k, v = x.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "os":
                u.os = [a for a in re.split(r"[,\s]+", v) if a]
            elif k == "typ":
                u.typ = v
            elif k in ("cíl", "cil"):
                u.cil = v
            elif k in ("rodič", "rodic"):
                u.rodic = v
            elif k in ("zavisi", "závisí"):
                u.zavisi = [a for a in re.split(r"[,\s]+", v) if a]
            elif k == "stav":
                u.stav = v
            elif k == "cena":
                u.cena = v
            elif k == "kdy":
                u.kdy = v
            elif k == "do":
                u.do = v
            elif k == "pokusu" and v.isdigit():
                u.pokusu = int(v)
    return u


def nacti(f):
    """(úvod, [Ukol]) – úvod = vše před prvním úkolem."""
    p = cesta(f)
    if not os.path.exists(p):
        return "", []
    radky = open(p, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    uvod, ukoly, akt = [], [], None
    for r in radky:
        u = parse_hlavicka(r)
        if u:
            akt = u
            ukoly.append(u)
            akt._t = []
        elif akt is not None:
            akt._t.append(r)
        else:
            uvod.append(r)
    for u in ukoly:
        u.text = "\n".join(u._t).strip("\n")
        del u._t
    return "\n".join(uvod).rstrip("\n"), ukoly


def uloz(f, uvod, ukoly):
    ukoly = sorted(ukoly, key=lambda u: (u.p, CENY.index(u.cena) + 1 if u.cena in CENY else 0, int(u.id[2:])))   # priorita, cena (levné napřed)
    r = ([uvod.rstrip("\n"), ""] if uvod.strip() else [])
    for u in ukoly:
        r += u.radky()
    t = "\n".join(r).rstrip("\n") + "\n"
    with open(cesta(f), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t)


def vse():
    return {f: nacti(f) for f in FRONTY if os.path.exists(cesta(f))}


def nejvyssi_id(data):
    """Nejvyšší dosud použité číslo úkolu: ve frontách i v historii (smazaný úkol svoje ID neuvolní, aby šla historie sledovat)."""
    n = max([int(u.id[2:]) for _, uk in data.values() for u in uk] + [0])
    for e in nacti_historii():
        for x in [e.get("id", "")] + [d.get("id", "") for d in e.get("deti", [])]:
            m = re.fullmatch(r"U-(\d+)", str(x))
            if m:
                n = max(n, int(m.group(1)))
    return n


def dalsi_id(data):
    return f"U-{nejvyssi_id(data) + 1:04d}"


def pripraveny(u, dnes):
    """Otevřený úkol, nebo čekající, kterému už uplynulo datum `do` (zaparkovaný úkol se tak sám vrátí)."""
    return u.stav == "otevřeno" or (u.stav == "čeká" and (not u.do or u.do <= dnes.isoformat()))


def frontier(data, dnes=None):
    """Úkoly připravené k přidělení, jejichž závislosti jsou hotové: závislost na úkolu, který už v žádné frontě není, je splněná
    (hotové úkoly se mažou)."""
    dnes = dnes or datetime.date.today()
    existuji = {u.id for _, uk in data.values() for u in uk}
    return [u for _, uk in data.values() for u in uk if pripraveny(u, dnes) and not (set(u.zavisi) & existuji)]


def stejny(a, b):
    """Tentýž úkol: shodný cíl, nebo (bez cíle u obou) stejný typ a přesně stejné osoby. Pouhý překryv osob nestačí: dva úkoly
    o téže osobě mívají jiný záměr (běh 15. 11. 2026 tak sloučil noční čtení do dotazů na archiv)."""
    if a.rodic and a.rodic == b.rodic:   # části téhož rozděleného úkolu jsou z definice různé úkoly (osoby zdědily po rodiči)
        return False
    if a.cil or b.cil:
        return bool(a.cil) and a.cil == b.cil
    return bool(a.typ) and a.typ == b.typ and bool(a.os) and set(a.os) == set(b.os)


def sluc(stary, novy):
    stary.os = list(dict.fromkeys(stary.os + novy.os))
    stary.p = min(stary.p, novy.p)
    stary.cil = stary.cil or novy.cil
    if novy.text.strip() and bez_diakritiky(novy.text.strip()) not in bez_diakritiky(stary.text):
        stary.text = (stary.text + "\n\n" + novy.text.strip()).strip("\n")


# ---------- režim podle času ----------
def nacti_rezim():
    p = os.path.join(DATA, "rezim.json")
    r = dict(VYCHOZI_REZIM)
    if os.path.exists(p):
        r.update(json.load(open(p, encoding="utf-8-sig")))
    return r


def _cas(s):
    h, m = s.split(":")
    return datetime.time(int(h), int(m))


def je_volno(d, r):
    return d.isoweekday() not in r["pracovni_dny"] or d.isoformat() in r.get("svatky", [])


def rezim_v(now, r):
    """(režim, konec okna): režim = pracovni | noc | vikend (i svátek); konec okna = začátek další pracovní doby (None v pracovní)."""
    od, do = _cas(r["pracovni_od"]), _cas(r["pracovni_do"])
    if not je_volno(now.date(), r) and od <= now.time() < do:
        return "pracovni", None
    d = now.date() if (not je_volno(now.date(), r) and now.time() < od) else now.date() + datetime.timedelta(days=1)
    while je_volno(d, r):
        d += datetime.timedelta(days=1)
    konec = datetime.datetime.combine(d, od)
    return ("vikend" if konec - now > datetime.timedelta(hours=10) else "noc"), konec   # víkend i svátek = dlouhé okno


def zamek_cesta():
    return os.path.join(DATA, ".beh.json")


def cti_zamek():
    p = zamek_cesta()
    if not os.path.exists(p):
        return None
    z = json.load(open(p, encoding="utf-8"))
    try:
        if datetime.datetime.fromisoformat(z.get("do", "9999-12-31T00:00:00")) < datetime.datetime.now():
            return None   # zámek vypršel s oknem
    except ValueError:
        pass
    return z


# ---------- rozpočet okna (analyza/navrh-router-uloh.md kap. 5) ----------
def rozpocet_cfg(r):
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in VYCHOZI_REZIM["rozpocet"].items()}
    for k, v in (r.get("rozpocet") or {}).items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


def cena_vaha(u, cfg):
    return cfg["vahy"].get(u.cena or "M", cfg["vahy"].get("M", 3))


def schvaleno(u):
    return "Schváleno:" in u.text


def vyzaduje_schvaleni(u, cfg):
    """Úkol v pásmu ceny od prahu výš (výchozí XL) smí běžet jen po schválení člověkem (řádek „Schváleno: …“ v textu)."""
    return bool(u.cena in CENY and cfg.get("prah") in CENY and CENY.index(u.cena) >= CENY.index(cfg["prah"]) and not schvaleno(u))


def spotreba_cesta():
    return os.path.join(DATA, ".rozpocet.json")


def cti_spotrebu(okno):
    """Spotřeba rozpočtu v daném okně (nové okno = od nuly)."""
    try:
        with open(spotreba_cesta(), encoding="utf-8") as f:
            z = json.load(f)
        return int(z["spotreba"]) if z.get("okno") == okno else 0
    except (OSError, ValueError, KeyError):
        return 0


def zapis_spotrebu(okno, spotreba):
    with open(spotreba_cesta(), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"okno": okno, "spotreba": spotreba}, f)


def vybirej(data, fronta_, now, r, vzdy=False, typ=None):
    """Úkoly fronty v pořadí, v jakém je `dalsi` přidělí: [(Ukol, stav)], stav = ok | schvaleni | rezim (mimo režim úkolu)."""
    m, _ = rezim_v(now, r)
    cfg = rozpocet_cfg(r)
    pripraveno = {id(u) for u in frontier(data, now.date())}
    out = []
    for u in data[fronta_][1]:
        if (typ and u.typ != typ) or id(u) not in pripraveno:
            continue
        if u.kdy:
            if u.kdy != m:
                continue
        elif m == "pracovni" and not vzdy:
            continue
        out.append((u, "schvaleni" if vyzaduje_schvaleni(u, cfg) else "ok"))
    return out


# ---------- historie úkolů (data/ukoly_historie.jsonl, jen přidávání; analyza/navrh-router-uloh.md kap. 6.1) ----------
def historie_cesta():
    return os.path.join(DATA, "ukoly_historie.jsonl")


def prvni_radek(text, n=120):
    r = (text or "").strip().splitlines()
    return r[0][:n] if r else ""


def zapis_udalost(udalost, id_, **kw):
    """Připíše událost úkolu (vznik, doplneno, smerovani, deleni, parkovani, selhani, presun, hotovo). Hotový úkol se z fronty maže, stopa zůstává."""
    z = {"cas": datetime.datetime.now().isoformat(timespec="seconds"), "udalost": udalost, "id": id_}
    z.update({k: v for k, v in kw.items() if v not in (None, "", [])})
    os.makedirs(DATA, exist_ok=True)
    with open(historie_cesta(), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(z, ensure_ascii=False) + "\n")


def nacti_historii():
    p = historie_cesta()
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for r in f:
            if r.strip():
                try:
                    out.append(json.loads(r))
                except ValueError:
                    pass
    return out


def verze_tuple(s):
    """„0.10.1-fork.1“ → (0, 10, 1, 1); porovnání verzí nástroje."""
    return tuple(int(x) for x in re.findall(r"\d+", s or ""))


def znovu(data, vysledky, starsi, zalozit):
    """Neúspěšná čtení v deníku (aktivní, ne nahrazená opravou), jejichž nástroj je starší než `starsi` (nebo neznámý). Volitelně založí úkoly."""
    p = os.path.join(DATA, "denik.jsonl")
    if not os.path.exists(p):
        print("data/denik.jsonl neexistuje")
        return 1
    radky = []
    with open(p, encoding="utf-8") as f:
        for r in f:
            if r.strip():
                try:
                    radky.append(json.loads(r))
                except ValueError:
                    pass
    nahrazene = {z.get("opravuje") for z in radky if z.get("opravuje") is not None}
    hranice = verze_tuple(starsi)
    texty = " ".join(u.text for _, uk in data.values() for u in uk)
    cil = "vstup" if os.path.exists(cesta("vstup")) else "noc"
    nalezeno = zalozeno = 0
    for z in sorted(radky, key=lambda x: x.get("id", 0)):
        if z.get("id") in nahrazene or z.get("k_rucni_kontrole") or z.get("vysledek") not in vysledky:
            continue
        if z.get("nastroj") and verze_tuple(z["nastroj"]) >= hranice:
            continue
        nalezeno += 1
        print(f"deník {z['id']}: {z['vysledek']} – {str(z.get('hledano', ''))[:80]} ({z.get('nastroj') or 'nástroj neznámý'})")
        if zalozit and f"(deník {z['id']})" not in texty:
            text = (f"Přečíst znovu (deník {z['id']}): {z.get('hledano', '')}. Původní výsledek {z['vysledek']} "
                    f"({z.get('nastroj') or 'nástroj neznámý'}). Zdroj: {(z.get('zdroj') or {}).get('text', '')}.")
            novy = Ukol(nova_id(data, zalozeno), "P3", [str(x) for x in z.get("osoby", [])], "bádání", "", "", "otevřeno", text)
            uv, uk = data[cil]
            uk.append(novy)
            data[cil] = (uv, uk)
            uloz(cil, uv or "", uk)
            zapis_udalost("vznik", novy.id, fronta=cil, text=prvni_radek(text), duvod="znovu", denik=[z["id"]])
            zalozeno += 1
    print(f"nalezeno {nalezeno} čtení" + (f", založeno {zalozeno} úkolů ({cil})" if zalozit else " (--zaloz je založí)"))
    return 0


# ---------- router: směrování, dělení, parkování, selhání portálu (analyza/navrh-router-uloh.md) ----------
def nastav_dod(u, dod):
    """Definice hotového jako řádek textu úkolu (nahradí předchozí)."""
    radky = [r for r in u.text.splitlines() if not r.startswith("Definice hotového:")]
    u.text = "\n".join(radky + [f"Definice hotového: {dod.strip()}"]).strip("\n")


def nova_id(data, n=0):
    return f"U-{nejvyssi_id(data) + 1 + n:04d}"


def den_po(od, r, volny):
    """První den po `od`, který je volný (víkend, svátek) nebo pracovní."""
    d = od + datetime.timedelta(days=1)
    while je_volno(d, r) != volny:
        d += datetime.timedelta(days=1)
    return d


def rozhodnuti_za_portal(data, portal, u, druh, pokusu):
    """Jedno společné rozhodnutí za portál: počkat, nebo přeřadit čekající úkoly do ručního bádání. Další úkol téhož portálu se připojí."""
    uv, uk = data["rozhodnuti"]
    cil = f"portal:{portal}"
    r = next((x for x in uk if x.cil == cil), None)
    ids = {u.id}
    if r:
        ids |= set(re.findall(r"U-\d+", pole_rozhodnuti(r.text).get("Důkazy", "")))
    seznam = ", ".join(sorted(ids))
    doporuceni = "B (zákaz nebo zablokování portálu se opakováním neopraví)" if druh == "zakaz" else "A (výpadek bývá přechodný)"
    text = (f"Otázka: Portál {portal} nejde číst automaticky ({'zákaz nebo zablokování' if druh == 'zakaz' else 'opakované selhání'}); "
            f"čekají úkoly {seznam}. Počkat, nebo přeřadit do ručního bádání?\n"
            f"Možnosti: A) počkat a zkusit automat později; B) přeřadit čekající úkoly do ručního bádání\n"
            f"Důkazy: úkoly {seznam}\n"
            f"Zkoušeno: {druh}, pokusů {pokusu}\n"
            f"Doporučení: {doporuceni}\n"
            f"Výchozí postup: úkoly zůstanou čekat na toto rozhodnutí, nic se automaticky nezkouší")
    if r:
        r.text = text
    else:
        r = Ukol(nova_id(data), "P2", [], "portal", cil, "", "otevřeno", text)
        uk.append(r)
    data["rozhodnuti"] = (uv, uk)
    if r.id not in u.zavisi:
        u.zavisi.append(r.id)
    u.stav, u.kdy, u.do = "otevřeno", "", ""
    return r


def po_selhani(data, u, druh, portal, now, r):
    """Přechodná chyba: čekání podle `opakovani` (noc → víkend → pracovní doba); po vyčerpání nebo při zákazu rozhodnutí za portál."""
    kroky = r.get("opakovani") or VYCHOZI_REZIM["opakovani"]
    if druh == "zakaz":
        return rozhodnuti_za_portal(data, portal, u, druh, u.pokusu)
    u.pokusu += 1
    if u.pokusu > len(kroky):
        return rozhodnuti_za_portal(data, portal, u, druh, u.pokusu)
    krok = kroky[u.pokusu - 1]
    rez = krok.get("rezim", "noc")
    dnes = now.date()
    if rez == "vikend":
        d = den_po(dnes, r, True)
    elif rez == "pracovni":
        d = den_po(dnes, r, False)
    else:
        d = dnes + datetime.timedelta(days=max(2, int(krok.get("odstup_dnu", 2))))   # aspoň každou druhou noc
    u.stav, u.kdy, u.do = "čeká", rez, d.isoformat()
    return None


# ---------- kontrola ----------
def cil_splnen(cil):
    """krest:<k> / umrti:<k> / snatek:<k> – osoba k má v osoby.py fakt s datem; jinak None (neumím ověřit)."""
    m = re.fullmatch(r"(krest|umrti|snatek):(\d+)", cil or "")
    p = os.path.join(DATA, "osoby.py")
    if not m or not os.path.exists(p):
        return None
    ns = {}
    try:
        exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    except Exception:
        return None
    o = ns.get("P", {}).get(int(m.group(2)))
    if not o:
        return False
    znak = {"krest": r"\*", "umrti": r"†", "snatek": r"×"}[m.group(1)]
    return any(re.match(rf"^{znak}\s*\d{{1,2}}\. ?\d{{1,2}}\. ?\d{{4}}", f) for f in o.get("f", []))


def kontrola():
    data, chyby, upoz = vse(), [], []
    vsechny = [(f, u) for f, (_, uk) in data.items() for u in uk]
    ids = {}
    for f, u in vsechny:
        if u.id in ids:
            chyby.append(f"{u.id}: id je ve frontě {ids[u.id]} i {f}")
        ids[u.id] = f
        if u.stav not in STAVY:
            chyby.append(f"{u.id} ({f}): neznámý stav „{u.stav}“")
        if not u.text.strip():
            upoz.append(f"{u.id} ({f}): úkol bez textu")
        if u.rodic and u.rodic not in ids and u.rodic not in {x.id for _, x in vsechny}:
            upoz.append(f"{u.id} ({f}): rodič {u.rodic} už neexistuje (v pořádku, byl splněn)")
    zavisi = {u.id: set(u.zavisi) for _, u in vsechny}
    for f, u in vsechny:
        if u.id in u.zavisi:
            chyby.append(f"{u.id} ({f}): závisí sám na sobě")
        else:   # cyklus: z úkolu se po závislostech dostanu zpátky
            videno, hrana = set(), list(u.zavisi)
            while hrana:
                x = hrana.pop()
                if x == u.id:
                    chyby.append(f"{u.id} ({f}): závislosti tvoří cyklus")
                    break
                if x not in videno:
                    videno.add(x)
                    hrana += list(zavisi.get(x, ()))
    for i, (f1, a) in enumerate(vsechny):
        for f2, b in vsechny[i + 1:]:
            if stejny(a, b):
                upoz.append(f"{a.id} ({f1}) a {b.id} ({f2}) se překrývají – sluč: fronta.py pridej (doplní) nebo hotovo")
    for f, u in vsechny:
        if u.typ in ZRUSENE_TYPY:
            upoz.append(f"{u.id} ({f}): typ {u.typ} se ve frontách nevede – přesuň do data/poznamky_pro_skill.md nebo analyza/ukoly_na_skill.md a `fronta.py hotovo {u.id}`")
        if f == "rozhodnuti":
            ch = chyby_rozhodnuti(u.text)
            if ch:
                upoz.append(f"{u.id} (rozhodnuti): úkol nemá povinná pole ({'; '.join(ch)}) – doplň otázku, možnosti a výchozí postup")
            elif vypada_jako_prace(u.text):
                upoz.append(f"{u.id} (rozhodnuti): otázka začíná slovesem práce – není rozhodnutí člověka? (noc, badani nebo dotazy)")
    for f, u in vsechny:
        if u.cil and cil_splnen(u.cil):
            upoz.append(f"{u.id} ({f}): cíl {u.cil} už je v datech splněn – `fronta.py hotovo {u.id}`")
    for ch in chyby:
        print("CHYBA:", ch)
    for up in upoz:
        print("upozornění:", up)
    print(f"fronty: {sum(len(uk) for _, uk in data.values())} úkolů v {len(data)} souborech, {len(chyby)} chyb, {len(upoz)} upozornění")
    return 1 if chyby else 0


# ---------- příkazy ----------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("seznam"); s.add_argument("fronta", nargs="?", choices=list(FRONTY)); s.add_argument("--vse", action="store_true")
    s = sp.add_parser("cekajici"); s.add_argument("fronta", nargs="?", choices=list(FRONTY))
    s = sp.add_parser("odeslano"); s.add_argument("id"); s.add_argument("--uzivatel"); s.add_argument("--odpoved-do", dest="odpoved_do")
    s = sp.add_parser("pridej"); s.add_argument("fronta", choices=list(FRONTY))
    for a in ("--text", "--p", "--os", "--typ", "--cil", "--rodic", "--stav", "--zavisi", "--otazka", "--moznosti", "--dukazy", "--zkuseno",
              "--doporuceni", "--vychozi"):
        s.add_argument(a)
    s.add_argument("--nove", action="store_true")   # nesloučit s podobným úkolem, založit vždy nový
    s = sp.add_parser("uprav"); s.add_argument("id")
    for a in ("--text", "--p", "--os", "--typ", "--cil", "--rodic", "--stav", "--zavisi", "--pridat-text", "--cena", "--dod"):
        s.add_argument(a)
    s = sp.add_parser("frontier"); s.add_argument("fronta", nargs="?", choices=list(FRONTY))
    sp.add_parser("prejmenuj")
    s = sp.add_parser("hotovo"); s.add_argument("id", nargs="?"); s.add_argument("--cil")
    for a_ in ("--denik", "--soubory", "--spotreba", "--poznamka"):
        s.add_argument(a_)   # co úkol vyřešilo (řádky deníku, soubory), skutečná cena S|M|L|XL; zapíše se do historie
    s = sp.add_parser("historie"); s.add_argument("id", nargs="?")
    s = sp.add_parser("znovu"); s.add_argument("--vysledek", default="nečitelné,nenalezeno"); s.add_argument("--starsi-nez", dest="starsi", required=True)
    s.add_argument("--zaloz", action="store_true")
    s = sp.add_parser("presun"); s.add_argument("id"); s.add_argument("fronta", choices=list(FRONTY))
    sp.add_parser("trid")
    sp.add_parser("kontrola")
    s = sp.add_parser("rezim"); s.add_argument("--kdy")
    s = sp.add_parser("dalsi"); s.add_argument("fronta", choices=list(FRONTY)); s.add_argument("--typ"); s.add_argument("--vzdy", action="store_true")
    s.add_argument("--kdy")   # jen pro zkoušku: „2026-11-16 23:00“ místo aktuálního času
    s = sp.add_parser("plan"); s.add_argument("fronta", nargs="?", choices=list(FRONTY)); s.add_argument("--kdy"); s.add_argument("--vzdy", action="store_true")
    sp.add_parser("kalibrace")
    s = sp.add_parser("smeruj"); s.add_argument("id"); s.add_argument("--do", required=True); s.add_argument("--dod")
    s.add_argument("--cena"); s.add_argument("--p"); s.add_argument("--schvaleno", action="store_true")
    s.add_argument("--nove", action="store_true")
    s = sp.add_parser("rozdel"); s.add_argument("id")
    s.add_argument("--cast", nargs="+", action="append", metavar="ČÁST", required=True)
    s = sp.add_parser("zaparkuj"); s.add_argument("id"); s.add_argument("--do", required=True); s.add_argument("--duvod")
    s = sp.add_parser("selhani"); s.add_argument("id"); s.add_argument("--druh", choices=("prechodna", "zakaz"), required=True)
    s.add_argument("--portal", required=True); s.add_argument("--kdy")
    s = sp.add_parser("zamek"); s.add_argument("akce", choices=("start", "stop", "stav")); s.add_argument("typ", nargs="?", choices=("badani", "skill"))
    a = ap.parse_args(argv)

    if a.cmd == "kontrola":
        return kontrola()
    if a.cmd == "prejmenuj":
        zmeneno = 0
        for f, stary in STARE_NAZVY.items():
            sp_, np_ = os.path.join(DATA, stary), os.path.join(DATA, FRONTY[f])
            if os.path.exists(sp_):
                if os.path.exists(np_):
                    sys.exit(f"Nepřejmenováno: existuje {FRONTY[f]} i {stary}. Sluč je ručně a starý soubor smaž.")
                os.replace(sp_, np_)
                print(f"{stary} -> {FRONTY[f]}")
                zmeneno += 1
        print("přejmenováno" if zmeneno else "není co přejmenovat")
        return 0
    if a.cmd == "rezim":
        now = datetime.datetime.fromisoformat(a.kdy) if a.kdy else datetime.datetime.now()
        r = nacti_rezim()
        m, konec = rezim_v(now, r)
        print(f"{m}" + (f" – konec okna {konec:%Y-%m-%d %H:%M}" if konec else " – interaktivní: po doběhu vyhodnotit a čekat na instrukci")
              + f"; pomocníků max {r['pomocniku']}")
        return 0
    if a.cmd == "zamek":
        if a.akce == "stav":
            z = cti_zamek()
            print(json.dumps(z, ensure_ascii=False) if z else "bez zámku")
        elif a.akce == "start":
            if not a.typ:
                sys.exit("zamek start badani|skill")
            z = cti_zamek()
            if z and z["typ"] != a.typ:
                sys.exit(f"ODMÍTNUTO: běží {z['typ']} (od {z['od']}) – bádání a úprava skillu se nekombinují")
            _, konec = rezim_v(datetime.datetime.now(), nacti_rezim())
            json.dump({"typ": a.typ, "od": datetime.datetime.now().isoformat(timespec="minutes"),
                       "do": (konec or datetime.datetime.now() + datetime.timedelta(hours=8)).isoformat(timespec="minutes")},
                      open(zamek_cesta(), "w", encoding="utf-8"), ensure_ascii=False)
            print("zámek:", a.typ)
        else:
            if os.path.exists(zamek_cesta()):
                os.remove(zamek_cesta())
            print("zámek uvolněn")
        return 0

    data = vse()
    for f in FRONTY:
        data.setdefault(f, ("", []))
    if a.cmd == "seznam":
        dnes, ceka = datetime.date.today(), 0
        for f in ([a.fronta] if a.fronta else FRONTY):
            for u in data[f][1]:
                if not a.vse and u.stav == "čeká" and not pripraveny(u, dnes):   # čekající mimo úkoly k řešení (viz `cekajici`)
                    ceka += 1
                    continue
                print(f"{f:10} {u.hlavicka()[3:]}  {u.text.strip().splitlines()[0][:90] if u.text.strip() else ''}")
        if ceka:
            print(f"(čeká {ceka} úkolů do data – přehled: fronta.py cekajici; všechny: seznam --vse)")
        return 0
    if a.cmd == "cekajici":
        dnes = datetime.date.today()
        radky = []
        for f in ([a.fronta] if a.fronta else FRONTY):
            for u in data[f][1]:
                if u.stav == "čeká" and not pripraveny(u, dnes):
                    duvod = next((r for r in reversed(u.text.splitlines()) if r.startswith(("Čeká do", "Odesláno:"))), "")
                    radky.append((u.do, f"{u.do}  {u.id} ({f})  {prvni_radek(u.text, 70)}" + (f"  – {duvod}" if duvod else "")))
        for _, r in sorted(radky):
            print(r)
        if not radky:
            print("nic nečeká")
        return 0
    if a.cmd == "odeslano":
        if not (a.uzivatel or "").strip():
            sys.exit("ODMÍTNUTO: odeslání dotazu archivu a otázky pro rodinu potvrzuje uživatel (--uzivatel \"kdo odeslal\"); agent jen připravuje")
        for f, (uv, uk) in data.items():
            for u in uk:
                if u.id != a.id:
                    continue
                if f not in ("dotazy", "rodina"):
                    sys.exit(f"{u.id} je ve frontě {f}: odeslat se dá jen úkol z front dotazy a rodina")
                dnes = datetime.date.today()
                do = a.odpoved_do or (dnes + datetime.timedelta(days=int(nacti_rezim().get("odpoved_dnu", 30)))).isoformat()
                try:
                    datetime.date.fromisoformat(do)
                except ValueError:
                    sys.exit("--odpoved-do RRRR-MM-DD")
                u.stav, u.do = "čeká", do
                u.text = (u.text + f"\n\nOdesláno: {dnes.isoformat()}, odpověď čekáme do {do}").strip("\n")
                uloz(f, uv or "", uk)
                zapis_udalost("odeslano", u.id, fronta=f, do=do, potvrdil=a.uzivatel.strip())
                print(f"{u.id} ({f}): odesláno, čeká na odpověď do {do}")
                return 0
        sys.exit(f"{a.id} nenalezeno")
    if a.cmd == "trid":
        for f, (uv, uk) in data.items():
            if os.path.exists(cesta(f)) or uk:
                uloz(f, uv, uk)
        print("setříděno")
        return 0
    if a.cmd == "frontier":
        pripraveno = {id(u) for u in frontier(data)}
        for f in ([a.fronta] if a.fronta else FRONTY):
            for u in data[f][1]:
                if id(u) in pripraveno:
                    print(f"{f:10} {u.hlavicka()[3:]}  {u.text.strip().splitlines()[0][:90] if u.text.strip() else ''}")
        return 0
    if a.cmd == "dalsi":
        now = datetime.datetime.fromisoformat(a.kdy) if a.kdy else datetime.datetime.now()
        r = nacti_rezim()
        m, konec = rezim_v(now, r)
        cfg = rozpocet_cfg(r)
        limit = cfg["okno"].get(m)
        okno = konec.isoformat() if konec else ""
        spotreba = cti_spotrebu(okno)
        vyloucen_rozpoctem = False
        for u, stav in vybirej(data, a.fronta, now, r, a.vzdy, a.typ):   # blokovaný úkol se nepřidělí
            if stav == "schvaleni":                       # XL bez schválení člověkem
                continue
            vaha = cena_vaha(u, cfg)
            if limit is not None and not schvaleno(u) and spotreba + vaha > limit:
                vyloucen_rozpoctem = True
                continue
            druh = TYPY_RUN.get(u.typ or "bádání", "badani")
            z = cti_zamek()
            if z and z["typ"] != druh:
                continue
            if limit is not None:
                zapis_spotrebu(okno, spotreba + vaha)
            u.stav = "probíhá"                      # přidělený úkol se podruhé nepřidělí (a nepočítá se podruhé do rozpočtu)
            uv_, uk_ = data[a.fronta]
            uloz(a.fronta, uv_ or "", uk_)
            zapis_udalost("prideleno", u.id, fronta=a.fronta, rezim=m)
            print(u.hlavicka()[3:] + "\n" + u.text)
            return 0
        if m == "pracovni" and not a.vzdy:
            sys.exit("pracovní doba: další úkol se nepouští (--vzdy pro ruční spuštění)")
        if vyloucen_rozpoctem:
            print(f"rozpočet okna vyčerpán ({spotreba}/{limit}); zbylé úkoly počkají na další okno")
        else:
            print("žádný úkol")
        return 3
    if a.cmd == "plan":
        now = datetime.datetime.fromisoformat(a.kdy) if a.kdy else datetime.datetime.now()
        r = nacti_rezim()
        m, konec = rezim_v(now, r)
        cfg = rozpocet_cfg(r)
        limit = cfg["okno"].get(m)
        okno = konec.isoformat() if konec else ""
        spotreba = cti_spotrebu(okno)
        print(f"plán okna {m}" + (f" do {konec:%Y-%m-%d %H:%M}" if konec else "") + f"; rozpočet {spotreba}/{limit if limit is not None else 'bez limitu'}")
        for u, stav in vybirej(data, a.fronta or "noc", now, r, a.vzdy):
            vaha = cena_vaha(u, cfg)
            znacka = ""
            if stav == "schvaleni":
                znacka = "  čeká na schválení (cena " + u.cena + ")"
            elif limit is not None and not schvaleno(u) and spotreba + vaha > limit:
                znacka = "  mimo rozpočet"
            else:
                spotreba += vaha
            print(f"{u.id} | {u.p} | cena {u.cena or '?'} | váha {vaha} | {spotreba}/{limit if limit is not None else '-'}{znacka}")
        return 0
    if a.cmd == "kalibrace":
        smerovani, skutecne = {}, {}
        for e in nacti_historii():
            if e["udalost"] == "smerovani" and e.get("cena"):
                smerovani[e["id"]] = e["cena"]
            elif e["udalost"] == "hotovo" and e.get("spotreba"):
                skutecne[e["id"]] = e["spotreba"]
        odhady = {}
        for f_, (_, uk_) in data.items():
            for u_ in uk_:
                if u_.cena:
                    odhady.setdefault(u_.id, u_.cena)
        odhady.update(smerovani)
        # odhad z hlavičky úkolu, dokud byl ve frontě, je v historii jen u směrovaných; ostatní doplní událost smerovani
        tabulka = {c: {x: 0 for x in CENY} for c in CENY}
        for u_id, skut in skutecne.items():
            if u_id in odhady and skut in CENY and odhady[u_id] in CENY:
                tabulka[odhady[u_id]][skut] += 1
        if not any(sum(v.values()) for v in tabulka.values()):
            print("zatím není z čeho kalibrovat (potřeba směrování s cenou a hotovo --spotreba)")
            return 0
        for c in CENY:
            n = sum(tabulka[c].values())
            if not n:
                continue
            nad = sum(v for k, v in tabulka[c].items() if CENY.index(k) > CENY.index(c))
            pod = sum(v for k, v in tabulka[c].items() if CENY.index(k) < CENY.index(c))
            rada = " – podhodnoceno" if nad * 2 > n else (" – nadhodnoceno" if pod * 2 > n else "")
            print(f"{c}  {n} úkolů  skutečně: " + "  ".join(f"{k} {v}" for k, v in tabulka[c].items()) + rada)
        return 0
    if a.cmd == "historie":
        udal = nacti_historii()
        ids = {a.id} if a.id else None
        if ids:
            zmena = True
            while zmena:   # i události dětí rozdělených úkolů
                zmena = False
                for u in udal:
                    if u["udalost"] == "deleni" and u["id"] in ids:
                        for d in u.get("deti", []):
                            if d["id"] not in ids:
                                ids.add(d["id"])
                                zmena = True
        for u in udal:
            if ids is None or u["id"] in ids:
                dalsi_pole = {k: v for k, v in u.items() if k not in ("cas", "udalost", "id")}
                print(f"{u['cas']} {u['udalost']:10} {u['id']}  {json.dumps(dalsi_pole, ensure_ascii=False)}")
        return 0
    if a.cmd == "znovu":
        return znovu(data, [x.strip() for x in a.vysledek.split(",") if x.strip()], a.starsi, a.zaloz)
    if a.cmd == "smeruj":
        if a.do not in FRONTY or a.do == "vstup":
            sys.exit(f"smeruj --do: {', '.join(f for f in FRONTY if f != 'vstup')}")
        if a.cena and a.cena not in CENY:
            sys.exit(f"cena: {' | '.join(CENY)}")
        if not (a.dod or "").strip():
            sys.exit("ODMÍTNUTO: úkol bez definice hotového (--dod) se nesměruje: co je výsledek a kde bude zapsán")
        uv, uk = data["vstup"]
        u = next((x for x in uk if x.id == a.id), None)
        if u is None:
            sys.exit(f"{a.id} není ve frontě vstup")
        if u.cil and cil_splnen(u.cil):
            print(f"cíl {u.cil} už je v datech: fronta.py hotovo {u.id}")
            return 1
        nastav_dod(u, a.dod)
        u.cena = a.cena or u.cena
        u.p = a.p or u.p
        if a.do == "noc" and vyzaduje_schvaleni(u, rozpocet_cfg(nacti_rezim())):
            if not a.schvaleno:
                sys.exit(f"ODMÍTNUTO: cena {u.cena} je nad prahem rozpočtu – úkol patří do rozhodnutí (provést, odložit, nebo ručně?): "
                         "fronta.py smeruj <id> --do rozhodnuti …; po schválení uživatelem znovu s --schvaleno")
            u.text = (u.text + f"\n\nSchváleno: uživatel, {datetime.date.today().isoformat()}").strip("\n")
        if a.do == "rozhodnuti":
            vyzaduj_rozhodnuti(u.text)
        for f2, (uv2, uk2) in data.items():
            if f2 != a.do or a.nove:   # slučuje se jen v cílové frontě
                continue
            for x in uk2:
                if stejny(x, u):
                    sluc(x, u)
                    uk.remove(u)
                    uloz(f2, uv2, uk2)
                    uloz("vstup", uv, uk)
                    zapis_udalost("doplneno", x.id, fronta=f2, z_ukolu=u.id)
                    print(f"doplněno {x.id} ({f2}) – úkol {u.id} ze vstupu se slučuje")
                    return 0
        uk.remove(u)
        uv2, uk2 = data[a.do]
        uk2.append(u)
        uloz("vstup", uv, uk)
        uloz(a.do, uv2 or "", uk2)
        zapis_udalost("smerovani", u.id, z="vstup", do=a.do, dod=a.dod.strip(), cena=u.cena)
        print(f"{u.id}: vstup → {a.do}" + (f" (cena {u.cena})" if u.cena else ""))
        return 0
    if a.cmd == "rozdel":
        nalezeno = next(((f, x) for f, (_, uk) in data.items() for x in uk if x.id == a.id), None)
        if nalezeno is None:
            sys.exit(f"{a.id} nenalezeno")
        f0, rodic = nalezeno
        deti = []
        for i, cast in enumerate(a.cast):
            if len(cast) < 3:
                sys.exit("rozdel --cast FRONTA TEXT DOD [os=1,2] [typ=…] [cena=S|M|L|XL]")
            fronta_, text, dod = cast[:3]
            navic = dict(x.split("=", 1) for x in cast[3:] if "=" in x)
            if len(navic) != len(cast) - 3 or set(navic) - {"os", "typ", "cena"}:
                sys.exit("rozdel --cast: za definicí hotového smí být jen os=…, typ=…, cena=…")
            if fronta_ not in FRONTY or fronta_ == "vstup":
                sys.exit(f"rozdel --cast: neznámá fronta „{fronta_}“")
            if not text.strip() or not dod.strip():
                sys.exit("ODMÍTNUTO: každá část potřebuje text a definici hotového")
            if "os" not in navic and len(rodic.os) > 1 and len(a.cast) > 1:
                sys.exit(f"ODMÍTNUTO: {rodic.id} má víc osob ({', '.join(rodic.os)}); u každé části uveď její osoby (os=…), "
                         "části je po rodiči mlčky nedědí")
            if navic.get("cena") and navic["cena"] not in CENY:
                sys.exit(f"rozdel --cast: cena {', '.join(CENY)}")
            osoby = [x for x in re.split(r"[,\s]+", navic["os"]) if x] if "os" in navic else list(rodic.os)
            dite = Ukol(nova_id(data, i), rodic.p, osoby, navic.get("typ", rodic.typ), "", rodic.id, "otevřeno", text)
            dite.cena = navic.get("cena") or ""
            nastav_dod(dite, dod)
            if fronta_ == "rozhodnuti":
                vyzaduj_rozhodnuti(dite.text)
            deti.append((fronta_, dite))
        uv0, uk0 = data[f0]
        uk0.remove(rodic)
        uloz(f0, uv0, uk0)
        for fronta_, dite in deti:
            uv_, uk_ = data[fronta_]
            uk_.append(dite)
            uloz(fronta_, uv_ or "", uk_)
            print(f"{dite.id} ({fronta_}) z {rodic.id}")
        zapis_udalost("deleni", rodic.id, z=f0, deti=[{"id": d.id, "fronta": f_} for f_, d in deti])
        return 0
    if a.cmd == "zaparkuj":
        try:
            datetime.date.fromisoformat(a.do)
        except ValueError:
            sys.exit("zaparkuj --do RRRR-MM-DD")
        for f, (uv, uk) in data.items():
            for u in uk:
                if u.id == a.id:
                    u.stav, u.do = "čeká", a.do
                    if a.duvod:
                        u.text = (u.text + f"\n\nČeká do {a.do}: {a.duvod}").strip("\n")
                    uloz(f, uv or "", uk)
                    zapis_udalost("parkovani", u.id, fronta=f, do=a.do, duvod=a.duvod)
                    print(f"{u.id} ({f}): čeká do {a.do}")
                    return 0
        sys.exit(f"{a.id} nenalezeno")
    if a.cmd == "selhani":
        now = datetime.datetime.fromisoformat(a.kdy) if a.kdy else datetime.datetime.now()
        r = nacti_rezim()
        for f, (uv, uk) in data.items():
            for u in uk:
                if u.id == a.id:
                    drive = {x.id for _, uk_ in data.values() for x in uk_}
                    dec = po_selhani(data, u, a.druh, a.portal, now, r)
                    for f2, (uv2, uk2) in data.items():
                        uloz(f2, uv2 or "", uk2) if (uk2 or os.path.exists(cesta(f2))) else None
                    if dec and dec.id not in drive:
                        zapis_udalost("vznik", dec.id, fronta="rozhodnuti", p=dec.p, text=prvni_radek(dec.text), duvod="selhání portálu " + a.portal)
                    zapis_udalost("selhani", u.id, fronta=f, druh=a.druh, portal=a.portal, pokusu=u.pokusu,
                                  vysledek=(f"rozhodnutí {dec.id}" if dec else f"čeká do {u.do}, režim {u.kdy}"))
                    print(f"{u.id}: " + (f"rozhodnutí {dec.id} (portál {a.portal})" if dec else f"čeká do {u.do}, režim {u.kdy}, pokus {u.pokusu}"))
                    return 0
        sys.exit(f"{a.id} nenalezeno")
    if a.cmd == "pridej":
        if (a.typ or "") in ZRUSENE_TYPY:
            sys.exit("ODMÍTNUTO: " + ZPRAVA_TYP.format(t=a.typ))
        text = (text_rozhodnuti(a) if a.fronta == "rozhodnuti" else None) or a.text
        if not text:
            sys.exit("pridej: chybí --text" + (" (u rozhodnutí --otazka, --moznosti, --vychozi)" if a.fronta == "rozhodnuti" else ""))
        if a.fronta == "rozhodnuti":
            vyzaduj_rozhodnuti(text)
        if a.fronta != "vstup" and os.path.exists(cesta("vstup")):
            sys.exit("ODMÍTNUTO: nový úkol vstupuje přes frontu vstup (fronta.py pridej vstup --text …); "
                     "pak ho router zařadí: fronta.py smeruj <id> --do <fronta> --dod \"co je výsledek\" [--cena S|M|L|XL]")
        novy = Ukol(dalsi_id(data), a.p or "P2", [x for x in re.split(r"[,\s]+", a.os or "") if x], a.typ or "", a.cil or "",
                    a.rodic or "", a.stav or "otevřeno", text, [x for x in re.split(r"[,\s]+", a.zavisi or "") if x])
        if not re.fullmatch(r"P[1-3]", novy.p):
            sys.exit("priorita P1–P3")
        for f, (uv, uk) in data.items():
            if f != a.fronta or a.nove:   # slučuje se jen ve stejné frontě
                continue
            for u in uk:
                if stejny(u, novy):
                    sluc(u, novy)
                    uloz(f, uv, uk)
                    zapis_udalost("doplneno", u.id, fronta=f, text=prvni_radek(novy.text))
                    print(f"doplněno {u.id} ({f}) – nový úkol se nezakládá")
                    return 0
        uv, uk = data[a.fronta]
        uk.append(novy)
        uloz(a.fronta, uv or "", uk)
        zapis_udalost("vznik", novy.id, fronta=a.fronta, p=novy.p, text=prvni_radek(novy.text))
        print(f"založeno {novy.id} ({a.fronta})")
        return 0
    # uprav / hotovo / presun – podle id
    if a.cmd == "hotovo" and not a.id and not a.cil:
        sys.exit("hotovo <id> | --cil")
    zmeneno = 0
    for f, (uv, uk) in data.items():
        nove = []
        for u in uk:
            sel = (a.id and u.id == a.id) or (a.cmd == "hotovo" and a.cil and u.cil == a.cil)
            if not sel:
                nove.append(u)
                continue
            zmeneno += 1
            if a.cmd == "hotovo":
                zapis_udalost("hotovo", u.id, fronta=f, denik=[int(x) for x in re.split(r"[,\s]+", a.denik or "") if x.isdigit()],
                              soubory=[x for x in re.split(r"\s*,\s*", a.soubory or "") if x], spotreba=a.spotreba, poznamka=a.poznamka)
                print(f"smazáno {u.id} ({f})")
                continue
            if a.cmd == "presun":
                uv2, uk2 = data[a.fronta]
                if a.fronta != f:
                    if a.fronta == "rozhodnuti":
                        vyzaduj_rozhodnuti(u.text)
                    uk2.append(u)
                    uloz(a.fronta, uv2 or "", uk2)
                    zapis_udalost("presun", u.id, z=f, do=a.fronta)
                    print(f"{u.id}: {f} → {a.fronta}")
                    continue
            if a.cmd == "uprav":
                if a.p:
                    u.p = a.p
                if a.text is not None:
                    u.text = a.text
                if a.dod:
                    nastav_dod(u, a.dod)
                if a.pridat_text:
                    u.text = (u.text + "\n\n" + a.pridat_text).strip("\n")
                if (a.typ or "") in ZRUSENE_TYPY:
                    sys.exit("ODMÍTNUTO: " + ZPRAVA_TYP.format(t=a.typ))
                if a.cena:
                    if a.cena not in CENY:
                        sys.exit(f"cena: {' | '.join(CENY)}")
                    u.cena = a.cena
                for k, attr in (("typ", "typ"), ("cil", "cil"), ("rodic", "rodic"), ("stav", "stav")):
                    if getattr(a, k):
                        setattr(u, attr, getattr(a, k))
                if a.os:
                    u.os = [x for x in re.split(r"[,\s]+", a.os) if x]
                if a.zavisi is not None:   # prázdná hodnota závislosti smaže
                    u.zavisi = [x for x in re.split(r"[,\s]+", a.zavisi) if x]
                print("upraveno", u.id)
            nove.append(u)
        if (nove != uk or a.cmd == "uprav") and (nove or os.path.exists(cesta(f))):   # prázdný soubor fronty se nezakládá (vstup zapíná router)
            uloz(f, uv or "", nove)
    if not zmeneno:
        print("nic nenalezeno")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
