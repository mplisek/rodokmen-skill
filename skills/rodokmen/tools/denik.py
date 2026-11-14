#!/usr/bin/env python3
"""Výzkumný deník jako strukturovaná data (data/denik.jsonl, jen přidávání). Tabulka na webu se z něj generuje.

Použití (z kořene projektu): python3 -I tools/denik.py <příkaz> …
  pridej --datum RRRR-MM-DD --zdroj-typ archiv|stopa|rodina|jiné --zdroj TEXT --hledano VĚTA
         --vysledek nalezeno|vyvráceno|nenalezeno|částečně|nečitelné [--overeno] [--rozsah TEXT]
         [--nalez VĚTA (do 400 znaků)] [--citace TEXT] [--poznamka TEXT] [--osoby a,b] [--odkaz KLÍČ] [--opravuje ID]
                              přidá záznam; chybný záznam se odmítne a soubor se nezmění. Oprava = nový záznam s --opravuje
  vykresli [--do SOUBOR]      tabulka v Markdownu (opravené a nedořešené záznamy se nevykreslí)
  over                        zkontroluje celý soubor (schéma, zakázané vzory, duplicity, odkazy na opravované)
  migruj [--zdroj SOUBOR] [--znovu]
                              převede dosavadní tabulku research_log.md na denik.jsonl, protokol k ruční kontrole
                              zapíše do pracovni/migrace_denik.md
  overit-migraci [--zdroj SOUBOR]
                              ověří, že každý řádek původní tabulky má záznam a původní text se doslova shoduje

Pravidla: reference/zapisy.md, ADR 0002. Zakázané v textech pro web: čísla úkolů, jména agentů a modelů, cesty, údaje
o procesu, opravy uvnitř textu, mezera před dvojtečkou, šipky.
"""
import argparse
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import zaznamy_store as store  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
LOG = os.path.join(DATA, "denik.jsonl")
STARY = os.path.join(DATA, "research_log.md")
PROTOKOL = os.path.join(ROOT, "pracovni", "migrace_denik.md")

TYPY_ZDROJE = ("archiv", "stopa", "rodina", "jiné")
VYSLEDKY = ("nalezeno", "vyvráceno", "nenalezeno", "částečně", "nečitelné")
ROZSAH_POVINNY = ("nenalezeno", "vyvráceno", "částečně", "nečitelné")   # negativní výsledek vždy s rozsahem
NALEZ_POVINNY = ("nalezeno", "vyvráceno")
VEREJNA_POLE = ("rozsah", "hledano", "nalez", "citace", "poznamka", "odkaz")
SLOUPCE = ("#", "datum", "zdroj", "rozsah", "hledáno", "výsledek", "nález", "citace", "odkaz")
MAX_HLEDANO, MAX_NALEZ = 160, 400


def over_zaznam(z, id_pred=()):
    """Seznam chyb jednoho záznamu. id_pred = id záznamů před ním (pro kontrolu --opravuje)."""
    chyby = []
    if not isinstance(z.get("id"), int) or isinstance(z.get("id"), bool) or z["id"] < 1:
        chyby.append("id: celé číslo od 1")
    if z.get("k_rucni_kontrole"):   # migrovaný záznam k ruční kontrole: stačí původní text, na web nejde
        if not z.get("puvodni"):
            chyby.append("puvodni: záznam k ruční kontrole musí nést původní text")
        return chyby
    if not store.je_datum(z.get("datum")):
        chyby.append("datum: tvar RRRR-MM-DD (skutečné datum)")
    zd = z.get("zdroj")
    if not isinstance(zd, dict) or zd.get("typ") not in TYPY_ZDROJE or not str(zd.get("text") or "").strip():
        chyby.append(f"zdroj: {{typ: {'|'.join(TYPY_ZDROJE)}, text}} – typ a text jsou povinné")
    vys = z.get("vysledek")
    if vys not in VYSLEDKY:
        chyby.append(f"vysledek: jedna z hodnot {', '.join(VYSLEDKY)}")
    hl = str(z.get("hledano") or "")
    if not hl.strip():
        chyby.append("hledano: povinné, jedna věta")
    elif len(hl) > MAX_HLEDANO:
        chyby.append(f"hledano: nejvýš {MAX_HLEDANO} znaků (je {len(hl)})")
    nal = str(z.get("nalez") or "")
    if len(nal) > MAX_NALEZ:
        chyby.append(f"nalez: nejvýš {MAX_NALEZ} znaků (je {len(nal)}); zbytek patří do poznamka")
    if vys in ROZSAH_POVINNY and not str(z.get("rozsah") or "").strip():
        chyby.append(f"rozsah: povinný u výsledku {vys} (co přesně se prošlo)")
    if vys in NALEZ_POVINNY and not nal.strip():
        chyby.append(f"nalez: povinný u výsledku {vys}")
    if "osoby" in z and not (isinstance(z["osoby"], list) and all(isinstance(x, str) for x in z["osoby"])):
        chyby.append("osoby: seznam klíčů osob")
    if z.get("opravuje") is not None and z["opravuje"] not in id_pred:
        chyby.append(f"opravuje: záznam {z['opravuje']} neexistuje")
    texty = [("zdroj", (zd or {}).get("text", "") if isinstance(zd, dict) else "")] + [(p, str(z.get(p) or "")) for p in VEREJNA_POLE]
    for pole, text in texty:
        for nazev, nalezeno in store.zakazane_vzory(text):
            chyby.append(f"{pole}: zakázaný vzor „{nazev}“: {nalezeno}")
    return chyby


