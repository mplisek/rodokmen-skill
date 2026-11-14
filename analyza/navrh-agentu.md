# Návrh sady agentů, vynucování pravidel a testů (verze 0.4, rozhodnutí schválena, nic neimplementováno)

Stav: **návrh k diskusi, nic z toho zatím není implementováno.** Celá analýza je česky. Až se návrh schválí, vzniknou
z něj anglické soubory (agenti, instrukce, skilly, metodika pro model); návody k bádání a použití zůstávají česky
(viz kapitola 3).

## 1. Zjištění

### 1.1 Web (`/hledame/`, `/denik/`, rody)

Procházel jsem sestavený web staticky (`web/dist`); test v prohlížeči zatím čeká (kapitola 7).

- **`/hledame/`, konec stránky:** do textu pro rodinu prosákla syntaxe fronty úkolů
  (`U-0000 | P2 | os:1,2 | typ:snatek | cíl:snatek:1 | stav:otevřeno`) a procesní věty („žádost jen po souhlasu“,
  „jsou uložené a přístupné?“). Jedny položky jsou řazené podle rodu, jiné podle archivu.
- **`/denik/`:** záznamy se liší tvarem i obsahem: číslo úkolu a jméno uživatele („Rozhodnuto (U-0000, <jméno uživatele> potvrdil)“),
  cesty do pracovní složky, opravy vepsané do textu („dříve chybně …“), drobné chyby tvaru („Nehledáno :“). Starý i nový
  stav leží v jedné buňce.
- **Rody:** název rodu ve značce s barvou × holý text (hrubé měření): `hledame` 12 × 10, `denik` 0 × 32, `dokumenty`
  32 × 6, `index` 12 × 8. Zajímavosti a stránka Rody jsou jednotné.

### 1.2 Příčina

Pravidla (`reference/zapisy.md`, `tools/fronta.py`) existují, ale **nic je nevynucuje**. Obsah se liší u každého
záznamu (to je správně, bádáme tisíce různých věcí), **forma ale musí být pro daný typ informace pokaždé stejná**. Deník je
tabulka s pevnými sloupci, ne souvislý text. Když se tvar poruší, má to selhat při zápisu a při sestavení, ne zůstat
na webu.

### 1.3 Moje chyba: kdo skutečně zablokoval `curl` na localhost

Napsal jsem, že dotaz na `localhost:4321` zablokoval hlídač sítě. **To není pravda.** Ověřil jsem to: `hlidac_site.py` má
localhost, `127.0.0.1` a vlastní weby ve výjimkách (`VOLNE`) a neblokuje je. Zablokovalo to **plošné pravidlo oprávnění**
v `.claude/settings.json` projektu: `permissions.deny: ["Bash(curl:*)", "Bash(wget:*)"]`. Zapisuje ho `novy_projekt.py`
(`SIT_ZAKAZ`, řádek 314). Pravidlo `deny` má přednost před každým povolením, takže nejde zúžit „curl na localhost“ přidáním
výjimky.

Princip, který z toho plyne a který chci jako závazný:

- **Hlídač střeží vybrané nástroje a vybrané cíle** (archivy a jejich brzda, zápisy do chráněných dat, zveřejnění), **ne
  obecně zakazuje testovat vlastní práci.** Localhost, vlastní test a build nikdy neblokuje.
- Plošný zákaz `curl` a `wget` je příliš hrubý. Hlídač (`hlidac_site.py`) už `curl` na cizí servery přesměruje přes
  `slusne.py curl` a localhost pustí, zákaz je tedy navíc a škodí. Návrh: odstranit `SIT_ZAKAZ` z `novy_projekt.py`
  a při aktualizaci projektu ho ze `settings.json` vyjmout (změna v šabloně, s testem, že localhost projde a archiv ne).
- Výjimky hlídače (`VOLNE`) musí pokrýt **vlastní nasazení, testovací i produkční, na Netlify i Cloudflare**: dnes obsahují
  `netlify.app`, `workers.dev`, `cloudflare.com`, ale **chybí `pages.dev` a vlastní domény**. Vlastní domény se doplní
  z `web.json`, ne jako obecná výjimka. Testy a kontroly nasazeného webu jsou volné, **samotné nasazení** zůstává se souhlasem
  uživatele (kapitola 8, Q12).

## 2. Zásady

1. **Vynucovat, ne doporučovat** (kapitola 5): pravidlo je hotové, až ho **hlídá skript a test**, ne věta v návodu.
2. **Skript před agentem.** Co jde zapsat deterministicky (zápis, řazení, číslování, verze, kontrola, pokrytí), dělá skript.
   Agent dělá úsudek: čtení rukopisu, ztotožnění osob, návrh řešení, psaní textu.
3. **Oddělené role:** kdo hledá, nezapisuje; kdo zapisuje, nehledá; kdo testuje, neanalyzuje; kdo analyzuje, neopravuje; kdo
   opravuje, nerozhoduje o rozsahu. Rozhoduje orchestrátor a uživatel.
4. **Jedna cesta zápisu.** Do `data/` se píše přes `zapis.py` a navazující skripty. Agent bez práva zápisu vrací výsledek
   jako strukturovaný soubor `pracovni/vysledky/<id>.json`.
5. **Každý typ informace má jednu formu** (schéma + šablona vykreslení + test). Veřejný text se z polí **generuje**.
6. **Hlídač jen pro vybrané věci** (kapitola 1.3 a 5.4).
7. **Změna verze skillu v projektu spouští E2E** včetně kontroly pokrytí (kapitola 6).

## 3. Jazyk a vrstvy metodiky (varianta „zrcadlo + vlastní pravidla“)

Rozhodnutí: **soubory přebírané z originálu se nedělí ani nepřekládají**, aby se dál slučovaly gitem. Nad nimi vznikne
naše tenká anglická vrstva pravidel pro agenty a hlídá se, aby nezastarala. Důvody a srovnání variant jsou v historii
diskuse (rozdělení souborů by mělo tiché ztráty při slučování; originál mění `matriky.md` zhruba třikrát týdně).

### 3.1 Vrstvy

