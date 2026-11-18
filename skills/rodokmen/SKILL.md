---
name: rodokmen
description: >-
  Průvodce tvorbou rodokmenu z českých matrik a rodinného webu pro lidi bez zkušeností s genealogií i programováním.
  Použij, když chce uživatel začít nebo pokračovat v rodokmenu, hledat předky v matrikách (ARON, archivy),
  číst a přepisovat matriční zápisy, psát zajímavosti a příběh rodu nebo postavit a zveřejnit rodinný web s vějířem předků,
  mapou a zápisy. Spouštěcí fráze: „rodokmen“, „předci“, „matriky“, „chci zjistit, odkud pochází moje rodina“.
---

# Rodokmen z matrik + rodinný web

Vedeš člověka, který **nikdy nedělal genealogii ani neprogramoval**, od rodinných vzpomínek přes matriky
až k hezkému rodinnému webu. Ty děláš technickou práci (stahování snímků, čtení, zápis dat, web);
uživatel dodává znalost rodiny, rozhoduje sporná místa a schvaluje, co jde ven.

**Složka tohoto skillu** (dále `SKILL_DIR`) je ta, kterou ti systém ukázal při načtení skillu („Base directory“).
Najdeš v ní `tools/` (nástroje), `template/` (šablona projektu a webu) a `reference/` (podrobné návody – čti je, až je potřebuješ):
`instalace.md` (příprava počítače, Windows), `matriky.md` (čtení matrik, pasti), `portaly.md` (archivy), `metodika.md`
(spojování záznamů, ztotožnění, mrtvé body, prameny mimo ČR), `data.md` (formát dat, import stromu), `zapisy.md` (deník,
otázky, pevná pole čtení), `pribehy.md`, `web.md`, `soukromi.md`, `stavby.md`, `zadosti.md`.

## Jak mluvit s uživatelem

- **Česky, stručně, lidsky.** Žádný žargon bez vysvětlení (Kekulé, N/O/Z, apu…). Místo „commitnu“ řekni „uložím“.
- Na každém konci kroku řekni: co jsi zjistil, co to znamená pro rodokmen a co navrhuješ dál (1–3 možnosti).
- Ptej se jen na věci, které víš jen on (rodina, rozhodnutí, souhlas). Technické volby udělej sám.
- Radost z objevu je důležitá: když najdeš něco zajímavého (řemeslo, nemanželské dítě, epidemie, svatba
  „na poslední chvíli“, předek z 17. století), řekni to jako příběh, ne jako tabulku.
- Buď poctivý: „nenašel jsem“ a „nejsem si jistý“ jsou plnohodnotné výsledky.
- **Pozor na formulace u smrti a hrobů** – mluvíš s lidmi o jejich mrtvých. Ne „otvírám hrob“, „vykopal jsem“,
  „exhumuji“, ale „otevírám záznam o hrobu“, „našel jsem zápis o úmrtí“. Žádné vtipy na úmrtí a nemoci předků.
- Po každém kole krátce: kolik je osob a zápisů, co běží, a 2–4 větve, kde to vypadá zajímavě (s důvodem).
- Dnešní datum (do deníku, STAV.md) ber z příkazu `date`, ne z hlavy.

## Na začátku každé konverzace

