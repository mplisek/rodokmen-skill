# Analýza: doplnění badatelské metodiky o noční a víkendový režim

Stav: **návrh k ladění** (12. 11. 2026), nic z toho není implementováno. Pracovní dokument – prochází se a upravuje společně,
po schválení se rozdělí do skillu, šablony a projektu (viz kap. 4).

## 0. Zadání (shrnutí požadavků)

- Úkoly na noc = úkoly, které jde dělat **automaticky, bez lidského badatele**.
- Najde-li se při bádání něco, kde je potřeba **rozhodnout**, zapíše se to v nočním režimu (22:00–6:00) nebo víkendovém
  do `ukoly_k_rozhodnuti.md`; **daný úkol se odkládá**.
- Agent zjistí, že je potřeba **ověřit online někde, kam nemůže** → úkol se odkládá se zápisem do `ukoly_k_badani.md`.
- Co **není online dostupné** → záznam do `archivni_dotazy.md`.
- Nápady, na co se **zeptat rodiny** → `otazky_pro_rodinu.md`.
- Je-li úkol z jakéhokoli důvodu splněn, **záznam se maže z kteréhokoli souboru**.
- Při každém zápisu **kontrola duplicit**; existuje-li podobný úkol, **rozšíří se / doplní** podle rozsahu překryvu.
- Při každém zápisu **setřídění podle priority**; nový nález může změnit prioritu i rozdělit starší úkoly.
- **Úkoly na noc mohou vznikat z jiných úkolů na noc.**
- Běh **v pracovní době** (každý všední den 6:00–22:00): po skončení vyhodnotit výsledky, uložit, zobrazit dotazy a **čekat na instrukci**.
- Běh **mimo pracovní dobu**: jede se do konce úkolů, do konce období, nebo do **DOD** pro danou noc/víkend.
- Rozhodnout, co je **projektová záležitost**, co patří do **skillu** a co do **šablony** pro nové projekty.

## 1. Fronty – pět souborů v `data/`

| Soubor | Co v něm je | Kdo ho řeší |
|---|---|---|
| `ukoly_na_noc.md` | úkol, který jde udělat automaticky bez člověka | pomocníci + hlavní asistent |
| `ukoly_k_rozhodnuti.md` (**nový**) | věc, kde musí rozhodnout člověk | badatel |
| `ukoly_k_badani.md` | úkol jen online v prohlížeči (portál, kam skript nesmí) | badatel s asistentem |
| `archivni_dotazy.md` | věc, která online není | žádost archivu |
| `otazky_pro_rodinu.md` | nápad na otázku pro rodinu | rodina |

### Pravidlo směrování (kam co patří)

1. Jde to skriptem z ARONu bez úsudku → **na noc**.
2. Je třeba rozhodnout (spor zdrojů např. Jan × Matěj, dva kandidáti, změna jména v datech, soukromí, cokoli odesílaného ven)
   → **k rozhodnutí**; původní úkol se odloží a odkazuje na rozhodnutí.
3. Online, ale na portálu, kam skript nesmí (eBadatelna, MZA, Třeboň) → **k bádání**.
4. Online to není → **archivní dotaz**.
5. Může to vědět rodina → **otázka pro rodinu**.

## 2. Formát úkolu a pravidla zápisu

Jedna hlavičková řádka čitelná skriptem + volný text pod ní:

```text
### U-0412 | P1 | os:57,114,115 | typ:křest | cíl:krest:115 | rodič:U-0398 | stav:otevřeno
Anna Vzorová: křest ~1801, Smiřice 42-8 sn. 21 (kandidát) …
```

- **Duplicity:** při zápisu se porovná `typ`, osoby a místo. Překryv → sloučení (sjednocení osob, doplnění textu, priorita =
  maximum). Částečný překryv → doplnit nebo rozdělit podle rozsahu.
- **Priorita** (pravidlem, ne odhadem): **P1** odemyká chybějícího předka, **P2** mění „prob“ na „doc“, **P3** ověřuje
  rodinný údaj. Po každém zápisu přepočet a setřídění (priorita → generace → id).
- **Mazání:** pole `cíl:` je strojově ověřitelné; `kontrola.py` smaže/ohlásí úkol, jehož cíl už v datech je (v kterémkoli
  souboru front).
- **Invariant (platí pro všechny fronty): úkol nikdy nezmizí bez stopy.** Úkol končí jen tím, že je celý zapsán do rodokmenu
  (data), nebo se jeho zbytek zapsal do jiných úkolů v příslušných frontách. Kdykoli se při práci něco zjistí, **nikdy nezůstane
  „nikam neposunuto“**: upřesnění = nový úkol, rozdělení úkolu = víc úkolů, přeřazení = přesun do jiné fronty. Hotový úkol se
  z fronty maže (viz Mazání) právě proto, že jeho výsledek je v datech nebo v následných úkolech.
