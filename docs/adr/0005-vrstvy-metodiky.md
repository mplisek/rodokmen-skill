# 0005: Vrstvy metodiky: zrcadlo a vlastní pravidla

Stav: schváleno. Rozhodnutí: kapitola 3.

## Kontext

Originál často mění `matriky.md`, `portaly.md` a `SKILL.md`; rozdělení souborů by při slučování tiše ztrácelo změny.

## Rozhodnutí

Soubory z originálu zůstávají česky a beze změny struktury (zrcadlo). Nad nimi je naše anglická vrstva `rules/` s odkazem na zdrojový oddíl a otiskem a tenký anglický skill `rodokmen-agents`. `pravidla.py overit` hlásí změněné oddíly.

## Důsledek

Nová pravidla z originálu se překládají do angličtiny a ukládají v `rules/`.
