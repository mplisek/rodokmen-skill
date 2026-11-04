# Časová osa předků – návrh

Stav: schváleno v rozhovoru 4. 11. 2026, k naplánování.

## Proč

Uživatel chce na rodinném webu vidět a zároveň kontrolovat, jak na sebe životy předků časově navazují:
kdo žil souběžně s kým, kdy se kdo oženil, kdy se narodilo dítě a kdy kdo zemřel. Události mají být
propojené, aby bylo na první pohled vidět, že něco nesedí (otec zemřel roky před narozením syna apod.).
Dnešní `tools/kontrola.py` chronologii nehlídá vůbec.

Inspirace: TimeNets (Stanford 2010, https://vis.stanford.edu/files/2010-TimeNets-AVI.pdf) a Family Tree
Timeline od MyHeritage. Uživatel ze dvou náčrtů vybral variantu **„pruhy životů“** (podobné Ganttovu
diagramu), ne propletené linie ve stylu TimeNets.

## Cíle

1. Nová stránka rodinného webu **Časová osa** (`/osa/`), v menu vedle Vějíře.
2. Na ose jsou přímí předci z `data/osoby.py` (`P`), tedy stejní lidé jako ve Vějíři.
3. Pod osou je seznam **„Co časově nesedí“** a u dotčených osob na ose je ⚠. Obojí vidí celá rodina
   (rozhodnutí uživatele).
4. Stejná pravidla hlásí i `tools/kontrola.py` v terminálu.

## Podoba stránky (rozhodl uživatel)

- Vodorovná osa let, společná pro všechny. Jeden řádek = jedna osoba.
- Pořadí řádků: průchod stromem Kekulého čísel „otec – dítě – matka“ (in-order: řádky větve otce `2k`,
  pak `k`, pak řádky větve matky `2k+1`). Otec je tak vždy nad dítětem a matka pod ním, jako ve vodorovném
  rodokmenu.
- Pruh vede od narození do úmrtí.
- Kroužek na pruzích obou manželů značí jejich sňatek.
- Svislá čára v datu narození dítěte spojuje řádek otce s řádkem matky a pruh dítěte na ní začíná.
- V náčrtu byly v pruhu jméno a roky („Jan Novák 1890–1944“).

## Moje rozhodnutí (uživatel je viděl v rozhovoru a nerozporoval)

- Barva pruhu = barva rodu (`LINE_COLORS` v `export_web.py`, stejně jako Vějíř). Osoby 1–7 dostanou
  neutrální barvu.
- Žijící osoba: pruh je přerušovaný a vede až do současnosti, nemá konec. Za žijící se osoba počítá ve dvou
  případech: její `note` začíná „Žijící“ (konvence ze `soukromi.md`), nebo nemá úmrtí a narodila se
  v posledních 100 letech.
- Předek s neznámým úmrtím: pruh vede k poslední známé vlastní události (sňatek, narození dítěte z rodokmenu,
  údaj „po“) a pak krátce vybledne. Nekreslí se až do současnosti. Neznámé úmrtí žádné pravidlo kontroly
  neporuší.
- Nejisté údaje se kreslí jinak než jisté. Týká se to roku dopočítaného z věku, stavu `prob`, údajů
  „asi“, „před“ a „po“: konec pruhu je rozmazaný nebo vybledlý. Varování u nich má mírnější znění.
- Když najedeš myší na pruh, ukáže se jméno, data (celá, jsou-li známá) a věk při sňatku, narození dítěte
  a úmrtí. Klepnutím na pruh se otevře stránka osoby.
- Varování mají neutrální formulaci, ne „chyba“. Například: „Václav Novák zemřel 1887, syn Jan se narodil
  1890 – jeden z údajů asi nesedí.“ Rodina tak pozná, že jde o otevřenou otázku.
- Předek zapsaný v rodokmenu dvakrát (`SAME`): osa ho kreslí jako Vějíř (`fan_chart.py`, #31). Na místě
  aliasu se zopakuje hlavní osoba i s celou větví jejích předků, takže se strom nepřetrhne. Zopakované
  řádky odkazují na stejné stránky a data se berou z hlavního čísla. Varování se nezdvojí: každý rozpor
  je v seznamu jen jednou.
- Zástupné osoby („otec neuveden“, `placeholder()` v `export_web.py`) se nekreslí.
- Osoba bez jakéhokoli roku si řádek ponechá, aby strom nebyl roztržený. Má jen jméno, pruh nemá.
- Strom s 8 a více generacemi je vysoký: stránka se roluje dolů a řádek s roky zůstane nahoře
  přišpendlený. Na mobilu jde osa posouvat do strany.
- V `kontrola.py` budou tato hlášení jako UPOZORNĚNÍ, ne jako CHYBY. Data mohou být neobvyklá a přesto
  pravdivá, například pohrobek.
- Ukázková rodina Novákových zůstane bez varování (náčrt měl chybu přidanou schválně).

## Pravidla kontroly

Kontrola se týká dítěte `k`, otce `2k` a matky `2k+1`, jsou-li v `P`. Pravidla odsouhlasená v rozhovoru:

1. Otec zemřel víc než 9 měsíců před narozením dítěte.
2. Matka zemřela před narozením dítěte.
3. Matce bylo při narození dítěte méně než 15 nebo více než 50 let.
4. Sňatek proběhl, když jednomu z manželů bylo méně než 15 let.

Doplnil jsem tato pravidla:

5. Úmrtí je dřív než narození téže osoby.
6. Sňatek je až po úmrtí jednoho z manželů.
7. Otci bylo při narození dítěte méně než 15 let.

Narození dítěte před sňatkem rodičů se **nehlásí**. V matrikách je běžné.

**Hlásí se jen jisté rozpory.** Každé datum je interval podle toho, jak přesně je známé:

- celé datum = jeden den;
- „3/1867“ = celý měsíc;
- „1890“ = celý rok;
- „asi 1720“ = 1715–1725 (tolerance ±5 let jako konstanta, kterou jde doladit);
- „před 1740“ = cokoli do 1740;
- „po 1921“ = cokoli od 1921.

Pravidlo se ohlásí jen tehdy, když je porušené pro **všechny** možné kombinace dat v intervalech.
Příklad: otec zemřel 1889 a dítě se narodilo 1890, obojí jen na rok. To se nehlásí, protože jde o možného
pohrobka. Mírnější znění („možná nesedí“) má varování, ve kterém figuruje údaj „asi“ nebo osoba ve stavu
`prob`, `mh` či `fam`.

## Ověřené údaje (rozhodl uživatel)

Neobvyklý údaj, který uživatel ověřil, jde odškrtnout. Varování pak zmizí z webu (⚠ i seznam) a přestane
ho hlásit i `kontrola.py`. Příklady: matce bylo 51 let, sňatek ve 14 letech s dispenzí, chyba je přímo
v matrice.

Moje rozhodnutí o podobě:

- Každé pravidlo má krátký pevný klíč: `umrti-pred-narozenim`, `snatek-mlady`, `snatek-po-umrti`,
  `otec-zemrel`, `matka-zemrela`, `vek-matky`, `vek-otce`.
- Odškrtnutí se zapíše k osobě v `data/osoby.py`, u které se ⚠ ukazuje. U pravidel o rodičích a dítěti
  je to dítě. Zapisuje se nové volitelné pole s důvodem:
  `overeno={"vek-matky": "věk 51 let potvrzuje křest i úmrtí matky"}`.
- `kontrola.py` u každého upozornění vypíše hotový řádek k vložení. Funguje to stejně jako dnešní rada
  u `citlive_schvaleno`.
- Odškrtnutý alias `SAME` platí i pro hlavní číslo, protože varování se nezdvojují.
- Formát nového pole popíše `reference/data.md` a hlavička `template/data/osoby.py`.

## Odkud se berou data

- Události jsou ve faktech `f` osoby: `*` je narození, `×` sňatek, `†` úmrtí (`reference/data.md`).
  Formáty dat: „14. 2. 1890“, „3/1867“, „1797“ a předpony „asi“, „≈“, „před“, „po“.
- Když ve faktech chybí `*` nebo `†`, použijí se roky z pole `y` („asi 1720–1785“, „1680 – před 1740“,
  „† 1940“, „* 1895“). Funkce `years()` v `export_web.py` už tvary pole `y` rozebírá.
- Sňatek: vezme se ten fakt `×`, který odpovídá druhému rodiči. Stejnou heuristiku (příjmení manželky
  ve faktu) už používá `export_web.py` při stavbě `families`. Má-li osoba víc sňatků, kroužek dostane jen
  sňatek s druhým rodičem z rodokmenu.

## Kde bude kód (moje rozhodnutí)

- **Jeden modul s pravidly:** `skills/rodokmen/tools/chronologie.py`, jen standardní knihovna. Rozebere data
  z faktů na intervaly, sestaví události osob a vrátí seznam varování. Importují ho `export_web.py`
  i `kontrola.py`, a pravidla jsou tak na jednom místě. Import funguje stejně jako u `cache.py`
  (`ebadatelna.py`, `portafontium.py`).
- **Export:** `export_web.py` zapíše do `site.json` hotová data pro osu: řádky v pořadí, události s intervaly
  a příznakem nejistoty a varování. Web už jen kreslí a nic nepočítá.
- **Stránka:** `skills/rodokmen/template/web/src/pages/osa.astro` a odkaz v menu `Base.astro`
  (skupina s Rody, Mapou a Vějířem). SVG se sestaví při buildu. Na klientu běží jen malý skript pro
  bublinu při najetí myší, nebo stačí `<title>` v SVG.
- **Bez nových závislostí** v npm ani v Pythonu.

## Soukromí

Osa ani varování neukáže nic, co už web neukazuje. Pracuje jen s fakty, které `export_web.py` už dnes
posílá do `site.json`. Žijící osoby mají ve faktech jen rok narození („Žijící – údaje jen základní“)
a osa nic víc neodhalí.

## Mimo rozsah (non-goals)

- sourozenci a další příbuzní z `SIDE`;
- historické události na pozadí (války, epidemie);
- pohled na život jediné osoby (jako na MyHeritage);
- varianta s propletenými liniemi (TimeNets);
- úpravy dat z webu;
- odkaz na osu z úvodní stránky nebo ze stránky osoby (stačí menu).

Všechno z toho jde přidat později.

## Čeho se vyvarovat (anti-goals)

- Varování, která straší kvůli nepřesným datům. Proto se hlásí jen jisté rozpory.
- Obviňující formulace, které uvidí rodina.
- Víc údajů o žijících, než web už ukazuje.
- Nová knihovna nebo klientský framework jen kvůli ose.

## Ověření

- `tests/chronologie/test_chronologie.py`: testy pouze přes `assert` a standardní knihovnu, mimo složku skillu
  (stejně jako `tests/brzda/`, aby se nekopírovaly uživatelům). Ověří rozbor dat na intervaly a každé
  pravidlo, včetně hraničních případů: pohrobek s daty jen na rok se nehlásí, „před“, „po“, „asi“ a celá data.
  Ověří také, že varování odškrtnuté přes `overeno` se nehlásí.
  Spouští se `python -I -X utf8 tests/chronologie/test_chronologie.py`.
- Spuštěný `kontrola.py` na ukázkových datech nehlásí žádné chronologické upozornění. Na kopii
  s podvrženou chybou je hlásí.
- Ve `web/` projdou `npm run data` a `npm run build`. Stránka `/osa/` se zobrazí na ukázkových datech.
- Formát mezi `tools/` a `template/web/` se mění, proto podle `CLAUDE.md` vyzkoušej i aktualizaci projektu
  založeného verzí 0.7.0. Postup: `novy_projekt.py` na stejnou složku, `npm install`, `npm run data`,
  `npm run build`.

## Vydání

- Nová verze **0.8.0**: `.claude-plugin/plugin.json`, `skills/rodokmen/VERZE`, README na dvou místech
  a sekce v `CHANGELOG.md` (postup podle `CLAUDE.md` v kořeni repozitáře).
- Návody: seznam stránek v `reference/web.md`. Řádek `kontrola.py` v tabulce nástrojů v `SKILL.md`
  doplní, že hlídá i časovou návaznost. `reference/data.md` dostane poznámku, že přesnost dat ve faktech
  ovlivňuje kontrolu.
- Tag a vydání na GitHubu až po sloučení do `main` a se souhlasem uživatele.

## Necháno na staviteli

- Přesná grafika: výška řádku, styl bubliny, poloha ⚠ (u osoby, nebo přímo u události), použití
  proměnných z `global.css`.
- Jak přesně vypadá rozmazaný nebo vybledlý konec nejistého pruhu.
- Tvar dat pro osu v `site.json`.
- Zda se SVG skládá v Astro komponentě, nebo v Pythonu jako `fan_chart.py`. Podmínka: žádná nová závislost
  a pravidla zůstanou v `chronologie.py`.
- Chování na mobilu nad rámec vodorovného posouvání.