| Vrstva | Soubory | Jazyk | Původ | Slučování |
|---|---|---|---|---|
| **Zrcadlo originálu** | `SKILL.md`, `reference/*.md` (`matriky`, `metodika`, `portaly` …), README | česky, **beze změny struktury** | originál + naše úpravy | běžný `git merge upstream/main` |
| **Pravidla pro agenty** | `rules/*.md`, tenký skill `skills/rodokmen-agents/SKILL.md`, definice agentů v `.claude/agents/`, instrukce (`CLAUDE.md`, pravidla orchestrátora) | **anglicky** | naše | nikdy automaticky z originálu |
| **Výsledky a web** | `data/`, deník, fronty (věcný text), veřejné otázky, stránky webu, zprávy uživateli | česky | projekt | – |

Návody k bádání a použití zůstávají česky tam, kde jsou (zrcadlo). Agent odpovídá uživateli česky.

### 3.2 Pravidla pro agenty (`rules/`)

Krátká číslovaná pravidla, ne vyprávění. Každé má pole:

```text
id        stable key, e.g. R-ID-003
when      situation in which the rule applies
do        what the agent must do (imperative, one or two sentences)
why       the failure it prevents (a real case if one exists)
source    mirror file + section heading it derives from, or "fork" if it is our own rule
checked   hash of that section's text at the time the rule was last reviewed
```

Obsahem jsou rozhodovací pravidla: jistota `doc/prob/fam`, ztotožnění osob, co znamená „nenalezeno“, struktura knihy, pravidla
pro pomocníky, provozní pasti prostředí v krátkém tvaru. Vzniknou **extrakcí z dnešních návodů** (jednorázově, ručně
kontrolovaně), ne nahrazením návodů.

### 3.3 Hlídání změn originálu (proti driftu)

- `rules/zdroje.json` vede pro každé pravidlo odkaz na zdrojový oddíl a **otisk (hash) normalizovaného textu oddílu**.
- Skript `tools/pravidla.py`:
  - `overit` porovná otisky se současnými soubory. Pro **změněný** nebo **zmizelý** oddíl vypíše pravidlo a skončí chybou;
  - `potvrdit <id>` po revizi pravidla uloží nový otisk;
  - `pokryti` vypíše oddíly zrcadla, které nemá žádné pravidlo (informativně: co je v návodu nového a pravidlo k tomu není).
- **Po každém `git merge upstream/main`** (agent `upstream-sync`, 4.4) se spustí `pravidla.py overit`. Pro každou změnu vznikne
  úkol „přezkoumat pravidlo R-… proti změně v originálu“ (priorita podle toho, zda je pravidlo bezpečnostní). Nic se neztratí
  mlčky: oddíl je buď beze změny, nebo k němu existuje úkol.
- `overit` je součástí brány E2E po aktualizaci verze (kapitola 6) a testu `tests/pravidla/`.
- **Nová pravidla z originálu:** `upstream-sync` navrhne rozšíření `rules/` (překlad do EN, odkaz na PR nebo commit), schvaluje
  uživatel. Vše, co přijde do `rules/`, je přeloženo do angličtiny a uloženo anglicky.

### 3.4 Co se hlídá jazykově

`tests/jazyk/`: `rules/` a definice agentů jsou anglicky; `data/` (věcné texty), deník a stránky webu jsou česky. **Zrcadlo se
nekontroluje** (je smíšené záměrně).

### 3.5 Tenký anglický skill pro agenty (`rodokmen-agents`)

Rozhodnuto: `SKILL.md` (zrcadlo) zůstává česky a beze změny struktury; vedle něj vznikne druhý, **tenký anglický skill**
`skills/rodokmen-agents/SKILL.md`. Je určený jen agentům (orchestrátor a podagenti), uživatel ho nespouští.

- **Obsah (nejvýš zhruba 120 řádků):** role a seznam agentů s odkazem na jejich definice, smlouvy vstupu a výstupu
  (`pracovni/vysledky/<id>.json`, zadání opravy, karta rozhodnutí), jazyková politika, pravidla zápisu (jen přes skripty),
  odkaz na `rules/` a na `kontext.py` (jak se pravidla vybírají podle tématu). **Neopakuje** obsah `SKILL.md` ani návodů,
  jen na ně odkazuje (např. „archivní zákazy: `slusne.py`, `reference/portaly.md`“).
- **Spouštění:** popis (`description`) anglicky, určený pro agenty; skill se agentům nahrává přes definici
  (`skills:` v `.claude/agents/<jméno>.md`) a orchestrátor ho má vždy načtený. Český `SKILL.md` se tím nezmění ani nezpomalí.
- **Jedna pravda:** když se pravidlo objeví v `rules/`, v tenkém skillu je jen odkaz na jeho `id`, nikdy kopie textu.
- **Testy (`tests/agenti/`):** velikost skillu pod limitem; všechny odkazované soubory a `id` pravidel existují; popis a text
  jsou anglicky; definice každého agenta odkazuje jen na existující skill a nástroje; žádný text z `SKILL.md` se v něm
  neopakuje (kontrola shody řádků).
- **Slučování:** je to náš soubor, originál ho nezná, žádné konflikty. Změny `SKILL.md` z originálu ho neovlivní; dotčená
  pravidla ohlásí `pravidla.py overit` (3.3).

### 3.6 Rozsah vrstvy `rules/` (rozhodnuto)

`rules/` **začíná jen pravidly, která už způsobila skutečnou chybu**, a rozšiřuje se podle potřeby (nová chyba nebo
nová změna originálu = nové pravidlo). Počáteční sada, každá položka s doloženým případem v `matriky.md`, `metodika.md`
nebo v naší práci:

| Téma | Pravidlo (shrnutí) | Zdroj |
|---|---|---|
| Jistota | co je `doc`, `prob`, `fam`; „střední“ jistota od pomocníka na `doc` nestačí | `matriky.md` (Typické pasti), `SKILL.md` |
| Ztotožnění | spojit osoby jen podle dvou nezávislých znaků; vyjmenovat ostatní kandidáty | `metodika.md` (Ztotožnění) |
| „Nenalezeno“ | platí jen pro knihu, která ves pokrývá; index nenašel ≠ neexistuje; zapsat, co se prošlo | `matriky.md` (Knihy po vsích, Typické pasti) |
| Struktura knihy | před závěrem zmapovat všechny oddíly; posun snímek–strana nikdy nedomýšlet | `matriky.md` (Jak vypadá hledání) |
| Pomocníci | nikdy nepsat přepis, který neviděl; výřez, ze kterého četl; slepé druhé čtení | `matriky.md` (Velké kolo), `SKILL.md` |
| Zápis dat | jen přes skripty, žádné `sed -i` ani ruční Python na `data/` | `SKILL.md`, `matriky.md` (Technické pasti) |
| Procesní text | čísla úkolů, jména agentů a uživatelů, cesty nepatří do textů pro web | `zapisy.md`, kapitola 5 |
| Archivní zákazy | co skriptem nesmí (`slusne.py`, `ZAKAZ`); při blokaci skončit | `portaly.md`, `slusne.py` |

