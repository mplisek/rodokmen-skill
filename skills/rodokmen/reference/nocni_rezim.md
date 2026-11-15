# Noční a víkendový režim – fronty úkolů

Platí pro práci bez člověka: úkoly, které jde dělat automaticky, běží mimo pracovní dobu a výsledky se zapisují do front.
Nástroj: `python3 -I tools/fronta.py --help`. Konfigurace: `data/rezim.json`.

## Pět front (soubory v `data/`)

| Soubor | Co v něm je | Kdo ho řeší |
| --- | --- | --- |
| `ukoly_na_noc.md` | úkol, který jde udělat automaticky, bez člověka | hlavní agent + pomocníci |
| `ukoly_k_rozhodnuti.md` | věc, kde musí rozhodnout člověk | člověk |
| `ukoly_k_badani.md` | jen online v prohlížeči, kam skript nesmí (eBadatelna, MZA, Třeboň) | člověk s asistentem |
| `ukoly_dotazy_na_archivy.md` | co online není | žádost archivu |
| `ukoly_na_rodinu.md` | nápad na otázku pro rodinu | rodina |

**Směrování nálezu** (kam co zapsat, když při práci narazíš na něco nového). Úkol jde první větví, na kterou odpovíš „ano“:

1. **Je to už v datech nebo v dříve přečtených zdrojích** (cache, stažené svazky) a stačí to zapsat? → hotovo, zapsat do dat.
2. **Jde to vyřešit čtením online zdrojů, které smí skript** (i z cache)? → **na noc** (automatické bádání).
3. **Je to online, ale skript tam nesmí, nebo musí pomoct člověk?** → **k bádání** (ruční hledání, např. přes Playwright).
4. **Online to není?** → **archivní dotaz**.
5. **Může to vědět rodina?** → **otázka pro rodinu**. Ptej se jen na to, co rodina může pamatovat: **nejvýš 3–4 generace** zpět
   a **zajímavosti** (příběhy, souvislosti). Starší otázky patří archivu. Odpověď rodiny je důkaz stupně `fam`: nepřebije zápis v matrice,
   jen založí úkol k ověření ve zdrojích.
6. **Je to nejasné a rozhodnout může badatel?** → **k rozhodnutí**; původní úkol se odloží (`stav:odloženo`) a odkazuje na rozhodnutí.

**Do rozhodnutí patří jen výběr, který stroj udělat nemůže:** nejasná podoba jména nebo ztotožnění („Vzor, nebo Wzor“), dva kandidáti
se stejnými důkazy, spor zdrojů, cena a způsob („celý svazek má 123 listů, nákladné: automaticky, nebo ručně?“), soukromí a vše, co se odesílá ven.
**Nepatří tam:** potvrzení vlastní změny, kontrola nebo porovnání dat, „přečíst znovu“ a věcné otázky, na které odpovídají zdroje
(„v roce 1895 se ženil Jan, bral si Marii, nebo Janu?“ se zjistí čtením). Nejistotu zapiš jako `prob` s kandidátem v poznámce a úkol dej do fronty 2–4.

**Úkol k rozhodnutí má povinná pole** (`fronta.py pridej rozhodnuti` bez nich úkol odmítne):

```text
Otázka: jedna věta
Možnosti: A) …; B) …
Důkazy: odkazy na zápisy a řádky deníku
Zkoušeno: co už se zkusilo (včetně druhého čtení naslepo)
Doporučení: A
Výchozí postup: co se stane, když uživatel neodpoví (práce tím nestojí)
```

Povinné jsou Otázka, Možnosti (aspoň dvě, oddělené středníkem) a Výchozí postup; Důkazy, Zkoušeno a Doporučení se doporučují.
`fronta.py kontrola` varuje u starých úkolů bez těchto polí a u otázek, které začínají slovesem práce (ověřit, zkontrolovat, porovnat…).
Zakládá je jen hlavní agent (orchestrátor) na konci pracovní jednotky, když je další krok zablokovaný; podagenti vrací „potřebuje rozhodnutí“
ve výsledkovém souboru.

## Router: úkoly proudí přes vstup

