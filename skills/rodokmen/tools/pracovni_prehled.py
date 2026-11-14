#!/usr/bin/env python3
"""Soupis toho, co už leží ve složce pracovni/, aby se snímek nestahoval z archivu znovu. Jen čte, nic nemění, nepoužívá síť.

Použití (z kořene projektu):
  pracovni_prehled.py                  -> stažené svazky ARONu (pracovni/aron/<apu>_<signatura>/): kolik snímků z kolika, rozsah čísel,
                                          které řádky deníku se jich týkají; pod tím ostatní složky (výřezy, snímky bez známé adresy)
  pracovni_prehled.py --hledej TEXT    -> jen svazky a řádky deníku, které obsahují všechna slova z TEXT (bez ohledu na velikost
                                          písmen a diakritiku), např. „Libice 365“; kód 1, když nic nenajde
  --json                               -> totéž jako JSON {svazky: […], ostatni: […], denik: […]}
  --slozka SLOŽKA                      -> jiná složka než pracovni

Vazba na deník je přibližná: řádek se přiřadí svazku, když zdroj nebo rozsah obsahuje signaturu jako samostatné slovo.
Soupis je hlavně historický: svazky stažené dřív do pracovni/aron/. Nové snímky se hledají a ukládají do sdílené mezipaměti
(tools/cache.py, stahování přes brzdu tools/slusne.py); před novým stažením se podívej sem i do mezipaměti (cache.py najdi).
"""
import json
import os
import re
import sys
import unicodedata

OBRAZKY = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


def bez_diakritiky(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t).casefold()) if unicodedata.category(c) != "Mn")


def nacti_json(cesta, vychozi):
    try:
        with open(cesta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vychozi


def nacti_denik(cesta="data/denik.jsonl"):
    radky = []
    try:
        with open(cesta, encoding="utf-8") as f:
            for r in f:
                r = r.strip()
                if r:
                    try:
                        radky.append(json.loads(r))
                    except ValueError:
                        pass
    except OSError:
        pass
    return radky


def obrazky(slozka):
    for koren, _, soubory in os.walk(slozka):
        for s in soubory:
            if s.lower().endswith(OBRAZKY):
                yield os.path.join(koren, s)


def cislo_snimku(nazev):
    """Pořadí snímku v názvu souboru ARONu (CZ_<id>_<fond>_<kód>_<pořadí>_sign-…); jinak poslední číslo oddělené podtržítky."""
    m = re.search(r"_(\d{3,5})_sign", nazev) or re.findall(r"_(\d{4,5})_", nazev)
    if isinstance(m, list):
        return int(m[-1]) if m else None
    return int(m.group(1))


def text_radku(r):
    z = r.get("zdroj")
    return " ".join(str(x) for x in (z.get("text") if isinstance(z, dict) else z, r.get("rozsah"), r.get("hledano"),
                                     r.get("nalez")) if x)


def radky_k_signature(denik, sign):
    if not sign:
        return []
    vzor = re.compile(r"(?<![\w])" + re.escape(sign) + r"(?![\w])")
    out = []
    for r in denik:
        z = r.get("zdroj")
        zdroj = z.get("text") if isinstance(z, dict) else z
        if vzor.search(f"{zdroj or ''} {r.get('rozsah') or ''}") and isinstance(r.get("id"), int):
            out.append(r["id"])
    return out


def svazky_aronu(slozka, svazky_json, denik):
    out = []
    aron = os.path.join(slozka, "aron")
    if not os.path.isdir(aron):
        return out
    for jmeno in sorted(os.listdir(aron)):
        cil = os.path.join(aron, jmeno)
        m = re.fullmatch(r"([0-9a-f]{8})_(.+)", jmeno)
        if not (os.path.isdir(cil) and m):
            continue
        apu, sign = m.groups()
        snimky = list(obrazky(cil))
        cisla = [c for c in (cislo_snimku(os.path.basename(s)) for s in snimky) if c is not None]
        info = svazky_json.get(apu) or {}
        out.append({
            "apu": apu, "signatura": sign, "slozka": os.path.relpath(cil).replace(os.sep, "/"),
            "svazek": info.get("svazek", ""), "archiv": info.get("archiv", ""), "url": info.get("url", ""),
            "snimku_stazeno": len(snimky), "snimku_celkem": info.get("snimku"),
            "od": min(cisla) if cisla else None, "do": max(cisla) if cisla else None,
            "mb": round(sum(os.path.getsize(s) for s in snimky) / 1048576, 1),
            "denik": radky_k_signature(denik, sign),
        })
    return out


def ostatni_slozky(slozka):
    out = []
    if not os.path.isdir(slozka):
        return out
    for jmeno in sorted(os.listdir(slozka)):
        cil = os.path.join(slozka, jmeno)
        if jmeno.startswith(".") or jmeno == "aron" or not os.path.isdir(cil):
            continue
        s = list(obrazky(cil))
        if s:
            out.append({"slozka": jmeno, "souboru": len(s), "mb": round(sum(os.path.getsize(x) for x in s) / 1048576, 1)})
    return out


def shoduje_se(slova, haystack):
    h = bez_diakritiky(haystack)
    return all(s in h for s in slova)


def hledej(slova, svazky, denik):
    sv = [s for s in svazky if shoduje_se(slova, " ".join(str(s[k]) for k in ("apu", "signatura", "svazek", "archiv")))]
    dn = [r for r in denik if shoduje_se(slova, text_radku(r))]
    return sv, dn


def text(svazky, ostatni, denik_radky=None):
    r = []
    for s in svazky:
        z = f"{s['od']}–{s['do']}" if s["od"] is not None else "?"
        r.append(f"{s['apu']}  sign. {s['signatura']}  {s['snimku_stazeno']}/{s['snimku_celkem'] or '?'} snímků (č. {z}, {s['mb']} MB)"
                 f"  {s['svazek'][:90]}")
        if s["denik"]:
            r.append("    deník: " + ", ".join(map(str, s["denik"])))
    if ostatni:
        r.append("Ostatní složky (výřezy a snímky bez známé adresy):")
        r += [f"  {o['slozka']}: {o['souboru']} souborů, {o['mb']} MB" for o in ostatni]
    if denik_radky:
        r.append("Řádky deníku:")
        r += [f"  {d.get('id')}: {str(d.get('hledano', ''))[:80]} → {d.get('vysledek', '')}" for d in denik_radky]
    return "\n".join(r) or "pracovni/ neobsahuje žádné stažené svazky ani snímky."


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    slozka = "pracovni"
    if "--slozka" in argv:
        i = argv.index("--slozka")
        slozka = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    hledane = None
    if "--hledej" in argv:
        i = argv.index("--hledej")
        hledane = [bez_diakritiky(x) for x in argv[i + 1].split()]
        argv = argv[:i] + argv[i + 2:]
    denik = nacti_denik()
    svazky = svazky_aronu(slozka, nacti_json("data/svazky.json", {}), denik)
    ostatni = ostatni_slozky(slozka)
    dn = []
    if hledane is not None:
        svazky, dn = hledej(hledane, svazky, denik)
        ostatni = []
        if not svazky and not dn:
            print("nic nenalezeno")
            return 1
    if "--json" in argv:
        print(json.dumps({"svazky": svazky, "ostatni": ostatni, "denik": [d.get("id") for d in dn]}, ensure_ascii=False, indent=1))
    else:
        print(text(svazky, ostatni, dn))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