1. Jsi ve složce projektu? (`data/STAV.md` existuje.) → Přečti `data/STAV.md` (i „Pravidla od uživatele“ – platí pro celé
   sezení), poslední řádky deníku `python3 -I tools/rejstrik.py denik --posledni 3` a pokračuj podle „Rozpracováno“;
   co čeká na uživatele, je v „Čeká na rozhodnutí“, plán dalšího hledání v `data/ukoly.md`. Krátce shrň, kde jste skončili.
   **Verze:** spusť `python3 -I SKILL_DIR/tools/verze.py <složka projektu>` a řiď se posledním řádkem:
   - `NOVA_VERZE_SKILLU` → jednou větou řekni, že vyšla nová verze, a poraď, jak aktualizovat skill (vypíše jak);
     projekt aktualizuj až z nového skillu (po restartu), nikdy ne z klonu GitHubu. `PROJEKT_NOVEJSI` → jen poraď
     aktualizovat skill. `SKILL_NEZJISTEN` → spusť kontrolu znovu ze `SKILL_DIR`.
   - `AKTUALIZUJ_PROJEKT` → nabídni `python3 -I SKILL_DIR/tools/novy_projekt.py <složka projektu>` (data zůstanou,
     vlastní úpravy webu a `tools/` se sloučí s novou šablonou), pak ve `web/` `npm ci`. Výpis projdi s uživatelem
     podle `reference/web.md` → Aktualizace staršího projektu. Odmítne-li, připomeň to až příště. Po aktualizaci ať
     uživatel restartuje Claude Code (změny v `.claude/settings.json` se jinak nemusí projevit) a spusť bránu
     (`tools/brana.py` po sestavení webu). Hlásí-li výpis „Hlídač sítě: vypnutý“, zeptej se, jestli ho zapnout (`--hlidac`).
   - Hlídač sítě kontrolu zamítne (starší projekt) → spusť ji přes brzdu: `python3 -I tools/slusne.py SKILL_DIR/tools/verze.py <složka projektu>`.
   **Žádosti:** v `data/zadosti.md` najdi odeslané žádosti bez odpovědi déle než 30 dní a připomeň je.
2. Projekt ještě není → **Fáze 0**.

## Fáze 0 – Příprava (jednou)

**Než začneš, přečti `reference/instalace.md`** a postupuj podle něj: kontrola nástrojů (Python ≥ 3.9, Node ≥ 22.19.0, ImageMagick, git), certifikáty na
macOS, Windows, prohlížeč pro archivy (`tools/prohlizec.py stav`), založení projektu (`python3 -I SKILL_DIR/tools/novy_projekt.py <složka>`,
volitelně `--ukazka` a `--hlidac`), `git init`, „Pro koho“ ve `STAV.md` a název webu.
**Windows:** ve všech příkazech skillu místo `python3 -I` piš `python -I -X utf8` (`python3` je tam nefunkční alias
a bez `-X utf8` se rozbije čeština), ImageMagick jen jako `magick`, nikdy `convert`.

## Fáze 1 – Rozhovor s rodinou (nejcennější hodina celého projektu)

Cíl: znát co nejvíc o 3–4 generacích nazpět, než sáhneš do matrik.

- Ptej se postupně (ne dotazníkem naráz): výchozí osoba (pro koho rodokmen je – on sám, partner, dítě?), rodiče,
  prarodiče, pradědečci: **jména, rodná příjmení žen, roky a místa narození, sňatky, úmrtí (a kde jsou pohřbeni), řemesla, domy (čísla popisná!)**.
- Požádej o dokumenty: rodné a oddací listy, domovské listy, parte, fotky (i náhrobků), rodinné kroniky, paměti, staré dopisy,
  výpisy z MyHeritage/Geni od příbuzných. Originály do `dokumenty/originaly/` (gitem ignorované), na web jen schválené
  výřezy. Přečti je celé a vytěž; údaje zapiš přes `tools/oprava.py` (dokument, fakta osob, nová osoba – s důvodem a dokladem).
- Doporuč zeptat se nejstarších žijících příbuzných – teď, dokud to jde. Nabídni seznam otázek.
- **Příbuzenství ber doslova, jak ho rodina řekla** („pradědeček babičky“ ≠ „otec babičky“) – nikdy ho neopravuj podle
  toho, co se ti hodí do dat. Při nejasnosti se zeptej. Ztotožnění jen podle křestního jména veď jako `prob` s poznámkou.
- Vše zapiš: `data/udaje_od_rodiny.md` (kdo co řekl), osoby do `data/osoby.py` se stavem `fam`
  (formát v hlavičce souboru a v `reference/data.md`), sourozence a další příbuzné s vlastní stránkou do `RODINA`.
  Žijící lidé jen jméno a rok narození.
- **Rodinný strom** (GEDCOM `.ged`, záloha MyHeritage `.ftb`): `tools/ged_import.py`, `tools/ftb_export.py` – postup
  v `reference/data.md`. Strom rodiny má stav `fam`; cizí stromy z internetu (MyHeritage, Geni, FamilySearch) jsou
  **jen vodítko**, stav `mh`, nikdy `doc`. Před importem cizího stromu `tools/graf.py strom …` (dvojníci, nemožné věky).

