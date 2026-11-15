# Návrh optimalizace metodiky rodokmen-skill

Stav k 15. 11. 2026. Zadání: `analyza/audit-rodokmen-claude-code.md` (část 1). Podklady: `data/poznamky_pro_skill.md` projektu,
záznam sousedního sezení (běh orchestrátoru 14.–15. 11. 2026, 47 pomocníků) a jeho měřicí data, kód a testy větve `pracovni-prehled`.

Tento dokument je **jen návrh**. Nic z něj není implementováno ani ověřeno během. U každého zjištění je uvedeno, odkud pochází:

- **[kód]** potvrzeno čtením aktuálního kódu nebo testu (soubor a řádek),
- **[měření]** přepočítáno z dat sousedního sezení (viz 2.2),
- **[běh]** hlášení z poznámek, které jsem nezávisle neověřil,
- **[hypotéza]** úsudek, který je třeba ověřit.

Jména osob v ukázkách jsou smyšlená. Údaje z rodinného projektu tu nejsou.

## 1. Produkt, priority a systémové příčiny

### 1.1 Co je produkt

Produkt je rodinný web, který doložené výsledky bádání ukazuje přesně, úplně v daném rozsahu a všude stejně. Plugin, agenti, fronty a deník
jsou výrobní linka. Jednotkou úspěchu proto není levný běh agenta, ale **uzavřená badatelská otázka promítnutá na web**: buď doložené tvrzení
na všech stránkách, kam patří, nebo poctivě ohraničený negativní výsledek („v těchto knihách a letech není“).

### 1.2 Nepodkročitelné podmínky kvality

Varianty se porovnávají cenou až poté, co splní tyto podmínky. Kdo je nesplní, vypadává bez ohledu na cenu.

| Č. | Podmínka | Jak se pozná porušení |
|---|---|---|
| K1 | Tvrzení `doc` má důkaz, který kdokoli dohledá: svazek, snímek, výřez, přepis. | Tvrzení bez polohy důkazu neprojde zápisem. |
| K2 | Čtení, které se stane `doc`, bylo přečteno dvakrát nezávisle a obě čtení jsou uložena. | Zápis `doc` bez druhého čtení se odmítne. |
| K3 | Tvrzení je přiřazeno osobám přes jejich ID, ne jménem, a ID existuje. | Deník i výsledek s neznámou osobou se odmítnou. |
| K4 | Negativní výsledek nese prohledaný rozsah a typ pramene; mimo ten rozsah nic netvrdí. | „Nenalezeno“ bez rozsahu nebo z pramene, který hledanou roli nepokrývá, se odmítne. |
| K5 | Vyčerpaný rozpočet, nedostupný portál a nečitelný obraz jsou jiné stavy než „nenalezeno“. | Stav úkolu rozlišuje důvod; test 6 v oddíle 8. |
| K6 | Vztah se ukáže z obou stran se stejnou jistotou a stejným důkazem, pokud to nezakáže soukromí. | Kontrola webu proti nezávislé matici vztahů (oddíl 7). |
| K7 | Na web jde jen to, co odpovídá datům v okamžiku kontroly. | Brána svázaná s otiskem dat, šablon a `dist`. |
| K8 | Soukromí má přednost před úplností; opačná vazba ani vyhledávání nevyzradí skrytou osobu. | Test přístupových variant na HTML i indexech. |

### 1.3 Pět systémových příčin

Symptomy z poznámek (B1–B15, T1–T7) a z předauditu (A1–A9) se dají svést na pět příčin. Opravy jednotlivých symptomů příčiny neodstraní.

**P1. Poznání není uloženo jako adresovatelné tvrzení, ale jako text.**
Fakta osoby jsou věty v `f` a `note` (`template/data/osoby.py:11–15`), sňatek je věta „× datum Jméno“, svědci a kmotři jsou jen
ve `shrnuti` zápisu. Vazbu zápis → osoba drží jen ručně psaný seznam `r` u osoby (`export_web.py:1005, 1052`); zápis sám osoby nezná
(v projektu má 205 zápisů pole `klic, svazek, snimek, druh, datum, nazev, shrnuti, odkaz`, žádné `osoby`) **[kód, měření]**.
V `osoby.py` projektu je 422 odkazů na jinou osobu číslem v závorce uvnitř volného textu **[měření]**. Důsledek: tutéž skutečnost je třeba
zapsat ručně dvakrát až třikrát, validátor nemá co porovnat a vztah A–B se ztratí, kdykoli někdo zapíše jen jednu stranu.
Rodiče, děti, sourozenci a partneři se naopak odvozují správně z jednoho místa (`export_web.py:1097–1145`) **[kód]**; chyba je tedy
v tom, co odvozeno není.

**P2. Výstup badatele nemá strojový kontrakt a kontroluje se až po zaplacené práci.**
Výsledek je popsán slovně (`agents/researcher.md`, oddíl Result), test hlídá jen výskyt řetězce `pracovni/vysledky`
(`test_agenti_definice.py:141–143`) **[kód]**. Skutečný výsledek z běhu má osoby jako řetězce se jménem a číslem v závorce a zdroj jako
větu **[měření: `pracovni/vysledky/U-0046.json`]**. Tři nástroje pak mají tři různé představy o vstupu: `mapa.py` chce typ z výčtu
a interní ID svazku (`mapa.py:30, 92`), `denik.py` u osob kontroluje jen „seznam řetězců“ (`denik.py:103`), `fronta.py` slučuje podle typu
a překryvu osob (`fronta.py:259–263`) **[kód]**. Proto mapa odmítla 4 ze 4 výsledků a deník přijal jméno místo ID **[běh]**.

**P3. Rozhodnutí je odděleno od mechanického provedení agentem, ne nástrojem.**
Orchestrátor nesmí spustit nic, co zapisuje (`hooks/hlidac_orchestratora.py:15–17`), takže každý zápis fronty, deníku, mapy i každý commit
je nový agent. V běhu bylo 52 volání agenta: 23 fixer, 8 committer, 10 researcher, 6 verifier, 3 browser-reader, 1 analytik, 1 chybný název
**[měření]**. **31 z 52 běhů (60 %) tedy nic nečetlo ani nerozhodovalo, jen provedlo příkaz, který orchestrátor už znal.** Stály 2,21 mil. ekv
z 6,15 mil. za pomocníky (36 %) a každý vyžadoval kartu a zprávu zpět **[měření]**. Mechanická práce svěřená generování navíc chybuje:
11 zablokovaných příkazů committera, opravný řádek deníku s nesprávnými osobami **[měření, běh]**. Zároveň je to rozpor v instrukcích:
`orchestrator.md` krok 6 posílá zápis dat fixerovi, `fixer.md` má „never touch `data/` of a real project“ **[kód]**.

**P4. Stav bádání žije v historii sezení, ne v obnovitelném záznamu.**
Kontext hlavního vlákna měl medián 120 tis. a maximum 230 tis. tokenů; čtyři největší zápisy cache (208, 199, 159 a 102 tis. tokenů) přišly
po přepnutí modelu nebo po pauze **[měření]**. Když selhalo `kontext.py`, orchestrátor si stav skládal sám: `osoby.py` 5×, deník 4×,
26× Grep, 14× Glob **[měření]**. Do stejné příčiny patří i to, že vlastnosti pramene nejsou v datech (rejstřík jen ženichů → hledání nevěsty,
**[běh]**) a že vazba úkol ↔ deník ↔ osoby je vyplněna jen výjimečně: z 381 řádků deníku má `osoby` 16 a `ukol` 8 **[měření]**.

**P5. Definice hotového je rozptýlena a běh badatele neumí pokračovat.**
O „hotovo“ dnes něco říká karta, oddíl „Done when“ každého agenta, verifier (vrací `shoda/neshoda`, ačkoli první čtení nesmí vidět,
`agents/verifier.md`), pole `dod` úkolu, `rezim.json → dod` i hook nasazení **[kód]**. Badatel má jediný konec: soubor výsledku. Neúplný zápis
na okraji snímku tak znamená nový běh s novým startem a novým čtením kontextu; orchestrátor nemá v `tools:` nástroj pro pokračování
rozběhnutého pomocníka **[kód]**.

## 2. Současný tok, náklady a ztráty

### 2.1 Průchod dnes

