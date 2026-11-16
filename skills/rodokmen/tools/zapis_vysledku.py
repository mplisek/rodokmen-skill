#!/usr/bin/env python3
"""Zápis přijatého výsledku jedním voláním (analyza/navrh-optimalizace.md, etapa E2): řádek deníku, nový zápis a přepis, stránky do mapy
knihy, uzavření úkolu a navazující otázky. Buď se zapíše všechno, nebo nic; totéž rozhodnutí podruhé nic nezdvojí.

Použití (z kořene projektu):
  python3 -I tools/zapis_vysledku.py pracovni/vysledky/U-0101_rozhodnuti.json [--nanecisto]
        --nanecisto jen zkontroluje a vypíše, co by se zapsalo

Rozhodnutí (schema rozhodnuti/1, vzor: tools/vysledek.py vzor rozhodnuti) píše řídicí agent: on rozhoduje, co se přijímá a zda je úkol
hotov; tento nástroj hlídá jen integritu:
- nález úkolu (pracovni/vysledky/<úkol>.json) musí projít kontrolou a jeho stav musí výsledku odpovídat: po dosaženém stropu, nedostupném
  portálu nebo chybě nástroje se „nenalezeno“ ani „hotovo“ nezapíše;
- ověřený výsledek a každý nový zápis potřebuje druhé čtení naslepo, které se s prvním shoduje (vysledek.py porovnej);
- osoby jen klíčem z data/osoby.py; má-li zadání jmenovce k nezaměnění, rozhodnutí řekne, proč to nejsou oni;
- úkol se uzavře jen při splněné definici hotového.
Co se změnilo, zapíše do historie úkolu (událost „zapsano“ se seznamem souborů; podle ní commituje tools/commit.py).
"""
import contextlib
import datetime
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import denik  # noqa: E402
import fronta  # noqa: E402
import mapa  # noqa: E402
import vysledek  # noqa: E402
import zapis  # noqa: E402
import zaznamy_store as store  # noqa: E402

ROOT = vysledek.ROOT
BEZ_ZAPISU = ("nedostupné", "chyba prostředí")            # nic se nečetlo: patří do fronta.py selhani nebo do poznámek pro skill
DOVOLENY_VYSLEDEK = {"nalezeno": ("nalezeno",), "vyvráceno": ("vyvráceno",), "nenalezeno": ("nenalezeno",), "částečně": ("částečně",),
                     "nečitelné": ("nečitelné",), "rozpočet": ("částečně",)}
LZE_UZAVRIT = ("nalezeno", "vyvráceno", "nenalezeno")


class Odmitnuto(Exception):
    pass