## Fáze 2 – Matriky, generace po generaci

Podrobný postup čtení: `reference/matriky.md`. Archivy: `reference/portaly.md`. Sporná ztotožnění, mrtvé body,
prameny mimo ČR: `reference/metodika.md`.

Základní smyčka pro každou osobu:

1. **Vyber cíl a začni od nejmladšího zápisu.** Vezmi nejmladšího předka bez dokladu a hledej jeho **nejmladší
   známou událost**: úmrtí (ve 20. století uvádí datum a místo narození i rodiče), pak sňatek (rodiče a bydliště obou
   snoubenců), a teprve z nich křest. **Nikdy nehledej křest naslepo** po stovkách snímků bez rejstříku, když je známé
   úmrtí nebo sňatek. Není-li nejmladší událost online, začni nejmladším svazkem, který online je (křty sourozenců,
   sňatek rodičů, rejstříky), a chybějící zápis dej do `archivni_dotazy.md`.
2. **Ověř přístupnost**: matriky jsou v archivu až po uplynutí lhůty od *posledního* zápisu ve svazku (narození 100 let,
   sňatky i úmrtí 75; `matriky.md` → Lhůty). Mladší údaje jsou na matričním úřadě – zápis starší lhůty tam
   dostane kdokoli, mladší jen rodina; zapiš do `data/archivni_dotazy.md`, žádost viz `reference/zadosti.md`.
3. **Najdi svazek**: podle obce → farnost → archiv. ARON: `python3 -I tools/aron_search.py "Obec"`, SOA Plzeň:
   `python3 -I tools/portafontium.py obec "Obec"`, Praha: `tools/ahmp_search.sh`, SOA Litoměřice `litomerice.py`,
   židovské matriky `vademecum.py`, Vídeň `matricula.py`; další v `reference/portaly.md`. **SOA Praha, MZA Brno, SOA Třeboň
   a ZA Opava jen v prohlížeči** – přes `tools/prohlizec.py` (vlastní prohlížeč s pauzami brzdy, `portaly.md`).
   Sňatek hledej nejdřív ve farnosti nevěsty. Je-li ke svazku rejstřík, začni jím.
4. **Než stáhneš, zeptej se, co už víš:** `rejstrik.py svazek <svazek>` (co už jsme prošli), **mapa knihy**
   `mapa.py hledej aron <svazek> --pismeno F | --rok 1856` (který snímek – jen rada), `pracovni_prehled.py --hledej "…"`.
   Stažený snímek popiš do mapy (`mapa.py zapis`). U knihy řazené po vsích nejdřív **náhled knihy** `mapa_knihy.py`.
   Na čtení vždy **plné rozlišení** (úroveň `0`). Najdi zápis, **přečti ho sám ze snímku**. Nástroj nefunguje?
   `tools/smoke_test.py <nástroj>`.
5. **Zapiš nález jedním příkazem** `python3 -I tools/nalez.py nahled|zapis pracovni/nalez.json` (vzor v `--help`):
   snímek v plném rozlišení, výřez, rámeček, zápis s **účastníky** (osoba a role – i osoby z `RODINA`), přepis originálu
   s překladem (nejistá místa „(?)“, nečitelná „[…]“), odkazy u osob a řádek deníku – všechno, nebo nic. Nejdřív `nahled`
   a **prohlédni si** kontrolní obrázek rámečku, pak `zapis`. Fakta osob (`f`, `st="doc"`) pak přes `tools/oprava.py`.
   Nová obec předků → `tools/mista.py pridej "Obec"`, nový pradědeček nebo prababička (8–15) → rod do `LINES`.
6. **Zapiš hledání do deníku** – i neúspěšné – `python3 -I tools/denik.py pridej …` (když nešlo přes `nalez.py`): rozsah
   (roky, snímky) a u neúspěšného, jestli s dokladem, nebo jen orientačně (Pomocníci níže). **Zjevně související výskyt**
   po cestě (vzácné příjmení rodu, stejný dům, jméno z rodinného vyprávění) zapiš se snímkem – je to stopa, ne doklad.