def nacti_zaznamy():
    """(záznamy, chyby) – chyby jsou řádky s číslem řádku; duplicity id a odkazy na opravované se kontrolují tady."""
    zaznamy, chyby, videna = [], [], set()
    for n, z, e in store.nacti(LOG):
        if e:
            chyby.append(f"řádek {n}: {e}")
            continue
        for ch in over_zaznam(z, videna):
            chyby.append(f"řádek {n} (id {z.get('id')}): {ch}")
        if z.get("id") in videna:
            chyby.append(f"řádek {n}: duplicitní id {z.get('id')}")
        videna.add(z.get("id"))
        zaznamy.append(z)
    return zaznamy, chyby


def vykresli(zaznamy):
    nahrazene = {z.get("opravuje") for z in zaznamy if z.get("opravuje") is not None}
    radky = ["| " + " | ".join(SLOUPCE) + " |", "|" + "---|" * len(SLOUPCE)]
    for z in sorted(zaznamy, key=lambda x: x.get("id", 0)):
        if z.get("id") in nahrazene or z.get("k_rucni_kontrole"):
            continue
        nalez = store.bunka(z.get("nalez"))
        if z.get("poznamka"):
            nalez = (nalez + " " if nalez else "") + "<details><summary>poznámka</summary>" + store.bunka(z["poznamka"]) + "</details>"
        vys = z["vysledek"] + (" (ověřeno)" if z.get("overeno") else "")
        bunky = [z["id"], z["datum"], z["zdroj"]["text"], z.get("rozsah"), z.get("hledano"), vys]
        radky.append("| " + " | ".join(store.bunka(b) for b in bunky) + " | " + nalez + " | " + store.bunka(z.get("citace"))
                     + " | " + store.bunka(z.get("odkaz")) + " |")
    if len(radky) == 2:   # není co ukázat (prázdný deník): stránka nemá prázdnou tabulku
        return ""
    return "\n".join(radky) + "\n"


def cmd_pridej(a):
    zaznamy, chyby = nacti_zaznamy()
    if chyby:
        sys.exit("denik.jsonl má chyby, nejdřív je oprav (denik.py over):\n  " + "\n  ".join(chyby[:10]))
    z = {"id": max([x["id"] for x in zaznamy], default=0) + 1, "datum": a.datum,
         "zdroj": {"typ": a.zdroj_typ, "text": a.zdroj}, "rozsah": a.rozsah or "", "hledano": a.hledano,
         "vysledek": a.vysledek}
    if a.overeno:
        z["overeno"] = True
    for pole in ("nalez", "citace", "poznamka", "odkaz"):
        if getattr(a, pole):
            z[pole] = getattr(a, pole)
    if a.osoby:
        z["osoby"] = [x.strip() for x in a.osoby.split(",") if x.strip()]
    if a.opravuje is not None:
        z["opravuje"] = a.opravuje
    ch = over_zaznam(z, {x["id"] for x in zaznamy})
    if ch:
        sys.exit("Záznam se neuložil:\n  " + "\n  ".join(ch))
    with store.Zamek(LOG):
        store.pridej_radek(LOG, z)
    print(f"deník: záznam {z['id']} uložen")


