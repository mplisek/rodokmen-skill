# Návrh: router úkolů, pravidla front, rozpočet a historie

Stav: **návrh k ladění** (14. 11. 2026), nic z toho není implementováno. Vychází z rozhovoru o frontách (`reference/nocni_rezim.md`),
z auditu fronty „k rozhodnutí“ a z pozorování běhu orchestrátora. Příklady jsou vymyšlené (anonymita).

## 1. Proč

- Do fronty „k rozhodnutí“ se dostaly úkoly, které rozhodnutí člověka nepotřebovaly (potvrzení vlastní opravy, mechanické porovnání dat).
- Metodika to sama podporuje: odstavec „Nejisté čtení v noci“ posílá nejisté čtení do rozhodnutí s možností „přečíst znovu“, což je strojová práce.
- Úkol nemá jednotné místo, kudy vstupuje, takže o frontě, definici hotového (DOD), dělení a ceně rozhoduje ten, kdo ho právě zakládá.
- Hotový úkol se maže a po něm nezůstane stopa, kterou by šlo použít (co se četlo, čím, kdy).

## 2. Pravidla směrování (rozhodovací postup)

Úkol se řadí první odpovědí „ano“:

1. **Je v datech, nebo v dříve přečtených zdrojích (cache, historické svazky), a stačí to jen zapsat?** → hotovo (zápis do dat, úkol se uzavře).
2. **Jde vyřešit čtením online zdrojů, které smí skript (i z cache)?** → **noc** (automatické bádání).
3. **Je to online, ale skript tam nesmí (tabulka `ZAKAZ`), nebo musí pomoct člověk?** → **k bádání** (ručně, např. Playwright).
4. **Není to online?** → **dotazy na archivy** (odeslání jen člověkem, viz kap. 6).
5. **Může to vědět rodina?** → **na rodinu**. Patří sem jen to, co rodina může pamatovat: **nejvýš 3–4 generace zpět** (osobní vzpomínka, doma
   uložené doklady, fotografie) a **zajímavosti** (příběhy, souvislosti). Starší otázky patří archivu. Odpověď rodiny je důkaz stupně `fam`:
   nikdy nepřebije zápis v matrice, jen založí úkol k ověření ve zdrojích (rodina uvádí jednu matku, matrika jinou).
6. **Je to nejasné a rozhodnout může badatel?** → **k rozhodnutí**. Jen výběr, který stroj nemůže udělat:
   - nejasná identita nebo podoba jména („Vzor, nebo Wzor“), dva kandidáti se stejnými důkazy, spor zdrojů,
   - cena a způsob („celý svazek má 123 listů, nákladné: automaticky, nebo ručně?“),
   - selhání serveru, které se neopraví opakováním (viz 4.3),
   - soukromí a vše, co se odesílá ven.

Do rozhodnutí **nepatří**: potvrzení vlastní změny, kontrola nebo porovnání dat, „přečíst znovu“ a **věcné otázky, na které odpovídají zdroje**
(„v roce 1895 se ženil Jan, bral si Marii, nebo Janu?“ se zjišťuje čtením, ne rozhodnutím). Nejistota se zapíše jako `prob` s kandidátem
v poznámce a úkol jde do fronty 2–4.

Fronty a jejich soubory se nemění (`ukoly_na_noc.md`, `ukoly_k_badani.md`, `ukoly_dotazy_na_archivy.md`, `ukoly_na_rodinu.md`,
`ukoly_k_rozhodnuti.md`).

## 3. Router: jedno místo, kudy úkoly proudí

**Pravidlo:** nový úkol nikdy nevzniká přímo v cílové frontě. Vstupuje přes router.

- **Vstup** (`data/ukoly_vstup.md`, pátá a šestá fronta zůstávají beze změny): sem píše kdokoli (orchestrátor, uživatel). Agenti frontu nezakládají,
  vracejí „potřebuje rozhodnutí / další úkol“ ve výsledkovém souboru a zapíše ho orchestrátor.

- **Router je role orchestrátora** (krok postupu před kartou), ne nový agent. Pro každý úkol ve vstupu:
  1. **Kontrola dat:** je to už v datech (`fronta.py kontrola`, cíl úkolu)? → hotovo.
  2. **Duplicity:** podobný úkol existuje (typ, osoby, cíl)? → doplnit existující.
  3. **DOD:** napíše definici hotového (co je výsledek, kde bude zapsán). Úkol bez DOD se nesměruje.
  4. **Směrování** podle kap. 2; portál se bere z tabulky `ZAKAZ` (portál, kam skript nesmí, = `k bádání`).
  5. **Cena** (kap. 5): vyšší než práh → do rozhodnutí.
  6. **Dělení a parkování:** úkol se rozdělí do více úkolů v různých frontách; hotová část se uzavře, zbytek se zaparkuje (`stav:čeká`, `do:` datum).