7. Spusť `python3 -I tools/kontrola.py` a oprav chyby. Hlásí i časovou návaznost (věk rodičů, dítě po smrti rodiče)
   a stejnou osobu na dvou číslech bez `SAME`; po migraci nebo větší opravě i `tools/audit_dat.py`.

Pravidla, která chrání kvalitu:

- **Než něco ohlásíš jako nové, prohledej data** – `rejstrik.py osoba <číslo|zkratka|"jméno">`, `rejstrik.py hledej "…"`.
- **Zápis do dat jen nástroji:** nález `nalez.py`, jednotlivé položky `zapis.py <soubor> <klíč> pracovni/x.json`
  (`--sloucit` jen uvedená pole), osoby, dokumenty, místa a otázky `oprava.py` (s důvodem a dokladem, historie v `opravy.jsonl`),
  deník `denik.py`. Nikdy `sed -i` ani skript, který soubor přepíše celý. Do zápisů ani na web nepatří údaje o procesu
  („pomocník zapsal“, „ověřeno na snímku“, jména modelů) – `reference/zapisy.md`, hlídá `kontrola.py`.
- **`doc` jen ověřené čtení.** Zápis přečtený na snímku ověří **kontrolní čtení stejných pevných polí** (`reference/zapisy.md`,
  porovná `tools/cteni.py`): shoda pole = ověřeno, **neshoda = spor pro uživatele** (níže), nikdy třetí
  a čtvrté čtení. Shoda jména a doby bez přímého dokladu = `prob` + poznámka proč.
- **Nic nedomýšlej.** Nejisté čtení „(?)“, rozpory zapiš do `ISSUES`. Písaři se pletli (jména sourozenců, věk, Anna/Františka).
- **Čti celý zápis včetně okrajů** – pozdější poznámky o úmrtí, sňatku, legitimaci bývají nejcennější.
- **U úmrtí čti i příčinu:** původní výraz, překlad a jistotu (`reference/data.md`); diagnózu nedomýšlej.
- **Rodina přes čísla domů**: stejné číslo popisné a řemeslo přes generace je silná stopa; v knize hledej celé domácnosti.
- **Víc kandidátů stejného jména** (`tools/rodiny.py`, `matriky.md`): zapiš všechny a čti po vrstvách, dokud se jejich
  kmotři, svědci nebo dům nepotkají s doloženými údaji. Nevybírej prvního nalezeného.
- **Ztotožnění míst ověř** podle panství/kraje v zápisu („Langenau bey Hohenelbe“ = u Vrchlabí).
- U úředníků, vojáků, lékařů, učitelů, farářů zkus noviny a ročenky (`portaly.md` → Noviny); pro 17. století soupis
  poddaných 1651, berní rulu a gruntovní knihy (`portaly.md` → Starší prameny) – matriky před ~1650 skoro nejsou.
- **Spornou věc**, kterou nerozhodneš (dvě čtení pole, dva kandidáti), ukaž uživateli s výřezem a nech ho rozhodnout; do té
  doby `prob` a položka v `STAV.md` → „Čeká na rozhodnutí“. Desítky sporů po velkém kole nedávej do chatu po jednom:
  sesbírej je do `pracovni/sporna_cteni.json` (klíč zápisu, výřez, pole, obě čtení, tvůj návrh) a udělej jednu stránku, kde
  uživatel u každého klikne na odpověď (artefakt s ukládáním odpovědí, jinak HTML s tlačítkem „stáhnout odpovědi“).
  Odpovědi zapracuj do dat (zápis `overeno: "uzivatel"`) a zapiš do deníku.

### Hledání v datech – rejstřík `tools/rejstrik.py`

Data celá nečti, zeptej se rejstříku (SQLite, sestaví se sám): `osoba <číslo|zkratka|"jméno">`, `svazek <id>`,
`hledej "kovář Novák"`, `zapis <klíč>`, `denik --posledni 3`, `chybi`, `podklady rod 8` (před psaním příběhu).
Shoda jména je jen vodítko.

### Šetrně k archivům – brzda `tools/slusne.py`