| Přechod | Kdo rozhoduje | Spotřebuje | Vytvoří | Kde se ztrácí kvalita nebo cena |
|---|---|---|---|---|
| Otázka → úkol | orchestrátor, zapisuje fixer | historie sezení, fronty | úkol s `dod`, cenou | Vstupní fronta v projektu neexistuje, router se nevynucuje [běh]; slučování podle překryvu osob mění záměr úkolu [kód]. |
| Úkol → karta | orchestrátor | `kontext.py`, mapa knihy | volný text karty | Karta je próza; formát výsledku v ní není; pokrytí pramene není v datech. |
| Karta → čtení | researcher | karta, snímky, 4,5 tis. tokenů popisů nástrojů | snímky, výřezy | 48× `--help`, 70× grep velkých souborů, 16 celých skenů [běh]; výřezy do veřejných složek [běh]. |
| Čtení → výsledek | researcher | vlastní kontext | `pracovni/vysledky/<id>.json` bez schématu | Osoby jménem, zdroj větou; nikdo to před koncem běhu nezkontroluje. |
| Výsledek → ověření | orchestrátor, čte verifier | výřez | `shoda/neshoda` | Verifier nemůže posoudit shodu s tím, co nevidí; 13 obrázků nad 2000 px [běh]. |
| Ověření → rozhodnutí | orchestrátor | zprávy pomocníků | další karta | Jediné možnosti jsou „nový běh“ nebo „hotovo“. |
| Rozhodnutí → zápis | orchestrátor, zapisuje fixer | lístek v próze | deník, mapa, fronta, `zaznamy.json`, `osoby.py` | 23 běhů fixeru; čtyři nezávislé zápisy bez transakce; `r` a `f` ručně u každé osoby zvlášť. |
| Zápis → commit | orchestrátor, provede committer | lístek | commit | 8 běhů, 11 zamítnutých příkazů [měření]. |
| Data → web | uživatel (`aktualizuj_web.bat`), brána | data, šablony | `dist`, `pracovni/brana.json` | Hook nasazení porovná jen výsledek a verzi, ne otisk dat (`hlidac_site.py:202`) [kód]; přístupy se kontrolují slaběji než plná verze (`brana.py`) [kód]. |

### 2.2 Co běh stál

Přepočítáno z `mereni.json` sousedního sezení (144 záznamů, stav 15. 11. 9:44) a ze záznamu hlavního vlákna. Metrika je převzatá:
`ekv = vstup + 1,25 × zápis cache + 0,1 × čtení cache + 5 × výstup`. **Je to vážené číslo pro srovnání, ne účet.** Váhy odpovídají
obvyklým poměrům cen, ale nejsou přepočteny podle skutečných sazeb modelů (Opus, Sonnet a Haiku mají různé ceny, ekv je sčítá dohromady).

| Kdo | Běhů | Součet tis. ekv | Medián tis. ekv | Medián startu (tokeny) | Medián kroků | Chyby nástrojů |
|---|---|---|---|---|---|---|
| researcher (sonnet) | 10 | 3 374 | 274 | 11 297 | 26 | 17 |
| fixer (sonnet) | 13 | 1 613 | 142 | 11 800 | 12 | 5 |
| fixer (haiku) | 8 | 339 | 38 | 10 640 | 6 | 0 |
| committer (haiku) | 6 | 262 | 40 | 10 412 | 8 | 11 |
| verifier (sonnet) | 6 | 253 | 43 | 8 462 | 2 | 0 |
| browser-reader (sonnet) | 3 | 217 | 73 | 37 090 | 5 | 5 |
| failure-analyst (opus) | 1 | 89 | 89 | 11 622 | 7 | 0 |
| **pomocníci celkem** | **47** | **6 146** | | | | |
| hlavní vlákno (opus 170 tahů, sonnet 27) | 197 tahů | 4 466 | | kontext medián 120 tis. | | |

Poznámky k číslům:

- Poznámky uvádějí 10,88 mil. celkem a 4,73 mil. za orchestrátora; můj přepočet dává 10,61 a 4,47 mil. Rozdíl 2–6 % nevysvětluji
  (jiné odstranění duplicitních tahů nebo jiný okamžik měření). Řádově čísla souhlasí.
- Hlavní vlákno zahrnuje i práci, která nebyla bádáním: samotný audit tokenů, předávku sezení a 137 zpráv uživatele. Podíl „43 % na
  orchestraci“ je proto horní odhad ceny řízení bádání.
- Rozklad startu pomocníka po položkách (nástroje 4,5 tis. atd.) a ztráty cache 1,18 mil. jsem nepřepočítával **[běh]**.
- Co za to vzniklo: 20 řádků deníku (10 nalezeno, 7 nenalezeno, 3 částečně; z toho 11 opravných a jen 9 nových), 7 úkolů uzavřeno,
  13 dělení úkolů **[měření]**. Přesnější okno bez auditu (10,22 mil. ekv, hlavní vlákno 39 %) je v `analyza/baseline-2026-11-15.md`.
  Hrubě tedy **kolem 0,5 mil. ekv na jeden řádek deníku a 1,5 mil. ekv na uzavřený úkol**. Kolik z toho se dostalo na web jako nové
  tvrzení, z dat nezjistím, protože tvrzení nemají identitu (příčina P1).

### 2.3 Kam cena odchází

| Složka | Tis. ekv | Podíl | Povaha |
|---|---|---|---|
| Čtení pramenů (researcher, browser-reader) | 3 591 | 34 % | odborná práce; 217 tis. z toho bez výsledku |
| Nezávislé ověření (verifier) | 253 | 2 % | odborná práce |
| Mechanický zápis a commit (fixer, committer) | 2 214 | 21 % | provedení známého příkazu |
| Analýza selhání | 89 | 1 % | údržba |
| Řízení, rekonstrukce stavu, rozhovor s uživatelem, audit | 4 466 | 42 % | z toho ztráty cache asi 1,2 mil. [běh] |

Odborná práce, kvůli které systém existuje, je 36 % ceny. **Zbylých 64 % je řízení a přepisování známého.** To je hlavní nález
a odpovídá příčinám P3 a P4. Zkracování promptů čtenáře na tom změní málo.

### 2.4 Stav kandidátů z předauditu

| ID | Stav dnes | Důkaz |
|---|---|---|
| A1 rozpor fixer × zápis dat | trvá | `orchestrator.md` krok 6 × `fixer.md` poslední věta [kód] |
| A2 `dalsi` zapisuje, hook ho má za čtení | trvá, je to vědomé (přidělení a čerpání rozpočtu) | hook ř. 16; `fronta.py`, větev `dalsi` [kód] |
| A3 nasazení neporovnává otisk dat | trvá | `hlidac_site.py:202` [kód] |
| A4 výsledek bez schématu | trvá | `test_agenti_definice.py:141–143` [kód] |
| A5 slepý verifier vrací „shodu“ | trvá | `agents/verifier.md`, oddíl Result [kód] |
| A6 pokrytí = zmínka názvu | neověřováno znovu | [hypotéza podle předauditu] |
| A7 přístupy se kontrolují slaběji | trvá; `--site` dostane jen plná verze | `brana.py` [kód] |
| A8 „bez sítě“ × `npm ci` v testech | neověřováno znovu | [hypotéza podle předauditu] |
| drobnost: `cekajici` a `plan` hook nepustí | trvá | výčet v regulárním výrazu hooku ř. 16 [kód] |

## 3. Varianty a doporučení

### 3.1 Tři uspořádání

**V0 – dnes.** Jeden orchestrátor, který jen rozhoduje, a devět specialistů včetně fixeru a committera pro každý zápis.

**V1 – jeden řídicí agent s transakčními nástroji.** Řídicí agent smí spouštět úzké, validující zapisující skripty. Pomocníci zůstanou
jen tam, kde je potřeba čerstvý kontext (čtení obrazu) nebo nezávislost (druhé čtení). Údržba skillu běží ve stejné roli jako dnes.

**V2 – dva hlavní vstupy: badatel a metodik.** Badatel je řídicí agent z V1, ale jen pro bádání v projektu. Metodik je druhý hlavní
agent, který pracuje v repozitáři skillu nad podněty z bádání a nikdy neschvaluje běžné nálezy. Všichni ostatní jsou skrytí pomocníci
jednoho z nich.

### 3.2 Porovnání

| Hledisko | V0 dnes | V1 jeden řídicí + nástroje | V2 badatel + metodik |
|---|---|---|---|
| K1–K8 | K3, K4, K6, K7 nejsou vynuceny | vynutí nástroje | stejně jako V1 |
| Běhy agentů na uzavřený úkol (odhad z běhu: 52 volání na 7 úkolů ≈ 7) | ≈ 7 | ≈ 2–3 (čtení, ověření, případně pokračování) [hypotéza] | stejně jako V1 |
| Cena mechanického zápisu | 2,2 mil. ekv za běh | blízko nuly tokenů; zůstává cena jednoho volání nástroje | stejně jako V1 |
| Kontext řídicího agenta | bádání + fronty + údržba skillu + testy + sync | totéž, jen levnější zápisy | badatel nenese pravidla údržby, testů a syncu; metodik nenese rodinná data |
| Riziko, že změna pravidel změní rozdělanou práci | vysoké: tentýž agent mění pravidla i bádá | stejné | nízké: pravidla mají verzi, badatel ji přebírá jen mezi úkoly |
| Kdo vlastní DoD bádání | orchestrátor, ale spolurozhodují čtyři role | řídicí agent | badatel, jediný |
| Kdo vlastní DoD změny metodiky | nejasné (orchestrátor × sezení nad skillem) | nejasné | metodik + testy skillu |
| Soukromí při práci na skillu | sezení nad skillem vidí data projektu jen náhodou | stejné | metodik dostává jen technické podněty bez rodinných údajů (veřejný repozitář) |
| Údržba | 10 definic agentů | 6–7 definic | 2 hlavní + 4–5 pomocných |
| Cena přestavby | 0 | střední: kontrakt, zapisovací nástroj, hook | o málo vyšší než V1: rozdělení definice orchestrátoru na dvě, formát podnětu |