def cmd_vykresli(a):
    zaznamy, chyby = nacti_zaznamy()
    if chyby:
        sys.exit("denik.jsonl má chyby (denik.py over):\n  " + "\n  ".join(chyby[:10]))
    md = vykresli(zaznamy)
    if a.do:
        cil = os.path.join(ROOT, a.do)
        os.makedirs(os.path.dirname(cil), exist_ok=True)
        with open(cil, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        print(f"deník: tabulka zapsána do {a.do}")
    else:
        sys.stdout.write(md)


def cmd_over(a):
    zaznamy, chyby = nacti_zaznamy()
    if chyby:
        print("\n".join(chyby))
        sys.exit(f"denik.jsonl: {len(chyby)} chyb")
    print(f"denik.jsonl v pořádku ({len(zaznamy)} záznamů)")


# ---------------------------------------------------------------- migrace research_log.md -> denik.jsonl
ARCHIV = re.compile(r"ARON|SOA|SOkA|AHMP|eBadatelna|MZA|Porta|Matricula|FamilySearch|Geneteka|Třeboň|\bZA\b|Zemský archiv|"
                    r"Národní archiv|\bNA\b|Matriční úřad|matriční úřad|kronik", re.I)
KLIC = re.compile(r"^\*\*([^*]+)\*\*\s*(.*)$", re.S)
VETA = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ„\"])")
ZAVORKA = re.compile(r"\s*\([^()]*\)")
PREDPONA = re.compile(r"^([^:]{1,90}):\s+(?=\S)")   # „Pomocník (sonnet) + moje kontrola: ARON …“ – kdo práci udělal


def zdrojove_radky(cesta):
    """Řádky tabulky původního deníku (doslova, bez záhlaví a oddělovače)."""
    if not os.path.exists(cesta):
        sys.exit(f"Původní deník {os.path.relpath(cesta, ROOT)} neexistuje.")
    out = []
    for r in open(cesta, encoding="utf-8-sig").read().splitlines():
        if r.startswith("|") and not re.match(r"^\|\s*-{3}", r) and not re.match(r"^\|\s*#\s*\|", r):
            out.append(r)
    return out


def bunky_radku(radek):
    return [c.strip() for c in re.split(r"(?<!\\)\|", radek.strip())[1:-1]]


def sanitizuj(text):
    """(čistý text, odebrané části, zda se něco změnilo): procesní údaje pryč, věcný obsah zůstane."""
    puvodni, odebrano = text, []
    m = PREDPONA.match(text)
    if m and store.zakazane_vzory(m.group(1)):   # předpona s procesním údajem pryč, věcná část za dvojtečkou zůstane
        odebrano.append(m.group(1).strip())
        text = text[m.end():]
    while True:   # závorky s procesním údajem
        zm = next((m for m in ZAVORKA.finditer(text) if store.zakazane_vzory(m.group(0))), None)
        if not zm:
            break
        odebrano.append(zm.group(0).strip())
        text = text[:zm.start()] + text[zm.end():]
    vety = VETA.split(text)
    if len(vety) > 1 or store.zakazane_vzory(text):
        ponechat = []
        for v in vety:
            if store.zakazane_vzory(v):
                odebrano.append(v.strip())
            else:
                ponechat.append(v)
        text = " ".join(ponechat)
    text = re.sub(r"([^\W\d_]) :", r"\1:", text).replace("->", "→")
    text = re.sub(r"\s+([.,;])", r"\1", text).strip()
    return text, odebrano, text != puvodni.strip()


def rozdel(text, maximum):
    """(začátek do maxima znaků, zbytek): řez na konci věty, jinak na mezeře; nic se neztratí."""
    if len(text) <= maximum:
        return text, ""
    cast = text[:maximum]
    for rx in (r"[.!?]\s", r"\s"):
        m = list(re.finditer(rx, cast))
        if m:
            i = m[-1].end()
            return text[:i].strip(), text[i:].strip()
    return cast, text[maximum:].strip()


