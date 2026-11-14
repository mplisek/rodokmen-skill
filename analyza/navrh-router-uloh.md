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
   - nejasná identita nebo podoba jména („Culek, nebo Čulek“), dva kandidáti se stejnými důkazy, spor zdrojů,
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

## 6. Identita, historie a metadata čtení

### 6.1 Co navrhuju

- **Úkol má stabilní ID** (`U-0412`, už existuje) a **historii událostí** `data/ukoly_historie.jsonl` (jen přidávání, jako deník):
  vznik, směrování, dělení, parkování, hotovo; kdo (orchestrátor, uživatel), odkud a kam, důvod, DOD, odhad a skutečná cena, odkazy na řádky deníku
  a výsledkové soubory. Hotový úkol se z fronty maže dál, v historii zůstane.

- **Metadata čtení**: k řádku deníku se přidají strukturovaná pole `ukol` (ID úkolu), `nastroj` (verze skillu a nástroje), `model` (kdo četl),
  `snimky` (strojově čitelný seznam místo volného textu `rozsah`).

- **Opakované čtení podle schopnosti:** dotaz „které čtení se vrátily jako nečitelné nebo nenalezeno, četl je starší model nebo starší nástroj?“
  = filtr nad deníkem; z něj router založí nové úkoly jen pro ně.

### 6.2 Námitky a omezení (zahrnuté do návrhu)

- **Neukládat obsah snímků.** Snímek je obrázek bez textu (OCR se na rukopis nepoužívá; výjimkou jsou portály s textovou vrstvou). Čtení dělá model
  nad výřezem a zahodí vše, co nepotřebuje. Plný přepis každé stránky „pro příště“ by stál mnohem víc tokenů než cílené čtení, a navíc ukládaný
  negativní výsledek („jméno tam není“) je jen tak dobrý jako čtenář (R-NEG-001).

- **Co se ukládá:** otázka a odpověď (hledáno, kde, výsledek, kdo četl), ne obsah. To je v podstatě deník, jen strukturovaněji.
- **Kam ne:** metadata do cache snímků ne. Cache je společná pro všechny projekty, klíčovaná podle adresy a mazatelná kdykoli (limit, LRU).
  Znalost o výzkumu patří do projektu, ne do cache.

- **Kdy opakovat:** výsledek `nalezeno` a ověřený se neopakuje. Dotaz na stejnou otázku nad týmž místem, který skončil `nenalezeno` nebo `nečitelné`,
  se opakuje jen po změně schopností (nový model, nový nástroj, lepší výřez).

- **Platí pro každé čtení, ne jen noční.** Před čtením (v noci i přes den) se kontroluje cache a historie: byl tento výřez už čten pro tuto otázku?

### 6.3 Minimální verze

Stačí (1) pole `ukol`, `nastroj`, `model` v deníku, (2) strukturovaný `rozsah`, (3) `ukoly_historie.jsonl` a (4) příkaz
`fronta.py znovu --vysledek nečitelné,nenalezeno --starsi-nez <verze>`. Plná „kniha čtení“ po snímcích až když se ukáže, že to nestačí.

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
- **Q5:** Metadata čtení: **otevřeno, grilluje se** (kap. 6, uživatel navrhl popisy snímků a „mapu“ knihy v cache; viz odpověď a otázky Q-M1 až Q-M7).
- **Q6:** Zrušit typy `skill` a `test` v projektových frontách? **Potvrzeno** (úkoly pro skill: v projektu `poznamky_pro_skill.md`, v metodice `analyza/ukoly_na_skill.md`).
