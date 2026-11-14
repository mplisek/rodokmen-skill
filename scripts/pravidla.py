#!/usr/bin/env python3
"""Pravidla pro agenty a jejich zdroj v zrcadle originálu (Fáze E, ADR 0005). Nástroj údržby repozitáře skillu, do projektů se nekopíruje.

Pravidla jsou odstavce `## R-<TÉMA>-<NNN>` v `skills/rodokmen-agents/rules/*.md` s poli `when`, `do`, `why`, `source`.
`source` je `soubor#nadpis` (soubor vůči `skills/rodokmen/`), samotný soubor (třeba `tools/slusne.py`), nebo `fork` (vlastní pravidlo).
Otisk zdrojového oddílu při poslední revizi je v `rules/zdroje.json`; změní-li se oddíl v zrcadle (třeba po sloučení z originálu),
pravidlo je zastaralé, dokud ho někdo nepřezkoumá a nepotvrdí.

Použití: python3 -I scripts/pravidla.py <příkaz> [--rules SLOŽKA] [--zrcadlo SLOŽKA]
  overit               pole, duplicity, existence zdroje, shoda otisku; chyba (kód 1) u zastaralého nebo nepotvrzeného pravidla
  potvrdit <id> | --vse   po revizi pravidla uloží nový otisk zdrojového oddílu
  pokryti              vypíše oddíly zrcadla (nadpisy „## “), ke kterým není žádné pravidlo (informativně)
"""
import argparse
import hashlib
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(REPO, "skills", "rodokmen-agents", "rules")
ZRCADLO = os.path.join(REPO, "skills", "rodokmen")
POVINNA = ("when", "do", "why", "source")
ID = re.compile(r"R-[A-Z]+-\d{3}")
NADPIS = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
POLE = re.compile(r"^([a-z]+):\s*(.*)$")


def normalizuj(text):
    return re.sub(r"\s+", " ", text).strip()


def otisk(text):
    return hashlib.sha256(normalizuj(text).encode("utf-8")).hexdigest()[:16]


def cti(cesta):
    with open(cesta, encoding="utf-8-sig", newline="") as f:
        return f.read().replace("\r\n", "\n")


def nacti_pravidla(rules):
    """({id: {pole…, 'soubor'}}, chyby)."""
    pravidla, chyby = {}, []
    if not os.path.isdir(rules):
        return pravidla, [f"složka pravidel {rules} neexistuje"]
    for jmeno in sorted(os.listdir(rules)):
        if not jmeno.endswith(".md"):
            continue
        akt, klic = None, None
        for radek in cti(os.path.join(rules, jmeno)).split("\n"):
            m = re.match(r"^##\s+(.*?)\s*$", radek)
            if m:
                rid = m.group(1)
                if not ID.fullmatch(rid):
                    chyby.append(f"{jmeno}: neplatné id pravidla „{rid}“ (tvar R-TÉMA-001)")
                    akt = None
                    continue
                if rid in pravidla:
                    chyby.append(f"{jmeno}: duplicitní id {rid} (je i v {pravidla[rid]['soubor']})")
                    akt = None
                    continue
                akt = pravidla[rid] = {"soubor": jmeno}
                klic = None
                continue
            if akt is None or radek.startswith("#"):
                continue
            p = POLE.match(radek)
            if p:
                klic = p.group(1)
                akt[klic] = p.group(2).strip()
            elif klic and radek[:1] in (" ", "\t") and radek.strip():
                akt[klic] += " " + radek.strip()
    return pravidla, chyby


def sekce(text, nadpis):
    """Text oddílu pod nadpisem (po další nadpis stejné nebo vyšší úrovně, bloky kódu se nepočítají) nebo None."""
    radky, nalezeno, uroven, out, v_kodu = text.split("\n"), False, 0, [], False
    for radek in radky:
        if radek.lstrip().startswith("```"):
            v_kodu = not v_kodu
        m = None if v_kodu else NADPIS.match(radek)
        if nalezeno:
            if m and len(m.group(1)) <= uroven:
                break
            out.append(radek)
        elif m and m.group(2) == nadpis:
            nalezeno, uroven = True, len(m.group(1))
    return "\n".join(out) if nalezeno else None


def vypocti(zdroj, zrcadlo):
    """(otisk, chyba) zdroje `soubor#nadpis` nebo `soubor`."""
    soubor, _, nadpis = zdroj.partition("#")
    cesta = os.path.join(zrcadlo, soubor)
    if not os.path.isfile(cesta):
        return None, f"zdrojový soubor {soubor} neexistuje"
    text = cti(cesta)
    if nadpis:
        s = sekce(text, nadpis)
        if s is None:
            return None, f"zdrojový oddíl „{nadpis}“ v {soubor} zmizel (nebo se přejmenoval)"
        return otisk(s), None
    return otisk(text), None


def zdroje_cesta(rules):
    return os.path.join(rules, "zdroje.json")


def nacti_zdroje(rules):
    p = zdroje_cesta(rules)
    return json.load(open(p, encoding="utf-8-sig")) if os.path.exists(p) else {}