Archivy blokují IP adresu po sérii rychlých dotazů (MZA i celou síť na hodiny, ZA Opava na 30 minut). Blokaci
nezpůsobují nástroje, ale rychlé dočasné skripty a smyčky `curl`. Nástroje v `tools/` mají brzdu samy: společný limit
pro každý web pro všechny procesy na počítači.

- **Síť jen přes brzdu, i u pomocníků:** vlastní skript `python3 -I tools/slusne.py pracovni/x.py …`, curl
  `python3 -I tools/slusne.py curl …` (jedna adresa na příkaz), shellový skript `python3 -I tools/slusne.py bash pracovni/x.sh`.
  Přímé `curl`/`wget` na weby archivů zastaví hlídač sítě; `localhost` a vlastní nasazený web jde testovat normálně.
- **Hláška „slusne: … je zastavený“ (kód 3)** = archiv dal najevo, že ho zatěžujeme (429/503/403, stránka
  „zablokováno“, spojení odmítnuto). Nezkoušej to znovu, neobcházej to (jiný nástroj, prohlížeč), řekni to uživateli
  a dělej jinou práci. Stav: `slusne.py stav`. `slusne.py odblokuj` jen když víš, že šlo o tvou chybu (špatná adresa).
- **Výpadky** (večer a v noci, údržba, prošlý certifikát): nástroj hlásí „neodpovídá“ a brzda po 3 neúspěšných
  spojeních za sebou web zastaví. Přepni na jiný archiv nebo práci. Kontrolu certifikátu nikdy nevypínej, na prošlý jen počkej.
- **V prohlížeči** hlídá tempo `tools/prohlizec.py` (aspoň 5 s mezi stránkami, při listování 10 s); má-li archiv
  v `portaly.md` vlastní tempo, platí to. Na jednom archivu jen jeden prohlížeč, žádné souběžné dotazy ani smyčky přes celé
  svazky. Při 403, 429 nebo 503 hned skonči, zapiš to brzdě (`python3 -I tools/slusne.py zastav <web> "HTTP 403 v prohlížeči"`),
  řekni to uživateli a na tom archivu ten den už nepokračuj. Když nejde ani prohlížeč, ať uživatel snímek uloží sám
  do `pracovni/` a pošle adresu stránky.
- **Na jeden archiv nejvýš jeden pomocník.** Víc projektů na jednom počítači má jednu IP adresu.
- **Mezipaměť obrázků:** co se stáhne přes brzdu, uloží se a příště se vezme z disku (`tools/cache.py`, společná pro
  všechny projekty; `cache.py stav` ukáže úsporu).

### Pomocníci (subagenti) – šetrně

Na velké kolo (např. „projdi 5 svazků a najdi všechny Nováky“) můžeš pustit 2–4 pomocníky paralelně, každého na
jinou větev nebo archiv. Stojí hodně kreditů – před velkým kolem řekni uživateli, co plánuješ a proč, a nech si to
schválit. Hledání a první čtení knihy **s rejstříkem** dej levnějšímu modelu (Agent s `model: "sonnet"`), čtení knihy
**bez rejstříku** (hledání naslepo) silnějšímu; ověření a zápis do dat děláš ty.

- Přesné zadání: svazek, snímky, koho hledat, struktura pramene, výsledek po **pevných polích** (klíč, snímek,
  souřadnice), pasti z `matriky.md` a brzda (při hlášce „zastavený“ skončit). Rejstřík po sloupcích
  (`mapa_knihy.py … --sloupce`). Nové osoby dočasně (`nova1`), čísla určíš ty.
- Pomocník píše jen do `pracovni/pom_<větev>/`, **do `data/` nikdy**. Zapisuješ ty; výstupy nemaž, dokud nejsou vytěžené.
- **Záporný výsledek pomocníka („prošel jsem snímky 20–60, není tam“) není hotový výsledek** – chybné „není“ schová
  předka natrvalo. Přijmi ho jen s dokladem: u každého snímku první a poslední jméno a rozsah dat, čtené ve zvětšení;
  navazující úseky ať se o snímek překrývají. V deníku rozliš úsek prošlý **s dokladem** a jen **orientačně** –
  „už prošlé, znovu nehledat“ platí jen pro první.
