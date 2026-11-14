# 0003: Veřejné otázky odděleně od vnitřní fronty

Stav: schváleno. Rozhodnutí: Q4.

## Kontext

Soubory front (`archivni_dotazy.md`, `otazky_pro_rodinu.md`) se přenášely na web, takže tam skončily řádky fronty a procesní věty.

## Rozhodnutí

Vnitřní úkoly se na web nikdy nepřenášejí. Veřejná otázka je samostatný záznam (`verejne_otazky.json`) a vzniká z úkolu ručním potvrzením.

## Důsledek

Web čte jen `verejne_otazky.json`. Stránka Co hledáme se generuje z polí, ne z textu fronty.