### 3.3 Doporučení: V2, postavená na jádru V1

Doporučuji **V2**. Rozhodující úspora i přesnost pocházejí z jádra V1 (kontrakt, transakční zápis, pokračování čtenáře, obnovitelný stav);
bez něj by dva hlavní agenti byli jen přejmenování. V2 k tomu přidává tři věci, které V1 nemá:

1. **Odpovídá tomu, jak se už pracuje.** Jedno sezení bádá v projektu, druhé upravuje skill, předávají si `data/poznamky_pro_skill.md`.
   Dnes je to nepsaná praxe a role orchestrátoru přitom nese oba světy (oddíly „After a skill version update“, test-runner, upstream-sync).
2. **Odděluje dvě DoD.** Bádání je hotové, když je tvrzení přijato a je na webu. Změna metodiky je hotová, když projdou testy skillu
   a projekt převzal novou verzi. Smíchání vedlo k tomu, že audit tokenů běžel uvnitř badatelského sezení a platil jeho kontext.
3. **Drží hranici soukromí.** Metodik pracuje ve veřejném repozitáři. Dostane-li jen technický podnět, nemá co vynést.

Kompromisy, které tím přijímáme:

- Uživatel musí vědět, komu co zadat. Řeší to pravidlo jedné věty: „co se týká předků → badatel v projektu; co se týká toho, jak se
  pracuje → metodik ve skillu“. Když to uživatel splete, agent úkol nepřevezme a řekne, kam patří.
- Podnět putuje souborem, ne rozhovorem; oprava nástroje tedy není okamžitá. Je to záměr: badatel mezitím použije popsaný obchvat
  a nezmění pravidla za běhu.
- Badatel dostává oprávnění spouštět zapisující nástroje. Je to větší moc než dnes; ohraničuje ji seznam nástrojů v hooku, validace vstupu
  a auditní stopa (oddíl 4.4). **Je to první rozhodnutí, které musí udělat uživatel** (oddíl 10.4).

Kdy by V2 nedávala smysl: kdyby projekt i skill spravovala jedna osoba v jednom sezení a skill se neměnil. To zde neplatí.

### 3.4 Role v doporučené variantě

| Role | Druh | Kde běží | Model | Dělá | Nedělá |
|---|---|---|---|---|---|
| **badatel** | hlavní vstup | projekt | jeden po celé sezení (rozhodnutí uživatele) | plánuje, vybírá pramen, zadává čtení, hodnotí důkazy, rozhoduje o pokračování a o přijetí, spouští zapisovací nástroje | nečte snímky, neupravuje nástroje ani pravidla |
| čtenář | skrytý pomocník | projekt | sonnet | přečte zadaný rozsah pramene, vrátí nález podle kontraktu; lze v něm pokračovat | nezapisuje do `data/`, neurčuje identitu, nezná fronty |
| čtenář v prohlížeči | skrytý, podmíněný | projekt | sonnet | totéž na portálech se zákazem skriptů přes `tools/prohlizec.py` | spouští se jen po úspěšné kontrole prostředí skriptem |
| ověřovatel | skrytý pomocník | projekt | sonnet | druhé čtení výřezu naslepo, vrací vlastní přepis po polích | neposuzuje shodu, identitu ani DoD |
| **metodik** | hlavní vstup | repozitář skillu | podle velikosti změny | posuzuje podněty, mění pravidla, kontrakty, nástroje, testy; vydává verzi | nebádá, nečte rodinná data |
| test-runner, test-author, upstream-sync | skrytí pomocníci metodika | skill | haiku/sonnet | jako dnes | |
| fixer | skrytý pomocník metodika | skill | sonnet | úprava kódu podle lístku s regresním testem | **v bádání se nepoužívá** |

Zrušené role v bádání: **committer** (nahradí nástroj), **fixer pro zápis dat** (nahradí nástroj), **failure-analyst v projektu** (selhání
nástroje je podnět pro metodika). Každá další role by musela ukázat, že potřebuje čerstvý kontext nebo nezávislost; jinak je to nástroj.

Kdy se pomocník nevyplatí: čtení jednoho už staženého a oříznutého výřezu může ověřovatel zvládnout za 43 tis. ekv; zakládat kvůli tomu
čtenáře s plným startem smysl nemá. Naopak badatel nikdy nečte obraz sám: jeden celý sken v jeho kontextu se platí v každém dalším tahu.

## 4. Role, vlastníci DoD, rozhodovací pravidla a stavy

### 4.1 Rozhodovací tabulka

| Rozhodnutí | Kdo | Kdy | Na základě čeho | Kdo provede | Jak se ověří |
|---|---|---|---|---|---|
| Konec jednoho běhu čtenáře | čtenář | splnil rozsah zadání, nebo narazil na strop kroků, nebo zjistil překážku | zadání (`rozsah`, `strop`) | čtenář zapíše nález se stavem běhu | `vysledek.py over` (schéma, rozsah ⊆ zadání) |
| Rozšíření rozsahu (sousední strana, další svazek) | badatel | nález má `chybi` nebo `navrh_dalsiho_kroku` | nález + rozpočet úkolu | badatel pošle pokračování | čerpání se připíše témuž úkolu |
| Přijatelnost čtení | nástroj porovnání | existují dvě čtení téhož výřezu | první a druhý přepis po polích | `vysledek.py porovnej` | shoda polí → `doc` možné; neshoda → nejistota zůstává zapsaná |
| Přijatelnost tvrzení a identity osoby | **badatel** | po porovnání čtení | pravidla R-CONF, R-ID, nález, karta osoby | badatel sestaví rozhodnutí | validátor: ID osob existují, role odpovídají druhu zápisu, data nejsou v rozporu s životem osoby |
| Splnění badatelského úkolu (DoD) | **badatel** | po přijetí nebo po vyčerpání rozsahu | `dod` úkolu zapsané při směrování | `zapis_vysledku.py` uzavře úkol | nástroj odmítne „hotovo“, když stav nálezu `dod` neodpovídá |
| Technická způsobilost k uložení | nástroj | při každém zápisu | schéma, vazby, pokrytí pramene | `zapis_vysledku.py` | odmítnutí s přesným důvodem, nic se nezapíše |
| Způsobilost k publikaci | brána | před nasazením | otisk dat + šablon + `dist`, kontroly webu | `tools/brana.py`, hook nasazení | test 12 |
| Skutečné rozhodnutí člověka | uživatel | dva rovnocenní kandidáti, soukromí, cokoli ven, cena XL | lístek rozhodnutí s možnostmi | badatel připraví | fronta rozhodnutí, audit před zobrazením (už existuje) |
| Změna pravidla, kontraktu, nástroje | **metodik** | podnět se opakuje nebo ohrožuje K1–K8 | podnět + test, který chybu vyvolá | pomocníci metodika | testy skillu; projekt verzi převezme vědomě |

Jeden vlastník DoD bádání je badatel. Čtenář nerozhoduje, zda je úkol hotov, jen zda dočetl zadaný rozsah. Ověřovatel nerozhoduje nic.
Nástroj může zápis odmítnout, ale tím neříká nic o genealogii, jen o integritě.

### 4.2 Stavy úkolu a přechody

| Stav nálezu | Význam | Dovolené další kroky |
|---|---|---|
| `nalezeno` | cílový zápis přečten | ověřit naslepo → přijmout nebo zapsat rozpor |
| `částečně` | zápis přečten zčásti, je známo, co chybí a kde to nejspíš je | **pokračovat ve stejném běhu**; jinak nový běh s pokračovacím balíčkem |
| `nečitelné` | obraz existuje, čtení nelze | jiný výřez nebo jiné rozlišení; jiný pramen; nikdy „nenalezeno“ |
| `nenalezeno v rozsahu` | celý zadaný rozsah přečten, pramen hledanou roli pokrývá | uzavřít negativně v rozsahu; nebo vyžádat další pramen |
| `nedostupné` | portál selhal nebo je zakázán | `fronta.py selhani`; pozastavit |
| `rozpočet` | strop kroků nebo ceny dosažen před koncem rozsahu | pokračovat se schválením badatele (do prahu XL), jinak rozhodnutí uživatele |
| `vyvráceno` | pramen dokládá opak | zapsat tvrzení s rozporem; přezkoumat navazující tvrzení |
| `chyba prostředí` | nástroj selhal (cesta, alias, zámek souboru) | podnět metodikovi; úkol se vrací neotevřený, cena se účtuje zvlášť |

Pravidla přechodů:

- `rozpočet`, `nedostupné`, `nečitelné` a `chyba prostředí` **nikdy** nevedou do „hotovo“ ani do „nenalezeno“.
- „Nenalezeno v rozsahu“ lze zapsat jen s výčtem svazků, let a snímků a jen když `svazky.json` říká, že pramen hledanou roli obsahuje.
- Pokračování čerpá rozpočet téhož úkolu; nový úkol vzniká, jen když se mění otázka, ne když se mění strana.

### 4.3 Povinný scénář: neúplný zápis na okraji snímku