Rozšíření (přečíslování domů, místo původu, pasti kurentu a další) přibývají, až se projeví při bádání nebo při sloučení
z originálu. Každé nové pravidlo projde `pravidla.py pokryti` a dostane otisk zdrojového oddílu (3.3).

## 4. Sada agentů

Platforma: **podagent v Claude Code nemůže spouštět další podagenty**, proto orchestrátor běží jako **hlavní vlákno**
(`claude --agent orchestrator`, nebo pravidlo v `CLAUDE.md`). Ostatní jsou podagenti v `.claude/agents/<jméno>.md`
(`name`, `description`, `tools`, `model`; soubory budou anglicky).

### 4.1 Přehled

| Agent | Role | Model (výchozí → eskalace) | Zapisuje | Čte archivy |
|---|---|---|---|---|
| `orchestrator` | rozhodování, volba agenta, modelu a kontextu, brána kvality | nejsilnější | nic | nic |
| `researcher` | bádání v ARON a dalších portálech povolených skriptům | sonnet → opus u kurentu | jen `pracovni/vysledky/` | ano |
| `browser-reader` | čtení portálů zakázaných skriptům (Třeboň, Praha, MZA, Opava), jeden naráz | sonnet | jen `pracovni/` | ano (prohlížeč) |
| `verifier` | nezávislé druhé čtení na snímku („čtyři oči“) | sonnet, jiné sezení než čtenář | nic | jen snímek |
| `record-writer` | převod ověřeného výsledku na zápis přes skripty | haiku → sonnet | `data/` jen přes skripty | nic |
| `upstream-sync` | sledování originálu a PR, překlad, slučování | opus (konflikty), sonnet (rutina) | větev skillu | jen git/GitHub |
| `skill-dev` | změny nástrojů, šablon a testů | sonnet → opus | skill repo (větev) | nic |
| `web-steward` | texty a vzhled webu, jednotnost | sonnet | šablona, `web.json` | nic |
| `test-runner` | spouští testy a E2E, vrací strukturovanou zprávu | haiku | `pracovni/testy/` | nic |
| `test-author` | píše testy podle šablony a seznamu nepokrytého | sonnet | `tests/` | nic |
| `failure-analyst` | rozbor selhání, návrh opravy jako zadání | opus (nejasné), sonnet (jasné) | nic | nic |
| `fixer` | provede opravu přesně podle zadání | sonnet → opus | jen soubory ze zadání | nic |
| `privacy-reviewer` | soukromí před zveřejněním | sonnet | nic | nic |

**Počáteční sada je 9 agentů:** `orchestrator`, `researcher`, `browser-reader`, `verifier`, `upstream-sync`, `test-runner`,
`failure-analyst`, `fixer`, `test-author`. Čtyři zbylé (`record-writer`, `skill-dev`, `web-steward`, `privacy-reviewer`)
**zatím nahrazují skripty a stávající kontroly** (`zapis.py` a spol., testy, `kontrola.py` s E2E soukromím) a agentem se
stanou, až se ukáže, že skript nestačí.

**Skript, ne agent:** `vydani` (verze na třech místech, kontrola CHANGELOGu, tag), `kontext` (sestavení kontextového
balíčku), `denik`, `fronta`, `otazky` (zápisy), `pokryti`, `jazyk`, `sync_report` (co je nového v originále), `fix_auto`
(mechanické opravy).

### 4.2 `orchestrator`

Nástroje: `Agent`, `Read`, `Glob`, `Grep` a úzká výjimka v Bashi pro `fronta.py` (výpis) a `kontext.py`. **Nemá** zápis,
úpravy souborů, web ani prohlížeč. Čte jen proto, aby rozhodl; vše, co chce změnit, jde přes specialistu.

Ke každému úkolu vyrobí **kartu rozhodnutí** (uloží se do záznamu ve frontě): cíl, agent, model a proč, kontextový balíček,
zakázané vstupy, kdy je hotovo, maximum pokusů, kdy se ptát uživatele.

- **Skóre složitosti 0–6** (každý bod = jeden důvod): potřeba číst rukopis; víc kandidátů na osobu; nový archiv nebo portál;
  zasahuje data i kód; zasahuje soukromí; nejasné kritérium hotovo. Směrování: 0–1 haiku/malý sonnet, 2–3 sonnet, 4–6 opus,
  nebo úkol nejdřív rozdělit.
- **Kontextový balíček** sestavuje `kontext.py` deterministicky (záznam osoby, navázané zápisy, otevřené otázky, odstavce
  metodiky podle tématu, pravidla zápisu). Orchestrátor jen **vybere témata**. Zásada: nejmenší balíček, se kterým agent
  dokončí práci, nikdy celé `osoby.py`.
- **Souběh:** nejvýš 2 čtenáři archivu, 1 čtenář v prohlížeči.
- **Stop:** stejné selhání dvakrát, nebo se týká soukromí či archivního zákazu → ptá se uživatele. Nikdy sám neschvaluje
  nic navenek (push, vydání, nasazení, e-mail archivu).

### 4.3 Bádání

- **`researcher`:** výstup je JSON (`úkol, nález: nalezeno|vyvráceno|nenalezeno, osoby, klíč zápisu, zdroj {kniha, signatura,
  snímek, strana}, jistota, citace, poznámky, výřezy`). Nikdy nezapisuje do `data/` a nikdy netvrdí čtení, které neviděl.
  Hlásí vždy **co prošel**, i při nezdaru (pro deník).
- **`browser-reader`:** stejný výstup, jen pro zakázané portály; jedno sezení, pauzy podle `SKILL.md`; při CAPTCHA nebo
  omezení se zastaví a předá uživateli.
- **`verifier`:** dostane jen výřez a otázku, **ne odpověď čtenáře** (slepé čtení); vrátí shoda / neshoda / nečitelné
  s vlastním přepisem. Neshoda jde orchestrátorovi.