- **Výstup routeru** je záznam v historii (kap. 6): odkud, kam, proč, DOD, odhad ceny.

Nástroj: `fronta.py smeruj <id> --do <fronta> --dod "…" --cena S|M|L|XL`, `fronta.py rozdel <id> …`, `fronta.py zaparkuj <id> --do 2028-11-03`.
`fronta.py pridej` do jiné fronty než `vstup` odmítne (výjimka: `--smerovano`, jen pro samotný router).

## 4. Selhání a čekání

### 4.1 Přechody po selhání

| Výsledek úkolu v `noc` | Kam |
|---|---|
| nalezeno | zápis do dat, úkol hotový |
| nenalezeno online, kniha není online | `dotazy` |
| nenalezeno, ruční hledání může pomoct | `k bádání` |
| nečitelné | `noc` znovu ve větším rozlišení, jinak `k bádání` |
| nejasné ztotožnění | `k rozhodnutí` |
| chyba portálu | viz 4.3 |

### 4.2 Čekání

Úkol čekající na odpověď archivu nebo na datum (zápis zpřístupněný až v pozdější době) má `stav:čeká` a `do:<datum>`. Do té doby se
neukazuje mezi úkoly k řešení, jen v přehledu čekajících.

### 4.3 Chyba serveru

Navrhovaná odchylka od „chyba = rozhodnutí“, aby každý výpadek nezaplavil frontu (Q3 potvrzeno s úpravou 14. 11. 2026):

- **Přechodná chyba** (503, časový limit): router úkol sám vrátí do fronty, **nejdřív za dvě noci** (odstup aspoň každou druhou noc).
- **Jiný režim:** když to v noci stále selhává, zkusí se **o víkendu** a pak **přes den v pracovních hodinách** (výpadky portálů se liší podle doby).
  Počet pokusů v každém režimu a pořadí je v `rezim.json: opakovani`.
- **Zákaz nebo zablokování** (403, brzda „zastavený“): nikdy automatický opakovaný pokus.
- Teprve po vyčerpání režimů nebo při zákazu vznikne **jedno společné rozhodnutí za portál**: „portál X nedostupný, čeká N úkolů: počkat,
  nebo přeřadit do ručního bádání?“

## 5. Rozpočet na noc

- Router odhadne cenu úkolu v **pásmech** S, M, L, XL (podle složitosti 0–6 z orchestrátora, počtu snímků a modelu), ne v přesných tokenech
  (odhad se liší několikanásobně).

- `rezim.json: rozpocet` = počet úkolů nebo odhad v pásmech na noc a **práh XL**. Úkol nad prahem jde do rozhodnutí
  („provést, odložit, nebo ručně?“), aby první dva velké úkoly nespálily limit.

- Řazení na noc: priorita, pak cena (levné P1 napřed).
- Skutečná spotřeba dokončeného úkolu (z hlášení podagenta) se zapíše do historie a **kalibruje pásma** (kap. 6).
- Reálný limit předplatného agent nevidí, proto je rozpočet odhad a čas okna zůstává tvrdým stropem.

## 6. Identita, historie a mapa knihy

Potvrzeno 14. 11. 2026 (grilování Q-M1 až Q-M7).

### 6.1 Historie úkolů

- **Úkol má stabilní ID** (`U-0412`, už existuje) a **historii událostí** `data/ukoly_historie.jsonl` (jen přidávání, jako deník):
  vznik, směrování, dělení, parkování, hotovo; kdo (orchestrátor, uživatel), odkud a kam, důvod, DOD, odhad a skutečná cena, odkazy na řádky deníku
  a výsledkové soubory. Hotový úkol se z fronty maže dál, v historii zůstane.
- **Metadata čtení v deníku:** pole `ukol` (ID úkolu), `nastroj` (verze skillu a nástroje), `model` (kdo četl) a `snimky` (strojově čitelný seznam
  místo volného textu `rozsah`).
- **Opakované čtení podle schopnosti:** `fronta.py znovu --vysledek nečitelné,nenalezeno --starsi-nez <verze>` najde v deníku čtení, která skončila
  neúspěšně a četl je starší model nebo nástroj; router z nich založí nové úkoly jen pro ně.

### 6.2 Mapa knihy

**Nápad (uživatel):** u každého snímku vědět, co pokrývá (písmena A–C, roky 1830–1840, titul, prázdná strana), aby se stahovalo jen to, co je potřeba:
z mapy se pozná, že hledané písmeno F leží mezi známými body, a stáhne se rovnou správná stránka. Popis přežije smazání obrázku z cache a upraví se
při každém dalším čtení. Zjistí-li se, že snímek obsahuje jiný rozsah, než se čekalo, uloží se to.

