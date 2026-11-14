# Správa repozitáře rodokmen-skill

Fork originálu `sarsonj/rodokmen-skill` (remote `upstream`). Číslo verze forku = verze originálu, na které stojí,
plus `-fork.N` (např. `0.7.0-fork.1`, `0.7.0-fork.2`; po sloučení originálu 0.8.0 znovu `0.8.0-fork.1`) – nikdy
se nepotká s číslem originálu. Novou verzi originálu slučuj `git merge upstream/main` (historie se už nepřepisuje),
PR originálu `git merge --no-ff -m "Merge sarsonj/rodokmen-skill#N: <název>" refs/upstream-pr/N`. Pravidla archivů
z originálu (co skriptem nesmí, `tools/slusne.py` ZAKAZ) platí i pro úpravy forku.

Vydání nové verze: zvedni číslo ve třech místech najednou – `.claude-plugin/plugin.json` (`version`),
`skills/rodokmen/VERZE` (podle něj Claude u uživatele pozná, že má aktualizovat projekt) a README na dvou místech – nahoře „Aktuální verze: X.Y.Z (vydána D. M. RRRR)“ a v požadavcích
„Stav k D. M. RRRR (verze X.Y.Z)“, vždy s číslem verze i datem vydání.
Do `CHANGELOG.md` přidej nahoru sekci `## X.Y.Z – D. M. RRRR` (Nové / Opravy / Návody, krátké odrážky pro uživatele,
čísla issues jako `#11`). Po commitu a pushi vytvoř tag a vydání na GitHubu s textem té sekce:
`awk '/^## X.Y.Z /{f=1;next} /^## /{f=0} f' CHANGELOG.md > /tmp/notes.md && gh release create vX.Y.Z --target main --title "X.Y.Z" --notes-file /tmp/notes.md`.
Mění-li se formát mezi `tools/` a `template/web/`, otestuj i aktualizaci projektu založeného předchozí verzí
(`novy_projekt.py` na stejnou složku, `npm install`, `npm run data`, `npm run build`).

Testy: `python -X utf8 -m unittest discover -s skills/rodokmen/tests` (bez sítě; GitHub Actions je pouští při každém pushi
na Linuxu i Windows spolu s buildem ukázkového webu, `.github/workflows/testy.yml`). Nová funkce nástroje = nový test
v `skills/rodokmen/tests/` (dočasný projekt založí `pomocne.novy_projekt`). Před vydáním navíc
`python -X utf8 skills/rodokmen/tools/smoke_test.py` proti živým portálům – z domácí sítě, ne z firemní (blokace, certifikáty).

Pravidla pro agenty (`skills/rodokmen-agents/rules/`, anglicky) vycházejí z oddílů českého zrcadla originálu (`SKILL.md`, `reference/*.md`).
Po každém `git merge upstream/main` spusť `python -X utf8 scripts/pravidla.py overit`: zastaralé pravidlo (změnil se jeho zdrojový oddíl)
přezkoumej a potvrď `pravidla.py potvrdit <id>`; co z originálu patří do pravidel, přelož do angličtiny. Test `test_agenti_skill.py`
bez potvrzení neprojde. Veřejný repozitář nesmí obsahovat údaje z projektu: před pushem `python scripts/anonymita.py pred-pushem`
(lokální seznam `.anonymita-seznam`, vzor `.anonymita-seznam.priklad`; hook `pre-push` zapíná uživatel příkazem `anonymita.py nainstaluj`).

Agenti (`agents/`, anglicky) a hook orchestrátora (`hooks/`): před sloučením z originálu `python scripts/sync_report.py` (po `git fetch upstream`),
změna definice agenta musí projít `test_agenti_definice.py` (kritérium dokončení, nástroje, odkazy na existující pravidla a skripty).

Pokrytí: nový nástroj v `tools/` potřebuje test (nebo výjimku s důvodem v `tests/e2e/vyjimky.json`), nová trasa v `template/web/src/pages`
záznam v `tests/e2e/stranky.json`; ověřuje `python scripts/pokryti.py` (i v CI). Po aktualizaci projektu na novou verzi spusť v projektu
`tools/brana.py`, jinak hlídač nepustí nasazení.

Markdown: `.markdownlint.yaml` a `.editorconfig` v kořeni; kontrola `npx -y markdownlint-cli2@0.18.1 "**/*.md" "!**/node_modules/**"`
(v CI i před commitem, `--fix` jen s kontrolou `git diff`). MD037 je vypnuté kvůli „* 1890“ (narozen).
