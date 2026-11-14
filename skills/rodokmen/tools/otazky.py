#!/usr/bin/env python3
"""Veřejné otázky pro web (data/verejne_otazky.json), odděleně od vnitřní fronty úkolů (ADR 0003).

Na web jde jen záznam, který uživatel potvrdil. Vnitřní úkoly (data/ukoly_*.md) se na web nikdy nepřenášejí; jediné
propojení je `z-ukolu`: z úkolu vznikne nepotvrzený koncept a v datech zůstane odkaz z_ukolu.

Použití (z kořene projektu): python3 -I tools/otazky.py <příkaz> …
  pridej --druh rodina --otazka T --proc T [--pomuze T] [--rod 8] [--osoba JMÉNO] [--oddil NÁZEV]
  pridej --druh pramen --archiv T --co-hledat T [--rod 8] [--osoba JMÉNO]
                           nový nepotvrzený záznam (rodina = otázka pro příbuzné, pramen = zdroj mimo online matriky)
  z-ukolu <U-id> --druh rodina|pramen [--rod 8]
                           koncept z vnitřního úkolu (text úkolu přejde do otázky, ať ho uživatel upraví)
  uprav <id> [--otazka T] [--proc T] [--pomuze T] [--archiv T] [--co-hledat T] [--rod N] [--osoba J] [--oddil N]
  potvrd <id> --kdo JMÉNO [--datum RRRR-MM-DD]     pustí záznam na web (text musí být bez procesních údajů)
  smaz <id>                zodpovězenou otázku odstraní
  vykresli --druh rodina|pramen [--nazvy-rodu '{"8": "Novákové"}']   Markdown pro export webu (jen potvrzené)
  over                     zkontroluje celý soubor
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import zaznamy_store as store  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SOUBOR = os.path.join(DATA, "verejne_otazky.json")
DRUHY = ("rodina", "pramen")
POLE = {"rodina": ("otazka", "proc"), "pramen": ("archiv", "co_hledat")}      # povinná pole podle druhu
VEREJNA = ("otazka", "proc", "pomuze", "archiv", "co_hledat", "osoba", "oddil")
UVOD = {"rodina": "# Otázky pro rodinu\n\nCo z matrik nezjistíme a může vědět někdo z rodiny. Stačí odpovědět na to, co kdo ví; "
                  "i „nevím“ nebo „myslím, že…“ pomůže. Nejcennější jsou fotky dokumentů.\n\n",
        "pramen": "# Prameny mimo online matriky\n\nZápisy a knihy, které nejsou online – jsou jen v archivu nebo na matričním úřadě. "
                  "Oddíl = jeden archiv nebo úřad; v oddílu rod a osoba, co hledáme a proč to není online.\n\n"}


def nacti():
    if not os.path.exists(SOUBOR):
        return {"otazky": []}
    try:
        d = json.load(open(SOUBOR, encoding="utf-8-sig"))
    except ValueError as e:
        sys.exit(f"data/verejne_otazky.json nejde přečíst ({e}).")
    if not isinstance(d, dict) or not isinstance(d.get("otazky"), list):
        sys.exit('data/verejne_otazky.json: čekal jsem {"otazky": [ … ]}.')
    return d


def uloz(d):
    from soubory import zapis_json   # bezpečný zápis celého souboru (tools/soubory.py)
    with store.Zamek(SOUBOR):
        zapis_json(SOUBOR, d, indent=1, konec="\n")


def over_zaznam(z, potvrzene=False):
    chyby = []
    if not isinstance(z.get("id"), int) or z["id"] < 1:
        chyby.append("id: celé číslo od 1")
    if z.get("druh") not in DRUHY:
        chyby.append(f"druh: {' nebo '.join(DRUHY)}")
        return chyby
    for pole in POLE[z["druh"]]:
        if not str(z.get(pole) or "").strip():
            chyby.append(f"{pole}: povinné u druhu {z['druh']}")
    if z.get("rod") is not None and not isinstance(z["rod"], int):
        chyby.append("rod: číslo rodu (8–15) nebo vynechat")
    if "potvrzeno" in z:
        pz = z["potvrzeno"]
        if not (isinstance(pz, dict) and store.je_datum(pz.get("datum")) and str(pz.get("kdo") or "").strip()):
            chyby.append("potvrzeno: {datum RRRR-MM-DD, kdo}")
    for pole in VEREJNA:
        for nazev, nalezeno in store.zakazane_vzory(str(z.get(pole) or "")):
            chyby.append(f"{pole}: zakázaný vzor „{nazev}“: {nalezeno}")
    return chyby


def najdi(d, i):
    z = next((x for x in d["otazky"] if x.get("id") == i), None)
    if z is None:
        sys.exit(f"Záznam {i} neexistuje.")
    return z


def dalsi_id(d):
    return max([x.get("id", 0) for x in d["otazky"] if isinstance(x.get("id"), int)], default=0) + 1


def nastav(z, a):
    for pole in ("otazka", "proc", "pomuze", "archiv", "co_hledat", "osoba", "oddil"):
        h = getattr(a, pole, None)
        if h is not None:
            z[pole] = h
    if getattr(a, "rod", None) is not None:
        z["rod"] = a.rod


def cmd_pridej(a):
    d = nacti()
    z = {"id": dalsi_id(d), "druh": a.druh}
    nastav(z, a)
    ch = over_zaznam(z)
    if ch:
        sys.exit("Záznam se neuložil:\n  " + "\n  ".join(ch))
    d["otazky"].append(z)
    uloz(d)
    print(f"otázky: záznam {z['id']} uložen (nepotvrzený, na web nejde, dokud ho nepotvrdíš: otazky.py potvrd {z['id']} --kdo …)")


def cmd_z_ukolu(a):
    import fronta
    for f in fronta.FRONTY:
        for u in fronta.nacti(f)[1]:
            if u.id == a.id_ukolu:
                text = " ".join(u.text.split())
                d = nacti()
                z = {"id": dalsi_id(d), "druh": a.druh, "z_ukolu": u.id}
                if a.druh == "rodina":
                    z.update(otazka=text, proc="")
                else:
                    z.update(archiv="", co_hledat=text)
                if a.rod is not None:
                    z["rod"] = a.rod
                d["otazky"].append(z)
                uloz(d)
                print(f"otázky: koncept {z['id']} z úkolu {u.id}; uprav ho (otazky.py uprav {z['id']} …) a potvrď")
                return
    sys.exit(f"Úkol {a.id_ukolu} ve frontách není.")


def cmd_uprav(a):
    d = nacti()
    z = najdi(d, a.id)
    nastav(z, a)
    ch = over_zaznam(z) if "potvrzeno" in z else [x for x in over_zaznam(z) if "povinné" not in x]
    if ch:
        sys.exit("Úprava se neuložila:\n  " + "\n  ".join(ch))
    uloz(d)
    print(f"otázky: záznam {a.id} upraven")


def cmd_potvrd(a):
    d = nacti()
    z = najdi(d, a.id)
    z["potvrzeno"] = {"datum": a.datum or datetime.date.today().isoformat(), "kdo": a.kdo}
    ch = over_zaznam(z)
    if ch:
        sys.exit("Záznam nejde potvrdit, nejdřív ho uprav (otazky.py uprav):\n  " + "\n  ".join(ch))
    uloz(d)
    print(f"otázky: záznam {a.id} potvrzen a půjde na web")


def cmd_smaz(a):
    d = nacti()
    najdi(d, a.id)
    d["otazky"] = [x for x in d["otazky"] if x.get("id") != a.id]
    uloz(d)
    print(f"otázky: záznam {a.id} smazán")


def vykresli(zaznamy, druh, nazvy_rodu=None, uvod=True):
    """Markdown ve tvaru, který čte export webu (oddíl „## …“, odrážky, <!-- rody: N -->); jen potvrzené záznamy."""
    nazvy = {int(k): v for k, v in (nazvy_rodu or {}).items()}
    oddily = {}
    for z in zaznamy:
        if z.get("druh") != druh or "potvrzeno" not in z:
            continue
        rod = z.get("rod")
        znacka = f" <!-- rody: {rod} -->" if rod is not None else ""
        if druh == "rodina":
            hlava = nazvy.get(rod) if rod is not None else (z.get("oddil") or "Obecné")
            hlava = hlava or z.get("oddil") or f"Rod {rod}"
            text = " ".join(x for x in (z.get("otazka"), z.get("proc"), z.get("pomuze")) if x)
            radek = f"- {text}{znacka}"
        else:
            hlava = z["archiv"]
            kdo = " – ".join(x for x in (nazvy.get(rod) if rod is not None else "", z.get("osoba")) if x)
            radek = f"- **{kdo}:** {z['co_hledat']}{znacka}" if kdo else f"- {z['co_hledat']}{znacka}"
        oddily.setdefault(hlava, []).append(radek)
    if not oddily:
        return ""
    out = [UVOD[druh]] if uvod else []
    for hlava, radky in oddily.items():
        out.append(f"## {hlava}\n" + "\n".join(radky) + "\n")
    return "\n".join(out)


def cmd_vykresli(a):
    sys.stdout.write(vykresli(nacti()["otazky"], a.druh, json.loads(a.nazvy_rodu) if a.nazvy_rodu else None))


def cmd_over(a):
    d = nacti()
    chyby, ids = [], set()
    for n, z in enumerate(d["otazky"], 1):
        if not isinstance(z, dict):
            chyby.append(f"záznam {n}: není objekt")
            continue
        if z.get("id") in ids:
            chyby.append(f"záznam {n}: duplicitní id {z.get('id')}")
        ids.add(z.get("id"))
        chyby += [f"záznam {z.get('id')}: {x}" for x in over_zaznam(z) if "potvrzeno" in z or "povinné" not in x]
    if chyby:
        print("\n".join(chyby))
        sys.exit(f"verejne_otazky.json: {len(chyby)} chyb")
    print(f"verejne_otazky.json v pořádku ({len(d['otazky'])} záznamů, potvrzených {sum('potvrzeno' in z for z in d['otazky'])})")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    ap = argparse.ArgumentParser(prog="otazky.py", add_help=False)
    sub = ap.add_subparsers(dest="prikaz", required=True)
    for jmeno, fn in (("pridej", cmd_pridej), ("uprav", cmd_uprav), ("z-ukolu", cmd_z_ukolu)):
        p = sub.add_parser(jmeno)
        if jmeno == "uprav":
            p.add_argument("id", type=int)
        elif jmeno == "z-ukolu":
            p.add_argument("id_ukolu")
            p.add_argument("--druh", required=True, choices=DRUHY)
        else:
            p.add_argument("--druh", required=True)
        for pole in ("otazka", "proc", "pomuze", "archiv", "co-hledat", "osoba", "oddil"):
            if jmeno != "z-ukolu":
                p.add_argument("--" + pole, dest=pole.replace("-", "_"))
        p.add_argument("--rod", type=int)
        p.set_defaults(fn=fn)
    p = sub.add_parser("potvrd")
    p.add_argument("id", type=int)
    p.add_argument("--kdo", required=True)
    p.add_argument("--datum")
    p.set_defaults(fn=cmd_potvrd)
    p = sub.add_parser("smaz")
    p.add_argument("id", type=int)
    p.set_defaults(fn=cmd_smaz)
    p = sub.add_parser("vykresli")
    p.add_argument("--druh", required=True, choices=DRUHY)
    p.add_argument("--nazvy-rodu", dest="nazvy_rodu")
    p.set_defaults(fn=cmd_vykresli)
    p = sub.add_parser("over")
    p.set_defaults(fn=cmd_over)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