1. Čtenář čte snímek 54, řádek 7. Zápis křtu pokračuje na protější straně (kmotři). Vrátí nález `částečně` s tím, co přečetl, s polem
   `chybi: ["kmotři", "poznámka o legitimaci"]` a s návrhem `{"typ": "sousední strana", "snimek": 55, "duvod": "řádek pokračuje vpravo"}`.
   Soubor nálezu projde `vysledek.py over`, čtenář skončí tah a vrátí badateli tři řádky a cestu k souboru.
2. Badatel nález nečte celý; `vysledek.py souhrn <id>` mu dá stav, chybějící pole, návrh a dosavadní čerpání.
3. Badatel rozhodne „pokračuj na snímku 55“. Rozšíření autorizuje on, protože zůstává uvnitř `dod` úkolu a pod prahem ceny. Zapíše to
   jedním voláním `fronta.py uprav <id> --rozsah +55` (auditní stopa v `ukoly_historie.jsonl`).
4. **Pokračování:** badatel pošle témuž čtenáři zprávu „pokračuj: snímek 55, řádek 7, pole kmotři a poznámka“. Čtenář má snímek 54,
   řádek i písařovu ruku v kontextu; platí jen nové tokeny a čtení cache. Nález se doplní (`cast: 2`), ne přepíše.
5. Když pokračování není možné (pomocník skončil, cache vypršela, jiné sezení), badatel založí nový běh s **pokračovacím balíčkem**:
   zadání + cesta k nálezu části 1 + výřez konce řádku ze snímku 54. Nový čtenář nezačíná od rejstříku.
6. DoD se vyhodnotí až po části 2 a po slepém ověření spojeného řádku. Do té doby je úkol `probíhá`, ne `částečně hotovo`.

Co je o platformě ověřeno: popis nástroje `Agent` v tomto prostředí uvádí, že v dříve spuštěném pomocníkovi lze pokračovat zprávou
(`SendMessage`) se zachovaným kontextem. Co ověřeno není: zda to funguje pro agenta pluginu spuštěného jako hlavní vlákno s vlastním
seznamem `tools:` (dnes tam `SendMessage` není), jak dlouho po skončení tahu a za jakou cenu cache **[hypotéza; první pokus etapy E3]**.
Bez toho ověření platí bod 5 jako základní cesta.

Srovnání: nový agent stojí start 11 tis. tokenů + znovunačtení pravidel + nové stažení a orientaci na stránce; z běhu víme, že
nevhodný výřez vyvolal dva další běhy za 286 tis. ekv **[běh]**. Pokračování stojí řádově cenu jednoho až tří tahů **[hypotéza]**.

### 4.4 Skript, agent, člověk

| Operace | Dnes | Návrh | Proč |
|---|---|---|---|
| Zápis fronty (přidat, směrovat, rozdělit, hotovo, selhání) | fixer | badatel volá `fronta.py` přímo | deterministické, validované, s historií |
| Zápis výsledku (deník + mapa + tvrzení + úkol) | fixer, čtyři příkazy | jeden `zapis_vysledku.py <rozhodnuti.json>` | jedna transakce, idempotentní klíč |
| Commit | committer | `tools/commit.py <ukol>`: soubory z historie úkolu, pevný tvar zprávy, kontrola větve | žádné rozhodování; 11 zamítnutí odpadne |
| Nový záznam do `zaznamy.json`, přepis | fixer | `zapis.py` voláním badatele z rozhodnutí | data už jsou ve strukturovaném nálezu |
| Úprava volného textu `note`, příběhu, zajímavosti | fixer | zůstává agent (badatel sám, krátký text) | formulace je úsudek |
| Čtení rukopisu, výběr pramene, identita | agent | agent | není deterministické |
| Cokoli ven (dotaz archivu, rodině, nasazení, push) | člověk | člověk | beze změny |

Oprávnění badatele v hooku: výčet nástrojů a podpříkazů, vstup jen ze souboru v `pracovni/` (žádný text z příkazové řádky do dat),
jeden příkaz bez řetězení. Každý zapisovací nástroj: nejdřív validace všeho, pak zápis; při odmítnutí nulová změna a strojově čitelný
důvod; záznam do historie úkolu, kdo a kterým nástrojem. Neomezený `Edit` do `data/` badatel nedostane; chrání to dál `hlidac_zapisu.py`.

Technická chyba prostředí (alias `rm -iv`, `find` přes OneDrive, alias `python3` ze Store) není chyba bádání: nástroj ji vrátí vlastním
návratovým kódem, úkol se nezmění a vznikne podnět. Automatické `rm -f` řešením není; pomocníci mazat nemají co.

## 5. Kontext jako rozhraní

### 5.1 Matice kontextu

| Role a fáze | Povinné minimum | Podmíněně | Zakázáno | Zdroj a formát | Orientační velikost | Platnost |
|---|---|---|---|---|---|---|
| badatel, start sezení | `stav.py`: větev, verze pravidel, otevřené úkoly po frontách, rozpracované úkoly s posledním krokem, rozpočet okna | seznam rozhodnutí; podněty čekající na převzetí | celé `osoby.py`, deník, `research_log.md`, snímky | výstup skriptu, text | do 1 500 tokenů | do další změny fronty |
| badatel, plán úkolu | karta úkolu (`dod`, osoby ID, rozsah, cena), karta osob z `kontext.py`, pokrytí pramene ze `svazky.json`, rada mapy knihy | pravidla R-ID, R-NEG jen když jsou kandidáti nebo hrozí negativní závěr | zdrojové kódy nástrojů | `kontext.py --ukol U-…` (jeden příkaz) | 1–3 tis. tokenů | do uzavření úkolu |
| badatel, po nálezu | souhrn nálezu: stav, chybějící pole, rozpory, rozsah, návrh, čerpání, cesta | plný nález jen při rozporu | výřezy a skeny | `vysledek.py souhrn` | do 300 tokenů na nález | trvale v souboru |
| čtenář | zadání v1 (otázka, osoby s ID a rozlišovacími znaky, svazek s interním ID, rozsah, co vrátit, strop, formát nálezu s jedním vyplněným příkladem, přesné příkazy nástrojů) | pravidla R-BOOK při převodu folia; R-NEG při negativním závěru | fronty, deník, jiné osoby, pravidla publikace a commitu, `CLAUDE.md` projektu o nasazení | soubor `pracovni/zadani/<id>.json` + krátká zpráva | 800–1 500 tokenů zadání | jeden úkol |
| ověřovatel | jeden výřez, otázka po polích, jazyk a typ formuláře | abeceda písma (kurent), když je v pravidlech | první přepis, jméno hledané osoby, karta osoby | zpráva + obrázek | do 300 tokenů textu | jedno čtení |
| metodik | podnět (symptom, důkaz, dopad, četnost), dotčený kontrakt, testy | měřicí data | rodinná data, jména | `analyza/podnety/*.md` | podle změny | do vydání verze |

Zásady:

- **Start nese jen to, co je potřeba vždy.** Vše ostatní je soubor, na který zadání ukazuje. Pravidla se nenačítají přes `skills:` celá,
  ale tématem v balíčku (`kontext.py` to už umí).
- **Souhrn nesmí zahodit**: nejistotu, rozpor, prohledaný rozsah, identifikátory a návrh dalšího kroku. Proto ho dělá skript z polí
  nálezu, ne agent vlastními slovy.
- **Zkrácení nesmí vést k novému čtení.** Co čtenář viděl, je v nálezu (`stranky`) a v mapě knihy; další běh začíná odtud.
- Limit znaků v `kontext.py` zůstává pojistkou proti chybě, ne cílem. Limity 800/600 znaků, 12 kroků, 80 tis. tokenů a 55 minut
  z poznámek beru jako **výchozí hodnoty k měření** (oddíl 8.3), ne jako pravidla. Strop kroků čtenáře má vyvolat stav `rozpočet`
  s dílčím nálezem, nikdy ukončení bez výsledku.

### 5.2 Co se dědí a co s tím

| Položka startu | Dnes [běh] | Návrh | Co nelze odebrat |
|---|---|---|---|
| Popisy nástrojů | 4,5 tis.; browser-reader 37 tis. (chybí `tools:`) | výslovný `tools:` u každé role; čtenář `Read, Bash, Write`, ověřovatel `Read` | nástroje, které role opravdu volá |
| `skills: rodokmen-agents` | 1,5 tis. u všech | zrušit u ověřovatele a pomocníků metodika; čtenář dostane pravidla tématem v zadání | u badatele zůstává (tabulka pravidel) |
| `CLAUDE.md` projektu a paměť | 1,3 tis. u všech | pokyny k nasazení a Netlify přesunout do souboru, na který `CLAUDE.md` jen odkazuje | zákazy archivů a soukromí |
| Stav gitu | 0,5 tis. | pomocníci ho nepotřebují; zda jde vypnout, je třeba ověřit [hypotéza] | |
| Konektor dokumentů (od 2. kroku asi 1 tis.) | u všech | vypnout pro projekt, pokud to nastavení dovolí [hypotéza, rozhodnutí uživatele] | |
| Karta | 0,9 tis. | zadání souborem; ve zprávě jen cesta a jedna věta | |