def uloz_zdroje(rules, z):
    with open(zdroje_cesta(rules), "w", encoding="utf-8", newline="\n") as f:
        json.dump(z, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def cmd_overit(a):
    pravidla, chyby = nacti_pravidla(a.rules)
    zdroje = nacti_zdroje(a.rules)
    for rid, p in sorted(pravidla.items()):
        for pole in POVINNA:
            if not p.get(pole):
                chyby.append(f"{rid}: chybí pole {pole}")
        zdroj = p.get("source", "")
        if not zdroj or zdroj == "fork":
            continue
        ted, ch = vypocti(zdroj, a.zrcadlo)
        if ch:
            chyby.append(f"{rid}: {ch}")
            continue
        z = zdroje.get(rid)
        if not z:
            chyby.append(f"{rid}: pravidlo není potvrzené (python3 -I scripts/pravidla.py potvrdit {rid})")
        elif z.get("source") != zdroj:
            chyby.append(f"{rid}: pole source se změnilo od poslední revize – přezkoumej a potvrď (pravidla.py potvrdit {rid})")
        elif z.get("checked") != ted:
            chyby.append(f"{rid}: pravidlo je zastaralé, zdrojový oddíl {zdroj} se změnil od poslední revize – přezkoumej pravidlo "
                         f"a potvrď (pravidla.py potvrdit {rid})")
    for rid in sorted(set(zdroje) - set(pravidla)):
        chyby.append(f"{rid}: osiřelý záznam v zdroje.json (pravidlo už neexistuje)")
    for ch in chyby:
        print("CHYBA:", ch)
    print(f"pravidla: {len(pravidla)} pravidel, {len(chyby)} chyb")
    sys.exit(1 if chyby else 0)


def cmd_potvrdit(a):
    pravidla, chyby = nacti_pravidla(a.rules)
    if chyby:
        sys.exit("Pravidla mají chyby tvaru, nejdřív je oprav:\n  " + "\n  ".join(chyby))
    ids = sorted(pravidla) if a.vse else [a.id]
    zdroje = nacti_zdroje(a.rules)
    for rid in ids:
        if rid not in pravidla:
            sys.exit(f"Pravidlo {rid} neexistuje.")
        zdroj = pravidla[rid].get("source", "")
        if not zdroj or zdroj == "fork":
            zdroje.pop(rid, None)
            continue
        ted, ch = vypocti(zdroj, a.zrcadlo)
        if ch:
            sys.exit(f"{rid}: {ch}")
        zdroje[rid] = {"source": zdroj, "checked": ted}
    uloz_zdroje(a.rules, zdroje)
    print(f"potvrzeno: {', '.join(ids) if not a.vse else str(len(ids)) + ' pravidel'}")


def cmd_pokryti(a):
    pravidla, _ = nacti_pravidla(a.rules)
    kryto = {p["source"].partition("#")[0] + "#" + p["source"].partition("#")[2] for p in pravidla.values() if "#" in p.get("source", "")}
    soubory = [os.path.join(a.zrcadlo, "SKILL.md")] + [os.path.join(a.zrcadlo, "reference", f)
                                                        for f in sorted(os.listdir(os.path.join(a.zrcadlo, "reference")))
                                                        if f.endswith(".md")] if os.path.isdir(os.path.join(a.zrcadlo, "reference")) else []
    bez, vsechny = [], 0
    for cesta in soubory:
        if not os.path.isfile(cesta):
            continue
        rel = os.path.relpath(cesta, a.zrcadlo).replace("\\", "/")
        v_kodu = False
        for radek in cti(cesta).split("\n"):
            if radek.lstrip().startswith("```"):
                v_kodu = not v_kodu
            m = None if v_kodu else re.match(r"^##\s+(.*?)\s*$", radek)
            if m:
                vsechny += 1
                if f"{rel}#{m.group(1)}" not in kryto:
                    bez.append(f"{rel}#{m.group(1)}")
    for x in bez:
        print(x)
    print(f"pokrytí: {vsechny - len(bez)} z {vsechny} oddílů „## “ zrcadla má pravidlo; bez pravidla {len(bez)} (informativně)")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    spolecne = argparse.ArgumentParser(add_help=False)
    spolecne.add_argument("--rules", default=RULES)
    spolecne.add_argument("--zrcadlo", default=ZRCADLO)
    ap = argparse.ArgumentParser(prog="pravidla.py", add_help=False)
    sub = ap.add_subparsers(dest="prikaz", required=True)
    sub.add_parser("overit", parents=[spolecne]).set_defaults(fn=cmd_overit)
    p = sub.add_parser("potvrdit", parents=[spolecne])
    p.add_argument("id", nargs="?")
    p.add_argument("--vse", action="store_true")
    p.set_defaults(fn=cmd_potvrdit)
    sub.add_parser("pokryti", parents=[spolecne]).set_defaults(fn=cmd_pokryti)
    a = ap.parse_args()
    if a.prikaz == "potvrdit" and not (a.id or a.vse):
        sys.exit("potvrdit: zadej id pravidla nebo --vse")
    a.fn(a)


if __name__ == "__main__":
    main()