def typ_zdroje(text):
    t = text.strip().lower()
    if t.startswith("(stopa") or t.startswith("stopa"):
        return "stopa"
    if re.match(r"(rodina|rodin[aouy]|od rodiny|udaje od rodiny)\b", t):
        return "rodina"
    return "archiv" if ARCHIV.search(text) else "jiné"


def prevod_vysledku(klic):
    """(výsledek, ověřeno, odhad): odhad = klíč nebyl ze schváleného seznamu, mapuje se podle slov a jde do protokolu."""
    k = klic.strip().lower()
    over = "ověřeno" in k and "neověřeno" not in k or k.startswith("potvrzeno")
    if "nečiteln" in k or "nepřečten" in k:
        return "nečitelné", False, k.split()[0] not in ("nenalezeno", "nečitelné")
    if k.startswith("nenalezeno"):
        return "nenalezeno", False, False
    if k.startswith("vyvráceno"):
        return "vyvráceno", over, False
    if k.startswith("částečně") or k.startswith("nedočteno"):
        return "částečně", False, False
    if k.startswith("nalezeno") or k.startswith("potvrzeno"):
        return "nalezeno", over, False
    # volnější klíče ze starých řádků: mapují se odhadem podle slov (v protokolu ke kontrole)
    if "negativn" in k:
        return "nenalezeno", False, True
    if k.startswith("vyloučen"):
        return "vyvráceno", False, True
    if re.match(r"stop[ayu]\b", k):
        return "částečně", False, True
    if re.search(r"\b(?:ověřen|potvrzen|přečten)", k) and not re.search(r"neověřen|nepotvrzen|nepřečten", k):
        return "nalezeno", True, True
    if "nenalezen" in k or "nic nenašl" in k or "bez jistého" in k or "bez přímého" in k:
        return "nenalezeno", False, True
    if re.search(r"kandidát|stopa|zatím jen|rozpracováno|neověřeno|nejist", k):
        return "částečně", False, True
    if k.startswith("ověřeno") or re.search(r"\bnalezen", k):
        return "nalezeno", "ověřeno" in k, True
    return None, False, False


KONTEXT = re.compile(r"^(?:osob[ay]\s+)?\d[\d,\s–-]*$|\(\s*\d[\d,\s–-]*\)\s*$")
CISLA_OSOB = re.compile(r"\s*\(\s*\d[\d,\s–-]*\)")


def je_kontext(text, maximum=120):
    """Sloupec „hledáno“ ve starém deníku často nese jen rod nebo osoby s čísly (Culkové (72, 73), „osoba 24“, „144, 145“),
    ne větu o tom, co se hledalo."""
    t = (text or "").strip()
    return bool(t) and t not in ("–", "-") and len(t) <= maximum and bool(KONTEXT.search(t))


def bez_cisel_osob(text):
    """Text bez čísel osob v závorkách; zbude-li jen číslice a čárky, je výsledek prázdný."""
    t = CISLA_OSOB.sub("", text or "").strip(" ,;")
    return "" if re.fullmatch(r"[\d,\s–-]*", t) else t