Nový úkol nevzniká přímo v cílové frontě. Zakládá se do **vstupu** (`ukoly_vstup.md`: `fronta.py pridej vstup --text …`; dokud soubor ve
složce `data/` není, platí starší chování a lze zakládat přímo). **Router** je krok orchestrátora; pro každý úkol ve vstupu:

1. **Kontrola dat:** je cíl už v datech? Pak `fronta.py smeruj` úkol nezařadí a odkáže na `fronta.py hotovo`.
2. **Duplicity:** podobný úkol v jiné frontě se doplní a úkol ze vstupu zmizí.
3. **Definice hotového (DOD):** `--dod "co je výsledek a kde bude zapsán"` je povinná, uloží se do textu jako řádek `Definice hotového: …`.
   Úkol bez ní se nesměruje.
4. **Zařazení:** `fronta.py smeruj <id> --do noc|badani|dotazy|rodina|rozhodnuti --dod … [--cena S|M|L|XL] [--p P1]`; do rozhodnutí jen úkol
   s povinnými poli (viz níže). Portál, kam skript nesmí (tabulka `ZAKAZ`), znamená `badani`.
5. **Dělení:** `fronta.py rozdel <id> --cast FRONTA "text" "DOD" --cast …` rozdělí úkol na části v různých frontách (každá s DOD a `rodič:`);
   hotová část se ze zadání prostě vynechá, protože je v datech.
6. **Parkování:** `fronta.py zaparkuj <id> --do RRRR-MM-DD --duvod "…"` nastaví `stav:čeká`; úkol se sám vrátí mezi připravené, až datum
   uplyne (`fronta.py frontier`, `dalsi`). Hodí se pro zápis, který se zpřístupní později, nebo pro odpověď archivu.

Cena `S`, `M`, `L`, `XL` je odhad nákladu (složitost, počet snímků, model); `XL` patří do rozhodnutí („provést, odložit, nebo ručně?“),
aby první dva velké úkoly nespálily limit na noc.

**Slučování:** nový úkol se doplní do existujícího jen **ve stejné frontě** a jen když jde o tentýž úkol: shodný cíl (`cíl:`), nebo (bez cíle
u obou) stejný typ a přesně stejné osoby. Pouhý překryv osob nestačí, dva úkoly o téže osobě mívají jiný záměr. `--nove` (u `pridej` i `smeruj`)
sloučení zakáže.

## Selhání portálu

Hlásí se příkazem `fronta.py selhani <id> --druh prechodna|zakaz --portal ARON`.

- **Přechodná chyba** (503, časový limit): úkol dostane `stav:čeká` a režim `kdy:` podle `data/rezim.json` → `opakovani`. Výchozí pořadí:
  nejdřív za dvě noci (aspoň každou druhou noc), pak o víkendu, pak v pracovní době (výpadky portálů se liší podle doby). `fronta.py dalsi` pustí
  takový úkol jen v jeho režimu (úkol s `kdy:pracovni` smí běžet i přes den). Po vyčerpání pokusů: jedno rozhodnutí za portál.
- **Zákaz nebo zablokování** (403, brzda „zastavený“): žádný automatický opakovaný pokus; hned **jedno rozhodnutí za portál**: „portál nejde číst
  automaticky, čekají úkoly …: počkat, nebo přeřadit do ručního bádání?“ Další úkoly téhož portálu se připojí ke stejnému rozhodnutí
  (`cíl:portal:<portál>`) a závisejí na něm, takže se po rozhodnutí samy odblokují.

## Rozpočet na noc

Na noc bývá víc úkolů, než se stihne nebo než vydrží limit. Proto má úkol **pásmo ceny** `S`, `M`, `L`, `XL` (odhad podle složitosti, počtu snímků
a modelu; `fronta.py smeruj … --cena`, nebo `uprav --cena`) a okno má rozpočet.

- **Rozpočet** je v `data/rezim.json` → `rozpocet`: `vahy` (výchozí S 1, M 3, L 8, XL 20), `okno` (výchozí noc 24, víkend 60) a `prah` (výchozí XL).
  Váhy jsou odhad a mění se podle skutečnosti (`fronta.py kalibrace`).
