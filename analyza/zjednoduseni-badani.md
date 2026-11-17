# Zjednodušení bádání: dvě možnosti

Stav k 17. 11. 2026. Podnět uživatele: metodika bádání ve forku je překombinovaná a složitá. Dokument porovnává dvě cesty:

- **A – vzít originál** (sarsonj/rodokmen-skill 0.10.2) a doplnit do něj jen to, co je v otevřených PR originálu, ve forku nebo
  v návrhu zjednodušení a co se osvědčilo,
- **B – zjednodušit fork**, tedy ponechat dnešní základ a odebírat.

Je to **jen návrh**, nic z něj není implementované. Zdroje zjištění: **[kód]** čtení kódu a historie gitu, **[měření]**
`analyza/mereni-v0-2026-11-16.md`, **[běh]** záznamy bádacích sezení, **[hypotéza]** úsudek k ověření. Rodinné údaje tu nejsou.

## 1. Proč

- **[kód]** Fork má 80 nástrojů (21 tisíc řádků), originál 28 (6 tisíc řádků). `SKILL.md` forku má 4 700 slov, originálu 3 200.
  Definice badatele má 2 300 slov, 19 nástrojů a tabulku 16 cest k zápisu; agentů je 12, pravidel pro agenty 32.
- **[kód]** Jeden výsledek čtení prochází čtyřmi soubory (zadání, nález o 80 řádcích vzoru, ověření, rozhodnutí o 79 řádcích vzoru)
  a asi deseti kroky: `stav`, `frontier`, `kontext`, `zadani novy`, čtenář, `souhrn` (případně `rozsir`, `pripoj`), ověřovatel,
  `porovnej`, ručně skládané rozhodnutí, `zapis_vysledku`, `commit`.
- **[měření]** `mereni-v0`: 7 837 tis. ekvivalentních tokenů na 11 případů.
- **[běh]** Audit jednoho zápisu úmrtí (17. 11.), který všechna čtení čtou obsahově stejně, potřeboval čtyři kola oprav metodiky
  a ověřený není. Každé kolo přidalo výjimku: normalizace textu, „kratší čtení“, nespárovaná pole, `vysledek.py jadro`, `z_cteni`,
  `audit.pole`, `porovnej --pole`, započtení ověření rodičovského čtení.
- **[kód]** Příčina: ověření porovnává **volně pojmenovaná a volně ohraničená textová pole doslova**. Spor, který člověk nad výřezem
  rozhodne za vteřinu, řeší třetí a čtvrté slepé čtení, a nové čtení spor často rozšíří.

## 2. Rozdílová analýza: fork proti originálu

Srovnání `main` forku (0.10.2-fork.1) s `upstream/main` (0.10.2), **[kód]** `git diff upstream/main main`, 302 commitů forku navíc.

### 2.1 Přehled podle oblastí

| Oblast | Nové soubory | Změněné soubory originálu | Řádky + / − | Poznámka |
|---|---|---|---|---|
| `skills/rodokmen/tools/` | 53 | 21 | 15 450 / 341 | 52 nových nástrojů a k nim moduly; změny originálu hlavně v `export_web.py`, `kontrola.py`, `vyrez.py` |
| `skills/rodokmen/reference/` | 4 | 8 | 1 607 / 77 | nové `nocni_rezim.md`, `zapisy.md`, `zadosti.md`, `stavby.md` |
| `skills/rodokmen/template/web/` | 29 | 32 | 4 092 / 320 | 11 nových stránek, přístupy, komponenty |
| `skills/rodokmen/template/data/` | 13 | 3 | 221 / 21 | jiné formáty dat projektu (2.2); 2 soubory originálu smazané |
| `skills/rodokmen/SKILL.md` | – | 1 | 209 řádků změn | 4 700 slov proti 3 200 (2.3) |
| `skills/rodokmen/tests/` | 81 | – | 10 745 / 0 | testy nástrojů forku (unittest), originál je nemá |
| `tests/` | 20 | 11 | 2 828 / 19 | skriptové testy originálu a jejich rozšíření |
| `agents/`, `hooks/`, `skills/rodokmen-agents/` | 25 | – | 1 324 / 0 | 12 agentů, 3 hooky, 32 pravidel; originál nemá nic z toho |
| `scripts/`, `docs/adr/`, `GLOSSARY.md`, CI, `.githooks/` | 18 | – | asi 1 000 | údržba repozitáře: pokrytí, pravidla, anonymita, synchronizace s originálem, ADR |
| `analyza/` | 17 | – | 3 303 / 0 | analýzy a návrhy metodiky (pracovní dokumenty) |

Ve forku je tedy asi 40 tisíc řádků navíc, z toho asi 13,5 tisíce řádků testů a 3,3 tisíce řádků pracovních analýz.

### 2.2 Data projektu

Tady je rozdíl, který rozhoduje o migraci (možnost A, oddíl 4.2).

| Soubor v `data/` | Originál | Fork |
|---|---|---|
| deník | `research_log.md` (Markdown tabulka, ručně) | `denik.jsonl` (záznam na řádek, jen přes `denik.py`, opravy novým řádkem, osoby klíčem, snímky); `research_log.md` ze šablony zmizel |
| dotazy archivům | `archivni_dotazy.md` | fronta `ukoly_dotazy_na_archivy.md`; `archivni_dotazy.md` ze šablony zmizel |
| úkoly | odrážky v `STAV.md` → Rozpracováno | 6 front `ukoly_*.md` (vstup, noc, bádání, rozhodnutí, rodina, archivy) a historie `ukoly_historie.jsonl` |
| stav a předání | `STAV.md`, ručně | `STAV.md` vede `stav.py` (předání, pravidla od uživatele), ručně se nepíše |
| zápisy | `zaznamy.json` | navíc pole `ucastnici` (osoba a role), `overeno`, `audit`, `odkaz` |
| tvrzení, opravy | – | `tvrzeni.jsonl`, `opravy.jsonl` |
| veřejné otázky | součást `STAV.md` a front | `verejne_otazky.json` (stránka Co hledáme, ADR 0003, 0009) |
| nastavení | `web.json` | navíc `rezim.json` (noční režim, rozpočet, podpis commitu) |
| stavby, žádosti, příběhy | – | `stavby.py`, `zadosti.md`, `pribehy/*.md` |
| osoby | `osoby.py` (P, LINES, SIDE, ISSUES, HYPOTEZY, SAME) | totéž a navíc `RODINA` (příbuzní mimo přímou linii s vlastní stránkou) |
| pracovní soubory | `pracovni/` volně | navíc kontrakty `pracovni/zadani/`, `pracovni/vysledky/` (zadání, nález, ověření, rozhodnutí), `brana.json` |