Úspora na startu je malá proti P3 a P4: 47 pomocníků × asi 5 tis. ušetřených tokenů je čtvrt milionu tokenů zápisu cache, tedy kolem
0,3 mil. ekv z 10,6 mil. Stojí za to, ale až po odstranění zbytečných běhů; ty ušetří celý start, ne jeho polovinu.

### 5.3 Velké snímky

Dvě různé potřeby, dva různé obrazy:

- **Orientační pohled** (kde na straně je řádek, jaký je to typ stránky): zmenšenina celé strany. Smí ji vidět jen čtenář, nikdy není
  důkazem a nikdy z ní nevzniká přepis.
- **Důkazní čtení**: výřez jednoho záznamu v plném rozlišení. Řádek širší než limit se dělí na díly s překryvem (aby slovo na švu bylo
  celé aspoň v jednom dílu) a každý díl nese souřadnice ve zdrojovém snímku a pořadí. Ověřovatel dostává díly téhož řádku v jednom
  zadání, ne tři řádky v jednom obrázku.

Kontrolu vhodnosti dělá nástroj před předáním (`vyrez.py` vrátí rozměry a odmítne výřez, který by se při čtení zmenšil); badatel ani
ověřovatel ji nemají hádat. Hodnota 2000 px je vlastnost prostředí k ověření, ne pravidlo metodiky.

### 5.4 Sezení, cache, předávka, obnova

- **Jeden model po celé sezení badatele.** Přepnutí modelu zahodí cache; v běhu to byly čtyři zápisy po 100–208 tis. tokenech **[měření]**.
  Těžší úsudek se řeší pomocníkem s vyšším modelem, ne přepnutím hlavního vlákna.
- **Sezení se dá kdykoli zahodit.** Po každém zápisu je stav v souborech: fronta, historie úkolu, nález, rozhodnutí, deník. `stav.py`
  ho složí bez historie chatu. Předávka do `STAV.md` pak není ruční práce agenta, ale výpis.
- **Kdy začít nové sezení** je pravidlo k měření: po uzavřeném úkolu, když kontext přesáhne zvolenou mez, nebo po pauze delší než
  platnost cache. Práh 80 tis. tokenů a 55 minut z poznámek je rozumný první odhad; správnou hodnotu určí porovnání ceny obnovy
  (`stav.py` + karta úkolu, odhadem 3–5 tis. tokenů) s cenou tahu ve velkém kontextu.
- **Chybějící soubor nebo cesta** (např. `pracovni/.plugin_root`): nástroj skončí srozumitelnou chybou a kódem „prostředí“; badatel
  nezačne číst velké soubory sám. To je pravidlo role i hooku (čtení `osoby.py` a deníku celého badateli zakázat, nabídnout `kontext.py`).

## 6. Kontrakty

Všechny soubory nesou `"schema": "<název>/1"`. Schémata jsou jeden soubor ve skillu (`skills/rodokmen-agents/schemata/`), ze kterého čerpá
validátor, definice rolí i testy. Názvy polí česky a bez diakritiky jako ve zbytku dat. ID osoby je Kekulého číslo nebo zkratka z `RODINA`;
svazek je interní ID portálu (signatura je jen popisek).

### 6.1 Zadání (badatel → čtenář)

```json
{
  "schema": "zadani/1",
  "ukol": "U-0101",
  "otazka": "Najdi křest osoby 88 a přečti rodiče a kmotry.",
  "osoby": [
    {"id": 88, "jmeno": "Josef Vzorný", "role": "křtěnec", "znaky": "* asi 1812, otec chalupník, Lhota čp. 5"},
    {"id": 176, "jmeno": "Jan Vzorný", "role": "otec", "znaky": "† 1840 Lhota"}
  ],
  "nezamenit_s": [{"jmeno": "Josef Vzorný", "znaky": "* 1809, otec mlynář, Lhota čp. 12", "id": "josef-vzorny-1809"}],
  "pramen": {"portal": "aron", "svazek": "0a1b2c3d", "signatura": "712", "druh": "N", "pokryva": {"role": ["křtěnec"], "roky": [1800, 1825]}},
  "rozsah": {"snimky": [40, 52], "duvod": "mapa knihy: rok 1812 kolem snímku 46"},
  "vratit": ["datum", "misto", "cp", "otec", "matka", "kmotri"],
  "strop": {"kroku": 12, "snimku": 12},
  "dod_behu": "Rozsah přečten, nebo cílový zápis nalezen a přečten celý.",
  "pravidla": ["R-NEG-001", "R-BOOK-002"],
  "prikazy": {
    "stahni": "python -I -X utf8 tools/slusne.py tools/aron_img.py 0a1b2c3d <snimek>",
    "vyrez": "python -I -X utf8 tools/vyrez.py <obraz> <klic> x0,y0,x1,y1 --out pracovni/vysledky/U-0101_vyrezy",
    "over": "python -I -X utf8 tools/vysledek.py over pracovni/vysledky/U-0101.json"
  }
}
```

Zadání validuje nástroj dřív, než se pomocník spustí: osoby existují, svazek je ve `svazky.json`, `pokryva` obsahuje hledanou roli
(jinak se zadání odmítne: „rejstřík 759 vede jen ženichy“), rozsah leží ve svazku.

### 6.2 Dílčí nález (čtenář → badatel)

```json
{
  "schema": "nalez/1",
  "ukol": "U-0101",
  "cast": 1,
  "stav": "částečně",
  "stav_behu": "dočteno",
  "cteni": [{
    "id": "c1",
    "zdroj": {"portal": "aron", "svazek": "0a1b2c3d", "snimek": 46, "strana": "fol. 23v", "radek": 7},
    "vyrez": "pracovni/vysledky/U-0101_vyrezy/c1_a.jpg",
    "souradnice": [112, 1480, 2890, 1655],
    "doslova": {"datum": "17. Martii 1812", "ditě": "Josephus", "otec": "Joannes Wzorny chalupnik", "matka": "Anna nata Prziklad", "cp": "5"},
    "normalizace": {"datum": "1812-03-17", "ditě": "Josef", "otec": "Jan Vzorný", "matka": "Anna Příkladová"},
    "nejistota": {"matka": "příjmení čteno z konce řádku, poslední slabika v hřbetu knihy"},
    "chybi": ["kmotri"]
  }],
  "kandidati": [{"osoba": 88, "cteni": "c1", "pro": ["jméno", "rok", "čp. 5", "otec chalupník"], "proti": []}],
  "prohledano": [{"svazek": "0a1b2c3d", "snimky": [44, 46], "roky": [1811, 1812], "uplne": false}],
  "stranky": [{"portal": "aron", "svazek": "0a1b2c3d", "snimek": 46, "typ": "zápisy", "od": "1812-02", "do": "1812-04", "kvalita": "dobrá"}],
  "navrh_dalsiho_kroku": {"typ": "sousední strana", "snimek": 47, "duvod": "řádek 7 pokračuje na pravé straně (kmotři)"},
  "cerpani": {"kroku": 6, "snimku": 3}
}
```

Čtenář vrací **pozorování** (`doslova`), **normalizaci** a **kandidáty** s důvody pro a proti. Identitu ani tvrzení nezapisuje.
`vysledek.py over` spouští čtenář sám před koncem; chybu formátu opraví ve svém běhu za cenu jednoho tahu, ne za cenu nového běhu
po odmítnutí mapou.

### 6.3 Pokračování (badatel → tentýž čtenář)

```json
{
  "schema": "pokracovani/1",
  "ukol": "U-0101",
  "navazuje_na": {"nalez": "pracovni/vysledky/U-0101.json", "cteni": "c1"},
  "rozsireni": {"snimky": [47, 47], "radek": 7, "vratit": ["kmotri"]},
  "schvalil": "badatel",
  "duvod": "v rámci DoD úkolu; cena úkolu zůstává M",
  "strop": {"kroku": 4, "snimku": 1}
}
```

### 6.4 Ověření (ověřovatel → badatel) a porovnání

```json
{
  "schema": "overeni/1",
  "ukol": "U-0101",
  "cteni": "c1",
  "vyrezy": ["pracovni/vysledky/U-0101_vyrezy/c1_a.jpg", "pracovni/vysledky/U-0101_vyrezy/c1_b.jpg"],
  "doslova": {"datum": "17. Martii 1812", "ditě": "Josephus", "otec": "Joannes Wzorny", "matka": "Anna nata Prziklad?", "cp": "5"},
  "nejistota": {"matka": "konec příjmení nečitelný"},
  "necitelne": []
}
```

Ověřovatel nevrací „shodu“. `vysledek.py porovnej U-0101 c1` vydá po polích `shoda`, `neshoda`, `jen první`, `jen druhé` a u každého
obě znění. Neshoda se nezahazuje: do tvrzení jde s nejistotou a s oběma přepisy.

### 6.5 Rozhodnutí a přijaté tvrzení (badatel → `zapis_vysledku.py`)