**Rozhodnutí:**

- **Struktura (Q-M1):** jedna mapa na svazek (soubor s událostmi, jen přidávání) a stávající `data/svazky.json` jako registr svazků.
  Žádné soubory vedle každého snímku a žádný „index indexů“.
- **Obsah (Q-M2):** jen navigační údaje o stránce: snímek, typ (titul, rejstřík, zápisy, prázdná), od, do (písmeno, datum nebo číslo), sloupce,
  kvalita, kdy, kdo četl, nástroj. Žádné surové přepisy (stojí víc než cílené čtení, jména lidí). Přepis zůstává jen tam, kde už je zápis v datech.
- **Umístění (Q-M3):** uživatelská složka vedle cache (`rodokmen_snimky/mapy/<portál>/<svazek>.jsonl`), mimo úklid cache, sdílená mezi projekty
  na počítači, protože neobsahuje jména lidí. Přepisy a deník zůstávají v projektu.
- **Zápis (Q-M4):** čtenář (researcher, browser-reader) vrací údaje o stránce ve výsledkovém souboru; do mapy je zapíše orchestrátor přes
  `mapa.py zapis`. Agent nepíše mimo `pracovni/vysledky/`.
- **Jen rada (Q-M5):** mapa smí určit, kterou stránku stáhnout, **nikdy neuzavře hledání**. „Není tam“ vyžaduje přečíst stránky, které cíl
  ohraničují (R-NEG-001); pořadí v rejstřících a číslech zápisů nemusí být přísné.
- **Identita (Q-M6):** každý snímek, který vstoupí do cache (skriptem i ručně z prohlížeče), se zapíše do mapy jako (portál, svazek, snímek).
  Výsledek `browser-readeru` musí nést adresu, svazek a snímek. Staré soubory s hashem adresy se nemigrují (nejdou zpětně určit); `pracovni/aron/` se
  do mapy naplní z názvů souborů.
- **Měření (Q-M7):** `cache.py stav` ukáže stažené snímky na nalezený záznam, aby šlo doložit, zda mapa šetří archivy.

**Nástroj `mapa.py`:**

- `mapa.py hledej <svazek> --pismeno F | --rok 1856` vrátí nejlepší další snímek a co je o okolí známo (půlení intervalu z dvou známých bodů).
- `mapa.py zapis <vysledek.json>` přidá události z výsledkového souboru; `mapa.py stav <svazek>` vypíše pokrytí.

**Platí pro každé čtení** (noc i den): před stažením se zeptat mapy, a cache.

## 7. Odesílání ven a úkoly pro skill

- Dotazy na archivy a otázky pro rodinu **připravuje agent, odešle vždy člověk**; úkol zůstane ve frontě, dokud odeslání uživatel nepotvrdí.
- **Úkoly pro skill:** v kontextu projektu patří do `data/poznamky_pro_skill.md`; v kontextu metodiky (repozitář skillu) do
  `analyza/ukoly_na_skill.md`. Typy `skill` a `test` v projektových frontách zrušit.

## 8. Co je skill a co projekt

- **Skill (metodika):** pravidla (`reference/nocni_rezim.md`), agenty (orchestrátor jako router), `fronta.py` a testy, `rezim.json` ukázka.
- **Projekt:** konkrétní fronty, `ukoly_historie.jsonl`, `rezim.json` s prahy. `fronta.py` je v projektu kopie; v repozitáři skillu router nebo fronty
  neexistují, jeho úkoly se vedou v `analyza/ukoly_na_skill.md`.

## 9. Otevřené otázky k potvrzení

- **Q1:** Router jako role orchestrátora s nástrojem `fronta.py` (ne nový agent)? **Potvrzeno.**
- **Q2:** Vstup `ukoly_vstup.md` jako povinná první fronta? **Potvrzeno.**
- **Q3:** Opakování po přechodné chybě: nejdřív za dvě noci, pak víkend, pak pracovní doba, pak jedno rozhodnutí za portál. **Potvrzeno s úpravou (viz 4.3).**
- **Q4:** Rozpočet v pásmech S až XL s prahem v `rezim.json`? **Potvrzeno.**
- **Q5:** Metadata čtení: **potvrzeno** po grilování (kap. 6.2, Q-M1 až Q-M7; mapa knihy místo plné „knihy čtení“).
- **Q6:** Zrušit typy `skill` a `test` v projektových frontách? **Potvrzeno** (úkoly pro skill: v projektu `poznamky_pro_skill.md`, v metodice `analyza/ukoly_na_skill.md`).
