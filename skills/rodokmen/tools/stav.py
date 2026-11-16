#!/usr/bin/env python3
"""Stav bádání ze souborů, bez historie rozhovoru (analyza/navrh-optimalizace.md, etapy E2 a E7): čím začít nové sezení nebo pokračovat
po přerušení, a předání rozpracované práce do další bádací session v data/STAV.md.

Použití (z kořene projektu):
  python3 -I tools/stav.py [--json]
        jen čte: větev a neuložené změny, verzi nástrojů, pravidla od uživatele a předání ze STAV.md, počty úkolů po frontách, rozpočet
        okna, rozpracované úkoly (stav „probíhá“ nebo se zadáním či nálezem bez zápisu) s posledním krokem a tím, co má následovat,
        nedokončené zápisy a počet úkolů k rozhodnutí
  python3 -I tools/stav.py predani pracovni/predani.json [--nanecisto] [--bez-commitu]
        přepíše oddíl „Rozpracováno“ v data/STAV.md celý, nebo vůbec; tvar souboru: stav.py vzor. Úkoly jen odkazem (musí být ve frontě),
        podklady jen verzované: z pracovni/ je přesune do data/predani/. Pak commit přes tools/commit.py.
  python3 -I tools/stav.py pravidlo "text pravidla od uživatele" [--bez-commitu]
        připíše pravidlo s datem do oddílu „Pravidla od uživatele“ (jen na slovo uživatele)
  python3 -I tools/stav.py kontrola        tvar STAV.md: ručně vedené předání, oddíly navíc, odkazy do pracovni/ a na úkoly mimo fronty
  python3 -I tools/stav.py vyrad "Nadpis" [--bez-commitu]
        migrace staršího STAV.md: odstraní oddíl navíc (úkoly z něj patří do front, fronta.py pridej) a vypíše, co odstranil
  python3 -I tools/stav.py vzor            vzor souboru pro predani
  python3 -I tools/stav.py uklid pracovni/<soubor> […]
        smaže pracovní soubory, které už nejsou potřeba (jen v pracovni/, všechno, nebo nic; zadání a výsledky úkolů ve frontě,
        přerušené zápisy a .plugin_root nesmaže)

STAV.md se nevede ručně: „Pro koho“, „Kde co je“ a „Pravidla“ mění uživatel, předání a pravidla od uživatele tento nástroj.
"""
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fronta  # noqa: E402
import vysledek  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*a):
    try:
        r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def cti(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def dalsi_krok(zadani, nalez, zapsano, overeni):
    """Co má následovat, odvozeno jen ze souborů."""
    if zadani and not nalez:
        return "čtenář ještě nevrátil nález (spustit nebo pokračovat podle zadání)"
    if not nalez:
        return "sestavit zadání (tools/zadani.py novy)"
    if nalez.get("schema") != "nalez/1":
        return ("výsledek ve starém tvaru (před kontraktem): přečíst a rozhodnout, nebo zadat čtení znovu (tools/zadani.py novy); "
                "zapis_vysledku.py ho nepřijme")
    stav = nalez.get("stav")
    if zapsano and zapsano.get("uzavreno"):
        return "zapsáno a uzavřeno; zbývá commit, pokud neproběhl (tools/commit.py)"
    if stav == "částečně":
        n = nalez.get("navrh_dalsiho_kroku") or {}
        return "pokračovat v témže úkolu: " + (", ".join(f"{k} {v}" for k, v in n.items()) or "doplnit chybějící pole") + " (zadani.py rozsir)"
    if stav == "rozpočet":
        return "strop dosažen před koncem rozsahu: schválit pokračování, nebo předat rozhodnutí; není to „nenalezeno“"
    if stav == "nedostupné":
        return "portál: fronta.py selhani; úkol zůstává otevřený"
    if stav == "nečitelné":
        return "jiný výřez nebo jiný pramen; není to „nenalezeno“"
    if stav == "chyba prostředí":
        return "podnět do data/poznamky_pro_skill.md; úkol se vrací neotevřený"
    if stav in ("nalezeno", "vyvráceno") and not overeni:
        return "ověřit naslepo (verifier), pak vysledek.py porovnej"
    if zapsano:
        return "zapsáno, úkol otevřený: rozhodnout o uzavření nebo dalším kroku"
    return "rozhodnout a zapsat (rozhodnutí → tools/zapis_vysledku.py)"


def sestav():
    dnes = datetime.date.today()
    data = {f: fronta.nacti(f)[1] for f in fronta.FRONTY}
    hist = fronta.nacti_historii()
    posledni, zapsano = {}, {}
    for e in hist:
        posledni[e.get("id")] = e
        if e.get("udalost") == "zapsano":
            zapsano[e.get("id")] = e
    fronty = {f: {"celkem": len(uk), "probiha": sum(u.stav == "probíhá" for u in uk),
                  "ceka": sum(u.stav == "čeká" and not fronta.pripraveny(u, dnes) for u in uk)} for f, uk in data.items() if uk}
    kde = {u.id: (f, u) for f, uk in data.items() for u in uk}
    ids = {u.id for uk in data.values() for u in uk if u.stav == "probíhá"}
    for p in glob.glob(os.path.join(ROOT, "pracovni", "zadani", "U-*.json")) + glob.glob(os.path.join(ROOT, "pracovni", "vysledky", "U-????.json")):
        i = os.path.basename(p)[:6]
        if i in kde:   # hotový úkol už ve frontě není; jeho soubory jsou jen historie
            ids.add(i)
    rozprac = []
    for i in sorted(ids):
        f, u = kde.get(i, (None, None))
        zadani, nalez = cti(vysledek.cesta_zadani(i)), cti(vysledek.cesta_nalezu(i))
        overeni = sorted(os.path.basename(p)[len(i) + 9:-5] for p in glob.glob(os.path.join(ROOT, "pracovni", "vysledky", f"{i}_overeni_*.json")))
        e = posledni.get(i) or {}
        rozsah = None
        if zadani:
            rozsah = [(zadani.get("rozsah") or {}).get("snimky")] + [r.get("snimky") for r in zadani.get("rozsireni") or []]
        dod = next((r[len("Definice hotového:"):].strip() for r in (u.text.splitlines() if u else []) if r.startswith("Definice hotového:")), "")
        rozprac.append({"ukol": i, "fronta": f, "stav_ukolu": u.stav if u else None, "dod": dod, "osoby": u.os if u else [],
                        "posledni_udalost": f"{e.get('udalost')} {e.get('cas')}" if e else "", "rozsah": rozsah,
                        "nalez": (({"stav": nalez.get("stav"), "cast": nalez.get("cast"), "cerpani": nalez.get("cerpani"),
                                    "chybi": sorted({x for c in nalez.get("cteni") or [] if isinstance(c, dict) for x in c.get("chybi") or []})}
                                   if nalez.get("schema") == "nalez/1" else {"stary_tvar": True})
                                  if nalez else None),
                        "overeni": overeni, "zapsano": bool(zapsano.get(i)),
                        "dalsi_krok": dalsi_krok(zadani, nalez, zapsano.get(i), overeni)})
    r = fronta.nacti_rezim()
    rozpocet = None
    try:
        m, konec = fronta.rezim_v(datetime.datetime.now(), r)
        cfg = fronta.rozpocet_cfg(r)
        rozpocet = {"okno": m, "spotreba": fronta.cti_spotrebu(konec.isoformat() if konec else ""), "limit": cfg["okno"].get(m)}
    except Exception:   # noqa: BLE001 – rozpočet je jen doplněk
        pass
    try:
        with open(os.path.join(ROOT, ".skill_verze"), encoding="utf-8") as fh:
            verze = fh.read().strip()
    except OSError:
        verze = ""
    return {"vetev": git("branch", "--show-current").strip(), "neulozene": len([x for x in git("status", "--porcelain").splitlines() if x.strip()]),
            "verze": verze, "fronty": fronty, "rozpocet": rozpocet, "rozpracovano": rozprac,
            "nedokoncene_zapisy": sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "pracovni", "zapis_*.rozpracovano"))),
            "k_rozhodnuti": len(data.get("rozhodnuti") or [])}


