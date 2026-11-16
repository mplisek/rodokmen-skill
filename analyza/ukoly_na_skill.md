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

## Stav etap (16. 11. 2026)

Hotové a commitnuté ve větvích `e0-zmirneni` → `e1-kontrakt` → `e2-zapis` → `e3-pokracovani` → `e4-ucastnici` → `e5-web-brana` →
`e6-badatel-metodik` (každá navazuje na předchozí, nic není pushnuto ani sloučeno do `main`): E0 zmírnění, E1 kontrakt čtení, E2 zápis
bez pomocných agentů, E3 pokračování a výřezy, E4 účastníci zápisu a tvrzení, E5 kontrola webu z obou stran a brána, E6 badatel a metodik.
Popis je v CHANGELOG (Nepublikováno) a v `reference/nocni_rezim.md`.

Do projektu se z toho zatím zkopírovalo jen E0 a `spotreba.py`. Nástroje E1–E6 čekají ve skillu na měřicí běh `mereni-v0` (má změřit
dnešní postup dřív, než se změní).

## Otevřené po E0–E6

- Pokus na platformě: jde v pomocníkovi pluginu pokračovat zprávou se zachovaným kontextem (nástroj `SendMessage`), když je řídicí agent
  hlavní vlákno s vlastním seznamem `tools:`? Dnes je pokračování řešeno novým čtenářem, který dostane nález a čte jen rozšíření. Když pokus
  vyjde, přidat `SendMessage` do `tools:` řídicího agenta a do testu definic.
- Úplná sada testů po E6 prošla 16. 11. 2026 ve třech částech (662 testů, včetně sestavení ukázkového webu); na pozadí vcelku ji systém
  jednou ukončil pro nedostatek paměti, proto po částech.
- Přístupy a vyhledávání (scénář 11): kontrola vztahů běží jen nad celým webem (verze `vse`). Pro omezené přístupy chybí kontrola proti
  jejich vlastním datům a hledání jmen, která přístup vidět nemá, v HTML a v indexu vyhledávání.
- Tvrzení (`data/tvrzeni.jsonl`) se zatím jen ukládají a kontrolují; na web se nepromítají. Až bude vidět, kolik faktů v `f` z nich jde
  generovat, rozhodnout o dalším kroku (návrh, oddíl 6.7, možnost c).
- Role účastníků mimo zápisy: kmotr a svědek se na stránce osoby ukáže u zápisu („Role v zápisu“), samostatný oddíl „kmotřenci“ není.
- Po měřicím běhu: zkopírovat nástroje E1–E6 do projektu, v projektu `tools/brana.py`, pak `tools/ucastnici.py navrh` (role k ruční
  kontrole potvrzuje bádání) a měření `mereni-v1` na téže sadě.

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