- **Řazení:** priorita, pak cena (levné napřed); úkol bez ceny je před oceněnými.
- **Práh:** úkol v pásmu od prahu výš (XL) smí na noc **jen po schválení člověkem**. `fronta.py smeruj --do noc --cena XL` ho odmítne a odkáže
  na rozhodnutí („provést, odložit, nebo ručně?“); po schválení se zařadí s `--schvaleno` a v textu přibude řádek `Schváleno: …`.
  `fronta.py dalsi` neschválený úkol z prahu nepřidělí.
- **Čerpání:** `fronta.py dalsi` přidělí úkol, označí ho `stav:probíhá` (podruhé se nepřidělí ani nepočítá) a přičte jeho váhu k spotřebě okna
  (`data/.rozpocet.json`, pracovní stav mimo git). Co se do zbytku okna nevejde, počká na další okno; vyčerpaný rozpočet `dalsi` oznámí.
- **Plán okna:** `fronta.py plan [fronta]` ukáže pořadí, kumulativní váhu a které úkoly jsou mimo rozpočet nebo čekají na schválení.
- **Kalibrace:** `fronta.py hotovo <id> --spotreba S|M|L|XL` zapíše skutečnou cenu; `fronta.py kalibrace` porovná odhady při směrování se skutečností
  a řekne, které pásmo je podhodnoceno nebo nadhodnoceno.
- **Identita:** číslo úkolu (`U-0042`) se nikdy znovu nepřidělí; smazaný úkol svoje ID neuvolní, protože po něm zůstává historie.

## Před každým čtením: mapa knihy, mezipaměť a historie

Platí pro každé čtení, v noci i přes den. Cílem je stahovat z archivu jen to, co je opravdu potřeba.

- **Mapa knihy** (`tools/mapa.py`): u každého snímku svazku si pamatuje, co pokrývá (písmena rejstříku, roky, čísla zápisů, titul, prázdná strana).
  `mapa.py hledej <portál> <svazek> --pismeno F | --rok 1856 | --cislo 107` z dvou známých bodů odhadne, který snímek číst (jako při hledání ve slovníku),
  a vrátí i okolní popsané stránky. **Je to jen rada a nikdy neuzavře hledání:** „není tam“ vyžaduje přečíst stránky, které cíl ohraničují (R-NEG-001);
  pořadí v rejstřících a číslech zápisů nemusí být přísné.
- **Co se ukládá:** jen navigační údaje o stránce (typ, od–do, sloupce, kvalita, kdo a čím četl), žádné přepisy a jména. Proto je mapa společná pro
  všechny projekty na počítači: `rodokmen_mapy/<portál>/<svazek>.jsonl` vedle mezipaměti snímků (mimo její úklid; jen přidávání, poslední čtení snímku platí).
  Přepisy a deník zůstávají v projektu.
- **Kdo zapisuje:** čtenář (`researcher`, `browser-reader`) vrací údaje o stránkách ve výsledkovém souboru (`stranky`); orchestrátor je nechá zapsat přes `fixer`
  (`mapa.py zapis`). Agent nezapisuje mimo `pracovni/vysledky/`.
- **Identita:** snímek, který vstoupí do mezipaměti (`aron_img.py`; z prohlížeče výsledek `browser-readeru` s adresou, svazkem a číslem snímku), se zapíše do mapy;
  dříve stažené svazky doplní `mapa.py naplnit-z-pracovni`, eBadatelnu v mezipaměti `mapa.py naplnit-z-cache`.
- **Další zdroje, které se zeptají před stažením:** `pracovni_prehled.py --hledej`, `cache.py najdi <adresa>` a historie čtení (`fronta.py znovu`).
- **Měření:** `cache.py stav` ukáže „Stažených snímků na nalezený záznam“; klesá-li, mapa archivy šetří.

## Zadání, nález a ověření: jeden kontrakt

Čtení pramene se předává třemi soubory, jejichž tvar drží jediný nástroj `tools/vysledek.py` (`vzor` vypíše vyplněný příklad a dovolené hodnoty):

