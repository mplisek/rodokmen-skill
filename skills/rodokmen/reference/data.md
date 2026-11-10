# Formát dat projektu

Všechna data jsou v `data/`. Web se z nich generuje (`npm run data`), nikdy needituj `web/src/data/site.json` ručně.
Po změnách spusť `python3 -I tools/kontrola.py`. Ukázku vyplněných dat má `SKILL_DIR/template/ukazka/`.
Položky do JSON souborů přidávej a měň přes `python3 -I tools/zapis.py` (zachová formát souboru, viz SKILL.md).

## `osoby.py` – předci
Kekulého čísla: 1 = výchozí osoba, otec osoby n = 2n, matka = 2n+1.
| číslo | kdo |
|---|---|
| 1 | výchozí osoba (u ženy `sex="F"`) |
| 2, 3 | otec, matka |
| 4–7 | prarodiče (4, 5 otcovi rodiče; 6, 7 matčini) |
| 8–15 | pradědečci a prababičky = **8 rodů** (`LINES`) |
| 16–31, 32–63 … | každá další generace dvojnásobek |

Otec předka 22 je 44, matka 45; dítě předka 45 je 22 (45 // 2). Muži mají sudá čísla.

```python
P = {
 8: dict(n="Jan Novák", y="1890–1944", st="doc",
         f=["* 14. 2. 1890 Holice čp. 112", "kovář", "× 20. 6. 1919 Holice Josefa Pokorná", "† 1944 Holice"],
         r=["holice_krest_jan_novak_1890", "holice_snatek_jan_novak_josefa_pokorna_1919"],
         note="Proč nejistota / rozpor / odkud údaj"),
 9: dict(n="Josefa Pokorná", y="* 1895", st="doc", f=[...], r=[...]),
 33: dict(n="otec neuveden", st="unk", f=[], note="Nemanželský syn; otec v matrice není."),
}
```
- `n` jméno (ženy rodným příjmením, bez příjmení po sňatku – to je vidět u manžela; neznámé rodné příjmení
  `"Anna (příjmení neznámé)"`, ne `"Anna (Nováková)"`), `y` roky pro přehledy (`"* 1895"`, `"1890–1944"`, `"asi 1720–1785"`, `"1680 – před 1740"`,
  `"† 1940"` když známe jen úmrtí; nic nevíme → `""`).
- `zap` (volitelné) – tvary jména, jak stojí v zápisech: `zap=["Catharina Nowakin", "Kateřina Nováková"]`.
  Na stránce osoby se ukážou jako „V zápisech zapsána jako …“; s `"puvodni_jmena": true` ve `web.json` se jimi osoba
  i jmenuje (web, vějíř, mapa domů, statistiky). Adresa stránky zůstává podle `n`.
- `f` fakta: začínají `*` (narození), `×` (sňatek), `†` (úmrtí) nebo jsou volný text (řemeslo, bydliště).
  Názvy obcí ve faktech používá mapa (`mista.json` → `re`). Datum piš hned za značku (`"* 14. 2. 1890 Holice"`,
  `"× 3/1867"`, `"† asi 1785"`, `"† před 1740"`): podle jeho přesnosti hlídá `kontrola.py` i stránka Časová osa
  časovou návaznost (otec zemřel dřív, než se dítě mohlo narodit, matce by bylo 12 let…). Celé datum pozná víc než
  jen rok, „asi“ počítá s tolerancí ±5 let a hlásí se jen rozpor, který platí pro všechna možná data.
  Sňatek jmenuje partnera (`× 1919 Holice Josefa Pokorná`); `kontrola.py` hlásí, když žádný sňatek nejmenuje osobu
  na sousedním čísle (manžel 2k, manželka 2k+1, i přes `SAME`). U `doc` hlásí `čp.`, které není v žádném citovaném
  zápisu (`shrnuti`, přepis) jako číslo domu (`čp. 23`, `No 23`, `N. 23`, `[Dům] 23`, `z Ostřetína 23`; datum, věk ani
  číslo zápisu, strany či snímku neplatí); číslo převzaté odjinud označ ve faktu zdrojem: `* 1862 Ostřetín čp. 23 (podle stromu)`.
- `r` klíče zápisů ze `zaznamy.json`; přidávej je `python3 -I tools/zapis.py odkaz <číslo> <klíč> [<klíč> …]` (u `SIDE`
  místo čísla část jména) – nástroj zachová zbytek souboru a ověří, že zápis existuje. `st` viz `matriky.md`: `doc` přečteno v matrice, `prob` pravděpodobné,
  `fam` od rodiny (i strom, který si rodina vede sama, např. GEDCOM z jejího MyHeritage), `mh` cizí strom z internetu, `unk`.
- `vyz` (volitelné) – krátký popis, proč je předek významný (farář, starosta, legionář…); jde na stránku „Osobnosti“ nahoru.
  Bez něj stránka vybírá osobnosti sama podle slov ve faktech (`tools/osobnosti.py`).
- `overeno` (nepovinné) – neobvyklý údaj, který jsi ověřil(a), a varování časové návaznosti u téže osoby
  (u pravidel o rodičích a dítěti u dítěte) pak zmizí z `kontrola.py` i z webu:
  `overeno={"vek-matky": "věk 51 let potvrzuje křest i úmrtí matky"}`. Klíče: `umrti-pred-narozenim`, `snatek-mlady`,
  `snatek-po-umrti`, `otec-zemrel`, `matka-zemrela`, `vek-matky`, `vek-otce` – `kontrola.py` u každého upozornění
  vypíše, co přesně doplnit. Důvod piš vždy, ať je za rok jasné, proč to platí.
- `LINES = {8: ("Novákové", "Kováři z Holic…"), …}` – jen čísla 8–15; název rodu = příjmení v množném čísle. Vyplň hned, jak znáš pradědečka nebo prababičku – bez LINES web neukáže rody a nepřijde rada k příběhu.
- `RODINA` – osoby mimo přímou linii (sourozenci předků, jejich partneři a děti, děti výchozí osoby, předci partnerů):
  `"zkratka": dict(n="Marie Nováková", y="1892–1970", sex="F", otec=16, matka=17, partner=[...], st="doc", f=[...], r=[...], note="…")`.
  `otec`/`matka` = číslo přímého předka (děti výchozí osoby: `otec=1`) nebo zkratka jiné osoby z RODINA; sourozenec předka 8 má `otec=16, matka=17`
  i když 16/17 ještě neznáme. `partner` jen pro partnery bez společného dítěte. Stromový graf (`/strom/`) z nich skládá
  rozklikávací větve – od sourozence předka třeba až do 20. století. Každá osoba z RODINA má **vlastní stránku**
  (adresa: jméno a první rok z `y`) a u všech osob – předků i příbuzných – web stejně počítá **Děti**, **Sourozence**
  (i nevlastní) a **Manželství** z toho, kdo je čí otec a matka. Volitelné `v="manželka Václava Culka"` = vztah na
  stránce osoby (jinak ho web odvodí: „sestra osoby Jan Novák“). Žijící jen jménem a rokem narození (web to vynutí sám).
- `PARTNERI` (volitelné) – sňatky s podrobnostmi, i mezi předky (druhé manželství):
  `dict(a=44, b="rosalie-culkova", rok=1850, misto="Libice", konec="ovdověl 1860")`; `a`/`b` = číslo z `P` nebo zkratka
  z RODINA. Na stránce osoby v kartě Manželství („sňatek 1850, Libice, ovdověl 1860“); u žijících bez roku a místa. U předka v `P` lze zapsat `sour="hotovo"` / `"částečně"` (stav hledání sourozenců).
- `SIDE` – jen poznámky, které do RODINA nejdou (nejistý vztah, celá větev jednou větou):
  `dict(k=<číslo předka>, n="…", v="příbuzný (?)", y="…", t="text", r=[klíče])` – ve stromu jako „pozn.“ u předka.
  `v="bratr"`/`"sestra"` u předka k a `v="syn"`/`"dcera"` u jeho rodiče (2k, 2k+1) web ukáže u rodičů v kartě Děti jako
  „Další děti“ (s odkazem na poznámku); nevlastní sourozence ne – nevíme, po kterém rodiči jsou.
  Nedoloženou samostatnou rodinu nepřipojuj do hlavního stromu; jako `SIDE` ji veď jen jako výslovně označenou stopu
  u konkrétního možného příbuzného. Jinak ji ponech odděleně v deníku.
- `ISSUES` – otevřené otázky a rozpory v datech: `dict(k=16, otazka="Kdo byli rodiče Františka Nováka?", stav="otevřené",
  text="Rodina uvádí…, rozhodne křest nebo sňatek 1889.")` (`stav`: `otevřené` / `hypotéza` / `vyřešeno`; `k` = číslo
  předka nebo zkratka z RODINA, podle něj web otázku zařadí k rodu a odkáže na osobu). Na stránku „Co hledáme“ → Otevřené
  otázky; vyřešené se skryjí (časem je smaž). Starší dvojice `("Otázka", "Otevřené: …")` dál fungují, jen bez rodu.
  Jde na web – nepiš sem citlivé věci (příčiny úmrtí, rodinné spory) bez souhlasu.
- `HYPOTEZY` – `dict(rod=8, nadpis="…", text="…", polozky=[("jméno", "text")], zaznamy=[klíče])` → stránka rodu.
- `SAME = {350: 140}` – předek, který je v rodokmenu dvakrát (alias → hlavní číslo; alias v `P` může mít `f=["TÁŽ OSOBA jako 140"]`).
  `kontrola.py` (přes `tools/graf.py`) upozorní na stejné jméno a rok narození na dvou číslech bez `SAME` a na věk
  rodičů 2k a 2k+1 při narození dítěte k mimo 15–50 let u matky a 16–75 let u otce.

## `zaznamy.json` – zápisy
```json
[{"klic": "holice_krest_jan_novak_1890", "svazek": "1a0b2337", "snimek": 57, "druh": "N",
  "datum": "14. 2. 1890", "nazev": "Křest Jana Nováka",
  "shrnuti": "Jan, syn Václava Nováka, kováře v Holicích čp. 112, a Barbory roz. Malé z Ostřetína.",
  "odkaz": "https://aron.vychodoceskearchivy.cz/apu/…/dao/…/file/…"}]
```
- `klic`: malá písmena bez diakritiky, `obec_druh_kdo_rok` (druh: krest, snatek, umrti, index, scitani…). Je to i název obrázku.
- `druh` = **událost**: `N` křest / narození, `O` sňatek (i ohlášky), `Z` úmrtí / pohřeb, `B` biřmování, `S` soupis
  obyvatel (sčítání lidu, soupis duší, soupis poddaných), `J` jiný pramen (policejní přihláška, pozemková kniha, parte…).
  Web podle něj řadí stránku Zápisy do skupin.
- `rejstrik: true` – jen položka **rejstříku** (abecední seznam s odkazem do knihy: jméno, datum, dům), samotný zápis
  nečten. `druh` je i tak událost (položka rejstříku zemřelých → `"Z"`); na webu má štítek „rejstřík“. Starší
  `"druh": "I"` web převede sám podle klíče a názvu, `kontrola.py` ho připomene.
- `datum` jako v češtině („14. 2. 1890“, „3/1867“, „1797“) – web podle něj řadí.
- `shrnuti` je stručný obsahový souhrn, ne doslovný přepis. Při předání výzkumu bez originálního snímku nepřepisuj
  souhrn jako `orig` v `prepisy.json` a nevyráběj výřez ani rámeček; chybějící podklady výslovně poznamenej.
  `kontrola.py` má dál hlásit chybějící výřez nebo přepis.

### Příčina úmrtí

U zápisu druhu `Z` může být pole `pricina_umrti`. Zdroj a datum patří k tomuto zápisu; příčinu nevkládej bez dokladu do osobních údajů. Například (smyšlený údaj):

```json
{"pricina_umrti": {"stav": "uvedena", "puvodni": "Altersschwäche", "cesky": "stařecká slabost", "jistota": "doc", "poznamka": "Dobový výraz, nikoli dnešní diagnóza."}}
```

| `stav` | Význam |
|---|---|
| `uvedena` | Příčina je zapsaná. Vyplň `puvodni`, `cesky` a `jistota`: `doc` = bezpečné čtení, `prob` = nejisté čtení. |
| `necitelna` | Údaj tam je, ale nejde bezpečně přečíst. V `puvodni` lze nechat čitelnou část s `[…]`; `cesky` nech prázdné. |
| `nevyplnena` | Rubrika existuje, ale je prázdná. |
| `bez_rubriky` | Matrika rubriku pro příčinu nemá. |

U posledních dvou stavů `puvodni` a `cesky` vynech nebo nech prázdné; stačí například `{"stav": "bez_rubriky"}`. Volitelná `poznamka` vysvětlí nejasnost. Jistota čtení není potvrzení správnosti tehdejší diagnózy.

Původní výraz opiš doslova, nejistá místa označ `(?)` a zachovej sloupec v obrazu i přepisu. Příčinu neodvozuj z věku či sousedních zápisů a dobový termín nenahrazuj odhadem moderní nemoci. Pro novější citlivé údaje platí `soukromi.md`.

Pole je nepovinné kvůli starším datům. Když chybí, znamená to „zatím nezpracováno“, nikoli „bez rubriky“; web nic nedoplňuje. Pokud je vyplněné, zobrazí se u zápisu na stránce osoby i na detailu zápisu.

## `svazky.json`
`{"1a0b2337": {"archiv": "SOA Zámrsk – Sbírka matrik…", "portal": "ARON", "svazek": "N Holice 1880–1900, sign. …",
"popis": "obce", "url": "odkaz na svazek"}}` – u ARON zapisuje `aron_img.py <apu> svazek`.
Doklad, který online není (rodný list od rodiny, kopie z badatelny), má svazek bez `portal` a `url`, např.
`"rodina": {"archiv": "doklady od rodiny", "svazek": "Rodné a oddací listy", "popis": "dokumenty/…"}` – `kontrola.py`
pak u jeho zápisů nechce odkaz na snímek.

## `prepisy.json`
`{"<klic>": {"orig": "[Datum] 14. února 1890\n[Dům] 112\n[Otec] …", "cs": "Český překlad celou větou…"}}`
- `orig` věrný přepis po sloupcích, `[Název sloupce]` v hranatých závorkách, nejisté „(?)“, nečitelné „[…]“, zkratky ponechat.
- `cs` srozumitelný překlad pro rodinu; vysvětli staré pojmy (domkář, podruh).
- Souhrn nalezený v předaných poznámkách není originál ani přepis. Bez snímku ponech `orig` nedoplněné a zdrojovou mezeru popiš.
- Jiná pole web nezobrazí (třeba `preklad`) – `zapis.py prepisy` je odmítne a `kontrola.py` je ohlásí.

## `zvyrazneni.json`
`{"<klic>": {"boxes": [[x0, y0, x1, y1]], "status": "ok", "note": ""}}` – zlomky šířky/výšky obrázku `vyrezy/<klic>.jpg`.
Zapisuje `ramecek.py`. Rámeček má obepnout celý čtený zápis (ne jen jméno).

## `mista.json`
`{"Holice": {"re": "Holic", "dotaz": "Holice, Česko", "lat": 50.066, "lon": 15.986}}` – `re` je regulární výraz hledaný
ve faktech osob (kmen slova, aby sedělo skloňování: „Holic“ najde Holice i v Holicích). Spravuje `mista.py`.
Pozor na kolize (Hradec Králové × Nový Hradec Králové – použij `(?<!Nový )Hradec`; krátká jména jako `\bBuku?\b`).
Hypotéza: `"hypoteza": true, "rod": 8`. Zkratky obce, které se objevují ve faktech nebo souhrnech zápisů
(„HL čp. 12“), přidej jako `"zkratky": ["HL"]` – použije je stránka Domy. Stránka Domy bere vzory `re` z `mista.json`
přednostně, i k rozhodnutí, co je táž obec (vzor „Řetov“ spojí Řetovou i Velkou Řetovou) – u stejnojmenných
obcí (Lhota × Dolní Lhota) proto vzor zúži, jinak se domy obou obcí slijí. Když OpenStreetMap obec nenajde („Žár“, malé osady), zkus třetí parametr – dotaz: `mista.py pridej "Žár" "Žár" "Žár, Zdíkov, okres Prachatice"`
nebo dotaz s větší obcí či okresem. U **víceznačných názvů** (Podolí, Dub, Lhota) vezme OpenStreetMap kteroukoli ves
(„Podolí, Česko“ = Podolí u Brna) – v posledním sloupci výpisu zkontroluj okres a dej dotaz se sousední obcí
(`mista.py pridej "Podolí" "Podol" "Podolí, Odlochovice"`). Místopis nejlíp zná rodina – když si nejsi jistý, zeptej se.
`mista.py` hledá jen sídla a pod seznamem upozorní, když našel něco jiného než obec (bar, ulici) nebo když je nový bod
víc než 50 km od všech ostatních míst projektu (nejspíš jiná obec stejného jména). Kontrola mapy (`kontrola.py`) u
předků bez obce vypíše v hranatých závorkách slova z faktů, která vypadají jako obec. Když je obec v `mista.json`,
jen ji výraz `re` nechytí ve skloňovaném tvaru („v Přesece“ × `Přesek`) – uprav výraz (`Přese?[kc]`).

## `domy/` – domy předků na mapě (volitelné)
`data/domy/domy.geojson` a `data/domy/vyrezy/` jsou výstup skillu **stare-adresy** (`mapa.py`, polohy domů „obec čp.“
podle stabilního katastru). Export z nich udělá stránku `/domy/` a propojí domy s osobami a zápisy podle zmínek
„Obec čp. N“ ve faktech, poznámkách, `SIDE` a souhrnech zápisů. Adresy, které na mapě chybí, zapíše do
`data/domy/chybi.txt` – podklad pro další kolo geokódování. Bez `domy.geojson` se stránka v menu neukáže.

## `stavby.py` – dějiny významných domů (volitelné)
`data/stavby.py` (slovník `D`, klíč = id adresy z `data/domy/adresy.json`): držitelé, obyvatelé, události, čísla
popisná v čase a otevřené otázky k domům, které stojí za příběh (hostinec, mlýn, rychta, rodová usedlost, dům jiné
větve). Poloha domu zůstává v `data/domy/`, stavba na ni odkazuje polem `dum`. Každá položka má stav `st`
(`doc` / `lit` / `prob` / `fam` / `unk`) a zdroj (`r` = klíče ze `zaznamy.json`, nebo `zdroj` textem). Osoby se
odkazují Kekulého číslem z `P` nebo klíčem z `RODINA`. `python3 -I tools/stavby.py kontrola` hlídá existenci osob a
zápisů, povinné zdroje a soukromí; `tools/stavby.py kandidati` navrhne domy z `osoby.py`. Export (`export_web.py`)
zapíše `web/src/data/stavby.json`; na stránce Domy je u domu rozbalovací „Dějiny domu“. Úplný formát a postup
bádání: `reference/stavby.md`.

## `dokumenty.json` – rodinné fotky a dokumenty na webu
`[{"img": "foto_svatba_1919", "popis": "Svatba Jana a Josefy, Holice 1919.", "osoby": [8, 9]}]` – `popis` je na webu
vidět jako popisek, vyplň ho (stejně jako `t` u bočních příbuzných).
Obrázek ulož přes `vyrez.py dokumenty/<sken>.jpg foto_svatba_1919` (vznikne `vyrezy/` i `zdroje/`).

## `web.json` – nastavení webu
Viz `web.md`.

## Markdown poznámky
- `research_log.md` – tabulka `| # | datum | zdroj | rozsah | hledáno | výsledek | citace |`, nové řádky na konec, i negativní.
  Web ji zobrazuje jako „Výzkumný deník“. První sloupec může mít číselné nebo textové ID (např. `BA-1`, `KA-1`,
  `STR-10`); při slučování deníků zachovej původní ID nebo je uprav tak, aby byla v celém výsledném deníku jedinečná.
- `zajimavosti.md` – `## Nadpis` + text, odkazy `[Jméno](/osoba/<slug>/)`.
- `pribeh.md` – původní jediný příběh: frontmatter `title`, `lead` + kapitoly `##`; pokud `data/pribehy/` neobsahuje
  Markdown příběhy, zůstává stránka `/pribehy/` zachována. Více příběhů ukládej jako `data/pribehy/<slug>.md` s frontmatter
  `title`, `lead` a číselným `rod` (8–15); web vytvoří rozcestník `/pribehy/` a stránky `/pribehy/<slug>/`.
  Jak psát: `pribehy.md`.
- Poznámky pro Clauda v markdownu piš jako `<!-- … -->` – na web nejdou.
- `udaje_od_rodiny.md` – volný text (kdo co řekl, `st="fam"`).
- **Stránka „Co hledáme“ má tři části** – každá věc patří tam, kde se dá vyřešit, a jen jednou:
  - `otazky_pro_rodinu.md` → **Otázky pro rodinu** (co může vědět jen rodina). Oddíl `## Dokumenty doma` nahoře, pak
    `## <rod>` se stejným názvem jako v `LINES` (web je seřadí podle čísla rodu), jedna otázka na odrážku.
  - `ISSUES` → **Otevřené otázky** (rozpor nebo mezera v datech), viz výše.
  - `archivni_dotazy.md` → **Prameny mimo online matriky** (co je jen v archivu nebo na úřadě). Oddíl = archiv
    nebo úřad (`## SOA Zámrsk`, `## Matriční úřad Holice`), v odrážce `**Rod – osoba (k):** co hledáme – proč není online`.
  - Krátké věty pro rodinu, bez dat zápisu („zapsáno …“), čísel deníku a snímků (ty jsou v `research_log.md`).
    Vyřešené a zodpovězené smaž – výsledek do dat, `udaje_od_rodiny.md` nebo deníku. Pracovní poznámky do `<!-- … -->`.
    Jde na web: o žijících jen jméno a rok. `kontrola.py` hlídá tvar, data zápisu, zodpovězené položky a citlivé údaje.

## Odkazy na osoby (slug)
Slug = jméno bez diakritiky + rok, např. `jan-novak-1890`; při kolizi přidá číslo osoby. Přesné slugy po `npm run data`
v `web/src/data/site.json` (`people`). Při přejmenování osoby se slug změní – oprav odkazy v textech.
Při přečíslování předků promítni změny do `SIDE.k`, klíčů `LINES`, číselných odkazů v `web.json` i odkazů na osoby
v příbězích; potom spusť kontrolu a znovu vytvoř web.

## Import rodinného stromu (Fáze 1)
- **GEDCOM** (`.ged`, export z MyHeritage/Geni/FamilySearch): `python3 -I tools/ged_import.py dokumenty/strom.ged "Jméno Příjmení"`
  vypíše předky s čísly, všechny události a poznámky a **frontu zápisů** (nejmladší známá událost u každého předka,
  a jestli už je v archivu). `--osoby` dá kostru pro `osoby.py`. Poznámky ve stromu bývají plné rodinných historek –
  přečti je a vytěž do `udaje_od_rodiny.md`.
- Starší strom z **Brother's Keeper** (kódování ANSI a česká data „SRPEN 1945“ nástroj převede sám): místa tam bývají
  v 6. pádě („Táboře“) – do `osoby.py` je přepiš do 1. pádu. Kořenem takového stromu často nejsou uživatel, ale jeho
  děti (oba rody) – výchozí osobu proto vyber jménem.
- **Záloha stromu z MyHeritage** (ZIP se souborem `<strom>.ftb` a složkou `Photos/` – databáze, ne GEDCOM): rozbal do
  vlastní složky v `dokumenty/` (bývá velká – dej ji do `.gitignore`), pak
  `python3 -I tools/ftb_export.py <strom.ftb> dokumenty/strom.ged "Jméno Příjmení" <rok narození> pracovni/prima_linie.md <složka Photos>`.
  Vznikne GEDCOM pro `ged_import.py` (bez adres, e-mailů a telefonů) a přehled přímé linie s **původem údajů** – u každé
  osoby, ze kterých cizích stromů (Smart Match) či zdrojů její údaje přišly. Osoba bez cizí citace = `fam`, doložená jen
  cizími stromy = `mh`. V přehledu jsou i připojené skeny (opisy matrik, parte, domovské listy) – přečti je, bývají to
  nejcennější rodinné doklady.
- **Před importem cizího stromu** spusť `python3 -I tools/graf.py strom dokumenty/strom.ged "Jméno Příjmení"`: cizí stromy
  mívají dvojníky (táž osoba dvakrát, třeba u obou manželek otce) a chronologicky nemožné vazby (matce by bylo 6 let).
  Nástroj je vypíše, u dítěte ve dvou rodinách ukáže, kterou bere `ged_import.py` a která je podle dat možná, a u předka,
  který je v rodokmenu víckrát, navrhne `SAME`. Všechno ověř v matrice.
- Jméno nemusí být jedinečné: spusť nejprve výpis osob bez jména a kořen vyber podle GEDCOM ID (např. `@I42@`), ne jen podle
  shody jména. Import je podklad k posouzení, ne automatické přidání: počet osob ve vstupním stromu není počet nových
  osob projektu. Nedoloženou samostatnou rodinu automaticky nepřipojuj do `P` ani `LINES`; jako `SIDE` ji veď jen jako
  výslovně označenou stopu u konkrétního možného příbuzného, jinak ji ponech odděleně v deníku.
- Soubor `.doc` od rodiny nejdřív zkontroluj lokálně: začíná-li RTF hlavičkou `{tf`, otevři nebo převeď ho ve Wordu
  či LibreOffice. Nepoužívej online převodníky a originál ani pracovní převod neposílej na web. Originály ukládej do
  `dokumenty/originaly/` (gitem ignorované), pracovní převody do `pracovni/`; na web patří jen schválené výřezy.
- Údaje ze stromů (i Smart Match) jsou jen vodítko k zápisu – datum a číslo domu tě dovedou na stránku, ale **jména vždy
  ověř v zápisu** (skutečná chyba: „sňatek“ ze Smart Match byl jiný pár ze stejného domu).
