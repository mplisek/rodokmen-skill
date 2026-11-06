# Co je nového

Změny ve skillu rodokmen, nejnovější verze nahoře. Každá verze má na GitHubu i
[vydání (Releases)](https://github.com/mplisek/rodokmen-skill/releases) – kdo chce dostávat upozornění,
dá v repozitáři **Watch → Custom → Releases**.

Projekt založený starší verzí Claude sám nabídne aktualizovat (pozná to podle souboru `VERZE`).

Tohle je fork ([mplisek/rodokmen-skill](https://github.com/mplisek/rodokmen-skill)). Verze `X.Y.Z-fork.N` stojí
na verzi X.Y.Z originálu a popisuje jen to, co fork přidává; níže jsou změny originálu. Čísla PR (`PR #19`)
odkazují na pull requesty v originálu (sarsonj/rodokmen-skill).

## Nevydáno

### Nové
- Obrázky pro web se při exportu zmenší a překódují: na stránce nejvýš 1400 px (je-li k zápisu plné rozlišení),
  progresivní JPEG bez metadat, plné rozlišení v kvalitě 82. Na skutečném projektu asi o polovinu méně dat u obrázků
  na stránkách a o čtvrtinu u plného rozlišení – méně přenesených dat a kreditů na Netlify. Upravené verze jsou
  v `pracovni/.web_obrazky/`, další export je bere odtud. Bez ImageMagicku se jen kopíruje jako dřív.

### Návody
- Kredity na Netlify: ostré nasazení 15 kreditů, náhled (bez `--prod`, `--alias test`) zdarma – na zkoušení.

## 0.8.2-fork.1 – 6. 11. 2026

Fork na originálu 0.8.2 (Porta fontium podle far a 10 s mezi dotazy, FamilySearch do mezipaměti, `--kontrast`,
`anno.py --ztraty`, kontrola po nasazení na Netlify, brzda při visícím archivu – viz níže) a navíc:

### Nové
- **Osobní odkazy na web** (PR #94): každý příbuzný může dostat vlastní odkaz `https://<web>/?k=<klíč>`
  (`tools/pozvanky.py pridej "Teta Jana"`), který jde jednomu člověku zrušit nebo vyměnit; rodinná otázka platí dál.
  Ve forku navíc **i s přístupy**: `pozvanky.py pridej "Teta Jana" --pristup <id>` – teta pak vidí jen verzi webu
  pro ten přístup; změna `pozvanky.py pristup p1 <id>`. Poznámky ke stránkám fungují i pro příchozí přes odkaz.
  Jen na Netlify (nginx/Docker odkazy neumí).
- Snímky z ARONu na čtení ve výchozím plném rozlišení (PR #120).
- Holocaust.cz (`obeti.py`) a Arolsen (`arolsen.py`) stahují až po souhlasu s podmínkami portálu, který potvrdí
  uživatel sám v terminálu (`souhlas`, jednou za 30 dní; PR #123, #124).
- `smoke_test.py` rozliší i ZASTAVENO (brzda web zastavila) a přeskočí nástroje čekající na souhlas (PR #125).
- README: kapitola Nastavení – mezipaměť snímků, brzda, co jde nastavit v projektu (PR #107).
- **Dějiny významných domů:** `data/stavby.py` (držitelé, obyvatelé, události, čísla popisná v čase, otevřené otázky)
  a nástroj `tools/stavby.py` – `kontrola` (osoby, zápisy, stavy, soukromí), `kandidati` (náměty z `osoby.py`: řemesla
  a domy s více lidmi), `export` (volá ho `export_web.py`). Na stránce Domy je u domu rozbalovací „Dějiny domu“.
- Návod `reference/stavby.md`: formát, přehled pramenů podle doby (gruntovní a pozemkové knihy, sčítání lidu po domech,
  reambulace pro datování novostaveb) a postup. Vznikl podle skillu dejiny-domu.

### Opravy
- Encyklopedie Brna a Mauthausen: srozumitelná hláška při výpadku portálu, spolehlivější čtení výsledků (PR #121, #122).
- Úvodní text bez fotky vede přes celou šířku stránky (dřív jen do tří pětin).
- Kontrola po nasazení (`npm run overit`) běží i po nasazení z čisté složky (`nasadit.mjs`) a pozná přihlašovací
  stránku i bez otázky (jen osobní odkazy).
- `npm run nasadit` z čisté složky (projekt za odkazem) nasadí i funkci poznámek – zkopíruje `src/lib/poznamky.mjs` a doinstaluje `@netlify/blobs`; nasazuje s `--no-build` (web je sestavený předem).

### Návody
- Vybledlé písmo: nejdřív `--kontrast` (originál), u nejhorších snímků `--vylepsit` (navíc doostření).

## 0.8.2 – 5. 11. 2026

**Opravy**
- SOA Plzeň (Porta fontium): nástroje se ptají nejvýš jednou za 10 sekund, jak archiv žádá ve svém robots.txt.
  Stahování je pomalejší, hlavně mapa knihy (#129).

## 0.8.1 – 5. 11. 2026

V dnešním vydání jsem se zaměřil na nejčastěji hlášené problémy a vylepšení.

**Nové**
- Porta fontium: `portafontium.py obec "<obec>"` vypíše všechny knihy obce seskupené podle fary a seřazené podle let.
  Je z toho vidět i přechod obce mezi farami a stejnojmenné obce jiných far.
- FamilySearch: snímek z přihlášeného prohlížeče (Playwright) jde uložit do mezipaměti a do projektu v plném
  rozlišení (`cache.py uloz`) a dál normálně vyříznout. Nový postup pro **Slovensko**: najít faru v katalogu,
  zjistit, do kdy jsou knihy natočené (často jen do 1895), a jak pracovat s neúplným indexem.
- Vybledlé snímky: `vyrez.py` a `overit.py` mají přepínač `--kontrast`. Bledá stránka se už nemá prohlásit za prázdnou.
- Vojáci 1. světové války: `anno.py --ztraty` hledá jen v rakouských seznamech ztrát (pluk, domovská obec, ročník,
  raněn/zajat/padl).
- Netlify: po `npm run nasadit` se web sám otevře bez přihlášení a pozná, jestli ho místo rodinné otázky chrání
  přihlášení k Netlify (ochrana týmu u nových webů). Vypíše, jak ji vypnout. Ručně `npm run overit`.

**Opravy**
- Brzda se zastaví i tehdy, když archiv přijme spojení, ale neodpovídá (noční výpadky). Dřív každé volání čekalo
  přes dvě minuty.
- `anno.py`: filtr podle listu (`ANNO_TITLE`) vracel vždy 0 výsledků.

**Návody**
- ZA Opava: detail svazku neotvírat přímou adresou (ukáže jiný svazek), raději trvalým odkazem `permalink?xid`.
  Vestavěný prohlížeč aplikace Claude archiv odmítne, okno aspoň 1400×900, CAPTCHA řeší uživatel.
- SOA Litoměřice: hledání přes pole Místo, vyzkoušený úryvek pro adresy snímků, jak poznat blokaci.
- MZA: sčítací operáty 1857–1921 (jen v prohlížeči). Nástroj na stahování snímků z MZA nebude, archiv to zakázal.
- Claude in Chrome: výstup JavaScriptu s adresou rozšíření zablokuje – jak to obejít.
- Svazky „dosud uložené na matričním úřadě“, knihy řazené po vsích (neúplný popis, samostatné knihy vsí, pasti
  rejstříků) a posun mezi číslem v rejstříku a snímkem.
- Mapy stabilního katastru: jak se dostat k indikační skice a jak ji číst.
- Výpadky archivů: co dělat, když archiv večer nebo v noci neodpovídá.

Děkuji všem, kdo poslali zkušenosti e-mailem.

## 0.8.0-fork.1 – 4. 11. 2026

Fork na originálu 0.8.0 (bezpečná aktualizace projektu, ARON celým skenem, nové kontroly – viz níže) a navíc:

### Opravy
- `mista.py` dává přednost bodu vsi či města před hranicí obce (bod uprostřed katastru padal u obce s více částmi
  do jiné části nebo do pole).
- `kontrola.py` už nepadá (`UnboundLocalError`) u projektu s `PARTNERI` a bez `RODINA`; neexistující zápis hlídá
  u každé osoby z `RODINA`, ne jen u poslední.
- `npm run nasadit` funguje i u projektu za odkazem (junction/symlink): Netlify CLI tam končilo chybou „build.base …
  must be inside the repository root“, nově se nasazuje z čisté složky `~/.rodokmen-netlify/<projekt>`
  (`web/scripts/nasadit.mjs`).

### Nové
- Web má jen dvě šířky stránek: úzkou pro textové stránky (osoba, zajímavosti, příběhy…) a širokou přes celé okno
  (úvod, mapa, místo, časová osa, deník, poznámky, domy, zdroj); na široké stránce se text nezalamuje v polovině.
- Žádosti archivům a úřadům: `mailto.py` udělá z konceptu odkaz do e-mailu (i Gmail, Outlook, Seznam), přehled
  `data/zadosti.md` a vzory v `reference/zadosti.md` (PR #87).
- Příčina úmrtí u zápisů (`pricina_umrti`: původní znění, překlad, jistota čtení) na stránce osoby i zápisu (PR #92).
- Opravy z issues (PR #89): `zapis.py --smazat`, `overit.py`/`vyrez.py --vylepsit` pro vybledlé snímky,
  `ramecek.py --stranka`, kontrola polí v přepisech, doklady bez online odkazu; odkaz ARON hledá snímek ve všech
  digitálních objektech.
- Stránka předka ukazuje v kartě Děti i **Další děti** zapsané jen v `SIDE` (bratr/sestra dítěte v linii, syn/dcera
  předka) s odkazem na poznámku; děti z `RODINA` tam byly už dřív (obdoba #69 z PR #89 pro data forku).
- `aron_img.py odkazy --opravit` najde správný snímek i v jiném digitálním objektu svazku (nahradí celou adresu),
  nespadne na jednom nedostupném svazku a jde spustit i jako `opravit-odkazy [--zapsat]` jako v originálu.
- Stránka osoby mimo přímou linii (z `RODINA`) má i kapitolu **Předci** (tři generace přes otce a matku, od přímého
  předka dál po číslech) a řádek **Místa** s odkazy na obce z jejích údajů.
- `kontrola.py` hlídá Kekulého čísla: upozorní, když poznámka „otec Václava (72)“ nebo „syn Josefa (40)“
  neodpovídá číslu osoby (rodiče osoby k jsou 2k a 2k+1).

### Návody
- Stránka Domy: odkaz na skill stare-adresy, jak ho nainstalovat a že bez `domy.geojson` se stránka neukáže.
- Rejstřík celé fary (eBadatelna, klíč písmen ke vsím) jako rychlá cesta k zápisu mimo knihu vsi ženicha.
- Poznámky pro správce skillu jdou do issues forku (https://github.com/mplisek/rodokmen-skill/issues).
- `smoke_test.py` už nezkouší Třeboň ani eBadatelnu (skriptem zakázané); testy originálu běží i v CI forku.

## 0.8.0 – 4. 11. 2026

Bezpečná aktualizace projektu (vlastní úpravy zůstanou), rychlé stahování z ARONu a přesnější kontrola dat.

**Nové**
- Aktualizace projektu už nepřepisuje vlastní úpravy webu a nástrojů. Projekt si pamatuje šablonu, ze které vznikl,
  a při aktualizaci každý soubor buď přepíše (neupravený), nechá (šablona se nezměnila), nebo sloučí obě změny.
  Kde to nejde, nechá soubor beze změny a Claude s vámi projde, co je nového a co je vaše úprava. Projekt ze starší
  verze se při první aktualizaci přepíše jako dřív, ale původní soubory (nově i `tools/`) zůstanou v záloze
  v `pracovni/` (#79, PR #88).
- ARON: snímek se stahuje celý jedním požadavkem (jako tlačítko „stáhnout“) místo desítek dlaždic. Stránka, která
  trvala minuty, je tu za sekundu, v plném rozlišení přesně původní sken. Zmenšení a výřez se dělají z disku a další
  výřezy téže stránky už archiv nezatěžují.
- `kontrola.py` hlásí sňatek, který nejmenuje partnera z rodokmenu (druhý sňatek vdovce u první ženy), a číslo domu,
  které žádný citovaný zápis nedokládá (#80, PR #86). U předků bez obce na mapě ukáže slova, která vypadají jako obec
  (#81).

**Opravy**
- `mista.py` hledá jen sídla – už nenajde bar nebo kadeřnictví stejného jména – a varuje, když je nové místo přes
  50 km od ostatních (stejnojmenná obec jinde) (#81, PR #85).
- Mezipaměť obrázků ukládá jen celé obrázky: přerušené stažení se neuloží a zkrácený snímek se stáhne znovu.
- Aktualizace projektu neslučuje `package-lock.json`, vezme nový.

**Návody**
- SOA Třeboň: nástroj `trebon.py` je na žádost archivu odstraněn (licence DigiArchivu nepovoluje stahování
  snímků skripty, #91). Matriky se čtou v prohlížeči jako dosud.

Aktualizaci projektu napsal pavelzbornik (PR #88), stejně jako opravu `mista.py` (PR #85) a nové kontroly
(PR #86). Děkuji i všem, kdo poslali zkušenosti e-mailem.

## 0.7.0-fork.1 – 4. 11. 2026

První verze forku postavená přímo na originálu 0.7.0 (historie odpovídá originálu, otevřené pull requesty jsou
sloučené jako merge commity) a pravidla archivů z originálu platí i pro všechno, co fork přidává.

**Nové**
- Web: stránky **Statistiky** a **Domy**, volitelné původní tvary jmen (PR #19), **Osobnosti** (PR #23),
  **stromový graf** celé rodiny s rozbalováním větví a sourozenci (PR #13), **víc příběhů rodu** (PR #49),
  **Časová osa** s pruhy životů předků a seznamem „Co časově nesedí“ (PR #77), **stránka každého místa** s časovou
  osou lidí a událostí, odkaz z mapy (PR #73), vějíř s plynulým posunem a přibližováním (PR #55).
- Web podle projektu: příbuzní z `RODINA` mají vlastní stránky (děti, sourozenci, manželství se počítají stejně
  u všech), volitelné `PARTNERI`, vějíř předků pro libovolnou osobu (`/vejir/<osoba>/`), stránka `/dokumenty/`.
- **Soukromí žijících vynucuje export webu:** žijící a narození v posledních 100 letech bez známého úmrtí jen se
  jménem, rokem narození a vazbami – i na mapě, v Domech, Statistikách a na časové ose.
- **Přístupy k webu:** každá větev rodiny může mít vlastní odpověď a vidí jen svou část rodokmenu (`pristupy` ve web.json).
- **Poznámky ke stránkám:** tlačítko „Připomínka“, přehled `/poznamky/`, `npm run poznamky`.
- `kontrola.py` hlídá **časovou návaznost** narození, sňatků a úmrtí; ověřený neobvyklý údaj se odškrtne polem
  `overeno` (PR #76).
- Nové nástroje (PR #29): SOA Litoměřice (`litomerice.py`, jen když portál nežádá ověření), židovské matriky
  (`vademecum.py`), vězni a oběti 2. sv. války (`arolsen.py`, `mauthausen.py`, `obeti.py`, `vezni.py`), Matricula
  (`matricula.py`, `matricula_snimek.js`), Encyklopedie dějin města Brna (`brno_encyklopedie.py`), `kramerius.py --server`,
  `smoke_test.py` (kontrola síťových nástrojů na živých portálech). MZA Brno: `mza.py` jen hledá knihy, detail
  a snímky jsou v prohlížeči (MZA stahování skriptem nepovoluje). Všechny nové síťové nástroje jdou přes brzdu `slusne.py`.
- Bezpečný zápis datových souborů (`tools/soubory.py`): přerušení nenechá useknutý `svazky.json` ani jiný soubor.

**Opravy**
- ARON: odkaz na snímek otevře správný snímek, ne první; `aron_img.py odkazy` opraví staré odkazy (PR #22).
- SOA Třeboň: správné slepení dlaždic (PR #48).
- Přihlašovací odpověď bez znaků a-z0-9 (např. „***“, azbuka) už neskončí chybou (PR #66); nginx
  `map_hash_bucket_size 128` proti chybě 502 v Dockeru/CapRoveru (PR #56).
- `SKILL.md` se načte i v přísnějších parserech YAML a v GitHub Copilotu (PR #26, PR #59).
- Windows: chybějící kořenový certifikát (Porta fontium, Kramerius, ANNO) brzda doplní přes systémový `curl.exe`
  a spojení zopakuje – ověřování certifikátů zůstává zapnuté.
- AHMP: dočasné dlaždice se smažou i při chybě; stránka Osobnosti ukazuje jen předky; web skripty bez varování
  DEP0190 na Windows.

**Návody**
- Předávání výzkumu a práce s GEDCOM (PR #46), přesnější pokyny pro archivy a opakované pokusy eBadatelny (PR #47),
  vylepšení z praxe – čas aktualizace webu, web ve vnitřní síti, zaniklé obce (PR #41).
- Písemnosti vrchnosti, zemské desky a vodnimlyny.cz (PR #62); nové archivy a poválečné osídlení (PR #29).
- Německé formuláře – co vždy ověřit na výřezu; čísla zápisů společná pro celou farnost (z PR #28).
- Node.js 22.19 nebo novější (Astro 7.3.8).

## 0.7.0 – 3. 11. 2026

Sdílená mezipaměť obrázků: každý snímek se z archivu stáhne jen jednou. A kontrola, která nenechá prázdné rody a mapu.

**Nové**
- Mezipaměť obrázků pro všechny projekty na počítači (`~/.cache/rodokmen_snimky`, nejvýš 5 GB, staré se mažou
  samy). Snímek nebo dlaždici, kterou už nějaký nástroj stáhl, vezme příště z disku bez dotazu na archiv. Porta
  fontium dělá výřezy a náhledy z uloženého snímku. Kolik se ušetřilo, ukáže `cache.py stav` (#71, PR #60).
- eBadatelna (SOA Praha): snímek načtený v prohlížeči se uloží do mezipaměti a dál se čte z disku. Při návratu
  ke snímku (rejstřík, opakované čtení) už archiv nedostane žádný dotaz. `cache.py uloz … --nahled x.jpg` uloží
  snímek a rovnou udělá náhled 1600 px.
- `kontrola.py` hlásí známé pradědečky a prababičky (8–15) bez rodu v `LINES` a doložené předky, jejichž obec
  chybí na mapě. Upozornění, že je čas napsat příběh rodu, přijde i bez vyplněných rodů.

**Opravy**
- Hlídač sítě už nezamítá heredoc, který jen obsahuje text „import http.client“ v řetězci.
- `aron_img.py` si vytvoří výstupní složku sám.

**Návody**
- MZA: listovat v otevřené stránce (návrat je z mezipaměti prohlížeče), stránku neobnovovat. SOA Třeboň stahuje
  při každém zobrazení snímku všechno znovu – přečíst všechny potřebné zápisy najednou.
- Fáze 2: rod do `LINES` hned, jak je znám pradědeček nebo prababička, a každou novou obec do mapy.
- `matriky.md`: náboženství dětí ze smíšených manželství, jiné křestní jméno než v dospělosti, jméno opravené
  v zápisu, ale původní v rejstříku.

Mezipaměť navrhl MarekLu (#71) a první verzi napsal AdamFiser (PR #60). Děkuji i všem, kdo poslali zkušenosti
e-mailem.

## 0.6.4 – 3. 11. 2026

SOA Praha jen přes prohlížeč, orientace v knihách řazených po vsích, opravy nástrojů.

**Nové**
- SOA Praha (eBadatelna) od 2. 11. nástroj rodokmen zakazuje (robots.txt, HTTP 403). Skill proto čte středočeské
  matriky a archiválie jen v prohlížeči eBadatelny: výřez zápisu vykreslí ze snímku, který prohlížeč už načetl,
  a uloží snímek obrazovky. `ebadatelna.py` je zatím vypnutý (kromě odkazů) a brzda skripty na soapraha.cz
  zastaví (#72).
- Nástroj `mapa_knihy.py` pro knihy řazené po vsích: horní pruhy každého N-tého snímku pod sebou (stavba knihy
  na jednom obrázku) nebo sloupec se jmény z několika snímků vedle sebe. ARON, Porta fontium, AHMP, nebo
  z uložených snímků obrazovky (#12).
- Brzda: `slusne.py zastav <web>` – když archiv odmítne prohlížeč, stopka platí i pro skripty a pomocníky.

**Opravy**
- Policejní přihlášky: když portál přiškrtí přístup, umí vrátit kartu úplně jiné osoby. Nástroj teď ověří,
  že karta patří k hledání, jinak skončí chybou a nic neuloží. Brzda pro digi.nacr.cz 1 dotaz za 4 s.
- Vějíř: předek, který je v rodokmenu dvakrát, má na obou místech celou větev předků (#31). Velký plakát
  na pomalejším počítači už nehlásí falešnou chybu.
- Import GEDCOM z MyHeritage: český znak rozdělený na konci řádku se už nerozbije.
- `aron_img.py`: méně souběžných stahování (na macOS padal překlad adres), srozumitelné hlášky u svazku bez
  snímků, neexistujícího svazku a výpadku certifikátu ARONu; bez argumentů vypíše nápovědu (stejně
  `kramerius.py`).
- `kontrola.py`: žádné falešné poplachy u „nejsou dluhy“ a u data dovětku.
- `overit.py` si vytvoří výstupní složku sám.

**Návody**
- Čtení v prohlížeči: tempo 5–10 s mezi stránkami, jeden prohlížeč na archiv, při 403/429/503 hned skončit;
  když nejde ani prohlížeč, pošle snímky obrazovky uživatel.
- `matriky.md`: knihy řazené po vsích – nejdřív popis knihy a rejstřík, mapa knihy, montáž sloupců, pasti.
- MZA: doména actapublica.eu archivu nepatří.

Blokaci eBadatelny nahlásil george190321 (#72), chybu vějíře michalspondr (#31). Děkuji i všem, kdo poslali
zkušenosti e-mailem.

## 0.6.3 – 3. 11. 2026

Opravy po hlášeních z praxe.

**Opravy**
- Brzda: `slusne.py curl` se bez `-A` představí stejně jako nástroje. Porta fontium výchozí „curl“ odmítá (403)
  a brzda to brala jako zablokování archivu.
- SOA Litoměřice změnil koncem října cesty k obrázkům – `soal_zoomify.py` je potřeba dávat celou adresu
  obrázku (návod upraven).

**Návody**
- Příprava (Fáze 0): na macOS ověřit https – Python z python.org po instalaci nemá certifikáty.
- Prohlížeč pro Clauda: jak nainstalovat doplněk Playwright (README a příprava).
- Archivní mapy ČÚZK na nové adrese ags.cuzk.gov.cz/archiv.

Děkuji všem, kdo poslali hlášení e-mailem.

## 0.6.2 – 2. 11. 2026

SOA Třeboň jen přes prohlížeč.

**Nové**
- SOA Třeboň od 2. 11. odmítá stahovací nástroje (`trebon.py` dostává HTTP 403). Skill proto čte jihočeské
  matriky jen v prohlížeči archivu: přiblíží zápis a uloží snímek obrazovky, výřez pak jako u jiných archivů.
  `trebon.py` je zatím vypnutý a brzda skripty na digi.ceskearchivy.cz zastaví.

**Návody**
- `portaly.md`: SOA Třeboň a MZA Brno – vyzkoušené úryvky pro přiblížení zápisu v prohlížeči archivu,
  u Třeboně i trvalý odkaz přímo na zápis.

Kdo pracoval s `trebon.py`: Claude teď místo něj otevře prohlížeč (Playwright). Bez prohlížeče pošlete
snímky obrazovky sami. Děkuji všem, kdo na blokaci upozornili e-mailem.

## 0.6.1 – 2. 11. 2026

MZA Brno jen přes prohlížeč, opravy brzdy a hlídače na Windows.

**Nové**
- MZA Brno (Acta Publica) od 2. 11. blokuje stahovací skripty. Skill proto čte snímky jen v jejich prohlížeči:
  přiblíží zápis a uloží snímek obrazovky (Playwright), výřez pak jako u jiných archivů. Bez prohlížeče pošle
  snímky obrazovky uživatel sám. Skriptem jde jen hledání knih, ostatní adresy MZA brzda zastaví (#64).
- Brzda: když archiv odmítne podruhé za 24 hodin, stopka trvá 2 hodiny, potřetí 8 hodin (#53).
- Brzda hlídá i `curl`, `python` a `bash` spuštěné z Pythonu (#53).

**Opravy**
- Windows: hlídač sítě bez Git for Windows zamítal každý příkaz. Nově se spouští bez shellu, takže funguje
  v Git Bashi i v PowerShellu, i v projektu sdíleném přes OneDrive.
- Windows: brzda nepoznala u `curl` odmítnutí archivu (429/503) a po zablokování poslala další dotaz;
  `slusne.py bash` spuštěný z PowerShellu nebrzdil `curl` uvnitř skriptu (#53).
- Windows se Smart App Control: když `curl` z Gitu nejde spustit, brzda použije systémový `curl.exe`.
- Hlášky brzdy a hlídače na Windows bez rozsypané češtiny.
- Hlídač pozná i `import json, urllib.request`, `python -c "…"`, `bash -c "curl …"` a nástroj Monitor.

**Návody**
- `portaly.md`: MZA – postup v prohlížeči a tipy, jak listovat méně (části matriky, rejstříky, strana → snímek).
- `portaly.md`: židovské matriky Národního archivu ve VadeMeCum místo badatelna.eu (#54).
- README: jak aktualizovat skill (#58).

Kdo má na Windows zapnutý hlídač a Claude mu zamítá každý příkaz: nechte Claude aktualizovat projekt
(nabídne to sám), nebo hlídač vypněte příkazem `novy_projekt.py <projekt> --bez-hlidace`.

Opravy pro Windows a testy připravil svamberk (#53), blokaci MZA nahlásil HonzinaThor (#64).
Děkuji i všem, kdo e-mailem poslali zkušenosti z Windows a nápady k MZA.

## 0.6.0 – 2. 11. 2026

Brzda proti zablokování archivem.

**Nové**
- Brzda `tools/slusne.py`: společný limit dotazů pro každý archiv a všechny procesy na počítači
  (stránky 1 za 2 s, obrázky 10 za s). Když archiv dá najevo, že ho zatěžujeme, stahování se na 30 minut
  zastaví. Nástroje ji mají samy, vlastní skripty a `curl` se spouštějí přes ni (#45).
- Volitelný hlídač sítě (`novy_projekt.py --hlidac`): zamítne příkazy, které by šly na archiv mimo brzdu.
- Projekt má v `.claude/settings.json` zakázané přímé `curl` a `wget`.

**Opravy**
- Úvodní stránka webu s prázdným úvodem už nevypíše „0“.
- `kontrola.py`: žádné falešné poplachy u obce Petrovice nebo kontaktu „Petrovi“, zápisy z hypotéz
  se počítají jako citované, chybějící přihlašovací otázku hlídá až nasazení.
- Legenda vějíře neusekne popis rodu na „čp.“, „roz.“ a podobně.
- `novy_projekt.py --help` už nezaloží složku „--help“.

**Návody**
- SKILL.md: „Šetrně k archivům“ – síť jen přes brzdu, i u pomocníků, na jeden archiv nejvýš jeden pomocník.

Brzdu navrhl MarekLu (#45). Děkuji i všem, kdo poslali vlastní vyzkoušená řešení a zkušenosti s blokacemi.

## 0.5.0 – 24. 10. 2026

Zpětná vazba uživatelů (přes čtyřicet podnětů od šesti lidí).

**Nové**
- `zapis.py` – změní jednu položku dat a formát souboru nechá beze změny.
- `kontrola.py`: schválené citlivé zmínky (`citlive_schvaleno` ve `web.json`) a hranice 100 let.
- `mista.py` zkusí i sousední země.

**Opravy**
- Bezpečnost: otevřené přesměrování po přihlášení na webu.
- Konce řádků LF ve všech zápisech nástrojů.
- `soal_zoomify` bez `montage` (padal na ImageMagick 7.1.2), 4 vlákna, úklid dočasné složky.
- ImageMagick 6 (`convert`) mimo Windows.
- `vyrez` a `overit` odmítnou souřadnice v pixelech.
- `aron_search` při chybě opakuje dotaz.
- Mapa na webu přes celou šířku.

**Návody**
- ZA Opava (přepsáno), MZA Acta Publica, Geneteka API, rejstříky v Matricule.
- Druhopisy, roční výtahy, obce mezi farami, nejisté datum, chybějící nejmladší svazky.
- Přihlášení k Netlify v agentovi, oběti 2. světové války.

## 0.4.7 – 22. 10. 2026

**Opravy**
- Roky „– před 1888“ / „po 1921“ ve vějíři i na webu.
- `policie_prihlasky.py`: karta i pro pořadí nad 20.
- Konce řádků LF (`.gitattributes`, `novy_projekt` převede `.sh`).

**Návody**
- Příbuzenství doslova, datum sňatku ve křtu, špatný měsíc v oddacím zápisu, posun snímek–strana, Windows.

## 0.4.6 – 22. 10. 2026

**Opravy**
- UTF-8 výstup ve všech nástrojích (#11).
- Certifikát Porta fontium.
- `ged_import` čte Brother's Keeper (ANSI, česká data).
- `trebon`: hláška pro neznámá místa.

**Návody**
- winget, kontrola Pythonu, rejstřík místo chybějící matriky, pomocníci, Geneteka.

## 0.4.5 – 22. 10. 2026

**Opravy**
- `trebon.py`: místo bez diakritiky a mezer.
- `soal_zoomify` stahuje jen ze serverů archivů.
- `ramecek` ověří ImageMagick před zápisem.
- `.claude/launch.json` pro náhled webu v Claude desktop.

**Návody**
- Netlify Team protection, civilní matriky v Třeboni, posun stran v eBadatelně, víceznačné obce, heredoc ve Windows.

## 0.4.4 – 22. 10. 2026

**Opravy**
- Kontrola ImageMagicku před stahováním.
- `aron_search`: víc slov a řazení podle fary.
- Kontrola nefunkčních odkazů v textech webu.
- ZA Opava přes `soal_zoomify`.

**Návody**
- Rejstříky podle německého pravopisu.

## 0.4.3 – 21. 10. 2026

**Opravy**
- `overit.py` bere souřadnice jako zlomky.

**Návody**
- Rejstříky o pár stran vedle, evangelické a židovské matriky, údaje z cizích stromů ověřit jménem.

## 0.4.2 – 21. 10. 2026

**Nové**
- Claude sám nabídne aktualizaci projektu (verze skillu v `VERZE`, projekt si ji pamatuje v `.skill_verze`).
- Aktualizace projektu přepíše i změněné šablony webu (se zálohou do `pracovni/`); export odmítne starou šablonu přihlášení (#9).

**Opravy**
- `ftb_export`: vazby v rodinách jen na osoby, které jsou v exportu (#4).
- Porta fontium: odkaz spárovaný přímo se snímkem, kontrola výřezu, čekání po HTTP 429 a pauza mezi požadavky (#5).

## 0.4.1 – 21. 10. 2026

**Nové**
- Vedlejší nálezy se nezahazují (jedna věta v deníku).
- Hřbitovy jako doplňující otázka k úmrtí; formulace k hrobům bez návrhů na otevírání.
- FamilySearch: snímky filmů a limit 429.

**Bezpečnost** (podle externí analýzy)
- Nasazení bez přihlašovací otázky skončí chybou, v cookie jen otisk odpovědi.
- Escapování v mapě, v tooltipu mapy a v legendě vějíře.
- Cache ARON ve složce projektu, `novy_projekt` nepíše přes symlinky.

## 0.4.0 – 21. 10. 2026

**Nové**
- `portafontium.py` – matriky SOA Plzeň bez prohlížeče.
- `ebadatelna.py` – matriky a archiválie SOA Praha bez prohlížeče.
- `ftb_export.py` – záloha MyHeritage (`.ftb`) → GEDCOM a přehled přímé linie.
- Podpora Windows (Python bez `python3`, UTF-8, limit délky příkazu, Chrome/Edge).
- Bohatší ukázková rodina, licence MIT, upozornění v README, odkazy na genealogické společnosti, hlášení chyb přes issues.

**Opravy**
- `ged_import --osoby` escapuje jména (uvozovky ve jménu rozbily `osoby.py`).
- `vyrez.py` maže EXIF/GPS z fotek a otáčí je podle orientace.
- `fan_chart.py`: předek starší než 10. generace neshodí vějíř ani export webu.
- `ebadatelna.py`: stránkování u obcí s víc než 50 knihami; `portafontium.py`: název fary s diakritikou.

## 0.3.0 – 20. 10. 2026

- Oprava roků u neznámého narození.
- Policejní přihlášky, SOA Litoměřice.
- Pomocníci na modelu Sonnet, sporná čtení.

## 0.2.0 – 16. 10. 2026

Poučení z prvního ostrého projektu.

- Nové nástroje: `trebon.py`, `ahmp_*`, `matricula_*`, `anno*`, `kramerius.py`, `overit.py`, `ged_import.py`, `napady.py`.
- Metodika: začínat od nejmladšího zápisu, ověřování pomocníků, noviny u úředníků a vojáků.
- Zajímavosti průběžně a „Příběh rodu“ s konceptem ke schválení.
- `kontrola.py`: citlivé údaje z 20. století na webu.

## 0.1.0 – 16. 10. 2026

První verze: průvodce, nástroje, šablona webu a ukázka.