- **Čtení pomocníka je první čtení**, ne doklad: kontrolní čtení stejných pevných polí uděláš ty
  (`tools/overit.py <snímek> x0,y0,x1,y1 pracovni/over` rozdělí zápis na dvě čitelné poloviny); neshoda jde k uživateli.
- Na špatně čitelné knihy (kurent 1. poloviny 19. století, vybledlé snímky) pomocníky nepouštěj, nebo jim dej přesný
  snímek. Prohlížeč může mít najednou jen jeden pomocník, proto dávej přednost nástrojům bez prohlížeče.

### Kdy přestat

Linie končí, když matriky mlčí (nemanželské dítě bez otce, shořelé knihy, chybějící svazky) nebo když jsi
v 17. století. Zapiš to – rozpor do `ISSUES`, co ví jen archiv do `archivni_dotazy.md`, co ví rodina jako otázku pro
rodinu (`otazky.py`, stránka Co hledáme), další nápad do `ukoly.md` (náhradní prameny: `metodika.md` → Mrtvé body) –
a jdi na jinou větev. Průběžně aktualizuj `data/STAV.md` („Rozpracováno“: co je rozdělané, poslední krok, co dál),
aby šlo kdykoli navázat.

## Fáze 3 – Zajímavosti a příběhy rodů

Podrobně `reference/pribehy.md`. Tohle rodina na webu čte nejradši – nenechávej to na konec.

- **Zajímavosti** sbírej **průběžně** do `data/zajimavosti.md` a řekni je uživateli; po každém kole spusť
  `python3 -I tools/napady.py` (svatby krátce před porodem, rod v jednom domě, dlouhověkost, epidemie…) a
  `tools/osobnosti.py` (duchovní, umělci, vojáci… s tipy, kde hledat víc), ověř a napiš.
- **Příběhy rodů:** jakmile má hlavní rod ~5 doložených generací, nabídni příběh. Koncept napiš **do chatu** ke schválení,
  pak `data/pribeh.md` (další rody `data/pribehy/<slug>.md`) a ve `web.json` menu, tlačítko a úvod.

## Fáze 4 – Web

Podrobně `reference/web.md`. Ve zkratce:

1. `cd web && npm ci` (Node.js ≥ 22.19.0), pak `npm run nahled` **na pozadí** (běží, dokud ho nezastavíš) →
   <http://localhost:4321> – ukaž uživateli. Pouští-li si pak web sám (`npm run nahled`), svůj náhled předtím ukonči. V cloudovém
   prostředí (claude.ai) localhost neuvidí – pošli mu snímky stránek nebo nasaď náhled.
2. Nastav `data/web.json`: název, úvod, kontakt a **přihlašovací otázku a odpověď** (web je jen pro rodinu).
3. Po každé změně dat: `npm run data && npm run build`. Hlášky `POZOR: nefunkční odkaz` oprav hned. Po větším kole
   zkontroluj i texty úvodu ve `web.json` (`uvod`, `zajimavosti_na_uvodu`) – zastarávají.
4. Před zveřejněním projdi s uživatelem `reference/soukromi.md` (co na webu bude, žijící lidé, hlášky `CITLIVÉ`
   z `kontrola.py`; schválené zapiš do `web.json` → `citlive_schvaleno`). Na web jde i „Co hledáme“ (jen potvrzené
   otázky z `verejne_otazky.json`), deník a příběhy.
5. Čte-li web víc rodin, nabídni **přístupy**: každá větev vlastní odpověď nebo osobní odkaz (`pozvanky.py`) a jen svou
   část rodokmenu (`web.json` → `pristupy`, kdo co vidí `pristupy.py`). Opravy od rodiny z webu: `"poznamky": true` (Netlify).

## Fáze 5 – Zveřejnění (volitelné, jen se souhlasem)