- **Zadání** `pracovni/zadani/<úkol>.json` sestaví řídicí agent příkazem `tools/zadani.py novy` (otázka, hledaná role, osoby klíčem a znaky, podle
  kterých se poznají, jmenovci k nezaměnění, svazek klíčem, rozsah snímků, pole k přečtení, strop kroků a snímků). Nástroj zadání odmítne dřív,
  než se čtenář spustí: neznámá osoba, signatura místo klíče svazku, nebo pramen, který hledanou roli nevede.
- **Pokrytí pramene** se zapisuje ke svazku v `data/svazky.json` jako `"pokryva": {"role": ["ženich"]}` (koho rejstřík vede; přes `tools/zapis.py svazky`).
  Rejstřík ženichů tak nejde zadat k hledání nevěsty a „nenalezeno“ z něj se nepřijme. Svazek bez `pokryva` se nekontroluje.
- **Nález** `pracovni/vysledky/<úkol>.json` píše čtenář a před koncem ho sám ověří (`vysledek.py over`). Vrací pozorování: doslovný přepis,
  normalizaci, nejistotu, chybějící pole, kandidáty s důvody pro a proti, přečtený rozsah, popis stránek pro mapu knihy, návrh dalšího kroku
  a čerpání. O identitě osoby a o hotovém úkolu nerozhoduje.
- **Stavy:** `nalezeno`, `částečně`, `nečitelné`, `nenalezeno`, `nedostupné`, `rozpočet`, `vyvráceno`, `chyba prostředí`. „Nenalezeno“ jen po dočtení
  celého zadaného rozsahu; dosažený strop (`rozpočet`), nedostupný portál a nečitelný snímek jsou jiné stavy a úkol neuzavírají.
- **Pokračování:** zápis přetéká na další stranu nebo je potřeba další snímek → čtenář to navrhne, řídicí agent schválí `tools/zadani.py rozsir`
  a pokračuje se v **témže úkolu**; čtení mimo schválený rozsah nález neprojde.
- **Ověření naslepo** `pracovni/vysledky/<úkol>_overeni_<čtení>.json`: ověřovatel dostane jen výřezy a seznam polí a vrací vlastní přepis.
  Shodu vyhodnotí `tools/vysledek.py porovnej <úkol> <čtení>` po polích; při neshodě zůstávají oba přepisy a tvrzení je nejvýš `prob`.
- **Souhrn pro řízení:** `tools/vysledek.py souhrn <úkol>` (stav, co chybí, nejistoty, kandidáti, rozsah, návrh, čerpání); přepis zůstává v souboru.

**Dělení úkolu:** `fronta.py rozdel <id> --cast FRONTA "text" "DOD" os=… [typ=…] [cena=…]`; má-li rodič víc osob, každá část uvede své, mlčky je
nedědí. Definici hotového mění `fronta.py uprav <id> --dod "…"`.

## Historie úkolů a opakované čtení

- **Historie:** každá změna úkolu (vznik, doplnění, směrování, dělení, parkování, selhání, přesun, hotovo) se připíše do `data/ukoly_historie.jsonl`
  (jen přidávání, jeden JSON na řádek). Hotový úkol se z fronty maže, ale zůstane po něm stopa. `fronta.py historie [<id>]` vypíše události
  úkolu i jeho dětí po rozdělení. `fronta.py hotovo <id> --denik 12,13 --soubory pracovni/vysledky/x.json --spotreba M` zapíše, co úkol vyřešilo
  (řádky deníku, soubory) a jeho skutečnou cenu.
- **Metadata čtení v deníku:** `denik.py pridej … --ukol U-0042 --model sonnet --snimky 03066862:236-258` (a `--nastroj`, výchozí je verze skillu
  z `.skill_verze`). Na web nejdou. Strojově čitelný seznam snímků nahrazuje volný text u nových záznamů.