def klic_rozhodnuti(d):
    return hashlib.sha1(json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def uz_zapsano(klic):
    return next((e for e in fronta.nacti_historii() if e.get("udalost") == "zapsano" and e.get("klic") == klic), None)


def najdi_ukol(id_):
    for f in fronta.FRONTY:
        for u in fronta.nacti(f)[1]:
            if u.id == id_:
                return f, u
    return None, None


def over(d):
    """Chyby rozhodnutí vůči nálezu, zadání, ověření a datům. Vrací (chyby, nález)."""
    ch = vysledek.over_rozhodnuti(d)
    if ch:
        return ch, None
    ukol = d["ukol"]
    pn = vysledek.cesta_nalezu(ukol)
    if not os.path.exists(pn):
        return [f"nález {os.path.relpath(pn, ROOT)} neexistuje; rozhodnutí se opírá o nález čtenáře"], None
    nalez = vysledek.nacti(pn)
    zadani = vysledek.nacti(vysledek.cesta_zadani(ukol)) if os.path.exists(vysledek.cesta_zadani(ukol)) else None
    chn = vysledek.over_nalez(nalez, zadani)
    if chn:
        return ["nález neprošel kontrolou (vysledek.py over): " + "; ".join(chn[:3])], nalez
    stav, vys, uzavrit = nalez.get("stav"), d["vysledek"], bool(d.get("uzavrit"))
    if stav in BEZ_ZAPISU:
        ch.append(f"nález má stav „{stav}“: nic se nečetlo, do deníku se nezapisuje (portál: fronta.py selhani; nástroj: poznámky pro skill)")
    elif vys not in DOVOLENY_VYSLEDEK.get(stav, ()):
        ch.append(f"výsledek „{vys}“ neodpovídá stavu nálezu „{stav}“ (dovoleno: {', '.join(DOVOLENY_VYSLEDEK.get(stav, ()))})")
    if uzavrit and (stav not in LZE_UZAVRIT or not d.get("dod_splneno")):
        ch.append(f"úkol nelze uzavřít: stav nálezu „{stav}“" + ("" if d.get("dod_splneno") else ", definice hotového není splněna (dod_splneno)")
                  + "; pokračuj v témže úkolu (zadani.py rozsir) nebo ho nech otevřený")
    cteni = {c.get("id") for c in nalez.get("cteni") or [] if isinstance(c, dict)}
    dukaz = d.get("dukaz") or sorted(x for x in cteni if x)
    for c in dukaz:
        if c not in cteni:
            ch.append(f"dukaz: čtení {c} v nálezu není")
    if d["denik"].get("overeno") or d.get("zaznam"):
        for c in [c for c in dukaz if c in cteni]:
            cesty, docs, _ = vysledek.nacti_overeni(ukol, c)   # kopie téhož ověření se nepočítá dvakrát
            if not cesty:
                po = vysledek.cesta_overeni(ukol, c)
                ch.append(f"čtení {c} nemá ověření naslepo ({os.path.relpath(po, ROOT)}); bez něj nejde zapsat ověřený výsledek ani nový zápis")
                continue
            prvni = next(x for x in nalez["cteni"] if x.get("id") == c)
            vet = vysledek.vetsina(prvni, docs)   # 2 ze 3; při jednom ověření shoda obou
            rozdil = sorted(p for p, v in vet.items() if not v["overeno"])
            if rozdil:
                ch.append(f"čtení {c}: první a druhé čtení se neshodují v polích {', '.join(rozdil)}; zapiš výsledek bez „overeno“ a bez nového "
                          "zápisu (tvrzení nejvýš prob), nebo nech pole přečíst znovu")
        if not dukaz:
            ch.append("ověřený výsledek nebo nový zápis potřebuje aspoň jedno čtení (dukaz)")
    if zadani and zadani.get("nezamenit_s") and vys == "nalezeno":
        vyl = set((d.get("identita") or {}).get("vylouceno") or [])
        chybi = [str(x.get("id")) for x in zadani["nezamenit_s"] if str(x.get("id")) not in vyl]
        if chybi or not str((d.get("identita") or {}).get("proc") or "").strip():
            ch.append("identita: zadání má jmenovce k nezaměnění (" + ", ".join(str(x.get("id")) for x in zadani["nezamenit_s"])
                      + "); uveď identita.proc a identita.vylouceno se všemi")
    tv = nacti_tvrzeni()
    for i, t in enumerate(d.get("tvrzeni") or []):
        if t.get("jistota") == "doc" and not d["denik"].get("overeno"):
            ch.append(f"tvrzeni[{i}]: jistota doc jen u ověřeného výsledku (denik.overeno a shodné druhé čtení); jinak prob")
        if t.get("nahrazuje") and t["nahrazuje"] not in {x.get("id") for x in tv}:
            ch.append(f"tvrzeni[{i}].nahrazuje: {t['nahrazuje']} v data/tvrzeni.jsonl není")
        for c in t.get("dukaz") or []:
            if c not in cteni:
                ch.append(f"tvrzeni[{i}].dukaz: čtení {c} v nálezu není")
    f, _ = najdi_ukol(ukol)
    if uzavrit and f is None:
        ch.append(f"úkol {ukol} není ve frontách, nejde uzavřít")
    a = d.get("audit")
    if a is not None:   # audit už zapsaného zápisu: potvrzení nebo zpochybnění přepisu, nový zápis ani tvrzení nevzniká
        if not isinstance(a, dict) or a.get("vysledek") not in ("potvrzeno", "rozpor"):
            ch.append('audit: {"zaznam": "<klíč zápisu>", "vysledek": "potvrzeno" | "rozpor"}')
        else:
            if d.get("zaznam"):
                ch.append("audit: nový zápis se při auditu nezakládá (vynech zaznam); oprava stávajícího jde přes tools/oprava.py")
            if a.get("vysledek") == "potvrzeno" and not d["denik"].get("overeno"):
                ch.append("audit potvrzeno: jen se shodným druhým čtením (denik.overeno); jinak „rozpor“ nebo nechat otevřené")
            klice = {z.get("klic") for z in (vysledek._json("data", "zaznamy.json") or []) if isinstance(z, dict)}
            if a.get("zaznam") not in klice:
                ch.append(f"audit: zápis „{a.get('zaznam')}“ v data/zaznamy.json není")
    zaznamy_d, _ = denik.nacti_zaznamy()   # řádek deníku zkontrolovat už teď, ať nanečisto odpovídá ostrému zápisu
    zd = radek_deniku(d, nalez, zaznamy_d)
    ch += [f"řádek deníku: {x}" for x in denik.over_zaznam(zd, {x["id"] for x in zaznamy_d}) + denik.over_osoby(zd.get("osoby", []))]
    return ch, nalez


def cesta_tvrzeni():
    return os.path.join(ROOT, "data", "tvrzeni.jsonl")


def nacti_tvrzeni():
    out = []
    try:
        with open(cesta_tvrzeni(), encoding="utf-8") as f:
            for radek in f:
                if radek.strip():
                    out.append(json.loads(radek))
    except (OSError, ValueError):
        pass
    return out


def zapis_tvrzeni(d, cislo_deniku):
    """Přijatá tvrzení do data/tvrzeni.jsonl (jen přibývá; oprava = nové tvrzení s „nahrazuje“). Vrací přidělená ID."""
    nove = d.get("tvrzeni") or []
    if not nove:
        return []
    stara = nacti_tvrzeni()
    n = max([int(x["id"][2:]) for x in stara if isinstance(x.get("id"), str) and x["id"][2:].isdigit()], default=0)
    ids = []
    with open(cesta_tvrzeni(), "a", encoding="utf-8", newline="\n") as f:
        for t in nove:
            n += 1
            z = {"id": f"T-{n:04d}", "datum": datetime.date.today().isoformat(), "typ": t["typ"], "osoby": [str(x) for x in t["osoby"]],
                 "jistota": t["jistota"], "ukol": d["ukol"], "denik": cislo_deniku}
            for pole in ("text", "dukaz", "nahrazuje"):
                if t.get(pole):
                    z[pole] = t[pole]
            if (d.get("zaznam") or {}).get("klic"):
                z["zaznam"] = d["zaznam"]["klic"]
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
            ids.append(z["id"])
    return ids


def radek_deniku(d, nalez, zaznamy):
    dn = d["denik"]
    z = {"id": max([x["id"] for x in zaznamy], default=0) + 1, "datum": dn.get("datum") or datetime.date.today().isoformat(),
         "zdroj": {"typ": dn.get("zdroj_typ", "archiv"), "text": dn["zdroj"]}, "rozsah": dn.get("rozsah", ""), "hledano": dn["hledano"],
         "vysledek": d["vysledek"]}
    if dn.get("overeno"):
        z["overeno"] = True
    for pole in ("nalez", "citace", "poznamka"):
        if dn.get(pole):
            z[pole] = dn[pole]
    if (d.get("zaznam") or {}).get("klic"):
        z["odkaz"] = d["zaznam"]["klic"]
    if isinstance(d.get("audit"), dict):
        z["odkaz"], z["audit"] = d["audit"].get("zaznam"), d["audit"].get("vysledek")
    if dn.get("osoby"):
        z["osoby"] = [str(x) for x in dn["osoby"]]
    if dn.get("opravuje") is not None:
        z["opravuje"] = dn["opravuje"]
    z["ukol"] = d["ukol"]
    if denik.verze_nastroje():
        z["nastroj"] = denik.verze_nastroje()
    if d.get("model"):
        z["model"] = d["model"]
    sn = [{"svazek": p["svazek"], "od": p["snimky"][0], "do": p["snimky"][1]} for p in nalez.get("prohledano") or []
          if isinstance(p, dict) and isinstance(p.get("snimky"), list) and len(p["snimky"]) == 2]
    if sn:
        z["snimky"] = sn
    return z


def soubory_k_zaloze(nalez):
    out = [os.path.join(ROOT, "data", n) for n in ("denik.jsonl", "zaznamy.json", "prepisy.json", "ukoly_historie.jsonl", "tvrzeni.jsonl")]
    out += [fronta.cesta(f) for f in fronta.FRONTY]
    for s in nalez.get("stranky") or []:
        with contextlib.suppress(Exception):
            out.append(mapa.cesta(s["portal"], s["svazek"]))
    return list(dict.fromkeys(out))


def zaloha(cesty):
    z = {}
    for p in cesty:
        try:
            with open(p, "rb") as f:
                z[p] = f.read()
        except OSError:
            z[p] = None
    return z


def obnov(z):
    for p, data in z.items():
        if data is None:
            with contextlib.suppress(OSError):
                os.remove(p)
        else:
            with open(p, "wb") as f:
                f.write(data)


def tise(fn, *a, **kw):
    """Zavolá zapisovací funkci jiného nástroje; jeho sys.exit převede na Odmitnuto a výpis schová."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            r = fn(*a, **kw)
    except SystemExit as e:
        if e.code not in (None, 0):
            raise Odmitnuto(str(e.code) if not isinstance(e.code, int) else out.getvalue().strip() or f"kód {e.code}") from None
        r = 0
    if isinstance(r, int) and r not in (0,):
        raise Odmitnuto(out.getvalue().strip() or f"kód {r}")
    return out.getvalue()


def proved(d, nalez, klic):
    """Všechny zápisy; vrací (id řádku deníku, seznam změněných souborů v repozitáři)."""
    ukol = d["ukol"]
    zaznamy, chyby = denik.nacti_zaznamy()
    if d["denik"].get("opravuje") is not None:
        chyby = [c for c in chyby if "zakázaný vzor" not in c]
    if chyby:
        raise Odmitnuto("denik.jsonl má chyby (denik.py over): " + "; ".join(chyby[:3]))
    z = radek_deniku(d, nalez, zaznamy)
    ch = denik.over_zaznam(z, {x["id"] for x in zaznamy}) + denik.over_osoby(z.get("osoby", []))
    if ch:
        raise Odmitnuto("řádek deníku: " + "; ".join(ch))
    with store.Zamek(denik.LOG):
        store.pridej_radek(denik.LOG, z)
    zz = d.get("zaznam")
    if zz:
        prepis = zz.get("prepis")
        tise(zapis.zapis, "zaznamy", zz["klic"], {k: v for k, v in zz.items() if k != "prepis"})
        if prepis:
            tise(zapis.zapis, "prepisy", zz["klic"], prepis)
    zapis_tvrzeni(d, z["id"])
    stranky = [dict(s) for s in nalez.get("stranky") or []]
    try:
        mapa.svazek_ze_signatury(stranky)
        for s in stranky:
            mapa.zapis_stranu(s, jen_over=True)
    except ValueError as e:
        raise Odmitnuto(f"stránky pro mapu knihy: {e}") from None
    for s in stranky:
        mapa.zapis_stranu(s, kdo=d.get("model", "neznámý"), nastroj=denik.verze_nastroje())
    vstup = os.path.exists(fronta.cesta("vstup"))
    for n in d.get("navazujici") or []:
        a = ["pridej", "vstup" if vstup else n.get("fronta", "noc"), "--text", n["text"], "--rodic", ukol, "--nove"]
        for volba, pole in (("--os", "os"), ("--typ", "typ"), ("--cil", "cil"), ("--p", "p")):
            if n.get(pole):
                a += [volba, ",".join(map(str, n[pole])) if isinstance(n[pole], list) else str(n[pole])]
        tise(fronta.main, a)
    hot = d.get("hotovo") or {}
    if d.get("uzavrit"):
        a = ["hotovo", ukol, "--denik", str(z["id"])]
        if hot.get("spotreba"):
            a += ["--spotreba", hot["spotreba"]]
        if hot.get("soubory"):
            a += ["--soubory", ",".join(hot["soubory"])]
        tise(fronta.main, a)
    return z["id"]


def zmenene(pred):
    out = []
    for p, data in pred.items():
        if not os.path.abspath(p).startswith(os.path.abspath(ROOT) + os.sep):
            continue   # mapa knihy leží mimo projekt
        try:
            with open(p, "rb") as f:
                ted = f.read()
        except OSError:
            ted = None
        if ted != data:
            out.append(os.path.relpath(p, ROOT).replace("\\", "/"))
    return sorted(out)


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            _s.reconfigure(encoding="utf-8")
    argv = list(sys.argv[1:] if argv is None else argv)
    nanecisto = "--nanecisto" in argv
    argv = [a for a in argv if a != "--nanecisto"]
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    d = vysledek.nacti(argv[0])
    klic = klic_rozhodnuti(d)
    uz = uz_zapsano(klic)   # dřív než kontroly: po zápisu už úkol ve frontě není a nález může být dál
    if uz:
        print(f"už zapsáno ({uz.get('cas')}, deník {uz.get('denik')}); nic se nemění")
        return 0
    ch, nalez = over(d)
    if ch:
        print(f"ODMÍTNUTO, nic se nezapsalo ({len(ch)}):")
        for c in ch:
            print("  " + c)
        return 1
    if nanecisto:
        print(f"v pořádku: {d['ukol']} → deník „{d['vysledek']}“" + (", nový zápis " + d["zaznam"]["klic"] if d.get("zaznam") else "")
              + f", stránek do mapy {len(nalez.get('stranky') or [])}, navazujících {len(d.get('navazujici') or [])}"
              + (", úkol se uzavře" if d.get("uzavrit") else ", úkol zůstává otevřený"))
        return 0
    pred = zaloha(soubory_k_zaloze(nalez))
    znacka = os.path.join(ROOT, "pracovni", f"zapis_{klic}.rozpracovano")
    os.makedirs(os.path.dirname(znacka), exist_ok=True)
    with open(znacka, "w", encoding="utf-8") as f:
        f.write(d["ukol"] + "\n")
    try:
        cislo = proved(d, nalez, klic)
        soubory = zmenene(pred)
        fronta.zapis_udalost("zapsano", d["ukol"], klic=klic, denik=cislo, vysledek=d["vysledek"], uzavreno=bool(d.get("uzavrit")),
                             soubory=sorted(set(soubory) | {"data/ukoly_historie.jsonl"}),
                             zprava=d.get("zprava") or f"Deník {cislo}: {d['denik']['hledano']} ({d['vysledek']})")
    except (Odmitnuto, Exception) as e:   # noqa: BLE001 – cokoli uprostřed: vrátit všechny soubory do stavu před voláním
        obnov(pred)
        with contextlib.suppress(OSError):
            os.remove(znacka)
        print(f"ODMÍTNUTO, soubory vráceny do stavu před zápisem: {e}")
        return 1
    with contextlib.suppress(OSError):
        os.remove(znacka)
    print(f"zapsáno {d['ukol']}: deník {cislo} ({d['vysledek']})" + (", úkol uzavřen" if d.get("uzavrit") else ", úkol zůstává otevřený")
          + f"; změněno: {', '.join(soubory)}. Commit: python -I tools/commit.py {d['ukol']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