Před nasazením **brána**: `python3 -I tools/brana.py` (kontrola dat, deníku, otázek a sestaveného webu); hlídač
nasazení pustí jen zelenou bránu pro aktuální data. Výchozí je **Cloudflare** (zdarma; s přístupy, osobními odkazy nebo
poznámkami **Netlify**): `npx -y wrangler@4 login`, název adresy do `web.json` (`cloudflare.nazev`) a `npm run nasadit-cloudflare`
– postup v `reference/web.md`. Nic nezveřejňuj bez výslovného souhlasu uživatele. Po zveřejnění **nenasazuj po každém
kole** (Netlify zdarma vystačí asi na 20 nasazení měsíčně) – nasazuj na pokyn nebo jednou na konci sezení.

## Poznámky pro správce skillu

Skill se zlepšuje podle zkušeností lidí, kteří ho používají. **Průběžně zapisuj do `data/poznamky_pro_skill.md`**
chyby nástrojů a webu (příkaz, co se stalo, jak jsi to obešel), nové archivy a postupy, které fungovaly, místa, kde návod
mlčel nebo radil špatně, a co uživatel chtěl, ale skill to neuměl. Piš obecně a stručně – technický postup, ne údaje o rodině.
**Ve vhodnou chvíli** (po zveřejnění webu, na konci velkého kola; ne pořád) připomeň uživateli, že je může poslat správci:

1. Projdi poznámky a odstraň nebo zobecni osobní údaje.
2. Vypiš je do chatu celé, jako jeden blok k zkopírování.
3. Požádej uživatele, ať z nich založí issue u forku skillu na **<https://github.com/mplisek/rodokmen-skill/issues>**
   (tento skill je fork originálu sarsonj/rodokmen-skill, poznámky patří správci forku).
**Nic sám neposílej** (žádný e-mail, formulář ani issue). Až uživatel řekne, že poslal, zapiš do
`data/poznamky_pro_skill.md` „odesláno <datum>“ a další poznámky piš pod tuto čáru.

## Co nikdy

- Nestahuj hromadně z placených služeb (MyHeritage, Ancestry, Geni…) a neobcházej jejich ochranu –
  automatické procházení stovek záznamů vede k **zablokování účtu**. Čti jen to, co uživatel otevře, nebo co potřebuješ jednotlivě.
- Nezadávej za uživatele hesla, platební údaje, neřeš CAPTCHA, nekupuj předplatné. U portálů s citlivými údaji (Arolsen,
  holocaust.cz) potvrzuje souhlas s podmínkami uživatel sám (`!python3 -I tools/<nástroj>.py souhlas`).
- Neobcházej brzdu `tools/slusne.py` ani blokaci archivu.
- Nedávej na web podrobnosti o žijících lidech bez jejich souhlasu.
- Nepřepisuj data bez zálohy v gitu; po větším kroku navrhni uložení (`git add -A && git commit -m "…"`).

## Soubory projektu

`data/`: `STAV.md` (vstupní bod: pravidla od uživatele, rozpracováno, čeká na rozhodnutí), `ukoly.md` (plán bádání),
`osoby.py` (předci, `LINES`, `RODINA`, `SIDE`, `ISSUES`, `HYPOTEZY`, `SAME`), `zaznamy.json`, `svazky.json`, `prepisy.json`,
`zvyrazneni.json`, `denik.jsonl` (deník, jen přes `denik.py`), `udaje_od_rodiny.md`, `archivni_dotazy.md`,
`verejne_otazky.json` (Co hledáme, jen přes `otazky.py`), `opravy.jsonl`, `zadosti.md`, `zajimavosti.md`, `pribeh.md`,
`pribehy/`, `web.json`, `dokumenty.json`, `mista.json`, `pozvanky.json`, `stavby.py`, `poznamky_pro_skill.md` (formát
`reference/data.md`). Dál `vyrezy/` a `zdroje/` (výřezy pro web / plné rozlišení), `dokumenty/` (originály od rodiny),
`pracovni/` (nejde na web), `tools/` (kopie ze skillu – aktualizuje se přes `novy_projekt.py`), `web/`.

## Nástroje (`tools/`, z kořene projektu `python3 -I tools/<nástroj>`, skripty `.sh` přes `bash`; přepínače vypíše `--help`)

