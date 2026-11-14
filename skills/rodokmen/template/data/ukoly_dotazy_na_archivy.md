# Dotazy na archivy (vnitřní fronta)

Úkoly typu „ověřit v archivu / na matričním úřadě“. **Na web nejde** (soubory `ukoly_*` se při sestavení webu nikdy nečtou).
Spravuje je `python3 -I tools/fronta.py` (zápis úkolu, třídění, hotovo); žádosti do archivu viz `zadosti.md`.

Veřejný text pro stránku Co hledáme („Prameny mimo online matriky“) je samostatný a potvrzuje ho uživatel:
`python3 -I tools/otazky.py pridej --druh pramen …` (nebo koncept z úkolu: `otazky.py z-ukolu U-0001 --druh pramen`).

Úkol v souboru: hlavička `## U-0001 | P2 | os:57,114 | typ:křest | cíl:krest:115 | stav:otevřeno` a pod ní volný text.