# --- data/STAV.md: předání a pravidla od uživatele (E7) ---

STAV = os.path.join(ROOT, "data", "STAV.md")
STANDARDNI = ("Pro koho", "Kde co je", "Pravidla", "Pravidla od uživatele", "Rozpracováno")
ZNACKA = "<!-- Vede tools/stav.py predani"
MAX_TEXT = 600
UKOL = re.compile(r"U-\d{4}")
VZOR = {"schema": "predani/1", "polozky": [
    {"co": "co je rozdělané (jedna věta, bez opisu textu úkolu)", "posledni_krok": "co se naposledy udělalo",
     "dal": "co má další session udělat jako první", "ukoly": ["U-0001"], "podklady": ["pracovni/rozbor_knihy.md"]}]}


def nazev(nadpis):
    """„## Rozpracováno (aktualizovat průběžně)“ → „Rozpracováno“."""
    return re.sub(r"\s*\(.*\)\s*$", "", nadpis[3:]).strip()


def oddily(text):
    """[(název nebo None pro úvod, [řádky včetně nadpisu])]."""
    out = [(None, [])]
    for r in text.replace("\r\n", "\n").split("\n"):
        if r.startswith("## "):
            out.append((nazev(r), [r]))
        else:
            out[-1][1].append(r)
    return out