```json
{
  "schema": "rozhodnuti/1",
  "ukol": "U-0101",
  "vysledek": "nalezeno",
  "dod_splneno": true,
  "zaznam": {
    "klic": "lhota_krest_josef_vzorny_1812",
    "druh": "krest", "datum": "1812-03-17",
    "zdroj": {"portal": "aron", "svazek": "0a1b2c3d", "snimek": 46, "strana": "fol. 23v"},
    "ucastnici": [
      {"osoba": 88, "role": "křtěnec"},
      {"osoba": 176, "role": "otec"},
      {"osoba": 177, "role": "matka"},
      {"jmeno": "Václav Ukázka", "role": "kmotr"}
    ]
  },
  "tvrzeni": [
    {"id": "T-0412", "typ": "narozeni", "osoba": 88, "hodnota": {"datum": "1812-03-17", "misto": "Lhota", "cp": "5"},
     "jistota": "doc", "dukaz": ["c1"], "overeno": "overeni/U-0101/c1"},
    {"id": "T-0413", "typ": "rodic", "rodic": 176, "dite": 88, "jistota": "doc", "dukaz": ["c1"]},
    {"id": "T-0414", "typ": "rodic", "rodic": 177, "dite": 88, "jistota": "prob", "dukaz": ["c1"],
     "nejistota": "příjmení matky: druhé čtení konec nepotvrdilo", "nahrazuje": null}
  ],
  "identita": {"osoba": 88, "proc": "jméno, rok, čp. 5 a povolání otce; jmenovec z čp. 12 má otce mlynáře", "vylouceno": ["josef-vzorny-1809"]},
  "denik": {"nalez": "Křest Josefa Vzorného 17. 3. 1812 ve Lhotě čp. 5.", "rozsah": "kniha N 1800–1825, snímky 44–47"},
  "navazujici": [{"otazka": "Kdo byl kmotr Václav Ukázka?", "osoby": [88], "cena": "S"}]
}
```

Co nástroj udělá jedním voláním, v tomto pořadí a buď celé, nebo vůbec:

1. Ověří schéma, existenci osob, že `ucastnici` odpovídají druhu zápisu, že každé tvrzení `doc` má ověřené čtení (K2), že data neodporují
   životu osob (stejné kontroly jako `kontrola.py`), že úkol existuje a jeho `dod` odpovídá výsledku.
2. Spočte klíč `ukol + cast + otisk obsahu`. Je-li už zapsán, skončí „už zapsáno“ bez změny (idempotence).
3. Zapíše záznam, tvrzení, řádek deníku (s `ukol`, `osoby`, `snimky`, `model`), strany do mapy knihy, uzavře úkol a navazující otázky pošle
   do vstupní fronty.
4. Při selhání uprostřed vrátí zapsané soubory do stavu před voláním (zápis přes dočasné soubory a přejmenování na konci) a nechá
   značku `pracovni/zapis_<klic>.rozpracovano`, kterou `stav.py` ukáže.

### 6.6 Životní cyklus tvrzení a vztahu

- Tvrzení má stálé ID, typ, účastníky s ID, jistotu, důkaz a původ (úkol, nástroj, model, datum).
- **Aktualizace** = nové tvrzení s `nahrazuje: T-…`; staré zůstává v souboru jako nahrazené (stejně jako `--opravuje` v deníku).
- **Zpochybnění** = tvrzení typu `rozpor` s odkazem na obě strany; na webu se u obou osob ukáže otevřená otázka.
- **Vztah** je jedno tvrzení se dvěma účastníky a rolemi. Zapisuje se jednou. Oba pohledy z něj odvozuje export.
- **Slučování a dělení úkolů:** úkol má identitu `otázka + cílová osoba + role + pramen`. Překryv osob ke sloučení nestačí; sloučit lze
  jen úkoly se stejnou otázkou. Při dělení každé dítě dostává vlastní osoby, rozsah, cenu a `dod` výslovně; nic se nedědí mlčky a nástroj
  chybějící pole odmítne. Původ (`z: U-…`) zůstává v historii.

### 6.7 Kde tvrzení uložit: tři možnosti

| Možnost | Co znamená | Pro | Proti |
|---|---|---|---|
| a) nic neměnit, přidat kontroly | `kontrola.py` hlídá, že zápis sňatku je v `r` obou manželů apod. | nejlevnější, žádná migrace | kontrola neví, kdo jsou účastníci, dokud to není v datech; zůstává ruční dvojí zápis |
| **b) účastníci u zápisu + deník tvrzení** | `zaznamy.json` dostane `ucastnici` (ID, role); nové `data/tvrzeni.jsonl`; `r` u osoby se odvozuje, `f` zůstává jako čtený text | odstraní dvojí zápis vazby zápis ↔ osoba; dává validátoru i webu fakta; `osoby.py` zůstává slučitelný s originálem | migrace 205 zápisů (účastníky lze z velké části odvodit z dnešních `r` a druhu zápisu, zbytek ručně); dvě místa pravdy pro texty `f`, dokud se negenerují |
| c) tvrzení jako jediný zdroj, `osoby.py` generovaný | vše se odvozuje z tvrzení | čistý model | velká migrace, rozchod s originálem, ztráta ručně psaných formulací |

Doporučuji **b)**. Řeší příčinu P1 tam, kde dnes vzniká škoda (vazby a role), a nechává texty lidem. Možnost c) ať zůstane otevřená,
až bude vidět, kolik faktů v `f` se dá generovat bez ztráty čitelnosti.

## 7. Web: úplnost a konzistence

### 7.1 Scénář A–B: kde se vztah dnes může ztratit

| Druh vazby | Kde je dnes | Odvozuje se opačný pohled? | Riziko |
|---|---|---|---|
| rodič – dítě | Kekulého číslo, `otec`/`matka` v `RODINA` | ano (`export_web.py:1097–1124`) [kód] | nízké |
| sourozenci | odvozeno z rodičů | ano | nízké |
| partneři | `PARTNERI`, `partner`, společné dítě | ano (`export_web.py:1127–1145`) [kód] | střední: sňatek zapsaný jen větou „× …“ v `f` jedné osoby se u druhé neukáže |
| zápis – osoba | ruční `r` u každé osoby | **ne** | vysoké: zápis sňatku nebo křtu chybí u druhého účastníka |
| svědek, kmotr, kmotřenec | jen text `shrnuti` nebo `note` | **ne** | vysoké: vazba mezi rody se na webu neobjeví vůbec |
| příbuzný v `SIDE` | věta u předka `k` | **ne**, osoba nemá stránku | střední |
| zmínka „(číslo)“ v poznámce | volný text, 422 výskytů | **ne** | střední: stránka B o zmínce neví |
| dokument – osoby | pole `osoby` v dokumentech | ano [kód] | nízké |
| hypotéza | `HYPOTEZY` u rodu | jen u rodu | hypotéza se nesmí u osoby změnit v jistotu |
| cokoli × soukromí | filtr skrytých osob | filtr může odebrat jednu stranu | vazba na skrytou osobu nesmí prozradit jméno z druhé strany |

Postup hledání konkrétní chyby A–B (návrh diagnostiky, nevykonáno): 1. je vztah v datech jako struktura, nebo jen ve větě? 2. je-li
struktura, je v exportním JSON u obou osob? 3. je-li v JSON, vykreslí ho šablona u obou? 4. odebral ho filtr přístupu? Podle kódu je
nejpravděpodobnější odpověď hned první: vztah je věta.

### 7.2 Obecné pravidlo

**Každý vztah je jedno tvrzení se dvěma účastníky a rolemi; stránky jsou projekce.** Projekce je tabulka, ne kód rozesetý v šablonách:

| Tvrzení | U účastníka 1 | U účastníka 2 |
|---|---|---|
| `rodic(A, B)` | A: „dítě: B“ | B: „otec/matka: A“ |
| `partner(A, B, od, do)` | A: „manžel/ka: B“ | B: „manžel/ka: A“ |
| `svedek(A, zapis)` | A: „svědek při sňatku X a Y“ | X, Y: „svědek: A“ |
| `kmotr(A, B)` | A: „kmotr dítěte B“ | B: „kmotr: A“ |
| `totozny?(A, B)` (hypotéza) | A: „možná totožný s B“ | B: „možná totožný s A“ |

Jistota, zdroj a časová platnost patří tvrzení, proto jsou z obou stran stejné. Hypotetický vztah zůstává hypotetický v obou pohledech.
Dvě tvrzení mezi týmiž osobami (kmotr a zároveň švagr) jsou dva řádky, neslévají se.

### 7.3 Matice informací

