#!/usr/bin/env python3
"""Jednorázová migrace projektu na metodiku originálu (analyza/zjednoduseni-badani.md, oddíl 11): fronty úkolů → plán
data/ukoly.md, dotazy na archivy → data/archivni_dotazy.md, otázky pro rodinu a rozhodnutí → soubor k ručnímu zpracování.
Nástroj údržby repozitáře skillu, do projektů se nekopíruje; po migraci se odstraní (fork používá jen jeden uživatel).

Použití: python3 -I scripts/migrace_a.py <složka projektu> [--zapsat]
  bez --zapsat  nic v data/ nemění; zapíše pracovni/migrace_a_prehled.md – každý úkol s navrženým řádkem plánu
                a upozorněním (možná duplicita, osoba má otevřenou otázku v ISSUES, čekalo) k projití s uživatelem
  --zapsat      zapíše plán do data/ukoly.md (pod nadpisy Křty, Sňatky, Úmrtí, Jiné), dotazy připíše do data/archivni_dotazy.md
                a otázky pro rodinu a rozhodnutí do pracovni/migrace_a_rucne.md; fronty nemaže – archivaci vypíše jako příkazy
                pro git (soubory zůstanou v historii projektu)
Čísla úkolů jsou jen v přehledu (kvůli dohledání), do plánu se nepíšou. Definice hotového, ceny a stavy se zahazují.
"""
import os
import re
import runpy
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

FRONTY = {"vstup": "ukoly_vstup.md", "noc": "ukoly_na_noc.md", "rozhodnuti": "ukoly_k_rozhodnuti.md", "badani": "ukoly_k_badani.md",
          "dotazy": "ukoly_dotazy_na_archivy.md", "rodina": "ukoly_na_rodinu.md"}
HLAVICKA = re.compile(r"^##+ (U-\d+)\s*\|(.*)$")
POMOCNE = re.compile(r"^\s*(?:Definice hotového|Otázka|Možnosti|Důkazy|Zkoušeno|Doporučení|Výchozí postup|Cíl|Zdroj|Postup)\s*:", re.I)
DRUH = {"krest": "Křty", "křest": "Křty", "snatek": "Sňatky", "sňatek": "Sňatky", "umrti": "Úmrtí", "úmrtí": "Úmrtí"}
NADPISY = ("Křty", "Sňatky", "Úmrtí", "Jiné")


def nacti_frontu(path):
    """[(id, {pole hlavičky}, [řádky textu])]."""
    if not os.path.exists(path):
        return []
    out, akt = [], None
    for r in open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").split("\n"):
        m = HLAVICKA.match(r)
        if m:
            pole = {}
            for x in (y.strip() for y in m.group(2).split("|")):
                if ":" in x:
                    k, v = x.split(":", 1)
                    pole[k.strip()] = v.strip()
            akt = (m.group(1), pole, [])
            out.append(akt)
        elif akt is not None:
            akt[2].append(r)
    return out


def veta(text):
    """První věcný řádek textu úkolu, bez pomocných polí, nejvýš 200 znaků."""
    for r in text:
        s = r.strip().lstrip("-* ").strip()
        if s and not POMOCNE.match(s) and not s.startswith("#"):
            s = " ".join(s.split())
            return s if len(s) <= 200 else s[:199].rstrip() + "…"
    return ""


def osoby_ukolu(pole):
    return [a for a in re.split(r"[,\s]+", pole.get("os", "")) if a]


def otevrene_issues(projekt):
    try:
        ns = runpy.run_path(os.path.join(projekt, "data", "osoby.py"))
    except Exception:   # noqa: BLE001 – bez osob jen bez upozornění
        return set()
    out = set()
    for i in ns.get("ISSUES", []) or []:
        if isinstance(i, dict) and str(i.get("stav", "")).lower().startswith(("otev", "hypot")):
            out.add(str(i.get("k")))
    return out


def plan(projekt):
    issues = otevrene_issues(projekt)
    polozky, videno = [], {}
    for fronta, soubor in FRONTY.items():
        for uid, pole, text in nacti_frontu(os.path.join(projekt, "data", soubor)):
            os_ = osoby_ukolu(pole)
            typ = pole.get("typ", "").lower()
            radek = (f"{', '.join(os_)} – " if os_ else "") + veta(text)
            pozn = []
            klic = (tuple(sorted(os_)), typ)
            if os_ and klic in videno:
                pozn.append(f"možná duplicita s {videno[klic]}")
            videno.setdefault(klic, uid)
            if any(o in issues for o in os_):
                pozn.append("osoba má otevřenou otázku v ISSUES")
            if pole.get("stav") == "čeká" or pole.get("kdy"):
                pozn.append("čekalo" + (f" (kdy: {pole['kdy']})" if pole.get("kdy") else ""))
            if fronta == "dotazy":
                cil = "archivni_dotazy.md"
            elif fronta in ("rodina", "rozhodnuti"):
                cil = "ručně" if typ not in DRUH else "ukoly.md"
            else:
                cil = "ukoly.md"
            polozky.append({"id": uid, "fronta": fronta, "typ": typ, "nadpis": DRUH.get(typ, "Jiné"), "radek": radek, "cil": cil,
                            "pozn": pozn})
    return polozky


