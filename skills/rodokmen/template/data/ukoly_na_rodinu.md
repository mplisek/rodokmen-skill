# Otázky pro rodinu (vnitřní fronta)

Úkoly typu „zeptat se rodiny“. **Na web nejde** (soubory `ukoly_*` se při sestavení webu nikdy nečtou).
Spravuje je `python3 -I tools/fronta.py`.

Text, který čte rodina na stránce Co hledáme, je samostatný a potvrzuje ho uživatel:
`python3 -I tools/otazky.py pridej --druh rodina …` (nebo koncept z úkolu: `otazky.py z-ukolu U-0001 --druh rodina`).
Na web patří jen jméno a rok narození žijících, žádné adresy, nemoci ani spory.