def slozit(casti):
    return "\n".join("\n".join(r) for _, r in casti).rstrip("\n") + "\n"


def cti_stav():
    try:
        with open(STAV, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def telo(casti, jmeno):
    for n, r in casti:
        if n == jmeno:
            return [x for x in r[1:] if x.strip() and not x.lstrip().startswith("<!--")]
    return None


def otevrene_ukoly():
    return {u.id for f in fronta.FRONTY for u in fronta.nacti(f)[1]}


def kontrola_stavu(text=None):
    """Seznam nesouladů STAV.md s dělbou: předání nástrojem, úkoly ve frontách, podklady v gitu."""
    text = cti_stav() if text is None else text
    if text is None:
        return ["data/STAV.md chybí"]
    casti = oddily(text)
    jmena = [n for n, _ in casti if n]
    chyby = []
    for n in jmena:
        if n not in STANDARDNI:
            chyby.append(f"oddíl navíc „{n}“: úkoly z něj patří do front (fronta.py pridej), pak stav.py vyrad \"{n}\"")
    if "Rozpracováno" not in jmena:
        chyby.append("chybí oddíl „Rozpracováno“: stav.py predani ho založí")
    else:
        r = next(r for n, r in casti if n == "Rozpracováno")
        if not any(x.startswith(ZNACKA) for x in r):
            chyby.append("předání je vedené ručně: přepiš ho stav.py predani (úkoly odkazem, podklady verzované)")
        body = "\n".join(r)
        for p in sorted(set(re.findall(r"pracovni/[^\s`)'\",;]+", body))):
            chyby.append(f"předání odkazuje na neverzovaný podklad {p}: stav.py predani ho přesune do data/predani/")
        ids = otevrene_ukoly()
        for u in sorted(set(UKOL.findall(body)) - ids):
            chyby.append(f"předání odkazuje na úkol {u}, který ve frontách není")
    return chyby


def bez_textu(s):
    return not isinstance(s, str) or not s.strip()


def platna_cesta(p):
    c = p.replace("\\", "/")
    return bool(c) and not c.startswith(("/", "-")) and ":" not in c and ".." not in c.split("/")


def ignorovane(cesty):
    if not cesty or not git("rev-parse", "--git-dir").strip():
        return []
    try:
        r = subprocess.run(["git", "check-ignore", "--", *cesty], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        return [x for x in r.stdout.splitlines() if x.strip()]
    except (OSError, subprocess.SubprocessError):
        return []


def over_predani(d):
    """(chyby, položky, přesuny {z: do}) – nic nemění."""
    if not isinstance(d, dict) or d.get("schema") != "predani/1" or not isinstance(d.get("polozky"), list):
        return ["soubor není předání: čeká se {\"schema\": \"predani/1\", \"polozky\": [...]} (stav.py vzor)"], [], {}
    chyby, presuny, ids = [], {}, otevrene_ukoly()
    for i, p in enumerate(d["polozky"], 1):
        if not isinstance(p, dict):
            chyby.append(f"položka {i}: není objekt")
            continue
        for k in ("co", "dal"):
            if bez_textu(p.get(k)):
                chyby.append(f"položka {i}: chybí „{k}“")
        for k in ("co", "posledni_krok", "dal"):
            v = p.get(k)
            if v is None:
                continue
            if not isinstance(v, str):
                chyby.append(f"položka {i}: „{k}“ musí být text")
            elif len(v) > MAX_TEXT:
                chyby.append(f"položka {i}: „{k}“ má {len(v)} znaků (nejvýš {MAX_TEXT}); podrobnosti patří do úkolu nebo podkladu")
            elif "\n" in v or v.lstrip().startswith("#"):
                chyby.append(f"položka {i}: „{k}“ je jeden řádek bez nadpisu")
        for u in p.get("ukoly") or []:
            if not isinstance(u, str) or not UKOL.fullmatch(u):
                chyby.append(f"položka {i}: úkol {u!r} není ve tvaru U-0042")
            elif u not in ids:
                chyby.append(f"položka {i}: úkol {u} ve frontách není (hotový nebo neexistuje)")
        for c in p.get("podklady") or []:
            if not isinstance(c, str) or not platna_cesta(c):
                chyby.append(f"položka {i}: podklad {c!r} není cesta uvnitř projektu")
                continue
            c = c.replace("\\", "/")
            if not os.path.isfile(os.path.join(ROOT, c)):
                chyby.append(f"položka {i}: podklad {c} neexistuje")
            elif c.startswith("pracovni/"):
                cil = "data/predani/" + os.path.basename(c)
                if os.path.exists(os.path.join(ROOT, cil)) or cil in presuny.values() and presuny.get(c) != cil:
                    chyby.append(f"položka {i}: {cil} už existuje; přejmenuj podklad")
                presuny[c] = cil
    chyby += [f"podklad {c} git ignoruje (.gitignore); patří do data/" for c in ignorovane(
        [c.replace("\\", "/") for p in d["polozky"] if isinstance(p, dict) for c in p.get("podklady") or []
         if isinstance(c, str) and platna_cesta(c) and not c.replace("\\", "/").startswith("pracovni/")])]
    return chyby, d["polozky"], presuny


def oddil_predani(polozky, presuny):
    dnes = datetime.date.today()
    r = ["## Rozpracováno", "",
         f"{ZNACKA} (naposledy {dnes.day}. {dnes.month}. {dnes.year}); ručně neupravovat. Úkoly jsou ve frontách, tady jen odkaz. -->", ""]
    if not polozky:
        r.append("- (nic rozpracovaného)")
    for p in polozky:
        r.append(f"- {p['co'].strip()}")
        if not bez_textu(p.get("posledni_krok")):
            r.append(f"  - poslední krok: {p['posledni_krok'].strip()}")
        r.append(f"  - dál: {p['dal'].strip()}")
        if p.get("ukoly"):
            r.append("  - úkoly: " + ", ".join(p["ukoly"]))
        if p.get("podklady"):
            r.append("  - podklady: " + ", ".join(f"`{presuny.get(c.replace(chr(92), '/'), c.replace(chr(92), '/'))}`" for c in p["podklady"]))
    return r + [""]


def zapis_stav(novy, presuny, bez_commitu, zprava):
    """Přesuny podkladů a nový STAV.md: všechno, nebo nic. Pak commit přes commit.py."""
    hotove = []
    tmp = STAV + ".novy"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(novy)
        for z, do in presuny.items():
            os.makedirs(os.path.dirname(os.path.join(ROOT, do)), exist_ok=True)
            shutil.move(os.path.join(ROOT, z), os.path.join(ROOT, do))
            hotove.append((z, do))
        os.replace(tmp, STAV)
    except OSError as e:
        for z, do in reversed(hotove):
            shutil.move(os.path.join(ROOT, do), os.path.join(ROOT, z))
        if os.path.exists(tmp):
            os.remove(tmp)
        print(f"ZAPSÁNO NIC: {e}")
        return 1
    soubory = ["data/STAV.md"] + list(presuny.values())
    print("zapsáno: " + ", ".join(soubory))
    if bez_commitu:
        return 0
    if not git("rev-parse", "--git-dir").strip():
        print("projekt není v gitu: necommitováno")
        return 0
    import commit
    try:
        kod = commit.main(["--soubory", ",".join(soubory), "--zprava", zprava])
    except SystemExit as e:
        print(f"COMMIT NEPROBĚHL: {e}; zápis zůstává, commit spusť znovu tools/commit.py")
        return 1
    return 0 if kod in (0, None) else 1


def nahrad_oddil(casti, jmeno, radky, pred="Rozpracováno"):
    """Nahradí oddíl, nebo ho vloží před oddíl `pred` (jinak na konec)."""
    for i, (n, _) in enumerate(casti):
        if n == jmeno:
            casti[i] = (jmeno, radky)
            return casti
    i = next((i for i, (n, _) in enumerate(casti) if pred and n == pred), len(casti))
    if i == len(casti) and casti and casti[-1][1] and casti[-1][1][-1].strip():
        casti[-1][1].append("")
    casti.insert(i, (jmeno, radky))
    return casti


def prikaz_predani(argv):
    if not argv or argv[0].startswith("-"):
        print("použití: stav.py predani pracovni/predani.json [--nanecisto] [--bez-commitu]")
        return 2
    try:
        with open(os.path.join(ROOT, argv[0]), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        print(f"ODMÍTNUTO: soubor předání nejde přečíst: {e}")
        return 1
    text = cti_stav()
    if text is None:
        print("ODMÍTNUTO: data/STAV.md chybí (novy_projekt.py ho založí ze šablony)")
        return 1
    chyby, polozky, presuny = over_predani(d)
    if chyby:
        print("ODMÍTNUTO, nic se nezměnilo:\n  " + "\n  ".join(chyby))
        return 1
    novy = slozit(nahrad_oddil(oddily(text), "Rozpracováno", oddil_predani(polozky, presuny), pred=None))
    if "--nanecisto" in argv:
        print("nanečisto, nic se nezměnilo:\n" + "\n".join(oddil_predani(polozky, presuny))
              + ("\npřesunulo by se: " + ", ".join(f"{z} → {do}" for z, do in presuny.items()) if presuny else ""))
        return 0
    return zapis_stav(novy, presuny, "--bez-commitu" in argv, "Předání rozpracované práce do další session")


def prikaz_pravidlo(argv):
    text = argv[0] if argv and not argv[0].startswith("--") else ""
    if not text.strip() or "\n" in text or text.lstrip().startswith("#") or len(text) > MAX_TEXT:
        print(f"ODMÍTNUTO: pravidlo je jeden řádek textu do {MAX_TEXT} znaků (stav.py pravidlo \"…\")")
        return 1
    stav = cti_stav()
    if stav is None:
        print("ODMÍTNUTO: data/STAV.md chybí")
        return 1
    casti = oddily(stav)
    dnes = datetime.date.today()
    stavajici = next((r for n, r in casti if n == "Pravidla od uživatele"), None)
    radky = list(stavajici) if stavajici else ["## Pravidla od uživatele", "", "Co uživatel řekl, jak pracovat; připisuje tools/stav.py pravidlo.", ""]
    while radky and not radky[-1].strip():
        radky.pop()
    radky += [f"- {dnes.day}. {dnes.month}. {dnes.year}: {text.strip()}", ""]
    novy = slozit(nahrad_oddil(casti, "Pravidla od uživatele", radky))
    return zapis_stav(novy, {}, "--bez-commitu" in argv, "Pravidlo od uživatele do stavu projektu")


def prikaz_vyrad(argv):
    jmeno = argv[0].strip() if argv and not argv[0].startswith("--") else ""
    if jmeno in STANDARDNI:
        print(f"ODMÍTNUTO: „{jmeno}“ je stálý oddíl STAV.md; vyřadit jde jen oddíl navíc")
        return 1
    stav = cti_stav()
    casti = oddily(stav or "")
    najdi = [i for i, (n, _) in enumerate(casti) if n == jmeno]
    if not jmeno or not najdi:
        print(f"ODMÍTNUTO: oddíl „{jmeno}“ v data/STAV.md není; oddíly navíc vypíše stav.py kontrola")
        return 1
    odstraneno = casti.pop(najdi[0])[1]
    print("odstraněno z data/STAV.md (zůstává v historii gitu):\n" + "\n".join(odstraneno).rstrip())
    return zapis_stav(slozit(casti), {}, "--bez-commitu" in argv, "Stav projektu: vyřazen oddíl navíc (úkoly jsou ve frontách)")


def prikaz_uklid(argv):
    """Smaže pracovní soubory, které už nejsou potřeba: jen soubory v pracovni/, všechno, nebo nic. Chrání stav rozpracované práce
    (zadání a výsledky úkolů, které jsou ještě ve frontě, přerušené zápisy, cestu k pluginu)."""
    if not argv:
        print("použití: stav.py uklid pracovni/<soubor> [pracovni/<soubor> …]")
        return 2
    otevrene, chyby, cesty = otevrene_ukoly(), [], []
    pracovni = os.path.normcase(os.path.abspath(os.path.join(ROOT, "pracovni"))) + os.sep
    for a in argv:
        c = a.replace("\\", "/")
        plna = os.path.normcase(os.path.abspath(os.path.join(ROOT, c)))
        jmeno = os.path.basename(c)
        if not platna_cesta(c) or not c.startswith("pracovni/") or not plna.startswith(pracovni):
            chyby.append(f"{a}: mazat jde jen soubory v pracovni/")
        elif not os.path.isfile(plna):
            chyby.append(f"{a}: není soubor (složky se nemažou)")
        elif jmeno == ".plugin_root" or jmeno.endswith(".rozpracovano"):
            chyby.append(f"{a}: patří k běhu nástrojů (přerušený zápis dokončí zapis_vysledku.py)")
        elif c.split("/")[1:2] in (["zadani"], ["vysledky"]) and jmeno[:6] in otevrene:
            chyby.append(f"{a}: patří k úkolu {jmeno[:6]}, který je ještě ve frontě")
        else:
            cesty.append(plna)
    if chyby:
        print("ODMÍTNUTO, nic se nesmazalo:\n  " + "\n  ".join(chyby))
        return 1
    for p in cesty:
        os.remove(p)
    print(f"smazáno {len(cesty)}: " + ", ".join(argv))
    return 0


def opravneni():
    """Co smí badatel zapisovat – přímo z hooku pluginu, který platí hned (definice agenta je v dlouhém sezení z doby startu).
    Cestu k pluginu zapisuje hook zapis_koren.py do pracovni/.plugin_root. Bez ní nic."""
    try:
        with open(os.path.join(ROOT, "pracovni", ".plugin_root"), encoding="utf-8") as f:
            koren = f.read().strip()
        import importlib.util
        spec = importlib.util.spec_from_file_location("hlidac_orchestratora", os.path.join(koren, "hooks", "hlidac_orchestratora.py"))
        h = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(h)
        nastroje = ", ".join(sorted(h.NASTROJE_ORCH))
        texty = ", ".join(getattr(h, "TEXTY_BADATELE", ())) + (", pribehy/*.md" if getattr(h, "TEXTY_BADATELE", ()) else "")
        return (f"smíš zapisovat (platí teď, podle hooku): nástroje {nastroje}; soubory v pracovni/ a mereni/"
                + (f"; texty v data/: {texty}" if texty else "")
                + ("" if "STAV.md" in texty else "; data/STAV.md jen přes stav.py predani a pravidlo")
                + ". Když si nejsi jistý, zkus nástroj – zamítnutí řekne, co smíš.")
    except Exception:   # noqa: BLE001 – bez pluginu nebo starší hook: nic
        return ""


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    prikazy = {"predani": prikaz_predani, "pravidlo": prikaz_pravidlo, "vyrad": prikaz_vyrad, "uklid": prikaz_uklid}
    if argv and argv[0] in prikazy:
        return prikazy[argv[0]](argv[1:])
    if argv and argv[0] == "vzor":
        print(json.dumps(VZOR, ensure_ascii=False, indent=1))
        return 0
    if argv and argv[0] == "kontrola":
        chyby = kontrola_stavu()
        print("STAV.md v pořádku" if not chyby else "STAV.md:\n  " + "\n  ".join(chyby))
        return 1 if chyby else 0
    if argv and argv[0] != "--json":
        print(f"neznámý příkaz {argv[0]}; nápověda: stav.py --help")
        return 2
    s = sestav()
    text = cti_stav()
    casti = oddily(text) if text is not None else []
    s["pravidla_od_uzivatele"] = telo(casti, "Pravidla od uživatele") or []
    s["predani"] = telo(casti, "Rozpracováno") or []
    s["stav_md"] = kontrola_stavu(text) if text is not None else []
    if "--json" in argv:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    print(f"větev {s['vetev'] or '?'}, neuložených změn {s['neulozene']}, nástroje {s['verze'] or '?'}")
    op = opravneni()
    if op:
        print(op)
    if s["pravidla_od_uzivatele"]:
        print("pravidla od uživatele (data/STAV.md):\n" + "\n".join("  " + x for x in s["pravidla_od_uzivatele"] if x.lstrip().startswith("-")))
    print("předání z minulé session (data/STAV.md):\n" + ("\n".join("  " + x for x in s["predani"]) or "  nic"))
    if s["stav_md"]:
        print(f"STAV.md neodpovídá dělbě ({len(s['stav_md'])}×): stav.py kontrola")
    print("fronty: " + (", ".join(f"{f} {v['celkem']}" + (f" (probíhá {v['probiha']})" if v["probiha"] else "") + (f" (čeká {v['ceka']})" if v["ceka"] else "")
                                  for f, v in s["fronty"].items()) or "prázdné"))
    if s["rozpocet"]:
        r = s["rozpocet"]
        print(f"rozpočet okna {r['okno']}: {r['spotreba']}/{r['limit'] if r['limit'] is not None else 'bez limitu'}")
    if s["k_rozhodnuti"]:
        print(f"k rozhodnutí: {s['k_rozhodnuti']} (před předložením projít: fronta.py seznam rozhodnuti)")
    for z in s["nedokoncene_zapisy"]:
        print(f"NEDOKONČENÝ ZÁPIS: pracovni/{z} (zápis byl přerušen a soubory vráceny; spusť tools/zapis_vysledku.py znovu)")
    if not s["rozpracovano"]:
        print("rozpracováno: nic")
    for x in s["rozpracovano"]:
        print(f"{x['ukol']} ({x['fronta'] or 'mimo fronty'}, {x['stav_ukolu'] or '-'}), osoby {','.join(x['osoby']) or '-'}; hotovo, když: {x['dod'] or 'NEURČENO'}")
        casti = []
        if x["rozsah"]:
            casti.append("rozsah " + " + ".join(f"{a[0]}–{a[1]}" for a in x["rozsah"] if isinstance(a, list) and len(a) == 2))
        if x["nalez"] and x["nalez"].get("stary_tvar"):
            casti.append("výsledek ve starém tvaru")
        elif x["nalez"]:
            n = x["nalez"]
            casti.append(f"nález {n['stav']} (část {n['cast']})" + (f", chybí {', '.join(n['chybi'])}" if n["chybi"] else ""))
        if x["overeni"]:
            casti.append("ověřeno " + ", ".join(x["overeni"]))
        if x["posledni_udalost"]:
            casti.append("poslední " + x["posledni_udalost"])
        print("  " + "; ".join(casti) if casti else "  bez zadání")
        print("  dál: " + x["dalsi_krok"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