| Typ informace | Autoritativní data | Povinné pohledy | Pravidlo zobrazení | Přípustná výjimka | Test |
|---|---|---|---|---|---|
| rodič, dítě, sourozenec | čísla a `otec`/`matka` | osoba (obě), rodina, strom, vějíř, rod | odvozeno, s jistotou slabší osoby | skrytá osoba: „žijící“ bez jména podle přístupu | matice vztahů proti HTML |
| partnerství | `PARTNERI` nebo tvrzení `partner` | osoba (obě), rodina, osa | datum a místo jen z tvrzení | soukromí | sňatek u A ⇒ sňatek u B se stejným datem |
| účast v zápisu | `ucastnici` zápisu | osoba (všichni s ID), zápis, zdroj | role u jména | účastník bez ID jen na stránce zápisu | každý účastník s ID má zápis na své stránce |
| svědek, kmotr | tvrzení | osoba (obě), zápis | role a rok | soukromí | opačný řádek existuje |
| událost (narození, úmrtí) | tvrzení nebo `f` | osoba, osa, mapa, statistiky | jedno datum všude | „asi“ zůstává „asi“ | tatáž hodnota na všech stránkách |
| jméno a varianty | `n` + tvrzení o variantě | osoba, jména, hledání | hlavní tvar jeden | | index hledání obsahuje varianty jen viditelných osob |
| místo | fakta se značkami, `mista.json` | osoba, místo, mapa | stejný název | | odkaz místo ↔ osoba oboustranný |
| zdroj | `svazky.json`, zápis | zápis, zdroj, osoba | signatura a odkaz | portál bez veřejného odkazu | každý zápis má zdroj, každý zdroj své zápisy |
| rozpor, otevřená otázka | `ISSUES`, tvrzení `rozpor` | osoba (všechny dotčené), Co hledáme | bez procesních údajů | vyřešené skryté | otázka o A a B je u obou |
| negativní výsledek | deník | deník, osoba (stav hledání) | s rozsahem | | „nenalezeno“ bez rozsahu se nevykreslí |

### 7.4 Kontroly

- **Nezávislý orákl.** Očekávání nesmí počítat `export_web.py`. Navrhuji malý ukázkový projekt psaný ručně (osm osob, dva rody, jeden
  druhý sňatek, jeden kmotr z druhého rodu, jedna žijící osoba, jedna hypotéza) a k němu **ručně psanou matici** „na stránce X musí být
  odkaz na Y s textem role Z“. Test sestaví web a čte hotové HTML.
- **Obecná kontrola symetrie** nad skutečnými daty: z tvrzení a účastníků (ne z exportu) se vygenerují dvojice (stránka, očekávaný odkaz)
  a ověří se v `dist`. Patří do `kontrola_webu.py`, a tedy do brány.
- **Mutační zkouška testu** (jednorázově při zavedení): úmyslně odebrat opačný řádek v šabloně a ukázat, že test zčervená. Bez toho
  test jen existuje.
- **Přístupy:** každá přístupová varianta se kontroluje proti své vlastní očekávané matici; navíc se v jejím `dist` (HTML, indexy hledání,
  JSON pro grafy) hledají jména a roky, které vidět nemá.
- **Čerstvost:** brána uloží otisk `data/`, `web/src/` a `dist/`; hook nasazení ho před nasazením přepočítá a při rozdílu zamítne.

## 8. Testy a měření

### 8.1 Průchodové scénáře

Fixtury jsou syntetické, bez sítě; čtení rukopisu se v nich nahrazuje připraveným nálezem. Každý scénář uvádí, čím se chyba **vyvolá**.

| Č. | Scénář | Vstup | Očekávání | Čím se chyba vyvolá |
|---|---|---|---|---|
| 1 | jasný záznam → web | rozhodnutí se třemi tvrzeními | záznam u všech účastníků, vztah z obou stran v HTML | odebrat účastníka → test selže |
| 2 | sousední strana | nález `částečně` + pokračování | jeden úkol, dvě části, DoD až po druhé; čerpání sečteno | uzavřít po části 1 → nástroj odmítne |
| 3 | jmenovec | zadání s `nezamenit_s`, nález s kandidátem na jmenovce | zápis odmítnut, dokud `identita.vylouceno` neřeší jmenovce | rozhodnutí bez `identita` |
| 4 | dva úkoly, stejná osoba | `pridej` dvou úkolů s jinou otázkou | dva úkoly; dělení bez výslovných osob odmítnuto | sloučení podle překryvu osob |
| 5 | rejstřík ženichů | zadání hledat nevěstu v prameni `pokryva: ženich` | zadání odmítnuto před spuštěním; „nenalezeno“ z takového pramene odmítnuto | svazek bez pole pokrytí → varování, ne tiché přijetí |
| 6 | tři různé nezdary | nález `nečitelné`, `nedostupné`, `rozpočet` | tři různé stavy úkolu, žádný řádek deníku „nenalezeno“ | zápis „nenalezeno“ se stavem běhu `rozpočet` |
| 7 | rozpor čtení | dvě čtení s jiným rokem | `porovnej` vydá neshodu; tvrzení nejvýš `prob`, oba přepisy uloženy, navržen další krok | zápis `doc` |
| 8 | špatné identifikátory | nález se signaturou místo ID, typ stránky mimo výčet, osoba jménem | `over` odmítne s názvem pole a příkladem správné hodnoty | každé pole zvlášť |
| 9 | opakování a přerušení | dvakrát totéž rozhodnutí; přerušení po zápisu deníku | jeden řádek deníku, jeden záznam; po přerušení stav jako před voláním | simulovaná výjimka mezi kroky |
| 10 | A–B | tvrzení `kmotr(A, B)`; pak nahrazení | řádek u A i B; po nahrazení oba zmizí nebo se změní | šablona bez opačného řádku |
| 11 | omezený přístup | B skrytá pro daný přístup | u A není jméno B ani v HTML, ani v indexu hledání | index obsahující všechny osoby |
| 12 | zastaralá brána | zelená brána, pak změna dat / šablony / `dist` | hook nasazení zamítne ve všech třech případech | každá změna zvlášť |
| 13 | restart | rozpracovaný úkol, žádná historie chatu | `stav.py` vrátí DoD, poslední krok, cestu k nálezu a další krok | chybějící nález → hlášení, ne tichý nový začátek |

### 8.2 Co testy nepotvrdí

Správnost čtení a úsudku. Pro ni navrhuji **referenční sadu**: 20–30 výřezů z už doložených zápisů projektu, u kterých přepis potvrdil
člověk (uživatel nebo někdo znalý kurentu), rozdělených podle obtížnosti (čitelná latina, kurent, poškozený okraj, jmenovci v jedné
farnosti). Na sadě se měří čtenář i ověřovatel při každé změně modelu, limitu obrazu nebo pravidel. Sada je v projektu, ne ve veřejném
skillu. Bez ní se o přesnosti čtení nedá říct nic kromě dojmu.

### 8.3 Měření a baseline

Baseline je běh 14.–15. 11. 2026 z oddílu 2.2. Jeho slabiny: neobsahuje přesnost (nikdo neověřoval, kolik z 20 řádků deníku je správně),
hlavní vlákno míchá bádání s auditem a úlohy byly těžké (staré rejstříky), takže není srovnatelný s libovolným jiným během.

Návrh opakovatelného srovnání:

1. **Sada případů:** 10–12 úkolů se známým výsledkem, složených z už vyřešených otázek projektu (4 jasné nálezy, 2 sousední strany,
   2 jmenovci, 2 poctivé negativní výsledky, 1 nečitelný, 1 nedostupný portál). Čte se z mezipaměti, aby archivy nenesly zátěž dvakrát.
2. **Stejné podmínky:** stejné modely, stejná sada, čisté sezení na začátku, žádná jiná práce v sezení.
3. **Ukazatele na případ:** ekv celkem a po rolích; počet běhů agentů, pokračování a restartů; počet předání; duplicitní čtení téhož
   snímku; správnost tvrzení proti známému výsledku; úplnost vazeb na webu (podíl splněných řádků matice); počet ručních oprav.
4. **Hlavní číslo:** ekv na **správně** uzavřený případ (cena všech případů dělená počtem správných). Chybný levný běh tak zdražuje.
5. **Peníze:** přepočet ekv na koruny až s ceníkem jednotlivých modelů a s oddělenými poli vstup / zápis cache / čtení cache / výstup po
   modelech; data na to v záznamech jsou, ceník jsem neověřoval, proto ho neuvádím.
6. **Průběžné měření:** `spotreba.py` připíše skutečné ekv k úkolu při uzavření ze záznamů sezení (dnes se zapisuje odhad **[běh]**);
   `fronta.py kalibrace` pak opraví pásma S/M/L.

Co čekat, aniž to slibuji: z rozkladu 2.3 je vidět, že mechanické zápisy (21 %) mohou zmizet téměř celé a že část ceny řízení (42 %)
tvoří ztráty cache a rekonstrukce stavu. Návrhy z poznámek se překrývají (kratší karta i méně běhů šetří tytéž tokeny), proto je
nesčítám. Úsporu potvrdí až srovnání na sadě; kvalitativní podmínky K1–K8 musí být splněny v obou měřených variantách.

### 8.4 Dosavadní výsledky testů

Sada skillu: 564 testů prošlo při posledním úplném běhu před pushem 15. 11. 2026 (větev `pracovni-prehled`). Pro tento návrh jsem testy
znovu nespouštěl. Zelená sada neříká nic o průchodu výsledku od nálezu na web; žádný ze 13 scénářů dnes jako test neexistuje.

## 9. Migrace a backlog

Pořadí je podle přínosu pro přesnost a provozní cenu a podle závislostí. Každá etapa je samostatně použitelná a vratná; práce ve feature
větvi skillu, test napřed, kopie nástrojů do projektu až po zelené bráně.