- **Opakované čtení podle schopností:** `fronta.py znovu --starsi-nez <verze> [--vysledek nečitelné,nenalezeno] [--zaloz]` najde v deníku
  neúspěšná čtení, která dělal starší (nebo neznámý) nástroj, a založí na ně úkoly (do vstupu, jinak do fronty noc). Úspěšná, ověřená čtení se
  neopakují. Spouští se po zlepšení nástroje nebo modelu.

**Skutečná spotřeba:** `tools/spotreba.py sezeni` sečte ze záznamů sezení, kolik stálo hlavní vlákno a kolik pomocníci podle role a modelu
(„ekv“ = vstup + 1,25 × zápis mezipaměti + 0,1 × čtení mezipaměti + 5 × výstup; vážené číslo pro srovnání, ne účet), `spotreba.py ukol U-…`
pomocníky jednoho úkolu (zadání pomocníka proto vždy jmenuje ID úkolu). Jen čte. Podle toho se opravují pásma S až XL.

## Fronta na noc

**Noční fronta je jen na to, co jde skriptem a bez člověka** (ARON a jiné portály, které skript smí). Úkol, který vyžaduje prohlížeč,
archiv, rodinu nebo čeká na lhůtu, se nezakládá do `ukoly_na_noc.md` s poznámkou „nelze v noci“, ale rovnou do správné fronty
(`ukoly_k_badani.md`, `ukoly_dotazy_na_archivy.md`, `ukoly_na_rodinu.md`) s důvodem v textu úkolu. Do souboru fronty se nepíšou stavové
odstavce o konkrétních osobách (stav patří do úkolů a dat); šablona fronty je negeneruje.

**Invariant:** úkol nikdy nezmizí bez stopy. Končí tím, že je celý zapsán do dat, nebo se jeho zbytek zapsal do jiných úkolů.
Upřesnění = nový úkol, rozdělení = víc úkolů, přeřazení = `fronta.py presun`. Hotový úkol se maže (`fronta.py hotovo`).

## Formát úkolu a pravidla zápisu

```text
## U-0412 | P1 | os:57,114 | typ:křest | cíl:krest:115 | rodič:U-0398 | stav:otevřeno
Text úkolu: co hledat, kde, co už je prohlédnuto.
```

- **Priorita:** P1 odemyká chybějícího předka, P2 mění „prob“ na „doc“, P3 ověřuje rodinný údaj. Fronty se při každém zápisu třídí
  (priorita, id).
- **Duplicity:** `fronta.py pridej` porovná typ, osoby a cíl ve všech frontách; podobný úkol se nezaloží, ale **doplní**
  (osoby, text, vyšší priorita). Částečný překryv: doplň jeden z úkolů a druhý zúž (`uprav`).
- **Cíl (`cíl:krest:115`, `umrti:`, `snatek:`)** umí `fronta.py kontrola` ověřit v datech; splněný úkol ohlásí ke smazání.
- **Typ:** otevřená množina podle věci (`křest`, `úmrtí`, `bádání`…). Úkoly na úpravu skillu se ve frontách **nevedou**: v projektu patří do `data/poznamky_pro_skill.md`,
  v repozitáři skillu do `analyza/ukoly_na_skill.md`; typy `skill`, `test` a `údržba` `fronta.py` odmítne a `kontrola` na staré upozorní.
- Úkoly mohou vznikat z jiných úkolů (`rodič:`).

## Režimy podle času

`data/rezim.json`: `pracovni_dny`, `pracovni_od` / `pracovni_do` (výchozí všední dny 6:00–22:00), `svatky` (berou se jako víkend),
`pomocniku` (max. souběžných pomocníků), `dod` (volitelná omezení běhu; výchozím ukončením je čas). `fronta.py rezim` řekne režim
a konec okna.

- **Mimo pracovní dobu (noc, víkend, svátek)** běh spouští uživatel. Jede se do konce úkolů, **konce okna**, nebo do DOD.
  Doběhne-li úkol po začátku pracovní doby, **další se nepouští**; končí-li okno dříve, hlavní agent pouští další úkol.
  Nikdy se neptá: rozhodnutí → `ukoly_k_rozhodnuti.md`, úkol se odloží; nelze-li online → `ukoly_k_badani.md`;
  není online → `ukoly_dotazy_na_archivy.md`; nápad pro rodinu → `ukoly_na_rodinu.md`.
