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

## Selhání portálu

Hlásí se příkazem `fronta.py selhani <id> --druh prechodna|zakaz --portal ARON`.

- **Přechodná chyba** (503, časový limit): úkol dostane `stav:čeká` a režim `kdy:` podle `data/rezim.json` → `opakovani`. Výchozí pořadí:
  nejdřív za dvě noci (aspoň každou druhou noc), pak o víkendu, pak v pracovní době (výpadky portálů se liší podle doby). `fronta.py dalsi` pustí
  takový úkol jen v jeho režimu (úkol s `kdy:pracovni` smí běžet i přes den). Po vyčerpání pokusů: jedno rozhodnutí za portál.
- **Zákaz nebo zablokování** (403, brzda „zastavený“): žádný automatický opakovaný pokus; hned **jedno rozhodnutí za portál**: „portál nejde číst
  automaticky, čekají úkoly …: počkat, nebo přeřadit do ručního bádání?“ Další úkoly téhož portálu se připojí ke stejnému rozhodnutí
  (`cíl:portal:<portál>`) a závisejí na něm, takže se po rozhodnutí samy odblokují.

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
- **Typ:** otevřená množina – `bádání`, `skill` (úprava skillu), `test`, `údržba`.
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
