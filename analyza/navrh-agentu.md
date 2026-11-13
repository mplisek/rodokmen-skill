# Návrh sady agentů, vynucování pravidel a testů (verze 0.2 k iteraci)

Stav: **návrh k diskusi, nic z toho zatím není implementováno.** Celá analýza je česky. Až se návrh schválí, vzniknou
z něj anglické soubory (agenti, instrukce, skilly, metodika pro model); návody k bádání a použití zůstávají česky
(viz kapitola 3).

## 1. Zjištění

### 1.1 Web (`/hledame/`, `/denik/`, rody)

Procházel jsem sestavený web staticky (`web/dist`); test v prohlížeči zatím čeká (kapitola 7).

- **`/hledame/`, konec stránky:** do textu pro rodinu prosákla syntaxe fronty úkolů
  (`U-0013 | P2 | os:32,33 | typ:snatek | cíl:snatek:32 | stav:otevřeno`) a procesní věty („žádost jen po souhlasu“,
  „jsou uložené a přístupné?“). Jedny položky jsou řazené podle rodu, jiné podle archivu.
- **`/denik/`:** záznamy se liší tvarem i obsahem: číslo úkolu a jméno uživatele („Rozhodnuto (U-0011, Martin potvrdil)“),
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

## 3. Jazyková politika (upravená podle zpětné vazby)

Dvě vrstvy:

| Vrstva | Jazyk | Co do ní patří |
|---|---|---|
| **Metodika pro model** (řídí chování) | **angličtina** | skilly (`SKILL.md`), instrukce (`CLAUDE.md`, pravidla pro agenty), definice agentů, rozhodovací pravidla (ztotožnění osob, jistota `doc/prob/fam`, pasti), šablony polí |
| **Návody k bádání a použití** (jak bádat, portály, postupy) | **čeština** | dnešní `reference/*.md` (portály, matriky, instalace, web, zadosti …) a README |
| **Výsledky bádání a web** | **čeština** | `data/`, deník, fronty (věcný text), veřejné otázky, stránky webu, zprávy uživateli |

Pravidla:

- **Co se přebírá z PR nebo z originálního repozitáře a patří do metodiky pro model, překládá se do angličtiny a ukládá
  v angličtině** (původní český text se v repozitáři nenechává, zůstane odkaz na PR nebo commit). Návody k bádání a použití
  z originálu zůstávají česky, tak jako dosud.
- Identifikátory (klíče dat, názvy souborů, `doc/prob/fam`) se nepřekládají.
- Agent odpovídá uživateli česky.

Vynucení: `tools/jazyk.py` + `tests/jazyk/` kontroluje, že (a) soubory anglické vrstvy jsou anglicky, (b) návody, data a web
jsou česky. Hranici mezi vrstvami určuje seznam cest v `analyza/jazyk-vrstvy.json` (návrh níže).

Otevřené: (a) **Kam patří dnešní `matriky.md` a `metodika.md`?** Jsou napůl návod, napůl pravidla pro model. Navrhuju je
rozdělit: rozhodovací pravidla (ztotožnění, jistota, pasti, ověřování) do anglické vrstvy, postupy a příklady zůstanou
česky v návodech. (b) `SKILL.md` má české spouštěcí fráze („rodokmen“, „předci“); navrhuju je nechat v `description`
česky, protože podle nich se skill spouští, a zbytek psát anglicky.

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
jsem dnes sestavoval ručně). Agent navrhne u každé položky převzít / upravit / vynechat a proč, schvaluje uživatel. Obsah
metodiky pro model se překládá do angličtiny, návody zůstávají česky; mapování `odkaz na originál → místní soubor` je
v `analyza/upstream-mapa.json`. U konfliktů dává přednost originálu tam, kde fork nic nepřidává. Sám nepushuje ani
nevydává, předá zelenou větev orchestrátorovi.

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
  povolených souborů, testy ke spuštění, riziko, velikost, čeho se nedotýkat.
- **`test-runner`** je expert na spuštění a hlášení: `{sada, prošlo, selhalo:[{test, soubor, zpráva}], nestabilní?, doba}`.
  Neúspěšný časovací test **jednou zopakuje** a označí `nestabilní`, nehádá (dnes se to stalo na Windows runneru).
- **`test-author`** píše testy podle šablony a seznamu nepokrytého (kapitola 6), nikdy neupravuje produkční kód.

### 4.8 Příklady rozhodování