Společné beze změny tvaru: `osoby.py` (P, LINES, SIDE…), `zaznamy.json` (základní pole), `prepisy.json`, `svazky.json`, `mista.json`,
`dokumenty.json`, `zvyrazneni.json`, `udaje_od_rodiny.md`, `zajimavosti.md`, `pribeh.md`.

### 2.3 Postup bádání (`SKILL.md` a role)

| Krok | Originál | Fork |
|---|---|---|
| začátek sezení | přečíst `STAV.md` a konec deníku | `stav.py` (fronty, rozpracované úkoly, předání, pravidla od uživatele, oprávnění) |
| kdo bádá | hlavní sezení, pomocníci podle potřeby | agent `badatel` jako hlavní vlákno, čtenáři `researcher`/`browser-reader`, ověřovatel `verifier`; hlídač omezuje příkazy |
| výběr práce | Rozpracováno v `STAV.md`, rozhodnutí sezení | fronty, `fronta.py frontier` nebo `dalsi`, priorita a cena úkolu, noční okno |
| zadání pomocníkovi | text v zadání | kontrakt `zadani.py novy` (osoba, role, svazek, rozsah snímků, pole, strop) |
| čtení | hlavní sezení čte snímek, čtení pomocníka ověří samo | čtenář vrací nález `nalez/1`, ověřovatel naslepo `overeni/1`, `vysledek.py porovnej` po polích, většina čtení |
| zápis | ruční úprava `osoby.py`, `zaznamy.json`, přepis, deník (`zapis.py`) | rozhodnutí `rozhodnuti/1` a `zapis_vysledku.py` (všechno, nebo nic), opravy `oprava.py`, commit `commit.py` |
| záporný výsledek | pravidlo v `SKILL.md` (0.10.2: doklad) | navíc vynucený kontraktem (`prohledano[].doklad`) |
| kontrola dat | `kontrola.py` | navíc `audit_dat.py`, `graf.py`, `rodiny.py`, `chronologie.py`, `rejstrik.py` |
| konec sezení | aktualizovat `STAV.md` | `stav.py predani`, commit nástrojem |
| bez člověka | ne | noční a víkendový režim (`reference/nocni_rezim.md`) |

Oddíly `SKILL.md`, které fork přidal: Hledání v datech (rejstřík), Noční a víkendový režim a fronty úkolů, Žádosti archivům;
„Příběh hlavního rodu“ se rozšířil na „příběhy rodů“.

### 2.4 Nástroje originálu, které fork změnil

21 nástrojů originálu je ve forku upravených **[kód]**. Největší:

| Nástroj | Řádků změn | Co fork mění |
|---|---|---|
| `export_web.py` | 1 566 | nové stránky, přístupy, soukromí, účastníci zápisů, RODINA, Co hledáme |
| `kontrola.py` | 362 | kontroly forku (chronologie, účastníci, procesní údaje na webu, žijící) |
| `vyrez.py` | 165 | výřez pro čtení do 2 000 px, díly řádku, začernění rodných čísel v dokumentech |
| `hlidac_site.py` | 119 | úzký hlídač místo plošného zákazu curl, hlídání brány před nasazením |
| `aron_img.py` | 114 | výchozí plné rozlišení (PR #120), sdílená mezipaměť |
| `zapis.py`, `ramecek.py`, `novy_projekt.py`, `overit.py` | 80–100 každý | sloučení zápisů, rámečky pro výřez, aktualizace projektu s bránou a hlídači |

Každá taková změna je při slučování originálu místem možného konfliktu (0.10.2: 5 konfliktů v 8 souborech).

### 2.5 Web

Stránky navíc: Dokumenty, Domy, Jména, místa (`misto/[slug]`), Časová osa, Osobnosti, Poznámky, příběhy rodů (`pribehy/[slug]`),
Statistiky, Strom, vějíř od libovolné osoby (`vejir/[slug]`). Dále přístupy pro větve rodiny (samostatná verze webu pro každý
přístup), vynucené soukromí žijících, barva rodu na celém webu, brána s kontrolou vztahů z obou stran. Web je na metodice bádání
nezávislý: čte jen data (2.2).

### 2.6 Co z rozdílu plyne

- **Vrstvy W, P, K, R (2.7) se dají přenést samostatně**: nástroje a stránky čtou data, bádání neřídí. Jejich jediná vazba na
  metodiku je přes formáty dat (`denik.jsonl`, `ucastnici`, `RODINA`, `verejne_otazky.json`).
- **Vrstva M je provázaná s daty**: fronty, `denik.jsonl`, kontrakty v `pracovni/`, `tvrzeni.jsonl`, `opravy.jsonl`, `rezim.json`.
  Odebrat ji znamená převést nebo archivovat tato data.
- **Konflikty s originálem** vznikají hlavně v `SKILL.md`, šabloně dat a ve 21 upravených nástrojích originálu; ne v nových nástrojích.

### 2.7 Vrstvy podle původu

52 nástrojů navíc a 11 stránek webu navíc rozdělených podle původu:

| Vrstva | Co to je | Příklady | Původ |
|---|---|---|---|
| W – web a data | stránky, přístupy, soukromí, export | stránky Domy, Jména, Osobnosti, Statistiky, Časová osa, Strom, místa, vějíř od osoby, přístupy pro větve rodiny (`pristupy.py`, `pozvanky.py`), vynucené soukromí žijících, poznámky ke stránkám, `kontrola_webu.py` | fork a sloučené PR originálu |
| P – prameny | nástroje k archivům a databázím | `litomerice.py`, `mza.py`, `matricula.py`, `vezni.py`, `arolsen.py`, `obeti.py`, `mauthausen.py`, `brno_encyklopedie.py`, `souhlas.py`, `smoke_test.py` | fork a otevřené PR originálu (#121–#125) |
| K – kontroly dat | kontroly rodiny a chronologie | `graf.py`, `rodiny.py`, `chronologie.py`, `datumy.py`, `audit_dat.py` | PR originálu (#76, #126, #135, #201) a fork |
| R – rejstřík | hledání bez čtení celých souborů | `rejstrik.py` | PR originálu #203, upravený pro fork |
| M – metodika bádání | řízení, kontrakty, fronty, agenti | `fronta.py`, `stav.py`, `kontext.py`, `zadani.py`, `vysledek.py`, `zapis_vysledku.py`, `commit.py`, `oprava.py`, `osoby_upravy.py`, `ucastnici.py`, `svazky.py`, `denik.py` (`denik.jsonl`), `mapa.py`, `podnet.py`, `spotreba.py`, `prohlizec.py`, `pracovni_prehled.py`, `hlidac_zapisu.py`, `brana.py`; 12 agentů, hooky, 32 pravidel, 6 front úkolů, noční režim | fork (fáze A–E, etapy E0–E7) |

Sloučené PR originálu ve forku: #13, 19, 22, 23, 26, 29, 41, 46–49, 55, 56, 59, 62, 66, 73, 76, 77, 87, 89, 92, 94, 107, 120–125, 135,
139, 140, 176, 182, 183, 189, 197, 200, 201, 203. Originál má otevřených asi 40 PR (prameny, web, kontroly, „zápis nálezu jedním
příkazem“ #187, „snímkovač“ #195, Slovakiana #199).

Složitost, na kterou si uživatel stěžuje, je téměř celá ve **vrstvě M**. Vrstvy W, P, K a R jsou samostatné funkce, které bádání
nekomplikují; kdo je nepoužívá, nevidí je.

## 3. Společné jádro obou možností

Dvě změny se vyplatí v obou cestách a nezávisí na tom, kterou se půjde.

### 3.1 Pevná pole podle druhu zápisu

První čtení i kontrolní čtení vyplňují **tatáž malá pole daná druhem zápisu**, ne pole, která si čtenář vymyslí.

| Druh | Pole jádra |
|---|---|
| křest | datum narození, datum křtu, jméno dítěte, otec (jméno, stav, dům, obec), matka (jméno, rodné příjmení, otec matky), kmotři (jména) |
| sňatek | datum, ženich (jméno, věk, stav, dům, obec, rodiče), nevěsta (totéž), svědci (jména) |
| úmrtí | datum úmrtí, datum pohřbu, jméno, stav nebo povolání, dům, obec, věk, příčina (krátké označení) |

**Z přepisu se nic neztrácí.** Úplný přepis a překlad zůstávají v `prepisy.json`, včetně všeho, co se do jádra nevejde (hodina,
okrajové poznámky, delší věty o příčině, kdo pohřbil, opravy písaře). Do jádra jde jen to, co se zapisuje do dat jako fakt, a jen to
se porovnává pole po poli. Pole jádra se **neukládají**: slouží jen jako formulář obou čtení při porovnání; do dat jde
výsledek (fakta a `overeno` u zápisu). Neobvyklý zápis (dvojčata, dodatečná legitimace, přeškrtnutý údaj) čtenář označí `neobvykle: <důvod>`
a jde k člověku. Druh mimo tabulku (pozemková kniha, rodinný doklad) ověřuje člověk.

### 3.2 Sporná místa rozhodne člověk nad výřezem

1. První čtení a **jedno** kontrolní čtení stejných polí jádra. Shoda pole po normalizaci = ověřeno.
2. **Neshoda = spor pro člověka**, ne další čtení. Položka sporu: výřez v plném rozlišení s rámečkem na poli, název pole a obě čtení.
3. Spory se sbírají do dávky (fronta k rozhodnutí, typ `spor čtení`); odpověď „A“, „B“, vlastní čtení, nebo „nečitelné“.
4. Rozhodnutí člověka je čtení originálu: pole je `doc` s údajem, kdo a kdy rozhodl.
5. Badatel spor nerozhoduje a nezadává kvůli němu další čtení; jen připraví položku. Výjimka: špatný výřez – nový výřez.

Odpadne většina 2 ze 3, třetí a další čtení a všechny výjimky ze 17. 11. **[hypotéza]** Sporů zbude jedno až dvě pole na deset
zápisů (v auditu ze 17. 11. byly spory hlavně v rozsahu jména a v pravopisu data; skutečný zbyl jeden, číslo domu). Nezměřeno.

## 4. Možnost A: originál a doplnit

### 4.1 Jak by to vypadalo

Nová větev z `upstream/main` (0.10.2). Bádání podle `SKILL.md` originálu: hlavní sezení samo čte snímky, pomocníci (subagenti) hledají
podle zadání v textu, čtení pomocníka hlavní sezení ověří na snímku, každé hledání do deníku, stav v `STAV.md`. Do toho se doplní:

| Doplnit | Odkud | Proč |
|---|---|---|
| vrstvy W, P, K, R | fork a PR originálu (sloučit stejně jako dnes, PR po PR) | samostatné funkce, bádání nekomplikují |
| pevná pole jádra a spory k člověku (3.1, 3.2) | návrh | jediná přidaná metodika; nahrazuje kontrakty a většinu |
| záporný výsledek s dokladem a rozsahem (K4, R-HELP-006) | originál 0.10.2 to už má v `SKILL.md` | bez nástroje, jen pravidlo |
| zápis výsledku jedním příkazem | PR originálu #187 (místo `zapis_vysledku.py` a rozhodnutí v JSON) | jedno místo zápisu, menší vlastní kód |
| brána a hlídač nasazení | fork (`brana.py`, `kontrola_webu.py`) | ochrana webu, nezávisí na bádání |
| předání do další session (`stav.py predani`) | fork, E7 | jen pokud se ukáže potřeba; originál má `STAV.md` ručně |

Nepřebírá se: fronty úkolů a noční režim, router, rozpočet, agenti `badatel`/`researcher`/`verifier`/`committer`…, kontrakty
`zadani`/`nalez`/`overeni`/`rozhodnuti`, `kontext.py`, hooky orchestrátoru, 32 pravidel (zůstává `SKILL.md` a `reference/`).

### 4.2 Migrace projektu

**[kód]** Data projektu jsou ve formátech forku: deník v `denik.jsonl` (originál `research_log.md`), fronty `ukoly_*.md`,
`ucastnici` u zápisů, `tvrzeni.jsonl`, `opravy.jsonl`, `rezim.json`. Tři cesty:

1. ponechat `denik.py` a `denik.jsonl` jako fork nad originálem (malý rozdíl, jeden nástroj) – doporučeno,
2. převést deník zpět do `research_log.md` (ztráta strukturovaných polí: osoby, snímky, opravy řádků),
3. fronty převést na seznam v `STAV.md` (otevřené úkoly jako odrážky), historii úkolů archivovat.

Web a data osob (`osoby.py`, `zaznamy.json`, `prepisy.json`) jsou společné; `ucastnici` umí export webu forku – přebírá se s vrstvou W.

### 4.3 Pro a proti

| Pro | Proti |
|---|---|
| nejjednodušší bádání: jedno sezení, text místo kontraktů | ztráta strojových záruk K2 (dvojí nezávislé čtení) a K5 (stavy rozpočtu, nedostupnosti) – zůstanou jen jako pravidla v textu |
| novinky originálu se slučují bez konfliktů ve vrstvě M | velká jednorázová práce: vybrat a přenést W, P, K, R; migrace projektu |
| menší kód k údržbě (vrstva M je asi 20 nástrojů a 12 agentů) | noční a víkendový režim bez člověka zmizí; bádání jen interaktivně |
| hlavní sezení vidí snímek samo, spory řeší s uživatelem hned | hlavní sezení čte samo, což je dražší model na čtení (originál to tak dělá) |

## 5. Možnost B: zjednodušit fork

### 5.1 Jak by to vypadalo

Ponechat dnešní základ a odebírat ve vrstvě M:

| Č. | Změna | Co odpadne |
|---|---|---|
| Z1 | pevná pole jádra a spory k člověku (3.1, 3.2) | `jadro`, většina 2 ze 3, `audit.pole`, `--pole`, „kratší čtení“, nespárovaná pole, třetí čtení |
| Z2 | rozhodnutí krátkým příkazem nad nálezem („přijmi čtení c1 jako zápis, osoby 88 a 89, uzavři“); zbytek odvodí nástroj | ručně skládané rozhodnutí v JSON o 79 řádcích |
| Z3 | prořezat podle skutečného použití (deník, `ukoly_historie.jsonl`, `spotreba.py` za poslední týdny): sloučit nebo zrušit nepoužité nástroje, volby a fronty; kandidáti: část ze 6 front, router a rozpočet nočního režimu, překrývající se výpisy | desítky nástrojů a voleb |
| Z4 | definice badatele na jednu obrazovku, podrobnosti jen v `--help` nástrojů | většina z 2 300 slov |

### 5.2 Pro a proti

| Pro | Proti |
|---|---|
| zachová záruky K1–K8 jako kód (zápis jen přes validující nástroje, brána, rozlišené stavy) | i po zjednodušení zůstane vrstva M (kontrakty, fronty, agenti); složitost klesne, nezmizí |
| žádná migrace dat projektu | slučování originálu dál naráží ve vrstvě M (`SKILL.md`, deník, šablona) |
| postupné kroky s měřením po každém | riziko, že se zjednodušení zase obalí výjimkami, pokud se nezmění návrh ověření (Z1 je nutná, ne volitelná) |
| noční režim bez člověka zůstává | kódu k údržbě zůstává hodně |

## 6. Porovnání

| Kritérium | A – originál a doplnit | B – zjednodušit fork |
|---|---|---|
| Složitost bádání | nízká (text, jedno sezení) | střední (méně kroků, kontrakty zůstávají) |
| Záruky K1–K8 | K1, K3, K4, K6–K8 kódem; K2 a K5 jen pravidlem | všechny kódem |
| Cena na případ **[hypotéza]** | nižší řízení, dražší čtení (hlavní model čte) | nižší než dnes po Z1–Z2; změřit `mereni-v1` |
| Slučování originálu | snadné | dál s konflikty ve vrstvě M |
| Jednorázová práce | velká (výběr W/P/K/R, migrace) | menší, po krocích |
| Noční režim bez člověka | ne | ano |
| Riziko | ztráta osvědčených ochran, které vznikly z chyb (stavy rozpočtu, zápis jen nástrojem) | návrat složitosti |

## 7. Doporučení

Rozhoduje, **jestli je potřeba bádání bez člověka** (noční a víkendový režim). Vrstva M vznikla hlavně kvůli němu: kontrakty,
fronty, rozpočet a agenti nahrazují člověka, který by jinak hlídal kvalitu.

- **Bez nočního režimu → A.** Interaktivní bádání s člověkem u ruky nepotřebuje kontrakty; spory a nejistoty řeší uživatel hned
  (3.2). Doplnit pevná pole jádra a deník `denik.jsonl`, zbytek vrstvy M nechat archivovaný ve větvi.
- **S nočním režimem → B**, ale se Z1 jako první a povinnou změnou, a s měřením `mereni-v1` před Z2–Z4.

V obou případech nejdřív **3.1 a 3.2**, protože řeší dnešní problém ověřování a přenesou se do kterékoli cesty.

## 8. Postup a měření

1. Rozhodnutí R9–R13 (níže).
2. 3.1 a 3.2 na větvi ze `main` (B), nebo ze `upstream/main` (A); testy napřed: shoda, neshoda → spor, neobvyklý zápis → člověk, audit.
3. Měření `mereni-v1` na sadě `mereni-v0`: kroky na úkol, tokeny na případ, spory pro člověka, přesnost proti potvrzeným odpovědím.
   Cíl: přesnost aspoň stejná, tokeny a kroky výrazně méně, spory do dvou polí na deset zápisů.
4. A: výběr a přenos W, P, K, R po vrstvách, migrace projektu (4.2). B: Z2, pak Z3 a Z4 podle měření.
5. Dočasná řešení ze 17. 11. (`vysledek.py jadro`, `audit.pole`, započtení ověření rodiče, větev `podnety-17-11b`) po 3.1 a 3.2
   odstranit.

## 9. Rozhodnutí pro uživatele

Rozhodnuto 17. 11. 2026: R9 ano, R10 ano (pokud nebude bobtnat, 11.3), R11 větev ponechat celou nesloučenou, R12 jen s člověkem,
R13 možnost A, R14 podle doporučení (`audit_dat` a `oprava` ano, `podnet` ne, `mapa` podle změřeného použití).

| Č. | Otázka | Doporučení |
|---|---|---|
| R9 | Spory čtení v poli jádra rozhoduje člověk nad výřezem místo dalších slepých čtení? | ano |
| R10 | Pevná pole jádra podle druhu zápisu; zbytek jen v přepisu, strojově neověřený? | ano |
| R11 | Větev `podnety-17-11b`: sloučit jen úpravu hlídače pro sestavení webu a bránu, `jadro` a spol. ponechat ve větvi? | ano |
| R12 | Je potřeba bádání bez člověka (noční a víkendový režim)? | rozhodne mezi A a B (oddíl 7) |
| R13 | A, nebo B? | podle R12: bez nočního režimu A, s ním B |
| R14 | Při A: verdikty V v 10.2 (`audit_dat`, `mapa`, `podnet`, `oprava` s `osoby_upravy`) | `audit_dat` a `oprava` ano, `mapa` a `podnet` ne |

## 10. Plán přechodu na originál (možnost A)

Zadání uživatele: při přechodu na originál zachovat **web**, **přístupy**, **nástroj pro bádání v prohlížeči** (Playwright),
některá **pravidla** (třeba „do zápisu nepatří, že pomocník zapsal“), **anonymitu repozitáře skillu** a případně **měření**.

### 10.1 Co zachovat a na čem to stojí

| Zachovat | Soubory | Závisí na (nutno přenést také) |
|---|---|---|
| Web | `template/web/` forku, `export_web.py` forku, `statistiky.py`, `stavby.py`, `domy_export.py`, `osobnosti.py`, `soubory.py`, `obraz.py` | **[kód]** `export_web.py` importuje `denik`, `otazky`, `ucastnici`, `chronologie`, `pohled`: tedy deník `denik.jsonl` (`denik.py`, `zaznamy_store.py`), veřejné otázky `verejne_otazky.json` (`otazky.py`), účastníky zápisů (`ucastnici.py`), `chronologie.py` s `datumy.py`; `RODINA` v `osoby.py` |
| Kontrola a brána webu | `kontrola_webu.py`, `znackuj_rody.py`, `rody_html.py`, `brana.py`, `hlidac_site.py` forku | `kontrola.py` forku (importuje `chronologie`, `graf`, `pohled`, `ucastnici`, `export_web`) |
| Přístupy | `pohled.py`, `pristupy.py`, `pozvanky.py`, šablony přihlášení a brány (`netlify/`, `cloudflare/`, `nginx`) | export webu (výše) |
| Bádání v prohlížeči | `prohlizec.py` (vlastní Edge přes Playwright, pauzy a stopky brzdy), agent `browser-reader` nebo jen pokyn v `SKILL.md`, `reference/portaly.md` forku | `slusne.py` (ZAKAZ, brzda) z originálu; `svazky.py` (svazek z prohlížeče do katalogu) jen po odpojení od `vysledek.py` |
| Pravidla | kontrola procesních údajů v `kontrola.py` (vzor „pomocník“, „agent“, „ověřeno na snímku“…), totéž v `kontrola_webu.py`; text `reference/zapisy.md` → „Co nepatří do dat ani na web“; doplňky forku v `reference/matriky.md` a `metodika.md` (pasti, ztotožnění, knihy po vsích) | nic; jde o text a regulární výrazy |
| Anonymita repozitáře | `scripts/anonymita.py`, `.githooks/pre-push`, `.anonymita-seznam.priklad`, kontrola v CI | nic |
| Měření | `spotreba.py` (spotřeba sezení podle rolí ze záznamů Claude Code) | nic; role se po přechodu čtou podle typu pomocníka |

**Důsledek:** web nejde přenést bez deníku `denik.jsonl`, veřejných otázek a účastníků zápisů. Ty se stávají součástí „webové“
vrstvy, ne metodiky. `otazky.py` je třeba **odpojit od `fronta.py`** (dnes převádí veřejnou část front příkazem `z-fronty`; po
přechodu se otázky zakládají přímo).

### 10.2 Soupis nástrojů navíc a co s nimi

52 nástrojů, které originál nemá **[kód]**. Verdikt: **Z** zachovat, **ZZ** zachovat jako závislost, **Ú** zachovat po úpravě,
**V** volitelně (rozhodne uživatel), **N** nepřebírat (zůstane v archivní větvi).

| Nástroj | K čemu | Vrstva | Verdikt | Poznámka |
|---|---|---|---|---|
| `pohled.py` | přístupy a pohled od jiné osoby | W | Z | přístupy |
| `pristupy.py` | přehled, kdo co vidí | W | Z | přístupy |
| `pozvanky.py` | osobní odkazy na web | W | Z | přístupy |
| `statistiky.py` | stránka Statistiky | W | Z | |
| `stavby.py` | dějiny staveb, stránka Domy | W | Z | |
| `domy_export.py` | domy předků pro web | W | Z | |
| `osobnosti.py` | stránka Osobnosti | W | Z | |
| `kontrola_webu.py` | kontrola sestaveného webu z obou stran, procesní text | W | Z | pravidlo „pomocník“ na webu |
| `znackuj_rody.py` | jednotná značka rodu | W | Z | |
| `brana.py` | brána před nasazením | W | Z | |
| `hlidac_zapisu.py` | hlídač ručních zápisů do chráněných souborů | W | Z | chrání `denik.jsonl`, `verejne_otazky.json`, generované soubory webu |
| `rody_html.py` | pomůcky pro text stránek | W | ZZ | pro `kontrola_webu`, `znackuj_rody` |
| `soubory.py` | bezpečný zápis souborů | W | ZZ | |
| `obraz.py` | hledání ImageMagicku | W | ZZ | |
| `denik.py` | deník jako `denik.jsonl` | W/M | ZZ | web z něj generuje stránku Deník |
| `zaznamy_store.py` | úložiště JSONL pod zámkem | W/M | ZZ | pro `denik.py`, `otazky.py` |
| `ucastnici.py` | účastníci zápisů (zápis na stránce každého účastníka) | W | ZZ | export i kontrola webu |
| `otazky.py` | veřejné otázky (stránka Co hledáme) | W | Ú | odpojit od `fronta.py` |
| `chronologie.py` | časová návaznost, časová osa | K | ZZ | export i kontrola |
| `datumy.py` | data a roky na jednom místě | K | ZZ | pro `chronologie`, `graf`, `rodiny` |
| `jmena.py` | volné porovnání jmen | K | ZZ | pro `graf`, `rodiny` |
| `graf.py` | kontrola rodiny jako grafu | K | Z | PR originálu #135 |
| `rodiny.py` | rekonstrukce rodiny, kandidáti | K | Z | PR originálu #126 |
| `audit_dat.py` | rozpory v datech bez čtení snímků | K | V | čte jen data; užitečné po migraci |
| `rejstrik.py` | rejstřík dat v SQLite | R | Z | PR originálu #203, verze forku čte `denik.jsonl` |
| `prohlizec.py` | vlastní prohlížeč pro portály bez skriptů | P | Z | bádání v prohlížeči |
| `svazky.py` | svazek z prohlížeče do katalogu | P | Ú | odpojit od `vysledek.py` |
| `litomerice.py` | matriky SOA Litoměřice | P | Z | |
| `mza.py` | hledání matrik MZA | P | Z | |
| `matricula.py` | Matricula Online | P | Z | |
| `vademecum.py` | VadeMeCum, židovské matriky | P | Z | |
| `vezni.py` | databáze Památníku Terezín | P | Z | |
| `arolsen.py` | Arolsen Archives | P | Z | PR originálu #124 |
| `obeti.py` | oběti holocaust.cz | P | Z | PR originálu #123 |
| `mauthausen.py` | zemřelí v Mauthausenu | P | Z | PR originálu #122 |
| `brno_encyklopedie.py` | Encyklopedie dějin Brna | P | Z | PR originálu #121 |
| `souhlas.py` | souhlas s podmínkami portálu | P | ZZ | pro `arolsen`, `obeti` |
| `smoke_test.py` | kontrola síťových nástrojů | P | Z | PR originálu #125 |
| `mailto.py` | žádosti archivům jako odkaz do e-mailu | P | Z | PR originálu #87 |
| `pracovni_prehled.py` | co už je stažené v `pracovni/` | P | Z | šetří archivy |
| `mapa.py` | mapa knihy (co který snímek pokrývá) | P | V | dnes ho plní `zapis_vysledku.py`; ručně jde `mapa.py zapis` |
| `spotreba.py` | měření spotřeby sezení | – | Z | měření |
| `podnet.py` | podnět pro správce skillu s kontrolou anonymity | M | V | malý; originál má `poznamky_pro_skill.md` ručně |
| `oprava.py` | změna dat jedním voláním s důvodem a historií | M | V | pohodlné u rodinných dokumentů; originál edituje data přímo |
| `osoby_upravy.py` | úprava jedné položky `osoby.py` | M | V | jen s `oprava.py` |
| `fronta.py` | fronty úkolů, noční režim | M | N | |
| `stav.py` | stav a předání ze souborů | M | N | originál: `STAV.md` ručně |
| `kontext.py` | kontextový balíček pro agenta | M | N | |
| `zadani.py` | kontrakt zadání | M | N | |
| `vysledek.py` | kontrakt nálezu, ověření, porovnání | M | N | z něj jen tabulka jádra a porovnání pro 3.1 a 3.2 (malý modul) |
| `zapis_vysledku.py` | zápis výsledku jedním voláním | M | N | nahradit PR originálu #187, nebo `zapis.py` |
| `commit.py` | commit dokončené práce nástrojem | M | N | |

Souhrn: **Z 28, ZZ 10, Ú 2, V 5, N 7** (52). Z vrstvy M se nepřebírá 7 nástrojů, ale také 12 agentů, hooky orchestrátoru,
32 pravidel a `reference/nocni_rezim.md`. Upravené nástroje originálu (2.4) se přenesou ve verzi forku tam, kde je potřebuje web
(`export_web.py`, `kontrola.py`, `hlidac_site.py`, `novy_projekt.py`); jinak se vezme verze originálu.

### 10.3 Co se z dat projektu ponechá a co archivuje

| Data | Po přechodu |
|---|---|
| `denik.jsonl`, `verejne_otazky.json`, `ucastnici` u zápisů, `RODINA`, `stavby.py`, `pribehy/`, `zadosti.md` | ponechat (web) |
| `osoby.py`, `zaznamy.json`, `prepisy.json`, `svazky.json`, `mista.json`, `dokumenty.json`, `zvyrazneni.json` | beze změny |
| `ukoly_*.md`, `ukoly_historie.jsonl` | otevřené úkoly převést do `STAV.md` (Rozpracováno, odrážky), soubory archivovat ve větvi projektu |
| `tvrzeni.jsonl`, `opravy.jsonl`, `rezim.json` | archivovat (web je nepotřebuje) |
| `pracovni/zadani/`, `pracovni/vysledky/` | `pracovni/` git neukládá; nic nepřevádět |

### 10.4 Kroky

| Krok | Co | Hotovo, když |
|---|---|---|
| 0 | rozhodnutí: verdikty V v 10.2 a R9–R14; zálohová značka dnešního forku (`fork-metodika-2026-11`) | uživatel potvrdil seznam |
| 1 | větev ze `upstream/main` 0.10.2 | větev existuje, testy originálu procházejí |
| 2 | infrastruktura repozitáře: `scripts/anonymita.py` a pre-push, CI (`testy.yml`), markdownlint, `scripts/pokryti.py`, `scripts/sync_report.py`, `CLAUDE.md`, číslování verzí | anonymita a CI zelené na prázdné změně |
| 3 | vrstva K a R: `datumy`, `chronologie`, `jmena`, `graf`, `rodiny`, `rejstrik` s testy | testy zelené |
| 4 | deník `denik.jsonl` (`denik.py`, `zaznamy_store.py`, `hlidac_zapisu.py`), šablona `data/` bez front | `novy_projekt.py` založí projekt s deníkem; testy |
| 5 | vrstva W: export a stránky, `ucastnici`, `otazky` (odpojené od front), `pohled`, `pristupy`, `pozvanky`, kontrola webu, brána | ukázkový web se sestaví, kontrola webu a brána zelené, test přístupů |
| 6 | vrstva P: portálové nástroje, `prohlizec.py`, `svazky.py` (odpojený), `souhlas`, `smoke_test`, `mailto`, `pracovni_prehled` | testy zelené; smoke test z domácí sítě |
| 7 | pravidla: kontrola procesních údajů v `kontrola.py`, texty `reference/zapisy.md`, `matriky.md`, `metodika.md` forku do `reference/`; `SKILL.md` originálu doplnit jen o odkazy (deník přes `denik.py`, prohlížeč, rejstřík, pevná pole a spory k člověku) | `SKILL.md` delší nejvýš o desetinu proti originálu |
| 8 | pevná pole jádra a spory k člověku (3.1, 3.2) jako malý modul | testy: shoda, neshoda → spor, neobvyklý zápis |
| 9 | měření: `spotreba.py`, měření `mereni-v1` na sadě `mereni-v0` (bez agentů M, jedno sezení) | čísla vedle `mereni-v0` |
| 10 | migrace projektu (10.3) na jeho vlastní větvi, `novy_projekt.py`, `npm run data`, `npm run build`, brána | web projektu se sestaví se stejným obsahem, brána zelená |
| 11 | vydání (CHANGELOG, verze); stará metodika zůstává ve větvi a značce | vydáno |

Odhad práce **[hypotéza]**: kroky 1–7 jsou hlavně přenos hotového kódu s testy (několik sezení metodika), krok 10 jedno sezení
s kontrolou webu. Nejvíc práce je v kroku 5: `export_web.py` forku se od originálu liší o 1 566 řádků a je třeba ho postavit na
originál, ne zkopírovat.

### 10.5 Rizika

- **Ztráta strojových záruk vrstvy M** (zápis jen přes validující nástroje, rozlišené stavy rozpočtu a nedostupnosti, dvojí čtení
  vynucené kódem). Zmírnění: pevná pole se spory k člověku (3.2), kontrola dat, brána.
- **Noční a víkendový režim skončí**; bádání jen interaktivně.
- **Rozjetá data projektu**: fronty a předání je třeba převést dřív, než se stará metodika odstraní (10.3).
- **Export webu**: největší kus a největší riziko regresí; před migrací porovnat sestavený web projektu starou a novou verzí
  (počet stránek, vztahy z obou stran, přístupy).

## 11. Data projektu před a po přechodu (možnost A)

Rozhodnutí uživatele 17. 11. 2026 (oddíl 9): R12 jen s člověkem (bez nočního režimu), R13 možnost A, R9 ano, R10 ano s podmínkou,
že pevná pole nebudou bobtnat, R14 podle doporučení, větev `podnety-17-11b` ponechat (nesloučit), audit z projektu dokončit až po
přechodu.

**[kód]** Soupis složky `data/` projektu 17. 11. 2026 (jen názvy, velikosti a počty položek; obsah se nečetl).

### 11.1 Fronty úkolů: co s nimi

Dnes 6 front, 187 otevřených úkolů a historie 122 událostí:

| Fronta | Úkolů | Druhy | Po přechodu |
|---|---|---|---|
| `ukoly_na_noc.md` | 133 | křty 56, sňatky 33, úmrtí 18, bádání 23, jiné 3 | `ukoly.md` (plán bádání) |
| `ukoly_k_badani.md` | 46 (3 čekají) | křty 23, sňatky 17, bádání 6 | `ukoly.md` |
| `ukoly_vstup.md` | 1 | jiné | `ukoly.md` |
| `ukoly_dotazy_na_archivy.md` | 5 | různé | `archivni_dotazy.md` (soubor originálu) |
| `ukoly_na_rodinu.md` | 2 | dotaz, bádání | otázka pro rodinu → `verejne_otazky.json` (stránka Co hledáme), bádání → `ukoly.md` |
| `ukoly_k_rozhodnuti.md` | 0 | – | `STAV.md` → „Čeká na rozhodnutí“ (sem i spory čtení, R9) |
| `ukoly_historie.jsonl` | 122 událostí | – | archiv (zůstává v historii gitu projektu), z `data/` pryč |

Rozdělení na noční a denní frontu bez nočního režimu ztrácí smysl. Ceny S–XL, priority, okna, `pokusu`, `kdy` a stav `čeká` s datem
patřily rozvrhu bez člověka; v novém plánu zůstává jen to, co potřebuje člověk s badatelem u jednoho stolu.

**Nový `data/ukoly.md`** – jeden prostý seznam, žádný nástroj ho nečte ani nehlídá:

```markdown
# Plán bádání

Co hledat dál. Hotové se maže (výsledek je v deníku). Rozpracované a předání jsou v STAV.md.

## Křty
- 88 – křest, Lhota 1810–1814 (svazek 0a1b2c3d); vodítko: otec chalupník čp. 5
## Sňatky
- 44 × 45 – sňatek asi 1835, farnost nevěsty
## Úmrtí
## Jiné
```

Řádek = osoba (číslo z P nebo zkratka z RODINA), co hledat, kde, případně vodítko. Převod je jednorázový skript: z každého úkolu
vezme osoby, druh a první řádek textu a definici hotového zahodí. **[hypotéza]** Část úkolů jsou duplicity otevřených otázek
v `ISSUES` a jiné jsou už vyřešené; převod je vypíše k ručnímu projití s uživatelem, nemaže je sám.

### 11.2 Mapování souborů

Značky: **=** beze změny, **~** zůstává se změnou, **+** nový soubor, **→** převod do jiného souboru, **A** archiv (z `data/`
pryč, zůstává v historii gitu projektu), **×** smazat (generovaný nebo dočasný).

| Soubor dnes | Velikost | Po přechodu | Formát po přechodu | Proč |
|---|---|---|---|---|
| `osoby.py` | 200 kB | = | P, LINES, SIDE, ISSUES, HYPOTEZY, SAME, RODINA | RODINA potřebuje web |
| `zaznamy.json` | 160 kB | ~ | jako dnes; `ucastnici` a `overeno` zůstávají, `overeno` může mít hodnotu `"uzivatel"` (spor rozhodl člověk) | účastníci jsou pro web; R9 |
| `prepisy.json` | 156 kB | = | `orig` a `cs` beze změny | pevná pole se neukládají (11.3) |
| `denik.jsonl` | 620 kB | = | záznam na řádek přes `denik.py` | web generuje stránku Deník |
| `research_log.md` | 240 kB | A | – | starý deník před převodem do `denik.jsonl`; před archivací **ověřit**, že se převedl celý |
| `STAV.md` | 24 kB | ~ | šablona originálu: Pro koho, Kde co je, Pravidla (s pododdílem Pravidla od uživatele), Rozpracováno, Čeká na rozhodnutí; vede se ručně | originál; bez front a kopií plánů |
| `ukoly_na_noc.md`, `ukoly_k_badani.md`, `ukoly_vstup.md` | 72 + 24 + 4 kB | → `ukoly.md` | prostý seznam (11.1) | bez nočního režimu |
| `ukoly_dotazy_na_archivy.md` | 8 kB | → `archivni_dotazy.md` | soubor originálu (nadpis a odrážky) | originál |
| `ukoly_na_rodinu.md` | 8 kB | → `verejne_otazky.json`, `ukoly.md` | – | Co hledáme na webu |
| `ukoly_k_rozhodnuti.md` | 4 kB | → `STAV.md` | oddíl Čeká na rozhodnutí | |
| `ukoly_historie.jsonl` | 36 kB | A | – | rozvrh a ceny úkolů |
| `opravy.jsonl` | 108 kB | = | historie změn přes `oprava.py` | R14: `oprava.py` zůstává |
| `rezim.json` | 4 kB | × | – | noční režim, rozpočet, podpis commitu |
| `.rozpocet.json` | 1 kB | × | – | rozpočet nočního režimu |
| `verejne_otazky.json` | 1 kB | = | přes `otazky.py` (odpojený od front) | stránka Co hledáme |
| `web.json` | 12 kB | = | nastavení webu a přístupy | |
| `pozvanky.json` | 1 kB | = | osobní odkazy | přístupy |
| `dokumenty.json` | 20 kB | = | rodinné dokumenty | |
| `mista.json` | 12 kB | = | místa na mapě | |
| `svazky.json` | 52 kB | = | katalog svazků; struktura knihy jako poznámka v `popis` (náhrada mapy knihy) | |
| `zvyrazneni.json` | 36 kB | = | rámečky ve výřezech | |
| `stavby.py` | 12 kB | = | dějiny staveb | stránka Domy |
| `domy/` (`adresy.json`, `domy.geojson`, `chybi.txt`) | 24 kB | = | výstup skillu stare-adresy; `chybi.txt` generuje export | stránka Domy |
| `udaje_od_rodiny.md`, `zajimavosti.md`, `pribeh.md`, `pribehy/` | 48 kB | = | texty | |
| `zadosti.md` | 4 kB | = | žádosti archivům a úřadům | `mailto.py` |
| `poznamky_pro_skill.md` | 4 kB | = | zapisuje se ručně (bez `podnet.py`) | R14 |
| – | – | + `ukoly.md` | prostý seznam (11.1) | náhrada front |
| – | – | + `archivni_dotazy.md` | soubor originálu | náhrada fronty dotazů |
| `__pycache__/` | – | × | – | generované Pythonem (patří do `.gitignore`) |

Mimo `data/`: `pracovni/zadani/`, `pracovni/vysledky/` (kontrakty) a `pracovni/brana.json` git neukládá; zadání a nálezy po
přechodu nevznikají, `brana.json` zůstává (brána). `mereni/` projektu zůstává kvůli měření `mereni-v1`.

### 11.3 Kontrola bobtnání (podmínka k R10)

- Pevná pole jsou **formulář pro čtení, ne data**: obě čtení (první a kontrolní) je vyplní v `pracovni/`, porovnají se a spor jde
  k člověku; uloží se jen výsledek – fakta jako dosud a `overeno` u zápisu. Uložené jádro by nikdo nečetl (web, kontroly i rejstřík
  berou fakta z `osoby.py`, `zaznamy.json` a přepisu), byla by to jen duplicita.
- Tabulka polí (3.1) je pokyn v `reference/` pro tři druhy (křest, sňatek, úmrtí); nový druh nebo pole jen rozhodnutím uživatele.
- Žádné další soubory v `data/` kvůli ověřování: spory jsou v `STAV.md`, rozhodnutí v `zaznamy.json` (`overeno`).
- Měřítko: `SKILL.md` po přechodu nejvýš o desetinu delší než originál (krok 7 v 10.4); kontrola v `scripts/pokryti.py`.

### 11.4 Převod (krok 10 plánu)

1. Na větvi projektu: jednorázový skript skillu (`scripts/migrace_a.py`, po migraci se z repozitáře odstraní) převede fronty podle
   11.1 a vypíše úkoly k ručnímu projití (duplicity s `ISSUES`, zjevně hotové).
2. Ruční projití s uživatelem: smazat hotové a duplicitní, zkrátit řádky.
3. `STAV.md` přepsat do šablony originálu (Rozpracováno, Čeká na rozhodnutí, Pravidla od uživatele).
4. Archivovat `research_log.md` (po kontrole úplnosti převodu), `ukoly_historie.jsonl`; smazat `rezim.json`, `.rozpocet.json`.
5. `novy_projekt.py` nové verze, `npm run data`, `npm run build`, brána; porovnat web se starou verzí (počet stránek, vztahy, přístupy).