- **V pracovní době** po doběhu vyhodnoť výsledky, ulož, vypiš dotazy (rozhodnutí, nové úkoly k bádání) a čekej na instrukci.
- **Po každém doběhu úkolu hlavní agent vždy zkontroluje výstupy a zápis** a výsledek zapíše tam, kam patří (data, fronty).
- Chyba portálu (brzda „zastavený“): úkol zůstane `otevřeno`, zapíše se do deníku a běh končí.

## Čekání a odesílání ven

- **Čekání:** úkol, který čeká na odpověď archivu nebo na datum, má `stav:čeká` a `do:<datum>` (`fronta.py zaparkuj`, nebo `odeslano`). Mezi úkoly k řešení se
  neukazuje: `fronta.py seznam` je jen spočítá a `fronta.py cekajici` je vypíše seřazené podle data s důvodem (`seznam --vse` ukáže všechno). Po uplynutí data
  se úkol sám vrátí mezi připravené.
- **Odesílá vždy člověk:** dotaz archivu a otázku pro rodinu agent jen **připraví** (úkol zůstane ve frontě `dotazy` nebo `rodina`); odeslat smí jen uživatel. Až odešle,
  zapíše se to příkazem `fronta.py odeslano <id> --uzivatel "kdo odeslal" [--odpoved-do RRRR-MM-DD]`: úkol dostane `stav:čeká` do data odpovědi
  (výchozí `data/rezim.json` → `odpoved_dnu`, 30 dnů), v textu řádek `Odesláno: …` a v historii záznam s tím, kdo odeslání potvrdil. Bez `--uzivatel` příkaz odmítne.

## Brzda: bádání × úprava skillu

V jednom běhu jede **buď bádání, nebo úprava skillu**, nikdy obojí. Zámek: `fronta.py zamek start badani|skill`, `stop`, `stav`
(`data/.beh.json`, vyprší s koncem okna); `fronta.py dalsi` nepustí úkol jiného druhu. Úprava skillu běží **ve feature větvi**
(`skill/<téma>`, bez push, vydání a nasazení); ráno se rozhodne, co s větví. Změna pravidel bádání (metodiky) až po rozhodnutí.

## Kdo úkol dělá

| Činnost | Kdo |
| --- | --- |
| směrování, priorita, slučování a dělení úkolů, ověření čtení, ztotožnění, spory zdrojů, zápis do dat, úpravy skillu | hlavní agent s plným kontextem |
| rutinní čtení snímků a rejstříků, hledání knih v ARONu | podagent na středním modelu (`sonnet`) |
| mechanické práce (stahování, hromadné přejmenování, oprava lintu, migrace podle šablony) | podagent na nižším modelu |
| složité čtení (kurent, špatné snímky), nejasné ztotožnění | hlavní agent, případně podagent na vyšším modelu s přesným zadáním |

Model odpovídá složitosti úkolu. Podagent **nikdy nezapisuje do `data/` ani do skillu**, píše jen do `pracovni/pom_<téma>/`.
Brzda `slusne.py` a limit souběžných pomocníků (`rezim.json`) platí dál. Jen ARON, nic se neodesílá ven.

## Nejisté čtení v noci

Do dat jdou jen **jisté** údaje (shoduje se jméno, rodiče, místo a datum). Nejisté se zapíše jako **kandidát v poznámce** osoby
(stav zůstane `prob`). Pak:

1. **druhé čtení naslepo** (agent `verifier`, bez cizího přepisu), případně čtení ve větším rozlišení (úkol na noc nebo k bádání);
2. pokud se čtení shodují, údaj se potvrdí; pokud ne, nebo když chybí zdroj online, jde úkol do fronty podle směrování výše (archivní dotaz,
   ruční bádání);
3. **do `ukoly_k_rozhodnuti.md` jde jen trvalý rozpor mezi kandidáty**, který čtením nevyřešíš, s povinnými poli úkolu k rozhodnutí.

Šablony a zakázané údaje o procesu: `zapisy.md`.