- **`record-writer`:** vstup je ověřený soubor výsledku, výstup jsou jen volání `zapis.py`, `denik.py`, `fronta.py`. Věty
  nevymýšlí, skripty je skládají z polí. Jádro (zápis nálezu jedním příkazem) pokrývá otevřené PR #187, doporučuju je převzít.

### 4.4 `upstream-sync`

Krok 1 je **skript** `sync_report.py` (nové commity, verze, PR, issues, dotčené soubory a překryv s naším forkem; tu tabulku
jsem dnes sestavoval ručně). Agent navrhne u každé položky převzít / upravit / vynechat a proč, schvaluje uživatel.
Slučuje běžným `git merge` (zrcadlo se nedělí), pak spustí `pravidla.py overit` a **vytvoří úkoly k přezkoumání
dotčených pravidel** (3.3). Co patří do `rules/`, překládá do angličtiny s odkazem na PR nebo commit. U konfliktů dává
přednost originálu tam, kde fork nic nepřidává. Sám nepushuje ani nevydává, předá zelenou větev orchestrátorovi.

### 4.5 Úprava skillu a správa webu

- **`skill-dev`:** pracuje ve větvi, k nové funkci vždy test (pravidlo z `CLAUDE.md`), před hlášením pustí testy a linter,
  nesahá do `data/` skutečného projektu. Selhání CI sám nevykládá, předá je podle 4.7.
- **`web-steward`:** vlastní pravidla vzhledu (5.3) a šablony. Obsah mění jen přes skripty. Ručně upravený generovaný
  soubor odmítne. Každou vizuální změnu předá `test-runner`u.

### 4.6 `privacy-reviewer`

Před sestavením určeným k nasazení kontroluje: žádný žijící bez souhlasu, žádné RČ, žádný procesní text, žádný zakázaný
dokument. Používá `kontrola.py` a E2E sadu soukromí; agent jen posuzuje hraniční texty. Vrací splněno / nesplněno
s citacemi, nic neupravuje.

### 4.7 Testy a opravy

```text
test-runner  ->  zpráva o selhání (strukturovaná, bez názoru)
                     |
        mechanická třída? (lint, formátování, generovaný soubor, obnova snímku)
                     |-- ano --> skriptová oprava (fix_auto.py), znovu test-runner; bez agenta
                     |-- ne  --> failure-analyst: diagnóza + ZADÁNÍ OPRAVY
                                     |
                       velikost S (<= 1 soubor, beze změny chování) --> fixer (sonnet)
                       velikost M (kód + test, jedna oblast)        --> fixer (sonnet/opus)
                       velikost L (návrh, víc oblastí, soukromí)    --> orchestrátor (rozhoduje uživatel)
                                     |
                              fixer změní JEN soubory ze zadání
                                     |
                              test-runner (stejné testy + celá brána)
                                     |-- zeleně --> hotovo
                                     |-- 2× červeně --> orchestrátor se ptá uživatele
```

- **Analytik nikdy neupravuje, opravář nikdy nerozhoduje o rozsahu.** Jeden agent, který by dělal obojí, je u maličkostí
  rychlejší, ale hodnotí vlastní práci a v „opravě“ se skrývají změny návrhu. Třída S drží cenu nízkou.
- **Zadání opravy:** příznak (test a řádek), příčina s důkazem (commit, řádek, reprodukce), změna (soubory a co), seznam
  povolených souborů, testy ke spuštění, **regresní test (povinné pole)**, riziko, velikost, čeho se nedotýkat.
- **Každá nahlášená chyba dostane regresní test dřív, než se uzavře** (rozhodnuto, Q7). Chybu nahlásil uživatel nebo ji našel
  test: zadání bez regresního testu se nepřijme, `fixer` úkol neuzavře, dokud test neexistuje a neprošel, a `test-author` ho
  napíše podle šablony. Cíl: tatáž chyba se v příštích bězích nemůže vrátit nepozorovaně.
- **`test-runner`** je expert na spuštění a hlášení: `{sada, prošlo, selhalo:[{test, soubor, zpráva}], nestabilní?, doba}`.
  Neúspěšný časovací test **jednou zopakuje** a označí `nestabilní`, nehádá (dnes se to stalo na Windows runneru).
- **`test-author`** píše testy podle šablony a seznamu nepokrytého (kapitola 6), nikdy neupravuje produkční kód.

### 4.8 Příklady rozhodování

| Úkol | Skóre | Agent / model | Balíček |
|---|---|---|---|
| Najít křest Anny Nové, ARON, 1801 | 2 | `researcher` / sonnet | osoba 17 (příklad), matriky fary, pravidla ztotožnění |
| Číst vybledlý kurent 1815, Třeboň | 4 | `browser-reader` / opus, pak `verifier` | výřez, otázka, pasti kurentu |
| Sloučit originál 0.10.2 | 3 | `upstream-sync` / sonnet (opus při konfliktu) | `sync_report`, naše překryvy |
| Špatná mezera v záznamu deníku | 1 | skript (`denik.py oprav`) | žádný |
| Test selhal: nová stránka `/jmena/` bez testu | 2 | `test-author` / sonnet | seznam pokrytí, šablona |

## 5. Vynucování: forma, deník, fronty, web

### 5.1 Čtyři vrstvy vynucení

Pravidlo platí, jen když ho hlídá **každá** z vrstev (selhání jedné zachytí další):

1. **Při zápisu** (skript): zápis přes `denik.py`, `fronta.py`, `otazky.py`, `zapis.py` ověří pole, délky, povolené hodnoty
   a zakázané vzory. Chybný zápis se **odmítne**, nic se neuloží. Text pro člověka skládá šablona z polí, ne agent.
2. **Při pokusu o obejití** (úzký hlídač v `PreToolUse`): blokuje jen **zápis (Edit, Write, Bash) do chráněných souborů**
   (generované Markdown a JSON, `data/denik.jsonl`, `data/ukoly.jsonl`, generované stránky). Hláška řekne, kterým skriptem se
   to dělá. **Žádné jiné nástroje ani cíle neblokuje** (localhost, testy, build).
3. **Při commitu a v CI:** `kontrola.py` a testy z 5.4. Porušení **zastaví** (chyba, ne upozornění).
4. **Při sestavení webu:** `export_web.py` selže s chybou (ne s varováním), když text pro web obsahuje zakázaný vzor nebo
   pole nesplňuje schéma. Web se nesestaví z rozbitých dat.

