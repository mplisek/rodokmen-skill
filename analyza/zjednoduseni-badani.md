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

## 2. Co fork přidává nad originál

**[kód]** 302 commitů nad `upstream/main`, 52 nástrojů navíc, 11 stránek webu navíc. Rozděleno podle původu:

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
se porovnává pole po poli. Neobvyklý zápis (dvojčata, dodatečná legitimace, přeškrtnutý údaj) čtenář označí `neobvykle: <důvod>`
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

| Č. | Otázka | Doporučení |
|---|---|---|
| R9 | Spory čtení v poli jádra rozhoduje člověk nad výřezem místo dalších slepých čtení? | ano |
| R10 | Pevná pole jádra podle druhu zápisu; zbytek jen v přepisu, strojově neověřený? | ano |
| R11 | Větev `podnety-17-11b`: sloučit jen úpravu hlídače pro sestavení webu a bránu, `jadro` a spol. ponechat ve větvi? | ano |
| R12 | Je potřeba bádání bez člověka (noční a víkendový režim)? | rozhodne mezi A a B (oddíl 7) |
| R13 | A, nebo B? | podle R12: bez nočního režimu A, s ním B |
