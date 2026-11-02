# Správa repozitáře rodokmen-skill

Vydání nové verze: zvedni číslo ve třech místech najednou – `.claude-plugin/plugin.json` (`version`),
`skills/rodokmen/VERZE` (podle něj Claude u uživatele pozná, že má aktualizovat projekt) a README („Stav k … (verze …)“).
Do `CHANGELOG.md` přidej nahoru sekci `## X.Y.Z – D. M. RRRR` (Nové / Opravy / Návody, krátké odrážky pro uživatele,
čísla issues jako `#11`). Po commitu a pushi vytvoř tag a vydání na GitHubu s textem té sekce:
`awk '/^## X.Y.Z /{f=1;next} /^## /{f=0} f' CHANGELOG.md > /tmp/notes.md && gh release create vX.Y.Z --target main --title "X.Y.Z" --notes-file /tmp/notes.md`.
Mění-li se formát mezi `tools/` a `template/web/`, otestuj i aktualizaci projektu založeného předchozí verzí
(`novy_projekt.py` na stejnou složku, `npm install`, `npm run data`, `npm run build`).

Testy: `python -X utf8 -m unittest discover -s skills/rodokmen/tests` (bez sítě; GitHub Actions je pouští při každém pushi
na Linuxu i Windows spolu s buildem ukázkového webu, `.github/workflows/testy.yml`). Nová funkce nástroje = nový test
v `skills/rodokmen/tests/` (dočasný projekt založí `pomocne.novy_projekt`). Před vydáním navíc
`python -X utf8 skills/rodokmen/tools/smoke_test.py` proti živým portálům – z domácí sítě, ne z firemní (blokace, certifikáty).