- **Rodokmen úkolů:** pole `rodič` drží původ (N14 → N14c).
- **Rozdělení a přeřazení:** `rozděl` a `přesuň` umožní, aby nový nález přeřadil starší úkoly (jiný soubor, jiná priorita).

## 3. Režimy podle času (konfigurace `data/rezim.json`)

```json
{"pracovni_dny":[1,2,3,4,5], "pracovni_od":"06:00", "pracovni_do":"22:00",
 "dod": {"max_snimku":150, "max_pomocniku":2, "vlny":"1-3"}}
```

- **Mimo pracovní dobu** (noc 22:00–06:00 a víkend od pátku 22:00 do pondělí 06:00): běh bez člověka. Jede se do konce úkolů,
  konce okna, nebo DOD. **Nikdy se neptá** – rozhodnutí do `ukoly_k_rozhodnuti.md`, úkol se odloží.
- **V pracovní době:** po skončení vyhodnotit výsledky, uložit, vypsat dotazy (rozhodnutí + nové úkoly k bádání) a čekat.
- **Automatický režim a čas (rozhodnuto):** o režimu rozhoduje **čas spuštění**; ukončení je dané časem.
  - Spuštěno v noci/víkendu a běh **doběhne do pracovní doby** → další úkol se už **nepouští**.
  - Konec okna je **dříve** než pracovní doba → hlavní agent **pouští další úkol** (až do konce okna, konce front nebo DOD).
  - Po doběhu každého úkolu **hlavní agent vždy zkontroluje výstupy a zápis** a případně zapíše výsledek tam, kam patří.
- **Beze změny:** jen ARON, max. 2 pomocníci, `tools/slusne.py`, do `data/` píše jen hlavní asistent po ověření na snímku
  (čtyři oči), nic se neodesílá ven.

### Typy úkolů – rozšiřitelné (rozhodnuto)

Úkol na noc není jen bádání v matrikách. Pole `typ:` je **otevřená množina** a platí obecně pro všechny fronty:

| Typ | Příklad | Výsledek |
|---|---|---|
| `bádání` | najdi křest, sňatek, úmrtí | zápis do dat (po ověření na snímku) |
| `skill` | uprav metodiku, nástroj nebo šablonu skillu | změna ve skillu + **test** |
| `test` | otestuj úpravy (testy, lint, build ukázkového webu) | zpráva o výsledku |
| `údržba` | migrace formátu, oprava dat, sjednocení | změna v datech + kontrola |

- Úkoly na úpravu skillu mohou **vznikat z bádání** (agent narazí na slabé místo metodiky nebo nástroje) i z jiných úkolů na noc
  (po změně nástroje následuje úkol `test`). Dnes pro ně slouží `poznamky_pro_skill.md`; v nové podobě to jsou úkoly ve frontě.
- Úkol typu `skill` je splněn teprve tehdy, když **testy a lint projdou**; jinak se vrací jako nový úkol s popisem selhání.
- Směrování zůstává stejné: rozhodnutí, co se v metodice má změnit, patří do `ukoly_k_rozhodnuti.md`; čistě technická oprava
  (překlep, chybějící test) jde rovnou do běhu.

## 4. Kam co patří

### Skill (platí pro všechny projekty)

- sekce „Noční a víkendový režim“ v `SKILL.md` + nový `reference/nocni_rezim.md` (směrování, formát, priorita, DOD, režimy),
- `tools/fronta.py` (přidej, sluč, rozděl, hotovo, přesuň, setřiď, kontrola) + testy,
- rozšíření `tools/kontrola.py` (formát hlaviček, duplicity, úkoly s již splněným cílem),
- obecná „Pravidla běhu“ pomocníků z projektového `ukoly_na_noc.md` se přesouvají do referencí.

### Šablona (nové projekty a aktualizace)

- v `template/data/`: prázdné `ukoly_na_noc.md`, `ukoly_k_rozhodnuti.md`, `ukoly_k_badani.md` a výchozí `rezim.json`,
- `novy_projekt.py` při aktualizaci jen **doplní chybějící** soubory, stávající nepřepíše,
- `template/CLAUDE.md` dostane odkaz na režim,
- fronty se na web **nikdy neexportují** (ověřit testem).

### Projekt `rodokmen` (jen obsah)

- vlastní úkoly a jejich migrace do nového formátu,
- vlastní `rezim.json` a DOD pro konkrétní noc,
- projektové výjimky (seznam „Nelze v noci“, omezení sítě).