| Etapa | Co | Soubory a komponenty | Závisí na | Testy | Návrat |
|---|---|---|---|---|---|
| **E0 okamžité zmírnění** (bez změny architektury) | `tools:` u browser-readeru; `.gitignore` pro `data/.rozpocet.json` (lépe přesun do `pracovni/`); `hooks.json` nejdřív `python`; `aron_img.py` bez výstupu jen do mezipaměti; `denik.py` ověří osoby proti `osoby.py`; `fronta.py` neslučuje napříč frontami a jinými cíli; hook pustí `cekajici` a `plan`; pravidlo jednoho modelu na sezení | definice agentů, `hooks/`, `denik.py`, `fronta.py`, `aron_img.py` | – | regresní test ke každé položce | vrácení commitu |
| **E1 kontrakt** | schémata `zadani`, `nalez`, `overeni`, `rozhodnuti`; `tools/vysledek.py over / souhrn / porovnej`; `svazky.json` pole pokrytí; ověřovatel vrací přepis | `skills/rodokmen-agents/schemata/`, `vysledek.py`, `agents/researcher.md`, `verifier.md`, `mapa.py` (přijme nález) | E0 | scénáře 5, 7, 8 | staré výsledky se dál čtou jako `nalez/0` |
| **E2 transakční zápis** | `zapis_vysledku.py`, `commit.py`, `stav.py`; hook badatele s výčtem zapisovacích nástrojů; fixer a committer z bádání pryč | `tools/`, `hooks/hlidac_orchestratora.py`, `agents/orchestrator.md` | E1, rozhodnutí R1 | scénáře 6, 9, 13 | role fixer a committer zůstávají v pluginu jednu verzi jako záloha |
| **E3 pokračování** | ověřit pokračování pomocníka na platformě; `pokracovani/1`; pokračovací balíček; `vyrez.py` dělení řádku s překryvem | `agents/`, `vyrez.py` | E1 | scénář 2 | bez pokračování platí nový běh s balíčkem |
| **E4 účastníci a tvrzení** | `ucastnici` v `zaznamy.json`, `data/tvrzeni.jsonl`, odvození `r`; migrační skript s návrhem k ruční kontrole; export a šablony podle tabulky projekcí | `zapis.py`, `zaznamy_store.py`, `export_web.py`, `kontrola.py`, šablony osoby a zápisu | E2 | scénáře 1, 3, 10 | `r` v `osoby.py` zůstává, dokud kontrola nepotvrdí shodu s odvozeným |
| **E5 web a brána** | ručně psaná matice vztahů, kontrola symetrie v `dist`, kontrola přístupů a indexů, otisk dat + šablon + `dist` v hooku nasazení | `kontrola_webu.py`, `brana.py`, `hlidac_site.py`, `tests/e2e/` | E4 (symetrie), jinak samostatné | scénáře 11, 12 | brána má přepínač staré kontroly po dobu jedné verze |
| **E6 dva hlavní agenti** | rozdělit `orchestrator.md` na `badatel.md` a `metodik.md`; formát podnětu; verze pravidel a její převzetí projektem | `agents/`, `skills/rodokmen-agents/SKILL.md`, `analyza/podnety/` | E2 | `test_agenti_definice.py` rozšířit o vlastníky rozhodnutí | alias `orchestrator` na badatele po jednu verzi |
| **E7 měření** | referenční sada čtení, sada případů, `spotreba.py`, první srovnání s baseline | projekt (sada), `tools/spotreba.py` | E2 pro novou variantu; baseline lze změřit hned | – | – |

Poznámky:

- **E7 baseline změřit dřív než E1.** Jinak nebude s čím srovnávat a úspora zůstane tvrzením.
- E0 je to, co poznámky navrhují jako T1, T2, T5, T7. Je správné to udělat, ale příčiny P1–P5 to neodstraní.
- Slučitelnost s originálem: `ucastnici` a `tvrzeni.jsonl` jsou přidaná pole a nový soubor, `osoby.py` zůstává ve tvaru originálu.
  Schémata, zapisovací nástroj a nové role jsou věcí forku; `scripts/sync_report.py` na ně při slučování upozorní.
- Nahrazovaná rozhodnutí: „orchestrátor nic nespouští, vše zapisuje specialista“ (fáze C, Q-C4) se nahrazuje pravidlem „rozhoduje agent,
  mechaniku provádí validující nástroj“. Důvod: měřená cena a chybovost delegovaného zápisu (2.2, 2.3).

## 10. Vývoj metodiky, šablony, omezení a rozhodnutí

### 10.1 Jednotný postup změny

Podnět → analýza dopadu na produkt a cenu → návrh pravidla nebo kontraktu → implementace s testem → ověření → převzetí projektem.

- Podnět vzniká v projektu (`data/poznamky_pro_skill.md`), je technický a bez rodinných údajů. Metodik ho převezme do skillu a z projektu
  smaže.
- **Jedno místo pro každé pravidlo:** badatelská pravidla v `rules/*.md` s ID, tvary dat ve `schemata/`, routování v `nocni_rezim.md`.
  Definice rolí pravidla necitují, odkazují na ID; test hlídá, že odkaz existuje (už dnes) a nově i to, že každé pravidlo má aspoň jeden
  test nebo je označeno „jen úsudek“.
- **Verze pravidel:** projekt nese `.skill_verze`. Rozpracovaný úkol si pamatuje verzi, se kterou vznikl; nová verze se přebírá mezi
  úkoly, nikdy uprostřed. Mění-li verze kontrakt, starý nález se čte starým schématem.
- Badatel pravidla nemění. Narazí-li na chybu nástroje, zapíše podnět, použije popsaný obchvat a pokračuje.

### 10.2 Šablony

**Zadání změny**

```text
Co se má změnit (jedna věta):
Proč: symptom, kde se projevil, kolikrát, důkaz (soubor, řádek, měření):
Dopad na přesnost (K1–K8):          Dopad na cenu (odhad, z čeho):
Co se měnit nesmí:
Hotovo, když:
```

**Analýza**

```text
Příčina (ne symptom) a důkaz [kód / měření / běh / hypotéza]:
Dotčená pravidla, schémata, nástroje, role, stránky webu:
Varianty (aspoň dvě) a proč vybraná:
Dopad na existující projekty a na slučování s originálem:
Jak se chyba vyvolá testem:
```

**Implementační lístek**

```text
Změna:                                   Velikost: S / M / L
Povolené soubory:
Regresní test (napřed, musí selhat):     Další testy ke spuštění:
Čeho se nedotýkat:
Kopie do projektu po zelené bráně: ano / ne
```

**Testovací protokol**

```text
Verze, větev, datum, model:
Spuštěno (příkaz):                       Výsledek (počty, co selhalo, výstup):
Scénáře 1–13 dotčené změnou a jejich stav:
Měření před a po (sada, ekv na správně uzavřený případ) nebo „neměřeno, proč“:
Co nebylo ověřeno:
```

### 10.3 Omezení tohoto návrhu

- Nic nebylo spuštěno jako pokus: žádný scénář, žádné čtení, žádný build webu. Tvrzení o úsporách jsou odhady z rozkladu jednoho běhu.
- Jeden běh, těžké úlohy, hlavní vlákno smíchané s auditem. Podíly v 2.3 se u jiného běhu mohou lišit.
- Chování platformy (pokračování pomocníka, vliv `tools:` na start, vypnutí konektoru a stavu gitu u pomocníků, limit obrazu) znám
  z popisu nástrojů a z poznámek, ne z vlastního pokusu.
- Web jsem posuzoval čtením `export_web.py`; šablony stránek jsem neprocházel řádek po řádku a konkrétní případ A–B z projektu jsem
  nedohledával.
- Soubor se podle pokynu uživatele jmenuje `navrh-optimalizace.md`; zadání uvádělo `navrh-optimalizace-metodiky.md`.

### 10.4 Rozhodnutí, která zbývají na uživateli

| Č. | Otázka | Doporučení | Co na tom visí |
|---|---|---|---|
| R1 | Smí badatel spouštět validující zapisující nástroje (fronta, zápis výsledku, commit)? | ano, s výčtem v hooku | E2; bez toho zůstává 60 % běhů mechanických |
| R2 | Přijmout dva hlavní vstupy badatel a metodik? | ano | E6 |
| R3 | Zavést `ucastnici` u zápisů a `tvrzeni.jsonl` (možnost b)? | ano | E4, E5; migrace 205 zápisů s ruční kontrolou |
| R4 | Který model pro badatele na celé sezení? | změřit na sadě; do té doby jeden model bez přepínání | cena řízení |
| R5 | Změřit baseline na sadě případů ještě před změnami? | ano | věrohodnost každého dalšího čísla |
| R6 | Kdo potvrdí přepisy referenční sady? | uživatel, případně znalec kurentu | měření přesnosti čtení |
| R7 | Vypnout konektor dokumentů v projektu, zkrátit `CLAUDE.md` projektu, upravit alias `rm`? | ano; jde o prostředí uživatele | start pomocníků, zaseknuté běhy |
| R8 | Oprava řádku deníku 378 (osoby) | čeká z minulého běhu | data projektu |

Další krok po schválení: **E7 baseline** a **E0**, obojí jde hned a jedno druhé neblokuje. Vykonavatel: metodik (sezení nad skillem),
sadu případů připraví badatel v projektu na pokyn uživatele.
