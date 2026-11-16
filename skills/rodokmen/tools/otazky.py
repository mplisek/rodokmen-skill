#!/usr/bin/env python3
"""Veřejné otázky pro web (data/verejne_otazky.json), odděleně od vnitřní fronty úkolů (ADR 0003).

Na web jde jen záznam, který uživatel potvrdil. Vnitřní úkoly (data/ukoly_*.md) se na web nikdy nepřenášejí; propojení je
`z-ukolu` (koncept z jednoho úkolu, v datech odkaz z_ukolu) a `z-fronty` (veřejná část fronty otázek pro rodinu nebo dotazů na
archivy – úvod a oddíly před kartami úkolů – jako nepotvrzené koncepty).

Rod se zadává číslem rodu (8–15, zakladatel v rodokmenu správce) nebo názvem rodu z LINES („novakove“, „Novákové“); v datech
je číslo, protože ho export pro každý přístup přečísluje.

Použití (z kořene projektu): python3 -I tools/otazky.py <příkaz> …
  pridej --druh rodina --otazka T [--proc T] [--pomuze T] [--rod R] [--osoba JMÉNO] [--oddil NÁZEV]
  pridej --druh pramen --archiv T --co-hledat T [--rod R] [--osoba JMÉNO] [--ceka-na-souhlas ano|ne]
                           nový nepotvrzený záznam (rodina = otázka pro příbuzné, pramen = zdroj mimo online matriky)
  z-ukolu <U-id> --druh rodina|pramen [--rod R]
                           koncept z vnitřního úkolu (text úkolu přejde do otázky, ať ho uživatel upraví)
  z-fronty --soubor rodina|archivy
                           veřejná část fronty (data/ukoly_na_rodinu.md | data/ukoly_dotazy_na_archivy.md) jako nepotvrzené koncepty;
                           rod podle nadpisu oddílu (rodina) nebo podle „**Rod – osoba:**“ (archivy); co už v datech je, přeskočí
  uprav <id> [--otazka T] [--proc T] [--pomuze T] [--archiv T] [--co-hledat T] [--rod R] [--osoba J] [--oddil N] [--ceka-na-souhlas ano|ne]
  potvrd <id> | --rod R | --obecne  --kdo JMÉNO [--druh rodina|pramen] [--datum RRRR-MM-DD]
                           pustí záznam(y) na web; po rodech: všechny nepotvrzené koncepty rodu (--obecne = bez rodu) – všechny,
                           nebo žádný (text musí být bez procesních údajů)
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
import unicodedata

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import zaznamy_store as store  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SOUBOR = os.path.join(DATA, "verejne_otazky.json")
DRUHY = ("rodina", "pramen")
POLE = {"rodina": ("otazka",), "pramen": ("archiv", "co_hledat")}      # povinná pole podle druhu
VEREJNA = ("otazka", "proc", "pomuze", "archiv", "co_hledat", "osoba", "oddil")
FRONTY = {"rodina": "ukoly_na_rodinu.md", "archivy": "ukoly_dotazy_na_archivy.md"}
UVOD = {"rodina": "# Otázky pro rodinu\n\nCo z matrik nezjistíme a může vědět někdo z rodiny. Stačí odpovědět na to, co kdo ví; "
                  "i „nevím“ nebo „myslím, že…“ pomůže. Nejcennější jsou fotky dokumentů.\n\n",
        "pramen": "# Prameny v archivech\n\nZápisy a knihy, které nejsou online – jsou jen v archivu nebo na matričním úřadě. "
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


# ---------- rody ----------
def slug(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def linie():
    """{číslo rodu: název} z data/osoby.py (LINES rodokmenu správce)."""
    p = os.path.join(DATA, "osoby.py")
    ns = {}
    try:
        exec(compile(open(p, encoding="utf-8-sig").read(), p, "exec"), ns)
    except Exception:   # noqa: BLE001 – bez osob jen čísla rodů
        return {}
    out = {}
    for k, v in (ns.get("LINES") or {}).items():
        jm = v[0] if isinstance(v, (tuple, list)) and v else (v.get("name") if isinstance(v, dict) else v)
        if isinstance(k, int) and isinstance(jm, str):
            out[k] = jm
    return out


def rod_z(hodnota, lines=None):
    """Číslo rodu z čísla („8“) nebo názvu („novakove“, „Novákové“, kmen příjmení „Novákovi“); ValueError, když nejde určit."""
    if hodnota is None or isinstance(hodnota, int):
        return hodnota
    s = str(hodnota).strip()
    if re.fullmatch(r"\d+", s):
        return int(s)
    lines = linie() if lines is None else lines
    cil = slug(s)
    for k, jm in sorted(lines.items()):
        if cil in (slug(jm), f"{slug(jm)}-{k}"):
            return k
    kmen = cil.split("-")[0][:5]
    kandidati = [k for k, jm in lines.items() if kmen and slug(jm).split("-")[0][:5] == kmen]
    if len(kandidati) == 1:
        return kandidati[0]
    znam = ", ".join(f"{k} {slug(jm)}" for k, jm in sorted(lines.items())) or "žádné (data/osoby.py LINES)"
    raise ValueError(f"rod „{s}“ nejde určit; rody: {znam}")


# ---------- kontrola ----------
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
    if "ceka_na_souhlas" in z and z["ceka_na_souhlas"] is not True:
        chyby.append("ceka_na_souhlas: true nebo vynechat")
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
        try:
            z["rod"] = rod_z(a.rod)
        except ValueError as e:
            sys.exit(f"Záznam se neuložil: {e}")
    c = getattr(a, "ceka_na_souhlas", None)
    if c == "ano":
        z["ceka_na_souhlas"] = True
    elif c == "ne":
        z.pop("ceka_na_souhlas", None)


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
                    z.update(otazka=text)
                else:
                    z.update(archiv="", co_hledat=text)
                if a.rod is not None:
                    try:
                        z["rod"] = rod_z(a.rod)
                    except ValueError as e:
                        sys.exit(str(e))
                d["otazky"].append(z)
                uloz(d)
                print(f"otázky: koncept {z['id']} z úkolu {u.id}; uprav ho (otazky.py uprav {z['id']} …) a potvrď")
                return
    sys.exit(f"Úkol {a.id_ukolu} ve frontách není.")


def verejna_cast(text):
    """Úvod a oddíly fronty před první kartou úkolu („## U-0001 | …“): [(nadpis, [odrážky jako jeden řádek])]."""
    konec = re.search(r"(?m)^## U-\d{4}\b", text)
    text = text[:konec.start()] if konec else text
    oddily = []
    for cast in re.split(r"(?m)^(?=## )", text):
        if not cast.startswith("## "):
            continue
        hlava, _, telo = cast.partition("\n")
        polozky = []
        for radek in telo.splitlines():
            if re.match(r"[-*] ", radek):
                polozky.append(radek[2:].strip())
            elif polozky and radek.startswith((" ", "\t")) and radek.strip():
                polozky[-1] += " " + radek.strip()   # odsazené pokračování odrážky
        oddily.append((hlava[3:].strip(), polozky))
    return oddily


def cmd_z_fronty(a):
    path = os.path.join(DATA, FRONTY[a.soubor])
    if not os.path.exists(path):
        sys.exit(f"data/{FRONTY[a.soubor]} neexistuje.")
    lines = linie()
    d = nacti()
    zname = {(z.get("druh"), z.get("otazka") or z.get("co_hledat")) for z in d["otazky"]}
    nove, preskoceno = [], 0
    for nadpis, polozky in verejna_cast(open(path, encoding="utf-8-sig").read()):
        if a.soubor == "rodina":
            try:
                rod = rod_z(nadpis, lines)
            except ValueError:
                rod = None
            for text in polozky:
                z = {"druh": "rodina", "otazka": text, "z_fronty": a.soubor}
                z.update({"rod": rod} if rod is not None else {"oddil": nadpis})
                nove.append(z)
        else:
            for text in polozky:
                z = {"druh": "pramen", "archiv": nadpis, "z_fronty": a.soubor}
                m = re.match(r"\*\*(.+?):\*\*\s*(.*)", text)
                if m:
                    rod_txt, _, osoba = m.group(1).partition(" – ")
                    try:
                        z["rod"] = rod_z(rod_txt, lines)
                        if osoba.strip():
                            z["osoba"] = osoba.strip()
                    except ValueError:
                        z["osoba"] = m.group(1).strip()   # prefix není rod: celý jako osoba
                    z["co_hledat"] = m.group(2).strip()
                else:
                    z["co_hledat"] = text
                nove.append(z)
    pridano = 0
    for z in nove:
        if (z["druh"], z.get("otazka") or z.get("co_hledat")) in zname:
            preskoceno += 1
            continue
        z = {"id": dalsi_id(d), **z}
        d["otazky"].append(z)
        zname.add((z["druh"], z.get("otazka") or z.get("co_hledat")))
        pridano += 1
    if pridano:
        uloz(d)
    print(f"otázky: z data/{FRONTY[a.soubor]} {pridano} nových konceptů (nepotvrzené), {preskoceno} už v datech; "
          "potvrzení po rodech: otazky.py potvrd --rod <rod> | --obecne --kdo …")


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
    if a.id is not None:
        vyber = [najdi(d, a.id)]
    elif a.rod is not None or a.obecne:
        try:
            rod = rod_z(a.rod) if a.rod is not None else None
        except ValueError as e:
            sys.exit(str(e))
        vyber = [z for z in d["otazky"] if "potvrzeno" not in z and z.get("rod") == rod and (not a.druh or z.get("druh") == a.druh)]
        if not vyber:
            sys.exit("Není co potvrdit: žádný nepotvrzený koncept " + (f"rodu {rod}" if rod is not None else "bez rodu"))
    else:
        sys.exit("potvrd <id> | --rod R | --obecne  --kdo JMÉNO")
    chyby = []
    for z in vyber:
        zkusmo = dict(z, potvrzeno={"datum": a.datum or datetime.date.today().isoformat(), "kdo": a.kdo})
        chyby += [f"záznam {z.get('id')}: {x}" for x in over_zaznam(zkusmo)]
    if chyby:
        sys.exit("Nic se nepotvrdilo, nejdřív uprav (otazky.py uprav):\n  " + "\n  ".join(chyby))
    for z in vyber:
        z["potvrzeno"] = {"datum": a.datum or datetime.date.today().isoformat(), "kdo": a.kdo}
    uloz(d)
    print(f"otázky: potvrzeno {len(vyber)} (" + ", ".join(str(z['id']) for z in vyber) + "), půjdou na web")


def cmd_smaz(a):
    d = nacti()
    najdi(d, a.id)
    d["otazky"] = [x for x in d["otazky"] if x.get("id") != a.id]
    uloz(d)
    print(f"otázky: záznam {a.id} smazán")


def vykresli(zaznamy, druh, nazvy_rodu=None, uvod=True):
    """Markdown ve tvaru, který čte export webu (oddíl „## …“, odrážky, <!-- rody: N -->, <!-- ceka -->); jen potvrzené."""
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
            ceka = " <!-- ceka -->" if z.get("ceka_na_souhlas") else ""
            radek = (f"- **{kdo}:** {z['co_hledat']}{znacka}" if kdo else f"- {z['co_hledat']}{znacka}") + ceka
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
        print(__doc__)
        sys.exit(0 if len(sys.argv) >= 2 else 2)
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
        if jmeno != "z-ukolu":
            for pole in ("otazka", "proc", "pomuze", "archiv", "co-hledat", "osoba", "oddil"):
                p.add_argument("--" + pole, dest=pole.replace("-", "_"))
            p.add_argument("--ceka-na-souhlas", dest="ceka_na_souhlas", choices=("ano", "ne"))
        p.add_argument("--rod")
        p.set_defaults(fn=fn)
    p = sub.add_parser("z-fronty")
    p.add_argument("--soubor", required=True, choices=tuple(FRONTY))
    p.set_defaults(fn=cmd_z_fronty)
    p = sub.add_parser("potvrd")
    p.add_argument("id", type=int, nargs="?")
    p.add_argument("--rod")
    p.add_argument("--obecne", action="store_true")
    p.add_argument("--druh", choices=DRUHY)
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