| Úkol | Skóre | Agent / model | Balíček |
|---|---|---|---|
| Najít křest Anny Matějkové, ARON, 1801 | 2 | `researcher` / sonnet | osoba 231, matriky fary, pravidla ztotožnění |
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

**Záznam deníku:** pevné sloupce `datum | zdroj | hledáno | výsledek | nález | osoby | odkaz | opravuje`. Zdroj má pevné
pořadí *archiv, signatura knihy, snímek*; `hledáno` je jedna věta (nejvýš 160 znaků); `výsledek` je z výčtu
*nalezeno / vyvráceno / nenalezeno / částečně*. Oprava je **nový záznam** s odkazem na opravovaný, ne přepis textu.

**Zakázáno ve všech textových polích** (skript i `kontrola.py`): číslo úkolu (`U-\d+`, `N\d+[a-z]`), jména agentů a modelů,
jméno uživatele, cesty (`pracovni/`, `C:\`), „ověřeno na snímku“, „čtyři oči“, „vlna“, „dříve chybně“ (to je pole
`opravuje`), mezera před dvojtečkou, šipky `->`.

### 5.3 Jednotná prezentace webu

- **Jeden zdroj značky rodu:** komponenta `Rod` (barevný kruh + název z `lines[slug]`). **Holý název rodu v textu je zakázán.**
  `export_web.py` při sestavení nahradí každý výskyt názvu rodu značkou, autor textu nic neznačkuje. Návrh tvaru: vždy *kruh
  a za ním „Plíškové“*, bez slova „rod“.
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

## 6. E2E při aktualizaci verze skillu v projektu

Spouští se po každé aktualizaci projektu na novou verzi (`novy_projekt.py`, změna `VERZE`), řídí ho orchestrátor.

1. `test-runner`: jednotkové testy skillu, `kontrola.py`, export, sestavení všech verzí webu.
2. **Kontrola pokrytí (`tools/pokryti.py`):**
   - **Stránky:** trasy z `web/src/pages` a z vygenerovaných dat (osoba, místo, rod, příběh) proti registru
     `tests/e2e/stranky.json` (vzor trasy → test). Nová nebo změněná trasa bez testu = **selhání brány**.
   - **Nástroje:** každý `tools/*.py` má test (nebo záznam výjimky s důvodem).
   - **Jazyk:** každý soubor je ve své vrstvě ve správném jazyce.
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

0. **Hlídač a oprávnění** (malá, nezávislá oprava): odstranit plošný zákaz `curl`/`wget` z `novy_projekt.py` a ze
   `settings.json` projektu, test `tests/hlidac/test_rozsah.py`.
1. **Fáze A – vynucování formy:** `denik.py`, `otazky.py`, rozšíření `fronta.py`, `kontext.py`, `jazyk.py`, `pokryti.py`,
   generování Deníku a Co hledáme, testy z 5.4, migrace stávajícího deníku.
2. **Fáze B – web:** komponenta `Rod`, automatické značkování, oprava `hledame` a `denik`, úzký hlídač zápisů.
3. **Fáze C – agenti:** definice v `.claude/agents/` (anglicky), `orchestrator` jako hlavní vlákno, pravidla jazyka.
4. **Fáze D – E2E brána** po aktualizaci verze a její zapojení do `novy_projekt.py`.
5. Průběžně: `upstream-sync` začne dělat zprávy hned (nízké riziko).

## 8. Rozhodnutí, která potřebuju od vás

1. **Hranice jazykových vrstev** (3, otevřená otázka a): rozdělit `matriky.md` a `metodika.md` na anglická rozhodovací
   pravidla a české postupy?
2. **Hlídač:** souhlasíte s bodem 0 (odstranit plošný zákaz `curl`/`wget`) a s úzkým hlídačem zápisů z 5.1?
3. **Obrácení toku deníku** (JSONL zdroj, tabulka generovaná): souhlasíte s migrací stávajícího `research_log.md`?
4. Značka rodu: *kruh + „Plíškové“*, bez slova „rod“?
5. Orchestrátor jako hlavní vlákno, s výjimkou pro `fronta.py` a `kontext.py`, nebo bez Bashe a zápisy front přes `clerk`?
6. Oprava selhání: třídění mechanická / S / M / L z 4.7; má u L vždy rozhodnout uživatel?
7. E2E: vizuální referenční snímky, nebo jen strukturní kontroly?
8. Veřejné „Co hledáme“: potvrzujete, že vnitřní fronta se na web nikdy nepřenáší automaticky?