### 5.2 Registr forem (jeden typ informace = jedna forma)

Soubor `analyza/formy.md` (později anglicky jako instrukce) vede pro každý typ informace: schéma polí, šablonu vykreslení
a test. Návrh typů:

| Typ | Forma | Zdroj pravdy → výstup |
|---|---|---|
| Záznam deníku | **tabulka**, pevné sloupce | `denik.jsonl` → tabulka v Markdownu i na webu |
| Úkol (vnitřní fronta) | tabulka/záhlaví z `nocni_rezim.md` | `ukoly.jsonl`, jen vnitřní, nikdy na web |
| Veřejná otázka (Co hledáme) | karta: rod, otázka, proč, co pomůže | `verejne_otazky.json` → web |
| Fakt osoby (`f`) | `* D. M. RRRR Místo čp. N; doplněk (zdroj)` | `osoby.py` |
| Zápis (`zaznamy.json`) | `nazev` ve stálém tvaru, `shrnuti` jen obsah | `zaznamy.json` |
| Rod | značka (barevný kruh + název) | komponenta `Rod` |

**Záznam deníku:** pevné sloupce `datum | zdroj | rozsah | hledáno | výsledek | nález | citace | osoby | odkaz | opravuje`
(dnešní deník má `# | datum | zdroj | rozsah | hledáno | výsledek | citace`, viz kapitola 10). Zdroj má pevné
pořadí *archiv, signatura knihy, snímek*; `hledáno` je jedna věta (nejvýš 160 znaků); `výsledek` je z výčtu
*nalezeno / vyvráceno / nenalezeno / částečně*. Oprava je **nový záznam** s odkazem na opravovaný, ne přepis textu.

**Zakázáno ve všech textových polích** (skript i `kontrola.py`): číslo úkolu (`U-\d+`, `N\d+[a-z]`), jména agentů a modelů,
jméno uživatele, cesty (`pracovni/`, `C:\`), „ověřeno na snímku“, „čtyři oči“, „vlna“, „dříve chybně“ (to je pole
`opravuje`), mezera před dvojtečkou, šipky `->`.

### 5.3 Jednotná prezentace webu

- **Jeden zdroj značky rodu:** komponenta `Rod` (barevný kruh + název z `lines[slug]`). **Holý název rodu v textu je zakázán.**
  `export_web.py` při sestavení nahradí každý výskyt názvu rodu značkou, autor textu nic neznačkuje. Tvar (schváleno): vždy *kruh
  a za ním název*, bez slova „rod“. **V zadání, pravidlech a metodice je pravidlo anonymní a přenositelné** (obecně
  „název rodu“, příklady jen s vymyšlenými jmény), aby šlo použít v kterémkoli projektu.
- **Barvy** jen z `lines[*].color`; žádná barva rodu mimo komponentu a statistiky.
- **Pořadí rodů** je na všech stránkách stejné (podle čísla předka), oddíl „bez rodu“ je poslední.
- **Datum, místa, čísla domů** stejným tvarem (D. M. RRRR, „čp. N“).
- **Žádný procesní text** na žádné stránce.

### 5.4 Testy (bez sítě)

| Test | Co hlídá |
|---|---|
| `tests/denik/test_schema.py` | pole, délky, výčty, zakázané vzory, pořadí zdroje |
| `tests/denik/test_render.py` | vykreslení do tabulky = referenční soubor |
| `tests/fronta/test_schema.py` | pole úkolu, stavy, duplicity, **vnitřní pole se nikdy nedostanou na web** |
| `tests/web/test_jednotnost.py` | žádný holý název rodu, správná barva značky, stejné pořadí rodů |
| `tests/web/test_proces_text.py` | žádná čísla úkolů, jména agentů, cesty na žádné stránce |
| `tests/web/test_soukromi_e2e.py` | v omezených verzích žádný žijící bez souhlasu, žádné RČ |
| `tests/jazyk/test_jazyk.py` | anglická vrstva anglicky, návody a web česky |
| `tests/hlidac/test_rozsah.py` | hlídač zablokuje zápis do chráněného souboru a **pustí** localhost, test a build |
| `tests/pokryti/test_pokryti.py` | každá stránka a nástroj má test |

Každý nový test napřed ověřím proti dnešním datům: `hledame` a `denik` ho musí **neprojít**, jinak nic nehlídá.

### 5.5 Návrh: kontrola anonymity před pushem do veřejného repozitáře (Q10)

Problém: repozitář skillu je veřejný a údaje z projektu (jména, příjmení, čísla osob a úkolů) se do něj snadno dostanou
v příkladech, testech nebo zprávách commitů. Kontrola se spouští **jen před pushem**, ne při každém commitu, a **nikdy nemění
historii** (rozhodnutí k Q9: git a slučování commitů zůstává na uživateli).

- **Lokální seznam** `.anonymita-seznam` (v `.gitignore`, **ne v gitu**, protože by sám prozradil jména). Jeden řetězec nebo
  regulární výraz na řádek, `#` komentář, hledá se bez ohledu na velikost písmen a diakritiku a nad kmeny (zadáš „Novák“,
  najde i „Novákové“). Řádek `!cesta/souboru` vyjme soubor (např. testovací data s vymyšlenými jmény).
- **Vzorový soubor** `.anonymita-seznam.priklad` je v gitu a obsahuje jen formát, žádná jména.
- **Skript** `scripts/anonymita.py` (údržba repozitáře, není součástí skillu pro projekty):
  - `pred-pushem` projde **všechny přidané řádky a zprávy všech commitů, které se budou pushovat** (`origin/main..HEAD`),
    ne jen výsledný stav. To chytí i jméno, které už je v dalším commitu odstraněné, ale zůstalo v historii (přesně dnešní případ);
  - při shodě skončí chybou a vypíše commit, soubor, řádek a **maskovaný** nález (`Nov***`); nic neopravuje a nepřepisuje;
  - `navrhni-z-projektu <cesta>` vytvoří **kandidáty** na seznam z dat projektu (příjmení a místa z `osoby.py`, bez běžných slov
    a krátkých řetězců), uživatel je prořeže; jména se do repozitáře nikdy nezapisují;
  - `nainstaluj` nastaví `core.hooksPath` na `.githooks/` (hook `pre-push` je v gitu a volá `pred-pushem`).
