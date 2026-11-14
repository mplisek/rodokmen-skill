# 0002: Deník jako strukturovaná data

Stav: schváleno. Rozhodnutí: Q3, Q8, Q14, Q15.

## Kontext

Deník byl volný Markdown. Tvar záznamů kolísal, do textu pronikaly procesní údaje a web je přebíral.

## Rozhodnutí

Zdrojem pravdy je `denik.jsonl` (jen přidávání, oprava je nový záznam). Tabulka v Markdownu a na webu se generuje pevnou šablonou. Sloupce: datum, zdroj (s typem), rozsah, hledáno, výsledek (výčet + příznak ověřeno), nález (do 400 znaků), citace, osoby, odkaz, opravuje; zbytek v rozbalitelné poznámce. Původní text se uchová v `puvodni`, procesní údaje v `proces` (nevykreslují se).

## Důsledek

Migrace nesmí nic ztratit: `denik.py overit-migraci` ověří každý řádek a doslovnost původního textu.