def prehled(polozky):
    r = ["# Migrace front – přehled k projití", "",
         "Každý úkol s navrženým řádkem. Smaž hotové a duplicitní, zkrať řádky; pak `migrace_a.py <projekt> --zapsat`.", "",
         "| Úkol | Fronta | Kam | Řádek | Pozor |", "|---|---|---|---|---|"]
    for p in polozky:
        r.append(f"| {p['id']} | {p['fronta']} | {p['cil']} / {p['nadpis']} | {p['radek'].replace('|', '/')} | {'; '.join(p['pozn'])} |")
    return "\n".join(r) + "\n"


def zapis_plan(projekt, polozky):
    cesta = os.path.join(projekt, "data", "ukoly.md")
    text = open(cesta, encoding="utf-8").read() if os.path.exists(cesta) else "# Plán bádání\n"
    for nad in NADPISY:
        if f"\n## {nad}" not in text:
            text = text.rstrip("\n") + f"\n\n## {nad}\n"
    for nad in NADPISY:
        nove = [f"- {p['radek']}" for p in polozky if p["cil"] == "ukoly.md" and p["nadpis"] == nad and p["radek"]]
        if not nove:
            continue
        i = text.index(f"\n## {nad}") + len(f"\n## {nad}\n")
        j = text.find("\n## ", i)
        j = len(text) if j < 0 else j
        oddil = text[i:j].rstrip("\n")
        stare = set(oddil.split("\n"))
        pridat = [x for x in nove if x not in stare]
        text = text[:i] + (oddil + "\n" if oddil.strip() else "\n") + "\n".join(pridat) + "\n" + text[j:]
    open(cesta, "w", encoding="utf-8", newline="\n").write(re.sub(r"\n{3,}", "\n\n", text))
    dotazy = [p for p in polozky if p["cil"] == "archivni_dotazy.md" and p["radek"]]
    if dotazy:
        c = os.path.join(projekt, "data", "archivni_dotazy.md")
        t = open(c, encoding="utf-8").read() if os.path.exists(c) else "# Prameny mimo online matriky\n"
        t = t.rstrip("\n") + "\n\n## Z fronty dotazů (migrace)\n\n" + "\n".join(f"- {p['radek']}" for p in dotazy) + "\n"
        open(c, "w", encoding="utf-8", newline="\n").write(t)
    rucne = [p for p in polozky if p["cil"] == "ručně"]
    if rucne:
        c = os.path.join(projekt, "pracovni", "migrace_a_rucne.md")
        open(c, "w", encoding="utf-8", newline="\n").write(
            "# K ručnímu zpracování\n\nOtázky pro rodinu: `tools/otazky.py pridej --druh rodina …`; rozhodnutí: STAV.md → Čeká na rozhodnutí.\n\n"
            + "\n".join(f"- {p['id']} ({p['fronta']}): {p['radek']}" for p in rucne) + "\n")
    return len([p for p in polozky if p["cil"] == "ukoly.md"]), len(dotazy), len(rucne)


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    zapsat = "--zapsat" in a
    a = [x for x in a if x != "--zapsat"]
    if len(a) != 1 or not os.path.isdir(os.path.join(a[0], "data")):
        print(__doc__)
        return 2
    projekt = a[0]
    polozky = plan(projekt)
    os.makedirs(os.path.join(projekt, "pracovni"), exist_ok=True)
    with open(os.path.join(projekt, "pracovni", "migrace_a_prehled.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(prehled(polozky))
    print(f"úkolů {len(polozky)}, z toho s upozorněním {sum(1 for p in polozky if p['pozn'])}; přehled pracovni/migrace_a_prehled.md")
    if not zapsat:
        print("nanečisto: data/ beze změny; po projití spusť znovu s --zapsat")
        return 0
    n_plan, n_dotazy, n_rucne = zapis_plan(projekt, polozky)
    print(f"zapsáno: plán {n_plan}, archivní dotazy {n_dotazy}, k ručnímu zpracování {n_rucne} (pracovni/migrace_a_rucne.md)")
    stare = [s for s in list(FRONTY.values()) + ["ukoly_historie.jsonl", "rezim.json", ".rozpocet.json"]
             if os.path.exists(os.path.join(projekt, "data", s))]
    if stare:
        print("archivace (soubory zůstanou v historii gitu projektu): git rm " + " ".join(f"data/{s}" for s in stare))
    return 0


if __name__ == "__main__":
    sys.exit(main())
