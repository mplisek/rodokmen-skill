#!/usr/bin/env python3
"""Fronty úkolů (noční a víkendový režim): úkoly na noc, k rozhodnutí, k bádání, archivní dotazy, otázky pro rodinu.

Použití (z kořene projektu): python3 -I tools/fronta.py <příkaz> …
  seznam [fronta]                         vypíše úkoly (fronta: noc | rozhodnuti | badani | dotazy | rodina)
  pridej <fronta> --text T [--p P1] [--os 57,114] [--typ krest] [--cil krest:115] [--rodic U-0001] [--stav otevřeno]
                                          nový úkol; podobný (stejný typ a překryv osob/cíle, v kterékoli frontě) se
                                          NEZALOŽÍ, ale doplní (osoby, text, vyšší priorita)
  uprav <id> [--p P2] [--text T] [--stav odloženo] [--os …] [--cil …] [--pridat-text T]
  hotovo <id> | hotovo --cil krest:115    úkol smaže (jeho výsledek je v datech nebo v následných úkolech)
  presun <id> <fronta>                    přesune úkol do jiné fronty
  trid                                    setřídí všechny fronty (priorita, id)
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
FRONTY = {"noc": "ukoly_na_noc.md", "rozhodnuti": "ukoly_k_rozhodnuti.md", "badani": "ukoly_k_badani.md",
          "dotazy": "archivni_dotazy.md", "rodina": "otazky_pro_rodinu.md"}
HLAVICKA = re.compile(r"^##+ (U-\d+)\s*\|(.*)$")
STAVY = ("otevřeno", "odloženo", "probíhá")
TYPY_RUN = {"bádání": "badani", "skill": "skill", "test": "skill", "údržba": "skill"}   # typ úkolu → druh běhu (brzda)
VYCHOZI_REZIM = {"pracovni_dny": [1, 2, 3, 4, 5], "pracovni_od": "06:00", "pracovni_do": "22:00", "svatky": [],
                 "pomocniku": 2, "dod": {}}


def cesta(f):
    return os.path.join(DATA, FRONTY[f])


def bez_diakritiky(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower()


class Ukol:
    def __init__(self, id_, p="P2", os_=None, typ="", cil="", rodic="", stav="otevřeno", text=""):
        self.id, self.p, self.os, self.typ, self.cil, self.rodic, self.stav, self.text = id_, p, list(os_ or []), typ, cil, rodic, stav, text

    def hlavicka(self):
        pole = [self.id, self.p]
        if self.os:
            pole.append("os:" + ",".join(self.os))
        for k, v in (("typ", self.typ), ("cíl", self.cil), ("rodič", self.rodic)):
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
            elif k == "stav":
                u.stav = v
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
    ukoly = sorted(ukoly, key=lambda u: (u.p, int(u.id[2:])))
    r = ([uvod.rstrip("\n"), ""] if uvod.strip() else [])
    for u in ukoly:
        r += u.radky()
    t = "\n".join(r).rstrip("\n") + "\n"
    with open(cesta(f), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t)


def vse():
    return {f: nacti(f) for f in FRONTY if os.path.exists(cesta(f))}


def dalsi_id(data):
    n = 0
    for f, (_, uk) in data.items():
        for u in uk:
            n = max(n, int(u.id[2:]))
    return f"U-{n + 1:04d}"


def stejny(a, b):
    """Podobné úkoly: stejný typ (nebo jeden bez typu) a shodný cíl, nebo překryv osob při shodném typu."""
    if a.cil and a.cil == b.cil:
        return True
    return bool(a.typ) and a.typ == b.typ and bool(set(a.os) & set(b.os)) and (not a.cil or not b.cil or a.cil == b.cil)


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
    for i, (f1, a) in enumerate(vsechny):
        for f2, b in vsechny[i + 1:]:
            if stejny(a, b):
                upoz.append(f"{a.id} ({f1}) a {b.id} ({f2}) se překrývají – sluč: fronta.py pridej (doplní) nebo hotovo")
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
    s = sp.add_parser("seznam"); s.add_argument("fronta", nargs="?", choices=list(FRONTY))
    s = sp.add_parser("pridej"); s.add_argument("fronta", choices=list(FRONTY))
    for a in ("--text", "--p", "--os", "--typ", "--cil", "--rodic", "--stav"):
        s.add_argument(a)
    s = sp.add_parser("uprav"); s.add_argument("id")
    for a in ("--text", "--p", "--os", "--typ", "--cil", "--rodic", "--stav", "--pridat-text"):
        s.add_argument(a)
    s = sp.add_parser("hotovo"); s.add_argument("id", nargs="?"); s.add_argument("--cil")
    s = sp.add_parser("presun"); s.add_argument("id"); s.add_argument("fronta", choices=list(FRONTY))
    sp.add_parser("trid")
    sp.add_parser("kontrola")
    s = sp.add_parser("rezim"); s.add_argument("--kdy")
    s = sp.add_parser("dalsi"); s.add_argument("fronta", choices=list(FRONTY)); s.add_argument("--typ"); s.add_argument("--vzdy", action="store_true")
    s = sp.add_parser("zamek"); s.add_argument("akce", choices=("start", "stop", "stav")); s.add_argument("typ", nargs="?", choices=("badani", "skill"))
    a = ap.parse_args(argv)

    if a.cmd == "kontrola":
        return kontrola()
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
        for f in ([a.fronta] if a.fronta else FRONTY):
            for u in data[f][1]:
                print(f"{f:10} {u.hlavicka()[3:]}  {u.text.strip().splitlines()[0][:90] if u.text.strip() else ''}")
        return 0
    if a.cmd == "trid":
        for f, (uv, uk) in data.items():
            if os.path.exists(cesta(f)) or uk:
                uloz(f, uv, uk)
        print("setříděno")
        return 0
    if a.cmd == "dalsi":
        m, _ = rezim_v(datetime.datetime.now(), nacti_rezim())
        if m == "pracovni" and not a.vzdy:
            sys.exit("pracovní doba: další úkol se nepouští (--vzdy pro ruční spuštění)")
        for u in data[a.fronta][1]:
            if u.stav != "otevřeno" or (a.typ and u.typ != a.typ):
                continue
            druh = TYPY_RUN.get(u.typ or "bádání", "badani")
            z = cti_zamek()
            if z and z["typ"] != druh:
                continue
            print(u.hlavicka()[3:] + "\n" + u.text)
            return 0
        print("žádný úkol")
        return 3
    if a.cmd == "pridej":
        if not a.text:
            sys.exit("pridej: chybí --text")
        novy = Ukol(dalsi_id(data), a.p or "P2", [x for x in re.split(r"[,\s]+", a.os or "") if x], a.typ or "", a.cil or "",
                    a.rodic or "", a.stav or "otevřeno", a.text)
        if not re.fullmatch(r"P[1-3]", novy.p):
            sys.exit("priorita P1–P3")
        for f, (uv, uk) in data.items():
            for u in uk:
                if stejny(u, novy):
                    sluc(u, novy)
                    uloz(f, uv, uk)
                    print(f"doplněno {u.id} ({f}) – nový úkol se nezakládá")
                    return 0
        uv, uk = data[a.fronta]
        uk.append(novy)
        uloz(a.fronta, uv or "", uk)
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
                print(f"smazáno {u.id} ({f})")
                continue
            if a.cmd == "presun":
                uv2, uk2 = data[a.fronta]
                if a.fronta != f:
                    uk2.append(u)
                    uloz(a.fronta, uv2 or "", uk2)
                    print(f"{u.id}: {f} → {a.fronta}")
                    continue
            if a.cmd == "uprav":
                if a.p:
                    u.p = a.p
                if a.text is not None:
                    u.text = a.text
                if a.pridat_text:
                    u.text = (u.text + "\n\n" + a.pridat_text).strip("\n")
                for k, attr in (("typ", "typ"), ("cil", "cil"), ("rodic", "rodic"), ("stav", "stav")):
                    if getattr(a, k):
                        setattr(u, attr, getattr(a, k))
                if a.os:
                    u.os = [x for x in re.split(r"[,\s]+", a.os) if x]
                print("upraveno", u.id)
            nove.append(u)
        if nove != uk or a.cmd == "uprav":
            uloz(f, uv or "", nove)
    if not zmeneno:
        print("nic nenalezeno")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