## 5. Postup realizace

1. `fronta.py` + testy (parser, slučování, priorita, mazání podle cíle).
2. `reference/nocni_rezim.md` + sekce v `SKILL.md`, šablony souborů, úprava `novy_projekt.py`.
3. Rozšíření `kontrola.py`.
4. Migrace úkolů v projektu `rodokmen`, první noční běh podle nového režimu.

## 6. Otevřené otázky k ladění

1. ~~**Formát:**~~ **Rozhodnuto (12. 11. 2026): markdown s hlavičkovou řádkou.** Soubory musí procházet `markdownlint` (viz kap. 11).
2. ~~**Spouštění**~~ **Rozhodnuto (12. 11. 2026): spouští uživatel.** Výchozí režim se řídí časem spuštění a ukončení je také dané časem (viz kap. 3).
3. ~~**DOD**~~ **Rozhodnuto (12. 11. 2026): ano.** Výchozím ukončením je **čas** (konec noci/víkendu); počet snímků, úkolů, cílová generace a další omezení jsou volitelná a **rozšiřitelná** v `rezim.json` (do budoucna přibudou další možnosti). Konkrétní výchozí hodnoty doladit při implementaci.
4. ~~**Svátky**~~ **Rozhodnuto (12. 11. 2026): ano, svátky se berou jako víkend** (státní svátky v `rezim.json`).
5. ~~**Pomocníci**~~ **Rozhodnuto (12. 11. 2026): ano, počet je nastavitelný v `rezim.json`** (výchozí max. 2).
6. ~~**Čtení nejistých údajů v noci**~~ **Rozhodnuto (12. 11. 2026): varianta A.** Do dat jdou jen **jisté** údaje (shoduje se jméno, rodiče, místo a datum).
   Nejisté (jeden z údajů nesedí nebo je čten s „?“) se zapíše jen jako **kandidát v poznámce** osoby (stav zůstane `prob`) a do
   `ukoly_k_rozhodnuti.md` přibude otázka s možnostmi: potvrdit, zamítnout, přečíst znovu v plném rozlišení.
   Příklad: nemanželská Cäcilia Katharina 22. 4. 1801 (matka Matiek × Martin) × Anna Vzorová.
7. ~~**Chyba portálu**~~ **Rozhodnuto (12. 11. 2026): ano** – úkol zůstane `otevřeno`, zapíše se do deníku (bez interních detailů, kap. 7) a běh skončí.
8. ~~**Úpravy skillu v noci**~~ **Rozhodnuto (12. 11. 2026): princip souhlasí.** Úprava skillu se děje **v samostatné feature větvi** (bez push, vydání a nasazení); ráno
   se rozhodne, co se s větví stane. **Pojmenování `noc/<datum>` ne** – nic neříká. Název větve i zprávy commitů určují šablony v kap. 7.
   **Potvrzeno (12. 11. 2026):** název větve `<typ>/<téma>` (nikdy jen datum) a zpráva commitu `<typ>: <co> (<osoby/téma>)` bez čísla úkolu a bez zmínky agenta či pomocníka.
9. ~~**Souběh skillu a bádání**~~ **Rozhodnuto (12. 11. 2026): nikdy se nekombinují.** Jede buď úprava skillu, nebo bádání (brzda, kap. 8). Pravidla, kdy jede hlavní agent a kdy podagent, jsou v kap. 9.

## 7. Zápisová pravidla a šablony

Cíl: **jednotné zápisy** (dnes se stejná věc zapisuje pokaždé jinak) a **žádné interní údaje o procesu na webu**.

### 7.1 Co nikdy nepatří do textů viditelných na webu a do dat

- Kdo práci udělal: „pomocník N3e“, „hlavní agent“, „sonnet“, „Claude“.
- Jak se ověřilo: „ověřeno na snímku“, „čteno na výřezu“, „čtyři oči“, „vlna 3“, čísla úkolů (N12d, U-0412).
- Co patří: **zdroj** (kniha, sign., snímek, strana), **míra jistoty** (`doc`/`prob`/`fam`, „?“ u nejistého čtení) a **fakta**.
- Proces patří jen do `ukoly_*`, `research_log.md` (pokud se vůbec publikuje) a zpráv commitů, nikdy do `f`, `note`, `shrnuti`, `popis`.
- Kontrola: `kontrola.py` hlásí zakázané výrazy (slovník `pomocník`, `agent`, `úkol N…`, `ověřeno na snímku`, …) v textech, které jdou na web.

### 7.2 Šablony zápisů (jedna podoba pro jeden druh)

