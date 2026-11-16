#!/usr/bin/env python3
"""Jednotná značka rodu na hotových stránkách (ADR 0004).

Použití: python3 -I tools/znackuj_rody.py <složka se stránkami> [--site web/src/data/site.json]

Ve všech textových uzlech stránek (*.html) nahradí holý název rodu značkou: barevný kruh a název s odkazem na stránku rodu
(stejný markup jako komponenta Rod.astro a export). Nemění text v odkazech, nadpisu stránky (h1), skriptech, stylech,
formulářích, titulku ani v atributech a už hotové značky nechává. Nahrazuje jen přesný tvar názvu (první pád množného čísla),
skloněné tvary ne. Názvy, barvy a adresy rodů bere z dat verze webu (site.json), takže je značka stejná ve všech verzích.
Opakované spuštění nic nemění. Volá ho sestavení webu (scripts/build.mjs) po `astro build` a před `pagefind`.
"""
import html as _html
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
import rody_html as rh  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def znacka(r):
    return (f'<span class="rod-znak"><span class="dot" style="background:{r["color"]}"></span>'
            f'<a href="/rod/{r["slug"]}/">{_html.escape(r["name"])}</a></span>')


# Šablona (jména, domy, mapa) dává před název rodu vlastní kruh v barvě rodu; značka rodu má kruh taky. Kruh šablony těsně před
# značkou stejné barvy se proto vynechá – jeden kruh na rod. Jiná barva znamená něco jiného a zůstane.
DVOJI_KRUH = re.compile(r'<span class="dot" style="background:([^";]+)"[^>]*></span>(<span class="rod-znak"><span class="dot" style="background:\1"></span>)')


def bez_dvojiho_kruhu(text):
    return DVOJI_KRUH.sub(r"\2", text)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    slozka = args[0]
    site = args[args.index("--site") + 1] if "--site" in args else os.path.join(ROOT, "web", "src", "data", "site.json")
    if not os.path.isdir(slozka):
        sys.exit(f"Složka {slozka} neexistuje.")
    if not os.path.exists(site):
        sys.exit(f"Chybí {site} (data verze webu; vytvoří ji export_web.py).")
    rody = rh.nacti_rody(site)
    rx = rh.regex_nazvu(rody)
    if not rx:
        print("značky rodů: žádné rody v datech, nic nedělám")
        return
    podle_nazvu = {r["name"]: r for r in rody}
    pocet = [0]

    def nahrad(text):
        def jedna(m):
            pocet[0] += 1
            return znacka(podle_nazvu[m.group(0)])
        return rx.sub(jedna, text)

    stranek = 0
    for cesta in rh.html_soubory(slozka):
        puvodni = rh.cti(cesta)
        nove = bez_dvojiho_kruhu(rh.projdi(puvodni, nahrad))
        if nove != puvodni:
            with open(cesta, "w", encoding="utf-8", newline="") as f:
                f.write(nove)
            stranek += 1
    print(f"značky rodů: {pocet[0]} náhrad na {stranek} stránkách")


if __name__ == "__main__":
    main()