def migruj_radek(radek, nahradni_id):
    """(záznam, důvody k ruční kontrole, odebrané procesní části)."""
    c = bunky_radku(radek)
    duvody, odebrano = [], []
    z = {"id": int(c[0]) if c and c[0].isdigit() else nahradni_id}
    posun = False   # sloupce se v řádku používaly jinak než v záhlaví: přeřazeno, jde to do protokolu
    if len(c) == 6:   # starší řádky bez sloupce rozsah (rozsah je ve zdroji): zdroj, hledáno, výsledek, citace
        c = c[:3] + [""] + c[3:]
        posun = True
    if len(c) != 7:
        duvody.append(f"řádek má {len(c)} sloupců místo 7")
        z.update(k_rucni_kontrole=True, puvodni=radek, duvod="; ".join(duvody))
        if len(c) >= 3:
            z["zdroj"] = {"typ": typ_zdroje(c[2]), "text": c[2]}
        return z, duvody, odebrano
    _, datum, zdroj, rozsah, hledano, vysledek, citace = c
    prazdne = ("", "–", "-")
    if je_kontext(hledano) and rozsah not in prazdne:        # hledáno = kontext, věta o hledání je ve sloupci rozsah
        nove = bez_cisel_osob(rozsah)
        if nove:
            rozsah, hledano, posun = "", nove, True
    elif hledano in prazdne and je_kontext(rozsah):          # hledáno prázdné, rod s čísly osob je ve sloupci rozsah
        nove = bez_cisel_osob(rozsah)
        if nove:
            rozsah, hledano, posun = "", nove, True
    if not store.je_datum(datum):
        duvody.append(f"datum „{datum}“ není RRRR-MM-DD")
    z["datum"] = datum
    typ = typ_zdroje(zdroj)
    zz, odeb, zm = sanitizuj(zdroj)
    odebrano += odeb
    z["zdroj"] = {"typ": typ, "text": zz}
    roz, odeb, zmr = sanitizuj("" if rozsah in ("–", "-") else rozsah)
    odebrano += odeb
    z["rozsah"] = roz
    m = KLIC.match(vysledek)
    vys, over, odhad = prevod_vysledku(m.group(1)) if m else (None, False, False)
    zbytek = m.group(2) if m else vysledek
    if vys is None:
        if typ == "stopa" and not m:   # stopa při čtení: není to hledání, věcný údaj je v textu
            vys = "nalezeno"
            hledano = "stopa při čtení" if hledano in ("–", "-", "") else hledano
        else:
            duvody.append("výsledek nemá rozpoznatelný klíč (**nalezeno** apod.)")
            vys = "nalezeno"
    if vys == "nalezeno" and odhad and "nenalezen" in zbytek[:300].lower():   # „křest nalezen, sňatek nenalezen“
        vys = "částečně"
    z["vysledek"] = vys
    if over:
        z["overeno"] = True
    hl, odeb, zm1 = sanitizuj("" if hledano in ("–", "-") else hledano)
    odebrano += odeb
    if not hl.strip() and roz.strip() and not posun:   # sloupec hledáno měl jen procesní text: věta o hledání je v rozsahu
        hl, roz, posun = roz, "", True
        z["rozsah"] = ""
    if posun and not roz.strip() and vys in ROZSAH_POVINNY:   # u posunutých řádků je rozsah (co se prošlo) ve zdroji
        z["rozsah"] = zz
    poznamka = []
    hl2, zbyt = rozdel(hl, MAX_HLEDANO)
    if zbyt:
        poznamka.append("Hledáno (celé): " + hl)
    z["hledano"] = hl2
    nalez, odeb, zm2 = sanitizuj(zbytek)
    odebrano += odeb
    nalez, zbyt = rozdel(nalez, MAX_NALEZ)
    if zbyt:
        poznamka.append(zbyt)
    if nalez:
        z["nalez"] = nalez
    cit, odeb, zm3 = sanitizuj("" if citace in ("–", "-") else citace)
    odebrano += odeb
    if cit:
        z["citace"] = cit
    if poznamka:
        z["poznamka"] = " ".join(poznamka)
    z["puvodni"] = radek
    if odebrano:
        z["proces"] = odebrano
    if odebrano or odhad or posun or zm or zmr or zm1 or zm2 or zm3:
        z["uprava_automaticky"] = True
    duvody += [x for x in over_zaznam(dict(z), ()) if not x.startswith("id:")]
    if duvody:
        z["k_rucni_kontrole"] = True
        z["duvod"] = "; ".join(duvody)
    return z, duvody, odebrano


