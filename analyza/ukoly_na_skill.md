# Úkoly na skill (metodika)

Postup, jak pokračovat v úpravě metodiky. Cíl a zdůvodnění: `analyza/navrh-optimalizace.md` (pět příčin P1–P5, etapy E0–E7),
výchozí měření: `analyza/baseline-2026-11-15.md`. Hotový úkol se odsud maže, výsledek je v CHANGELOG.

## Dělba: metodik a badatel

- **Metodik** = sezení nad tímto repozitářem. Mění pravidla, kontrakty, nástroje, definice agentů a testy. Nebádá, nevybírá ani
  nepotvrzuje badatelské případy, neopravuje deník a nerozhoduje, co je správné čtení.
- **Badatel** = sezení nad projektem. O pořadí jeho práce rozhoduje fronta úkolů. Pravidla a nástroje nemění.
- **Od badatele k metodikovi:** technický podnět bez rodinných údajů do `data/poznamky_pro_skill.md` projektu. Metodik ho převezme sem
  (nebo rovnou vyřeší) a v projektu smaže.
- **Od metodika k badateli:** co metodika od bádání potřebuje, se zapíše do `data/STAV.md` projektu (oddíl Rozpracováno, „Předání od
  metodiky“). Nové nástroje jdou do projektu jako kopie až po zelených testech; rozpracovaný úkol dojede podle verze, se kterou začal.
- Metodika **nečeká** na bádání. Jediná vazba: měřicí běh `mereni-v0` má proběhnout dřív, než se do projektu zkopírují nástroje E1.
  Do té doby zůstávají E1 a další ve větvi skillu.

## Jeden krok metodiky

Každá etapa i každý jednotlivý úkol jde stejně:

1. Větev z poslední hotové (`e0-zmirneni` → `e1-kontrakt` → …). Nic se nepushuje, neslučuje do `main` ani nevydává bez pokynu uživatele.
2. Zadání podle šablony v návrhu (oddíl 10.2): co, proč, dopad na K1–K8 a na cenu, hotovo když.
3. Test napřed. Musí chybu skutečně vyvolat (selže před změnou), ne jen hledat slovo v dokumentaci.
4. Změna. Pravidlo má jedno místo: badatelská pravidla `rules/*.md`, tvary dat `schemata/`, směrování `reference/nocni_rezim.md`;
   definice rolí na ně odkazují, neopisují je.
5. Ověření: úplná sada (`python -X utf8 -m unittest discover -s skills/rodokmen/tests`), `scripts/pokryti.py`, markdownlint,
   `scripts/anonymita.py pred-pushem` pro nový commit.
6. CHANGELOG (Nepublikováno), commit, tento soubor aktualizovat.
7. Po etapě stop: uživatel rozhodne o kopii do projektu a o další etapě. Mění-li etapa kontrakt nebo roli, do `STAV.md` projektu
   přibude věta, co se pro bádání mění.

## Pořadí

### E1 – kontrakt výsledku (příčiny P2, P5; na řadě)

- Schémata `zadani/1`, `nalez/1`, `overeni/1`, `rozhodnuti/1` v `skills/rodokmen-agents/schemata/` (jeden zdroj pro validátor, role i testy).
- `tools/vysledek.py over | souhrn | porovnej`: čtenář si výsledek ověří sám před koncem běhu; souhrn pro řídicího agenta dělá skript
  z polí (stav, chybějící pole, rozpory, rozsah, návrh dalšího kroku, čerpání); shodu dvou čtení vyhodnotí `porovnej` po polích.
- `mapa.py zapis` přijme `nalez/1`; signaturu převede na interní ID svazku, nebo odmítne s příkladem správné hodnoty.
- `svazky.json`: pokrytí pramene (koho rejstřík vede: ženichy, nevěsty, obojí; roky). Zadání hledat roli, kterou pramen nevede, se odmítne
  před spuštěním pomocníka.