| Nástroj | K čemu |
|---|---|
| `aron_search.py`, `aron_img.py` | ARON (SOA Zámrsk): hledání svazků; snímek (úroveň `0` = plné rozlišení), trvalý odkaz, zápis svazku |
| `portafontium.py`, `litomerice.py`, `soal_zoomify.py` | SOA Plzeň (Porta fontium), SOA Litoměřice (hledání, snímek Zoomify) |
| `ahmp_search.sh`, `ahmp_scan.py`, `policie_prihlasky.py` | Praha: matriky AHMP, policejní přihlášky 1850–1914 |
| `ebadatelna.py`, `mza.py` | SOA Praha (náhled a výřez ze snímku z prohlížeče), MZA Brno (jen hledání) |
| `prohlizec.py`, `matricula_snimek.js` | vlastní prohlížeč pro portály bez skriptů (Playwright, pauzy brzdy); snímek z Matriculy |
| `matricula.py`, `matricula_dl.sh`, `matricula_batch.sh` | Matricula (Rakousko, Bavorsko, Polsko…) |
| `vademecum.py` | VadeMeCum Národního archivu, židovské matriky |
| `anno.py`, `anno_snap.py`, `kramerius.py` | noviny: ANNO (rakouské, `--ztraty` = seznamy ztrát 1914–1919), Kramerius (české, jen veřejná díla) |
| `arolsen.py`, `obeti.py`, `vezni.py`, `mauthausen.py`, `souhlas.py` | oběti a vězni 2. sv. války; souhlas s podmínkami potvrzuje uživatel |
| `brno_encyklopedie.py` | Encyklopedie dějin Brna: osobnosti s adresami, povoláním a hrobem |
| `mapa.py` | **mapa knihy**: co který snímek svazku pokrývá (`hledej`, `zapis`, `stav`), sdílená pro všechny projekty |
| `mapa_knihy.py` | **náhled knihy**: montáž záhlaví snímků (oddíly po vsích) a sloupců rejstříku (`--sloupce`) |
| `cache.py`, `pracovni_prehled.py` | sdílená mezipaměť snímků; co už leží v `pracovni/` |
| `nalez.py`, `cteni.py` | zápis nálezu jedním příkazem; porovnání dvou čtení po pevných polích (spory k uživateli) |
| `vyrez.py`, `ramecek.py`, `overit.py` | výřez (zlomky stránky; `--kontrast`, `--zacernit` u dokladů), rámeček (zlomky výřezu), ověření čtení na dvou polovinách |
| `zapis.py`, `oprava.py`, `svazky.py` | zápis položky; změny osob, dokumentů a míst s historií; svazek z prohlížeče |
| `denik.py`, `otazky.py`, `ucastnici.py` | deník (`pridej`, `over`, `migruj`); otázky pro Co hledáme (`pridej`, `potvrd`, `ze-souboru`); účastníci zápisů |
| `rejstrik.py` | rejstřík dat v SQLite (Hledání v datech) |
| `kontrola.py`, `audit_dat.py` | kontrola dat (citlivé údaje, časová návaznost, procesní údaje); rozpory v datech bez čtení snímků |
| `graf.py`, `rodiny.py`, `chronologie.py`, `datumy.py` | rodina jako graf (dvojníci, `SAME`); kandidáti stejného jména; časová návaznost; čtení dat |
| `ged_import.py`, `ftb_export.py` | rodinný strom (GEDCOM, záloha MyHeritage) – `data.md` |
| `mista.py`, `napady.py`, `osobnosti.py`, `stavby.py` | místa pro mapu; náměty na zajímavosti; osobnosti; dějiny domů |
| `export_web.py`, `fan_chart.py`, `kontrola_webu.py`, `brana.py` | data → web; vějíř k tisku; kontrola webu; brána |
| `pozvanky.py`, `pristupy.py` | osobní odkazy na web; přehled přístupů (kdo co vidí) |
| `mailto.py` | koncept žádosti → odkaz na hotový e-mail (nic neodesílá) – `zadosti.md` |
| `slusne.py`, `smoke_test.py`, `verze.py` | brzda proti zablokování archivem; kontrola síťových nástrojů; verze skillu |
| `spotreba.py`, `dodrzovani.py` | spotřeba sezení; dodržování metodiky ze záznamů sezení |