def cmd_migruj(a):
    zdroj = os.path.join(ROOT, a.zdroj) if a.zdroj else STARY
    radky = zdrojove_radky(zdroj)
    if os.path.exists(LOG):
        stare = [z for _, z, e in store.nacti(LOG) if z]
        if not a.znovu:
            sys.exit("data/denik.jsonl už existuje, nic jsem nepřepsal. Znovu jen s --znovu (smí jen tehdy, když jsou v něm "
                     "samé migrované záznamy).")
        if any(not z.get("puvodni") for z in stare):
            sys.exit("denik.jsonl obsahuje i ručně přidané záznamy, --znovu by je smazalo. Nic jsem nezměnil.")
    zaznamy, vsechny_duvody, procesni, videna = [], {}, {}, set()
    cisla = [int(bunky_radku(r)[0]) for r in radky if bunky_radku(r) and bunky_radku(r)[0].isdigit()]
    nahradni = max(cisla or [0]) + 1
    for r in radky:
        z, duvody, odebrano = migruj_radek(r, nahradni)
        if z["id"] in videna:   # duplicitní číslo: nové id, řádek k ruční kontrole
            z["id"] = nahradni
            duvody.append("duplicitní číslo řádku")
            z["k_rucni_kontrole"] = True
            z["duvod"] = "; ".join(duvody)
        nahradni = max(nahradni, z["id"] + 1)
        videna.add(z["id"])
        if duvody:
            vsechny_duvody[z["id"]] = duvody
        if odebrano:
            procesni[z["id"]] = odebrano
        zaznamy.append(z)
    text = "".join(json.dumps(z, ensure_ascii=False) + "\n" for z in sorted(zaznamy, key=lambda x: x["id"]))
    os.makedirs(DATA, exist_ok=True)
    tmp = LOG + ".tmp"
    with store.Zamek(LOG):
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, LOG)
    os.makedirs(os.path.dirname(PROTOKOL), exist_ok=True)
    with open(PROTOKOL, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Migrace deníku: protokol\n\n")
        f.write(f"Záznamů: {len(zaznamy)}; k ruční kontrole (na web nejdou, dokud se neopraví): {len(vsechny_duvody)}; "
                f"s automaticky odebranými procesními údaji: {len(procesni)}.\n\n")
        f.write("## K ruční kontrole\n\n")
        for i, d in sorted(vsechny_duvody.items()):
            f.write(f"- {i}: {'; '.join(d)}\n")
        f.write("\n## Odebrané procesní údaje (zůstaly v poli proces, na web nejdou)\n\n")
        for i, o in sorted(procesni.items()):
            f.write(f"- {i}: " + " | ".join(o) + "\n")
    print(f"deník: převedeno {len(zaznamy)} řádků, k ruční kontrole {len(vsechny_duvody)}, protokol "
          f"{os.path.relpath(PROTOKOL, ROOT)}")


def cmd_overit_migraci(a):
    zdroj = os.path.join(ROOT, a.zdroj) if a.zdroj else STARY
    radky = zdrojove_radky(zdroj)
    zbyva = {}
    for _, z, e in store.nacti(LOG):
        if z and z.get("puvodni"):
            zbyva[z["puvodni"]] = zbyva.get(z["puvodni"], 0) + 1
    chyby = []
    for r in radky:
        if zbyva.get(r, 0) > 0:
            zbyva[r] -= 1
        else:
            cislo = (bunky_radku(r) or ["?"])[0]
            chyby.append(f"řádek {cislo} původního deníku nemá v denik.jsonl záznam se shodným původním textem")
    if chyby:
        print("\n".join(chyby))
        sys.exit(f"Migrace není úplná: {len(chyby)} řádků chybí nebo se liší.")
    print(f"Migrace ověřena: všech {len(radky)} řádků původního deníku je v denik.jsonl a původní text se shoduje.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    ap = argparse.ArgumentParser(prog="denik.py", add_help=False)
    sub = ap.add_subparsers(dest="prikaz", required=True)
    p = sub.add_parser("pridej")
    p.add_argument("--datum", required=True)
    p.add_argument("--zdroj-typ", dest="zdroj_typ", required=True)
    p.add_argument("--zdroj", required=True)
    p.add_argument("--hledano", required=True)
    p.add_argument("--vysledek", required=True)
    p.add_argument("--rozsah")
    p.add_argument("--nalez")
    p.add_argument("--citace")
    p.add_argument("--poznamka")
    p.add_argument("--osoby")
    p.add_argument("--odkaz")
    p.add_argument("--opravuje", type=int)
    p.add_argument("--overeno", action="store_true")
    p.set_defaults(fn=cmd_pridej)
    p = sub.add_parser("vykresli")
    p.add_argument("--do")
    p.set_defaults(fn=cmd_vykresli)
    p = sub.add_parser("over")
    p.set_defaults(fn=cmd_over)
    p = sub.add_parser("migruj")
    p.add_argument("--zdroj")
    p.add_argument("--znovu", action="store_true")
    p.set_defaults(fn=cmd_migruj)
    p = sub.add_parser("overit-migraci")
    p.add_argument("--zdroj")
    p.set_defaults(fn=cmd_overit_migraci)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
