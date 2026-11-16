#!/usr/bin/env python3
"""Účastníci zápisu (analyza/navrh-optimalizace.md, etapa E4): kdo v zápisu vystupuje a v jaké roli se píše jednou, u zápisu
(`data/zaznamy.json` → "ucastnici": [{"osoba": "88", "role": "křtěnec"}, {"jmeno": "Václav Ukázka", "role": "kmotr"}]). Web, kontrola
i karta osoby si z toho vazbu zápis ↔ osoba odvodí pro všechny účastníky; seznam `r` u osoby už není třeba psát u každého zvlášť.

Použití (z kořene projektu):
  python3 -I tools/ucastnici.py stav
        kolik zápisů účastníky má, kolik ne, a kde se liší od seznamů `r` v data/osoby.py
  python3 -I tools/ucastnici.py navrh [--out pracovni/ucastnici_navrh.json]
        pro zápisy bez účastníků navrhne účastníky z dnešních `r` a druhu zápisu; roli, kterou nejde odvodit, nechá prázdnou (null)
        k ruční kontrole – tu dělá bádání, ne nástroj
  python3 -I tools/ucastnici.py zapis pracovni/ucastnici_navrh.json
        zapíše jen položky, kde má každý účastník roli; ostatní přeskočí a vypíše

Knihovna: `dopln_r(ns, zaznamy)` doplní do seznamů `r` osob klíče zápisů, kde je osoba účastníkem (volá export webu, kontrola a kontext).
"""
import json
import os
import re
import sys
import time
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLE = ("křtěnec", "otec", "matka", "ženich", "nevěsta", "zemřelý", "kmotr", "svědek", "jiné")
HLAVNI = {"N": ("křtěnec",), "Z": ("zemřelý",), "O": ("ženich", "nevěsta")}   # hlavní role podle druhu zápisu


def klic_osoby(x, ns):
    """Klíč, jak ho nese data/osoby.py (číslo předka jako int, zkratka jako text), nebo None."""
    P, R, SAME = ns.get("P") or {}, ns.get("RODINA") or {}, ns.get("SAME") or {}
    s = str(x).strip()
    if s in R:
        return s
    if re.fullmatch(r"\d+", s):
        n = int(s)
        n = SAME.get(n, n)
        if n in P:
            return n
    return None


def over(zaznam, ns):
    """Chyby pole ucastnici jednoho zápisu."""
    u = zaznam.get("ucastnici")
    if u is None:
        return []
    if not isinstance(u, list) or not u:
        return ["ucastnici: neprázdný seznam {osoba nebo jmeno, role}"]
    ch = []
    for i, x in enumerate(u):
        if not isinstance(x, dict) or x.get("role") not in ROLE:
            ch.append(f"ucastnici[{i}].role: {', '.join(ROLE)}")
            continue
        if "osoba" in x:
            if klic_osoby(x["osoba"], ns) is None:
                ch.append(f"ucastnici[{i}].osoba: „{x['osoba']}“ není v data/osoby.py")
        elif not (isinstance(x.get("jmeno"), str) and x["jmeno"].strip()):
            ch.append(f"ucastnici[{i}]: osoba (klíč z osoby.py), nebo jmeno (kdo v rodokmenu není)")
    return ch


def dopln_r(ns, zaznamy):
    """Do `r` každé osoby přidá klíče zápisů, ve kterých je účastníkem. Mění ns na místě; vrací {klíč zápisu: {klíč osoby: role}}."""
    role = {}
    for z in zaznamy or []:
        if not isinstance(z, dict) or not isinstance(z.get("ucastnici"), list):
            continue
        for x in z["ucastnici"]:
            if not isinstance(x, dict) or "osoba" not in x:
                continue
            k = klic_osoby(x["osoba"], ns)
            if k is None:
                continue
            o = (ns.get("P") or {}).get(k) if isinstance(k, int) else (ns.get("RODINA") or {}).get(k)
            if not isinstance(o, dict):
                continue
            r = o.setdefault("r", [])
            if z.get("klic") not in r:
                r.append(z["klic"])
            role.setdefault(z["klic"], {})[k] = x.get("role")
            o.setdefault("_role", {})[z["klic"]] = x.get("role")   # role osoby v zápisu; přežije přečíslování pohledu i filtr přístupu
    return role


# ---------- příkazy ----------
def _nacti():
    ns = {}
    with open(os.path.join(ROOT, "data", "osoby.py"), encoding="utf-8-sig") as f:
        exec(f.read(), ns)
    try:
        with open(os.path.join(ROOT, "data", "zaznamy.json"), encoding="utf-8-sig") as f:
            zaz = json.load(f)
    except OSError:
        zaz = []
    return ns, zaz


def _citujici(ns):
    out = {}
    for k, o in list((ns.get("P") or {}).items()) + list((ns.get("RODINA") or {}).items()):
        for r in (o or {}).get("r", []):
            out.setdefault(r, []).append(k)
    return out


def _bez(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t).casefold()) if unicodedata.category(c) != "Mn")


def _pohlavi(k, ns):
    if isinstance(k, int):
        o = (ns.get("P") or {}).get(k, {})
        return o.get("sex") or ("M" if k % 2 == 0 else "F") if k > 1 else o.get("sex")
    return ((ns.get("RODINA") or {}).get(k) or {}).get("sex")