- **Zdroj pravdy o tom, co je chráněné, je jen lokální seznam.** Chybí-li, hook varuje a push nezastaví (CI seznam nemá).
- **Testy** (`tests/anonymita/`, dočasné repozitáře, bez sítě): shoda v koncovém stavu; shoda jen v prostředním commitu
  (musí selhat); shoda ve zprávě commitu; vyjmutá cesta projde; kmen se skloňováním; chybějící seznam jen varuje; skript nikdy
  nezmění historii ani pracovní strom.
- **Meze:** nechytí údaj, který v seznamu není, ani text v obrázcích. Proto je seznam živý (doplňuje se při každém úniku).

## 6. E2E při aktualizaci verze skillu v projektu

Spouští se po každé aktualizaci projektu na novou verzi (`novy_projekt.py`, změna `VERZE`), řídí ho orchestrátor.

1. `test-runner`: jednotkové testy skillu, `kontrola.py`, export, sestavení všech verzí webu.
2. **Kontrola pokrytí (`tools/pokryti.py`):**
   - **Stránky:** trasy z `web/src/pages` a z vygenerovaných dat (osoba, místo, rod, příběh) proti registru
     `tests/e2e/stranky.json` (vzor trasy → test). Nová nebo změněná trasa bez testu = **selhání brány**.
   - **Nástroje:** každý `tools/*.py` má test (nebo záznam výjimky s důvodem).
   - **Jazyk:** `rules/` a agenti anglicky, data a web česky (zrcadlo se nekontroluje).
   - **Pravidla:** `pravidla.py overit` – žádné pravidlo nesmí odkazovat na změněný nebo zmizelý oddíl bez potvrzené revize.
   - Při nepokrytí skript **sám vytvoří úkoly** do fronty „doplnit test pro `<trasa>`“ (typ `test`, priorita P2) a nabídne
     příkaz `doplň testy`, který je přidělí `test-author`.
3. **E2E v prohlížeči** (Playwright, proti dočasné kopii webu mimo projekt kvůli zámku `dist`):
   - všechny verze webu (správce, každý přístup): odkazy, styly, konzole bez chyb, žádné přetečení na šířkách 420 / 900 / 1400;
   - jednotnost (testy z 5.4): značky rodů, procesní text, jazyk, tvar tabulky deníku;
   - soukromí: přihlášení do omezeného přístupu, skryté osoby a doklady nejsou v DOM ani v obrázcích;
   - brána (přihlášení, odpověď, odkaz s tokenem) a vyhledávání;
   - referenční snímky klíčových stránek (úvod, rod, osoba, statistiky, hledáme, deník): odchylka = ke kontrole.
4. Výsledek jako jedna zpráva: **zelená / červená / nepokryto**. Červená jde analytikovi (4.7), nepokryto autorovi testů.
   Nasazení (testovací i ostré) se nespustí, dokud není zelená a nepokryto = 0.

Otevřené: (c) v projektu je Playwright přes systémový Edge (CDP), v CI Chromium; stačí jedna sada skriptů? (d) Referenční
snímky potřebují údržbu při záměrné změně; chceme je, nebo jen strukturní kontroly?

## 7. Plán (nic nezačínám, dokud neschválíte)

Pořadí a pravidlo schvalování (schváleno, Q13): **po každé fázi se zastavím**, výsledek zůstane jako lokální commity ve větvi
(bez pushe) a uživatel rozhodne, zda pokračovat. **Zatím se nic neimplementuje.**

0. **Hlídač a oprávnění** (malá, nezávislá oprava): odstranit plošný zákaz `curl`/`wget` z `novy_projekt.py` a ze
   `settings.json` projektu, doplnit `pages.dev` a vlastní domény z `web.json`, `tests/hlidac/test_rozsah.py`
   (localhost, test a kontrola na vlastních nasazeních projdou; archiv a zápis do chráněných souborů ne).
1. **Fáze A – vynucování formy:** `denik.py`, `otazky.py`, rozšíření `fronta.py`, `kontext.py`, `jazyk.py`, `pokryti.py`,
   generování Deníku a Co hledáme, testy z 5.4, migrace stávajícího deníku.
2. **Fáze B – web:** komponenta `Rod`, automatické značkování, oprava `hledame` a `denik`, úzký hlídač zápisů.
3. **Fáze C – agenti:** definice v `.claude/agents/` (anglicky), `orchestrator` jako hlavní vlákno, pravidla jazyka.
4. **Fáze D – E2E brána** po aktualizaci verze a její zapojení do `novy_projekt.py`.
5. **Fáze E – vrstva `rules/` a tenký skill (spolu s kontrolou anonymity z 5.5):** jednorázová extrakce pravidel z `matriky.md` a `metodika.md`, `rules/zdroje.json`, `tools/pravidla.py`
   (`overit`, `potvrdit`, `pokryti`), `tests/pravidla/`, skill `rodokmen-agents` + `tests/agenti/`, zapojení do `upstream-sync` a E2E brány.
6. Průběžně: `upstream-sync` začne dělat zprávy hned (nízké riziko).

## 8. Schválená rozhodnutí