- `researcher.md`: výsledek podle schématu, přesné příkazy místo `--help`. `verifier.md`: vrací jen vlastní přepis po polích, ne „shodu“.
- `fronta.py rozdel --cast` s vlastními osobami, typem a cenou (bez tichého dědění po rodiči), `uprav --dod`.
- Testy: scénáře 5, 7, 8 z návrhu (oddíl 8.1).

### E2 – transakční zápis (P3)

- `tools/zapis_vysledku.py <rozhodnuti.json>`: deník, mapa, záznam, uzavření úkolu a navazující otázky jedním voláním, celé nebo vůbec,
  opakování nic nezdvojí.
- `tools/commit.py <úkol>`: soubory z historie úkolu, pevný tvar zprávy, kontrola větve.
- `tools/stav.py`: stav bádání ze souborů bez historie rozhovoru (větev, rozpracované úkoly s posledním krokem, rozpočet, rozhodnutí).
- Hook: řídicí agent smí spouštět výčet zapisovacích nástrojů se vstupem ze souboru v `pracovni/` (schváleno uživatelem 15. 11. 2026).
  Fixer a committer z bádání pryč; rozpor `orchestrator.md` × `fixer.md` tím zaniká.
- Testy: scénáře 6, 9, 13.

### E3 – pokračování čtenáře a výřezy (P5)

- Nejdřív pokus: jde v pomocníkovi pluginu pokračovat zprávou se zachovaným kontextem, i když je řídicí agent hlavní vlákno? Podle výsledku
  buď `pokracovani/1`, nebo jen pokračovací balíček pro nový běh.
- `vyrez.py`: řádek širší než limit dělit na díly s překryvem a se souřadnicemi; odmítnout výřez, který by se při čtení zmenšil.
- Test: scénář 2.

### E4 – účastníci zápisu a tvrzení (P1; schváleno uživatelem 15. 11. 2026)

- `zaznamy.json` pole `ucastnici` (osoba, role), `data/tvrzeni.jsonl`, seznam `r` u osoby odvozený a hlídaný kontrolou.
- Migrační nástroj pro existující projekt: návrh účastníků z dnešních `r` a druhu zápisu, sporné k ruční kontrole (tu dělá bádání).
- Export a šablony podle tabulky projekcí (návrh, oddíl 7.2). Testy: scénáře 1, 3, 10.

### E5 – web a brána

- Ručně psaná matice vztahů na ukázkovém projektu, kontrola symetrie v `dist`, kontrola přístupů včetně indexů hledání.
- Brána a hook nasazení: otisk dat, šablon a `dist`. Testy: scénáře 11, 12.

### E6 – dva hlavní agenti

- `orchestrator.md` rozdělit na `badatel.md` (projekt) a `metodik.md` (skill), formát podnětu, verze pravidel a její převzetí mezi úkoly.

## Drobnosti mimo etapy (z poznámek projektu 15. 11. 2026)

- Hook proti holému `rm` (alias `rm -iv` čeká na potvrzení a běh visí) a proti `find .` z kořene projektu (15 GB `pracovni/` na OneDrivu);
  nabídnout `cache.py najdi` a `pracovni_prehled.py`.
- Zrušit `skills:` u committer, verifier, fixer, test-runner (start pomocníka); ověřit měřením, o kolik start klesne.
- Staré názvy souborů v hlášeních `kontrola.py` a `export_web.py`.
- Kontrola prohlížeče skriptem před spuštěním browser-readeru (tři běhy naprázdno).
- Jednotný podpis commitů a zákaz čísel úkolů ve zprávě (dnes hlídá jen text definice; s `commit.py` v E2 odpadne).

## Čeká na uživatele

- Vypnout konektor dokumentů pro projekt, zkrátit `CLAUDE.md` projektu (nasazení jinam), alias `rm` v `~/.bashrc`: jde o prostředí uživatele.
- Model řídicího agenta na celé sezení: rozhodnout po měření na sadě.
- Push a sloučení větví `e0-zmirneni` a dalších, vydání verze.