def _shoda(k, ns, nazev):
    """Jak jistě název zápisu jmenuje osobu: 2 = křestní jméno přesně a příjmení kmenem, 1 = obojí jen kmenem (skloňování), 0 = ne."""
    o = (ns.get("P") or {}).get(k) if isinstance(k, int) else (ns.get("RODINA") or {}).get(k)
    slova = re.findall(r"[^\W\d_]{3,}", _bez((o or {}).get("n", "")))
    tokeny = re.findall(r"[^\W\d_]{3,}", _bez(nazev))
    if len(slova) < 2:
        return 0
    krestni, prijmeni = slova[0], slova[-1]
    if not any(t.startswith(prijmeni[:max(3, len(prijmeni) - 3)]) for t in tokeny):
        return 0
    if krestni in tokeny:
        return 2
    return 1 if any(t.startswith(krestni) and len(t) - len(krestni) <= 2 for t in tokeny) else 0


def navrh(ns, zaz):
    """Návrh účastníků: hlavní roli dostane jen osoba, kterou název zápisu jmenuje nejjistěji a jediná; ostatním zůstane role prázdná."""
    cit = _citujici(ns)
    out = {}
    for z in zaz:
        if not isinstance(z, dict) or z.get("ucastnici") or not cit.get(z.get("klic")):
            continue
        druh = str(z.get("druh", ""))[:1]
        kandidati = {}
        for k in cit[z["klic"]]:
            sh = _shoda(k, ns, z.get("nazev", ""))
            moznosti = HLAVNI.get(druh, ())
            role = None
            if sh and len(moznosti) == 1:
                role = moznosti[0]
            elif sh and druh == "O" and _pohlavi(k, ns) in ("M", "F"):
                role = "ženich" if _pohlavi(k, ns) == "M" else "nevěsta"
            if role:
                kandidati.setdefault(role, []).append((sh, k))
        vybrani = {}
        for role, ks in kandidati.items():
            nej = max(sh for sh, _ in ks)
            vitezove = [k for sh, k in ks if sh == nej]
            if len(vitezove) == 1:
                vybrani[vitezove[0]] = role
        out[z["klic"]] = {"nazev": z.get("nazev", ""), "datum": z.get("datum", ""),
                          "ucastnici": [{"osoba": str(k), "role": vybrani.get(k)} for k in cit[z["klic"]]]}
    return out


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if a else 2
    ns, zaz = _nacti()
    if a[0] == "stav":
        ma = [z for z in zaz if isinstance(z, dict) and z.get("ucastnici")]
        cit = _citujici(ns)
        chybi = sum(1 for z in ma for k in cit.get(z["klic"], []) if str(k) not in {str(x.get("osoba")) for x in z["ucastnici"] if isinstance(x, dict)})
        chyby = [f"{z.get('klic')}: {c}" for z in ma for c in over(z, ns)]
        print(f"zápisů {len(zaz)}, s účastníky {len(ma)}, bez účastníků {len(zaz) - len(ma)}; "
              f"osob, které zápis citují v r a nejsou mezi účastníky: {chybi}; chyb {len(chyby)}")
        for c in chyby[:20]:
            print("  " + c)
        return 1 if chyby else 0
    if a[0] == "navrh":
        out = a[a.index("--out") + 1] if "--out" in a else os.path.join("pracovni", "ucastnici_navrh.json")
        n = navrh(ns, zaz)
        p = os.path.join(ROOT, out)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(n, f, ensure_ascii=False, indent=1)
            f.write("\n")
        uplne = sum(1 for v in n.values() if all(x["role"] for x in v["ucastnici"]))
        print(f"návrh pro {len(n)} zápisů v {out}: {uplne} s rolí u všech účastníků, {len(n) - uplne} k ruční kontrole (role null)")
        return 0
    if a[0] == "zapis" and len(a) > 1:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import contextlib
        import io
        import zapis as zapis_mod
        with open(a[1], encoding="utf-8-sig") as f:
            n = json.load(f)
        znam = {z.get("klic") for z in zaz if isinstance(z, dict)}
        hotovo, preskoceno = 0, []
        for klic, v in n.items():
            uc = [{k: x[k] for k in ("osoba", "jmeno", "role") if x.get(k)} for x in v.get("ucastnici") or [] if isinstance(x, dict)]
            if klic not in znam or not uc or any(not x.get("role") for x in uc) or over({"ucastnici": uc}, ns):
                preskoceno.append(klic)
                continue
            for pokus in range(5):   # Windows: soubor právě drží antivirus nebo synchronizace; krátce počkat a zkusit znovu
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        zapis_mod.zapis("zaznamy", klic, {"ucastnici": uc}, sloucit=True)
                    break
                except PermissionError:
                    if pokus == 4:
                        raise
                    time.sleep(0.3)
            hotovo += 1
        print(f"zapsáno {hotovo} zápisů, přeskočeno {len(preskoceno)} (chybí role, neznámá osoba nebo zápis): " + ", ".join(preskoceno[:15])
              + (" …" if len(preskoceno) > 15 else ""))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
