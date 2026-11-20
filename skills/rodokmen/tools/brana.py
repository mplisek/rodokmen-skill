#!/usr/bin/env python3
"""Strukturní brána po aktualizaci verze skillu v projektu (Fáze D, Q-D1, Q-D4). Bez sítě, bez prohlížeče.

Použití (z kořene projektu): python3 -I tools/brana.py [--json]

Spustí po sobě kontroly: `kontrola.py` (data), `denik.py over`, `otazky.py over` a `kontrola_webu.py` nad každou
sestavenou verzí webu (`web/dist/_p/<přístup>/`, jinak `web/dist/`). Web nesestavuje (`npm run build` je pomalý); brána ověřuje jen
to, co už je sestavené. Výsledek:

  zelená      všechny kroky prošly a web byl zkontrolován   (kód 0)
  červená     aspoň jeden krok selhal; vypíše se který a proč (kód 1)
  nepokryto   žádný sestavený web ke kontrole (kód 2) – není to zelená

Výsledek zapíše do `pracovni/brana.json` {vysledek, verze, otisk_dat, cas}. `verze` je obsah `.skill_verze` projektu; hlídač nasazení
(`hlidac_site.py`) nepustí nasazení, dokud výsledek není zelený pro aktuální verzi. Data nemění.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
KROKY = (("kontrola", ["kontrola.py"]), ("denik", ["denik.py", "over"]),
         ("otazky", ["otazky.py", "over"]))


def spust(argv):
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(TOOLS, argv[0]), *argv[1:]], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUTF8="1"))
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def verze_projektu():
    try:
        with open(os.path.join(ROOT, ".skill_verze"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def otisk_dat():
    h = hashlib.sha256()
    data = os.path.join(ROOT, "data")
    for koren, _, soubory in sorted(os.walk(data)):
        for j in sorted(soubory):
            h.update(os.path.relpath(os.path.join(koren, j), data).encode("utf-8"))
            with open(os.path.join(koren, j), "rb") as f:
                h.update(f.read())
    return h.hexdigest()[:16]


TEXTOVE = (".html", ".js", ".mjs", ".css", ".json", ".xml", ".txt", ".svg", ".astro", ".ts", ".md")


def _otisk(koren, preskoc=(), jen_obsah_textu=False):
    """Otisk stromu souborů: cesta a obsah; u binárních souborů sestaveného webu (obrázky) stačí cesta a velikost."""
    h = hashlib.sha256()
    if not os.path.isdir(koren):
        return ""
    for slozka, podslozky, soubory in os.walk(koren):
        rel = os.path.relpath(slozka, koren).replace("\\", "/")
        podslozky[:] = sorted(d for d in podslozky if (d if rel == "." else f"{rel}/{d}") not in preskoc and d != "node_modules")
        for j in sorted(soubory):
            cesta = os.path.join(slozka, j)
            h.update((j if rel == "." else f"{rel}/{j}").encode("utf-8"))
            if jen_obsah_textu and not j.lower().endswith(TEXTOVE):
                h.update(str(os.path.getsize(cesta)).encode())
                continue
            with open(cesta, "rb") as f:
                h.update(f.read())
    return h.hexdigest()[:16]


def otisky():
    """Otisk dat, zdrojů webu a sestaveného webu: brána je zelená jen pro přesně tento stav. Hlídač nasazení je před nasazením spočítá
    znovu; změna dat, šablony nebo dist po bráně znamená bránu pustit znovu (starý web by neodpovídal datům)."""
    web = os.path.join(ROOT, "web")
    return {"otisk_dat": otisk_dat(),
            "otisk_webu": _otisk(os.path.join(web, "src"), preskoc=("data", "generated")),   # data/ a generated/ vyrábí export z data/
            "otisk_dist": _otisk(os.path.join(web, "dist"), jen_obsah_textu=True)}


def verze_webu():
    """Složky sestavených stránek: dist/_p/<přístup>/ (každý přístup zvlášť), jinak dist/."""
    dist = os.path.join(ROOT, "web", "dist")
    pristupy = os.path.join(dist, "_p")
    if os.path.isdir(pristupy):
        out = sorted(os.path.join(pristupy, d) for d in os.listdir(pristupy) if os.path.isdir(os.path.join(pristupy, d)))
        if out:
            return out
    return [dist] if os.path.isfile(os.path.join(dist, "index.html")) else []


def neuplne_verze(weby):
    """Neúplně sestavené nebo nahrané verze (OneDrive umí soubor zamknout uprostřed sestavení): chybí úvodní nebo přihlašovací
    stránka, nebo má verze „vse“ (celý rodokmen) méně stránek než některý přístup."""
    chyby, pocty = [], {}
    for cesta in weby:
        jmeno = os.path.relpath(cesta, ROOT).replace("\\", "/")
        pristup = os.path.basename(os.path.dirname(cesta)) == "_p"
        for f in ("index.html",) + (("prihlaseni.html",) if pristup else ()):
            if not os.path.isfile(os.path.join(cesta, f)):
                chyby.append(f"{jmeno}: chybí {f} – verze je neúplná, sestav web znovu (npm run build)")
        pocty[os.path.basename(cesta)] = sum(1 for _, _, fs in os.walk(cesta) for x in fs if x.endswith(".html"))
    if "vse" in pocty and len(pocty) > 1 and pocty["vse"] < max(v for k, v in pocty.items() if k != "vse"):
        chyby.append(f"verze vse má {pocty['vse']} stránek, méně než přístup ({max(v for k, v in pocty.items() if k != 'vse')})"
                     " – verze je neúplná, sestav web znovu (npm run build)")
    return chyby


def poslednich(text, n=12):
    return "\n".join(text.splitlines()[-n:])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    kroky = []
    for jmeno, prikaz in KROKY:
        ok, vystup = spust(prikaz)
        kroky.append({"krok": jmeno, "ok": ok, "vystup": "" if ok else poslednich(vystup)})
    weby = verze_webu()
    site = os.path.join(ROOT, "web", "src", "data", "site.json")
    for cesta in weby:
        # site.json je z posledního exportu = celý rodokmen; názvy a barvy rodů v přístupu mají jiná data (jako test_jednotnost_web),
        # proto se podle něj kontroluje jen verze „vse“ (nebo jediný dist); přístup se kontroluje bez dat rodů
        pristup = os.path.basename(os.path.dirname(cesta)) == "_p" and os.path.basename(cesta) != "vse"
        arg = [cesta] + (["--site", os.path.join(os.path.dirname(site), "neexistuje.json")] if pristup
                         else ["--site", site] if os.path.isfile(site) else [])
        ok, vystup = spust(["kontrola_webu.py", *arg])
        kroky.append({"krok": "web", "cil": os.path.relpath(cesta, ROOT).replace("\\", "/"), "ok": ok,
                      "vystup": "" if ok else poslednich(vystup, 25)})
    neuplne = neuplne_verze(weby)
    if weby:
        kroky.append({"krok": "úplnost webu", "ok": not neuplne, "vystup": "\n".join(neuplne)})
    selhalo = [k for k in kroky if not k["ok"]]
    vysledek = "cervena" if selhalo else ("zelena" if weby else "nepokryto")
    znacka = {"vysledek": vysledek, "verze": verze_projektu(), **otisky(), "cas": time.strftime("%Y-%m-%dT%H:%M:%S")}
    os.makedirs(os.path.join(ROOT, "pracovni"), exist_ok=True)
    with open(os.path.join(ROOT, "pracovni", "brana.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(znacka, f, ensure_ascii=False, indent=1)
        f.write("\n")
    if "--json" in argv:
        print(json.dumps({**znacka, "kroky": kroky}, ensure_ascii=False, indent=1))
    else:
        for k in kroky:
            print(f"{'OK    ' if k['ok'] else 'CHYBA '} {k['krok']}{' (' + k['cil'] + ')' if k.get('cil') else ''}")
            if k["vystup"]:
                print("\n".join("        " + r for r in k["vystup"].splitlines()))
        if not weby:
            print("NEPOKRYTO  žádný sestavený web ke kontrole (web/dist); sestav ho: cd web && npm run build")
        print(f"\nBrána: {vysledek} (verze {znacka['verze'] or '?'})")
    return {"zelena": 0, "cervena": 1, "nepokryto": 2}[vysledek]


if __name__ == "__main__":
    sys.exit(main())