| # | Rozhodnutí |
|---|---|
| Q1 | Plošný zákaz `curl`/`wget` se odstraní. Hlídač nikdy neblokuje localhost ani testy a kontroly na vlastních nasazeních (Netlify i Cloudflare, test i produkce, včetně `pages.dev` a vlastních domén z `web.json`). Test to hlídá. |
| Q2 | Úzký hlídač `PreToolUse` blokuje jen ruční zápis do seznamu chráněných souborů, nic jiného. |
| Q3 | Deník: zdroj je `denik.jsonl`, tabulka se generuje. **Z dosavadního výzkumu se nesmí nic ztratit:** `denik.py overit-migraci` ověří počet řádků, že každý starý řádek má záznam a že pole `puvodni` se doslova rovná původnímu textu. |
| Q4 | Veřejné „Co hledáme“ je oddělené od vnitřní fronty, na web jde jen ručně potvrzené. |
| Q5 | Značka rodu = barevný kruh + název, bez slova „rod“. V zadání a metodice je pravidlo anonymní a přenositelné. |
| Q6 | Orchestrátor má Bash jen pro `fronta.py` (výpis) a `kontext.py`. |
| Q7 | Selhání se třídí na mechanická / S / M / L; u L rozhoduje uživatel. E2E má strukturní kontroly bez vizuálních snímků. **Každá nahlášená chyba dostane regresní test** (4.7). |
| Q8 | Historické záznamy deníku: původní text v `puvodni` (jen v datech), procesní údaje v `proces` (nevykreslují se), web používá zbylá pole. |
| Q9 | **Git a historii se nedotýkám.** Slučování lokálních commitů je věc uživatele ve větvi, kterou řídí. Před případným pushem upozorním, že lokální historie analýzy obsahuje starší, neanonymizované verze (`f620962`, `d4f9ebb`). |
| Q10 | Kontrola anonymity před pushem podle lokálního seznamu, bez zásahu do historie (návrh v 5.5). |
| Q11 | Počáteční sada je 9 agentů, čtyři další zatím nahrazují skripty (4.1). |
| Q12 | Testy a kontroly nasazeného webu jsou volné; samotné nasazení vždy se souhlasem uživatele (testovací režim bez `--prod`). |
| Q13 | Pořadí fází 0, A, B, E, C, D; po každé fázi zastávka a rozhodnutí uživatele. **Nic se neimplementuje**, dokud uživatel nedá pokyn. |

Nic z toho zatím není implementované, nic nebylo pushnuto ani vydáno.

## 9. Využití nainstalovaných skillů

V repozitáři jsou nainstalované cizí skilly (`.claude/skills/`, `.agents/`, `skills-lock.json`; zdroj `mattpocock/skills`). Nejsou
součástí našeho skillu a **nic z našeho návrhu na nich nezávisí**: jsou to pomůcky pro práci na něm. Níže je, kde pomáhají.
Dvě jsem rovnou použil (grilling při rozhodování, prototype na deníku, research na ověření platformy).

| Skill | Kde pomůže | Jak | Pozor |
|---|---|---|---|
| `grilling` (a `grill-me`, `grill-with-docs`) | rozhodování o návrhu; později `orchestrator` u nejasných úkolů | kola otázek s doporučenou odpovědí, „frontier“ = otázky, které jde položit hned | `grill-with-docs` zapisuje do glosáře a ADR (viz domain-modeling) |
| `writing-for-agents` | psaní `rules/`, tenkého skillu a definic agentů | pravidla v 9.1 | – |
| `tdd` | způsob implementace každé fáze | testy jen na dohodnutých rozhraních, nejdřív červený test (9.2) | před psaním testu se rozhraní potvrzuje s uživatelem |
| `diagnosing-bugs` | metoda `failure-analyst` a regresní test u každé chyby (Q7) | napřed „těsná“ smyčka, která na chybě padá; u nestabilních chyb měřit četnost (9.3) | – |
| `domain-modeling` | `GLOSSARY.md` a záznamy rozhodnutí (ADR) | sjednotí pojmy (rod, větev, přístup, pohled, svazek, záznam × zápis, jistota), které dnes kolísají; Q1–Q13 jsou hotové ADR (9.4) | soubory vznikají až při implementaci |
| `codebase-design`, `improve-codebase-architecture` | Fáze A | `denik`, `fronta` a `otazky` jsou tři skoro stejné „ověřované přidávací úložiště“; navrhuju jeden hluboký modul s jednou smlouvou a registrem schémat (9.5) | – |
| `code-review` | brána po každé fázi (Q13) | osa „Standards“ = `CLAUDE.md` + `rules/`, osa „Spec“ = tato analýza; výsledek vidí uživatel před rozhodnutím | – |
| `implement-spec`, `implement` | možný vykonavatel fází z úkolů s grafem závislostí | úkoly = fronta s `zavisi_na`; ale automaticky slučuje větve | **koliduje s Q9**: použít jen na větvi, kterou uživatel určí a výslovně povolí slučování; vyžaduje nastavení sledování úkolů, které tu není |
| `research` | ověřování faktů o platformě a sledování originálu | pozadí agent čte jen primární zdroje a píše soubor; teď běží (`analyza/overeni-platformy.md`) | – |
| `prototype` | zkouška tvaru, než se napíše šablona | použito na deníku (kapitola 10); stejně se vyzkouší tabulka deníku a značka rodu | zahazuje se |
| `handoff` | předání rozdělané práce novému sezení (také mezi fázemi) | shrne rozhovor a odkáže na soubory, ne je opakuje | musí vynechat osobní údaje |
| `pr` | popis PR při příspěvku do originálu | – | zatím nepotřeba |

Doporučení k repozitáři: protože jsou to cizí nástroje uživatele, patří do `.gitignore` (`.agents/`, `.claude/skills/`,
`skills-lock.json`), pokud je nechceš sdílet ve veřejném forku. Rozhodnutí je na uživateli.

### 9.1 Pravidla psaní agentů a pravidel (podle `writing-for-agents`)

- **Ukazatele s jednou spouštěcí podmínkou na větev:** `description` agenta i skillu začíná rozhodujícím slovem a nevyjmenovává
  synonyma. Orchestrátor má jeden ukazatel na `rules/` a vybírá téma přes `kontext.py`.
- **Jedna pravda:** pravidlo žije jen v `rules/`, ostatní dokumenty na ně ukazují přes `id`. Co je v prostředí (`--help`,
  schémata, seznam nástrojů), se nepřepisuje, jen se odkazuje.
- **Každý krok končí kritériem dokončení, které jde ověřit a je vyčerpávající.** Příklad: `researcher` je hotov, když existuje
  soubor výsledku **a** seznam všech prohledaných rozsahů; karta rozhodnutí má pole „hotovo, když“.
- **Žádné řízení zákazy.** Věty typu „nikdy nezapisuje do `data/`“ přitahují pozornost k zakázanému. Specifikace říká, co agent
  dělá („výsledek vrací jako soubor v `pracovni/vysledky/`; do `data/` zapisují skripty“), a zákaz vynucuje hlídač (kapitola 5).
  V návrhu výše jsou ještě formulace se zákazy, při psaní skutečných definic se přepíšou.
- **Vedoucí slova** (jeden pojem = jeden token, stále stejný): *frontier* (úkoly připravené k přidělení), *červený* test,
  *rozhraní* (testovaný okraj), *balíček* (kontext), *brána* (kontrola před krokem). Patří do glosáře.
