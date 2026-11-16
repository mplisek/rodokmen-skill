# 0009: Kontejner vázaný na rod má barvu rodu

Stav: schváleno uživatelem 16. 11. 2026.

## Kontext

Karta, box nebo oddíl, který patří k jednomu rodu, měl barvu rodu jen někde (karty rodů na /rody/), jinde ne (zajímavosti,
otázky na stránce Co hledáme). Stránka Co hledáme navíc po migraci front ztratila otázky pro rodinu a prameny v archivech.

## Rozhodnutí

- Kontejner vázaný na rod má barvu rodu stejně jako karta rodu na /rody/ (pruh nahoře, v záhlaví značka rodu). Obecný kontejner
  je neutrální. Jedna komponenta `RodBox.astro`, v Markdownu stejný markup (`class="card rod-box" data-rod="<slug>"`).
- Kontejner s více rody je obecný; rody v něm ukazují značky (ADR 0004).
- Co hledáme: otázky pro rodinu a otevřené otázky jeden kontejner na rod (Obecné první, pak rody podle čísla), prameny v archivech
  podle archivů s barvou rodu u každé položky; na web jdou všechny dotazy na archivy, i ty, které čekají na odeslání; bližší předci
  patří pod Obecné. Veřejné otázky se potvrzují po rodech (`otazky.py potvrd --rod … | --obecne`).
- Rod se v datech vede číslem zakladatele rodu (export ho pro každý přístup přečísluje); nástroje přijímají i název rodu.

## Důsledek

Kontrola webu (`kontrola_webu.py`) hlásí kontejner s rodem bez barvy rodu nebo s cizí barvou, obecný kontejner s barvou a na stránce
Co hledáme víc kontejnerů téhož rodu v jedné části. Nová stránka s obsahem vázaným na rod použije `RodBox`.