Pro každý druh zápisu jedna šablona se stálým pořadím a formátem. Návrh druhů a polí:

- **Fakt osoby (`f`)**: `* <datum> <místo> čp. <č>; <jistota/doplněk>` – stejné zkratky, stejný formát datumu (`D. M. RRRR`), stejné pořadí
  (datum, místo, čp., rodiče/partner, zdroj v závorce `(kniha, sn., str.)`).
- **Poznámka (`note`)**: věcný vztah (otec/matka/manžel), rozpory zdrojů, nejistoty – ne postup bádání.
- **Zápis (`zaznamy.json`)**: `nazev` = `<Druh> <jméno>, <místo> čp., <rok> (<kniha>, <strana>)`; `shrnuti` jen obsah zápisu.
- **Řádek deníku (`research_log.md`)**: stálé sloupce, výsledek v pořadí *nalezeno / vyvráceno / nenalezeno*, odkaz na zdroj.
- **Úkol (fronty)**: hlavičková řádka z kap. 2 + věta „cíl“ + věta „zdroj/postup“.
- **Zpráva commitu:** `<typ>: <co se změnilo> (<osoby nebo téma>)` – bez jména agenta a pomocníka; kdo commit dělal, vyplyne z autora/trailerů, ne z textu.
- **Název feature větve:** `<typ>/<téma>` (např. `skill/fronty-ukolu`, `data/migrace-front`), nikdy jen datum.
- Šablony se uloží do skillu (`reference/zapisy.md`) a kde to jde, vynutí je `kontrola.py` (formát datumu, povinná pole, zakázané výrazy).

## 8. Brzda režimů – bádání × úprava skillu

- V jednom běhu jede **buď** bádání, **nebo** úpravy skillu, **nikdy obojí**.
- Brzda je **technická**, ne jen domluva: při startu běhu se zapíše zámek (např. `data/.beh.json` s typem běhu a časem) a `fronta.py` odmítne
  vzít úkol jiného typu, dokud zámek platí. Zámek se uvolní po ukončení běhu (nebo po vypršení okna).
- Úkoly druhého typu čekají ve frontě; vzniknou-li za běhu (z bádání úkol `skill`), jen se zapíšou a spustí se v dalším běhu.
- Úprava skillu běží **ve feature větvi** (kap. 6, bod 8), ne na hlavní; bádání zapisuje do dat na hlavní větvi projektu.

## 9. Kdo úkol dělá – hlavní agent × podagent

| Činnost | Kdo | Model |
|---|---|---|
| Směrování nálezu, priorita, slučování a dělení úkolů | hlavní agent (plný kontext) | hlavní |
| Ověření čtení, ztotožnění, rozpory zdrojů, zápis do dat | hlavní agent | hlavní |
| Návrh a úprava skillu, architektura, rozhodnutí o formátech | hlavní agent | hlavní |
| Čtení snímků, rejstříků, hledání knih v ARONu (rutinní) | podagent | střední (sonnet) |
| Mechanické práce: stahování, hromadné přejmenování, oprava lintu, migrace podle šablony | podagent | nižší/rychlý |
| Složité čtení (kurent, špatné snímky), nejasné ztotožnění | hlavní agent, případně podagent na vyšším modelu s přesným zadáním | vyšší |

- **Pravidlo:** model odpovídá **složitosti** úkolu; čím víc úsudku a kontextu úkol potřebuje, tím spíš ho dělá hlavní agent.
- Podagent **nikdy nezapisuje do `data/`** ani do skillu; píše jen do svého pracovního výstupu, hlavní agent po doběhu **vždy** zkontroluje výstup a zapíše.
- Počet souběžných podagentů je v `rezim.json` (kap. 6, bod 5); sdílený limit přes `slusne.py` platí dál.
- Typ `skill` a `test`: pracuje hlavní agent; podagent jen na mechanické části (např. lint), nikdy sám o návrhu.

## 10. Nápady a doplnění (sem zapisuj)

-

## 11. Kontrola markdownu (`markdownlint`)

- Konfigurace: `.markdownlint.yaml` a `.editorconfig` v kořeni projektu (i skillu). Spuštění:
  `npx -y markdownlint-cli2 "data/**/*.md" "*.md"`, automatická oprava přidá `--fix`.
- **MD037 je vypnuté** – „* 1890“ (narozen) není zdůraznění a `--fix` by hvězdičku slepil s číslem a text poškodil.
- Po `--fix` vždy zkontroluj `git diff` (zvlášť hvězdičky a mezery v kódu).
- Návrh: `fronta.py` a `kontrola.py` spouštějí lint nad frontami a hlásí chyby; testy skillu lint pouští nad šablonou.