- **Dvě zátěže:** nepřidávat dokumenty a ukazatele bez důvodu. Člověk je rejstřík, proto zůstává 9 agentů a 8 témat pravidel.
- **Vyřadit prázdné pokyny:** co model dělá sám od sebe, se nepíše.

### 9.2 Postup `tdd` v našich fázích (rozhraní ke schválení)

Před každou fází navrhnu **rozhraní, na kterých se testuje**, a uživatel je potvrdí; mimo ně žádné testy. Každý test je nejdřív
červený (u webu proti dnešním datům, 5.4).

| Fáze | Rozhraní (testuje se zvenku) |
|---|---|
| 0 | vstup a výstup hlídače (příkaz → povolit/zablokovat + hláška); obsah `settings.json`, který vytvoří `novy_projekt.py` |
| A | příkazy `denik.py`, `fronta.py`, `otazky.py` (argumenty → soubor dat + vykreslená tabulka); `overit-migraci`; chyba exportu při zakázaném vzoru |
| B | sestavené HTML (`dist/`): značka rodu, pořadí rodů, žádný procesní text |
| E | příkazy `pravidla.py` nad dočasným zrcadlem; kontrola velikosti a odkazů tenkého skillu |
| D | `pokryti.py` nad dočasným projektem |

Bez zesměšňování vnitřku: žádné mockování našich vlastních modulů, jen dočasné projekty a soubory.

### 9.3 Postup `failure-analyst` (podle `diagnosing-bugs`)

První výstup analytika není úvaha, ale **příkaz, který na chybě padá** (jeden, už jednou spuštěný, s ukázaným výstupem). Teprve
pak následuje příčina a zadání opravy. U nestabilních chyb (dnešní časovací testy na Windows) je cíl **změřit četnost**
(opakovat 20×, uvést podíl pádů), ne „spustit znovu a doufat“. To zpřesňuje `test-runner`: jedno opakování zůstává, ale
při druhém pádu se místo zprávy o selhání spustí měření četnosti a výsledek se označí `nestabilní (X z 20)`.
Pravidlo z Q7 (regresní test u každé nahlášené chyby) je přímo tato červená smyčka uložená jako test.

### 9.4 Glosář a záznamy rozhodnutí (podle `domain-modeling`)

Návrh (nevytváří se, dokud se nezačne): `GLOSSARY.md` v kořeni (česky, u pojmů pro agenty anglický ekvivalent) a `docs/adr/`.
Počáteční pojmy, které dnes kolísají: rod × větev × linie, přístup × pohled × verze webu, záznam × zápis, jistota (`doc`, `prob`,
`fam`), úkol × fronta × veřejná otázka, deník × výzkumný deník. Rozhodnutí Q1–Q13 z kapitoly 8 se převedou na ADR (jedno na
rozhodnutí, krátce: kontext, rozhodnutí, důsledek).

### 9.5 Jeden hluboký modul místo tří (podle `codebase-design`)

`denik`, `fronta` a `otazky` dělají totéž: ověřují pole podle schématu, přidávají do souboru jen na konec, hlídají zakázané
vzory a vykreslují tabulku. Navrhuju jeden modul (provizorně `zaznamy_store`) s jedinou smlouvou (`pridej`, `oprav`, `vykresli`,
`over`) a **registrem schémat** (deník, úkol, veřejná otázka, později další typy). Nový typ informace pak znamená jen nové
schéma a šablonu, ne další skript. Rozhraní je malé, uvnitř je validace, zámek souboru a vykreslení.

### 9.6 Nový prvek do fronty: závislosti (podle pojmu *frontier*)

Do `ukoly.jsonl` přidat pole `zavisi_na` (seznam id). Orchestrátor pak přidělí jen úkoly, jejichž závislosti jsou hotové
(frontier), a může je dávat paralelně do limitu z 4.2. Dnes se pořadí drží v hlavě a v prioritách.

## 10. Zjištění z prototypu deníku (zahozená zkouška na dnešních datech)

Jednorázový skript (mimo repozitář, jen součty, žádná jména) prošel dnešní `research_log.md`. Výsledek mění část návrhu:

- **277 řádků tabulky, ale jen 259 se rozdělí na 7 sloupců; 18 ne** (6 sloupců, nejspíš nezapsaná buňka nebo znak `|` v textu).
  Migrace tedy nesmí tiše přeskakovat: `denik.py overit-migraci` musí selhat, dokud není zpracovaných všech 277 (Q3).
- **Skutečné sloupce jsou `# | datum | zdroj | rozsah | hledáno | výsledek | citace`.** Můj návrh sloupců jsem proto upravil
  (5.2): přibyly `rozsah` a `citace`, `nález` je krátké shrnutí.
- **17 % řádků (45 z 259) má zakázaný vzor:** 28 zmiňuje pomocníka, agenta nebo model, 13 cesty, 6 čísla úkolů, 6 procesní
  věty, 5 „opraveno“. Potvrzuje to Q8 (`puvodni` + `proces`).
- **Pole `výsledek` je mix:** 80 × „nenalezeno“, 68 × „nalezeno“ a pak varianty (`nalezeno (ověřeno)`, `potvrzeno`, `nedočteno`,
  `částečně`, `nenalezeno / nečitelné`), **11 řádků bez klíče**. Výčet hodnot se musí zvolit a existující varianty namapovat.
- **`výsledek` + `citace` je souvislý text:** medián 492 znaků, 83 řádků přes 600, nejdelší 1692. „Tabulka vždy“ proto potřebuje
  rozhodnutí, co smí být v buňce dlouhé a co se rozdělí (citace zvlášť, poznámka zvlášť).
- **`zdroj`:** 204 z 259 začíná archivem, 244 obsahuje snímek, signaturu nebo `apu`. Zbytek jsou stopy, rodinné zdroje apod.
  Zdroj tedy potřebuje **typ** (archiv, stopa, rodina, jiné).

Nové otevřené otázky z prototypu (Q14 a Q15) jsou v odpovědi uživateli, po schválení se zapíšou do kapitoly 8.

## 11. Ověření platformy

Předpoklady návrhu o Claude Code (podagent nespouští podagenty, hlavní vlákno jako agent, `skills:` u agenta, omezení Bashe,
přednost `deny`, hooky) ověřuje agent z primárních zdrojů do souboru `analyza/overeni-platformy.md`. Dokud nedoběhne, jsou
to nepotvrzené předpoklady.
