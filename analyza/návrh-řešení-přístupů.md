# Návrh řešení: přístupy k rodinnému webu pro větve rodiny

Návrh k zadání `data/analýza-spočných-přístupů.md` (verze 8). Verze návrhu 2, 10. 11. 2026 (rozhodnutí kap. 7, agenti kap. 8).
Co je **skill** (platí pro všechny projekty) a co **projekt** (tento rodokmen), v jakém pořadí a s jakými riziky.
Rozhodnutí jsou v kap. 7.

## 0. Výchozí stav – co už existuje

- Přístupy (`web.json` → `pristupy`) s kořenem (`koren`), každý přístup = **samostatně sestavená verze webu**
  (`dist/_p/<přístup>/`); data, která přístup nevidí, na serveru pro něj vůbec nejsou. Brána na Netlify pošle
  podle odpovědi nebo osobního odkazu jen verzi daného přístupu.
- **Rozsah osob** přístupu je dnes: předci kořene + **všichni potomci těchto předků** + partneři. To je téměř přesně
  **rozšířená linie** ze zadání – chybí jen **rodiče partnerů**.
- Žijící jsou všude jen jménem a rokem narození; dokumenty, zajímavosti a texty o žijících nemají žádná pravidla.
- Osobní odkazy (`tools/pozvanky.py`) mají přístup v `data/pozvanky.json`, ne ve `web.json`.
- Poznámky vidí každý přístup jen ze svého přístupu.

## 1. Datový model (skill)

### 1.1 Konfigurace přístupu ve `web.json`

```json
"pristupy": [
  {
    "nazev": "Větev B",
    "koren": ["libuse_patkova_1932"],
    "odpoved": "…",
    "odkazy": [{"id": "p3", "jmeno": "Jana", "otisk": "…", "vytvoreno": "2026-11-10"}],
    "prava": {"soukrome": true, "texty": false, "poznamky": true},
    "uvod": {"odstavce": ["Vlastní text větve – pokračuje za společným úvodem."]},
    "rody": {"8": ["Rod X", "Popis z pohledu větve B…"], "9": ["Rod Y", "…"]}
  }
]
```

- `odpoved` i `odkazy` nepovinné – přístup má aspoň jedno z nich (kontrola).
- `odkazy` = otisky klíčů (klíč se nikam neukládá); `pozvanky.py pridej "Jméno" --pristup <id>` zapíše odkaz sem.
  `data/pozvanky.json` zanikne (převod jednorázově nástrojem).
- `prava` – nevyplněné = `false`. Starší `texty` a `poznamky` přímo v přístupu se převedou do `prava`.
- Obecný přístup (`vse`) = `prihlaseni.odpoved` správce, má všechna práva (jako dnes).
- `rody` – klíče **8–15 od prvního kořene přístupu**; chybějící rod = varování při sestavení (zadání kap. 3).

### 1.2 Čtyři množiny osob pro každý přístup (`tools/pohled.py`)

| Množina | Definice | Použití |
| --- | --- | --- |
| **přímá** | kořeny + jejich předci | Statistiky, Rody, Mapa, Časová osa, Strom, Předci |
| **rozšířená** | přímá + potomci všech osob z přímé linie (= sourozenci kořene i předků s větvemi) + u každé jejich partner a rodiče partnera | ostatní stránky |
| **vlastní větev** | kořeny + jejich potomci + partneři | rozsah práva `soukrome` |
| **mimo** | vše ostatní | na webu přístupu vůbec není |

Každá osoba v datech přístupu dostane příznak `linie: "prima" | "rozsirena"`; stránky přímé linie berou jen `prima`.
Víc kořenů: množiny jsou sjednocení; Vějíř, Předci a Statistiky mají přepínač kořene (výchozí první kořen).

### 1.3 Soukromí osob (export)

Plné údaje o žijící osobě jen když **všechno** platí:

1. přístup má `prava.soukrome` (nebo je obecný),
2. osoba je ve **vlastní větvi** přístupu,
3. osoba má zapsaný **souhlas** (nové pole u osoby: `souhlas={"kdo": "…", "datum": "2026-11-10", "rozsah": ["udaje", "doklady"]}`).

Jinak jméno a rok narození (jako dnes). **Ruční označení** (zadání kap. 2):

- osoba: `soukrome=True` (i zemřelá – všechny údaje nad jméno a roky),
- jednotlivý údaj: fakt začínající `(soukromé)` – ukáže se jen tomu, kdo smí soukromé dané osoby,
- dokument, zajímavost, oddíl příběhu: `soukrome: true` / `<!-- soukrome -->`.

Rozhodnuto: prefix `(soukromé)` (kap. 7).

### 1.4 Rody jako vazba obsahu

Rody se počítají od kořene přístupu (8 pradědečků a prababiček), takže stejné číslo znamená u každého přístupu jiný
rod. Obsah proto **neodkazuje na číslo rodu, ale na osobu – zakladatele rodu** v číslování celého rodokmenu
(`osoby.py`): `rody: [8, 10]` = rod otce (8) a rod matky (10) z pohledu správce.

- Přístup obsah vidí, když je některý ze zakladatelů v jeho **přímé linii** (nebo je jeho předkem).
- Zobrazí se **rody přístupu**, do kterých zakladatel patří, s jejich názvy a barvami z pohledu přístupu
  (u větve B se obsah „rodu 8“ ukáže pod jejím rodem X).
- Bez `rody` = obecný obsah (zajímavost ho vidí každý; text řídí právo `texty`).

Rozhodnuto: číslem osoby (kap. 7).

### 1.5 Kde se rody zapisují

| Obsah | Zápis |
| --- | --- |
| zajímavost | `## Nadpis` + řádek `Rod: …` → strojově `<!-- rody: 8, 10 -->` pod nadpisem |
| příběh | frontmatter `rody: [8]` (dnes `rod: 8`) |
| otázka pro rodinu, pramen | oddíl `## <rod>` (dnes) nebo `<!-- rody: … -->` u odrážky |
| otevřená otázka (`ISSUES`) | `k` osoby (dnes) – rod se odvodí |
| dokument | `osoby` (dnes) – rody se odvodí; `pristupy: [...]` ruční výběr pro doklady s žijícími z víc větví |

### 1.6 Dokumenty (`dokumenty.json`)

```json
{"img": "rodny_list_anna_2005", "popis": "…", "osoby": ["anna"], "rc": ["anna", 1],
 "zacerneno": ["anna", 1], "pristupy": ["vse"], "soukrome": true}
```

- `rc` – osoby, jejichž rodné číslo je na dokladu. Zveřejnit, až je každá z nich **mrtvá s úmrtním listem**
  (dokument se `"druh": "umrtni_list"` a touto osobou) **nebo** je její RČ v `zacerneno`.
- `vyrez.py --zacernit x0,y0,x1,y1 [...]` – zakryje oblast v obrázku (zdroje/ i vyrezy/), zapíše do `zacerneno`.
- Doklad, na kterém je žijící osoba, je automaticky soukromý; doklad s žijícími z víc větví vidí jen přístupy
  v `pristupy` (zadání: rozhodne správce).

### 1.7 Poznámky

- Přístup s `prava.poznamky` vidí poznámky **od všech přístupů**, ale jen ke stránkám, které sám vidí:
  export zapíše pro každý přístup seznam jeho stránek (otisk přístupu → stránky), funkce `/api/poznamky` podle něj filtruje.
- Správce může poznámku označit soukromou (`npm run poznamky -- --soukrome <id>`) – pak ji vidí jen autorova větev a správce.

## 2. Web (skill)

- **Menu podle obsahu:** položka se ukáže, jen když má stránka v daném přístupu data (dnes jen Domy, Dokumenty, Poznámky).
- **Stránky přímé linie** (Statistiky, Rody, Mapa, Časová osa, Strom, Předci) berou jen osoby `prima`.
- **Komponenta „rod“** (barevný kruh + název z pohledu přístupu) – jednotně na stránkách Dokumenty, Co hledáme,
  Zajímavosti, Příběhy, Rody.
- **Dokumenty** po rodech + Obecné; **Co hledáme** – obě části po rodech; **Zajímavosti** po rodech s rody u každé.
- **Úvod** = společný text (`web.json` → `uvod`) + vlastní text přístupu; zajímavosti na úvodu jen z viditelných.
- **Přepínač kořene** na Vějíři, Předcích a Statistikách, když má přístup víc kořenů.

## 3. Kontroly (skill)

- `kontrola.py` – přístup bez odpovědi i odkazu, neznámý kořen, chybějící názvy rodů přístupu, dokument s RČ bez
  úmrtního listu / začernění, žijící se soukromými údaji bez souhlasu, zakladatel rodu, který není předek.
- Při sestavení přístupu: odkaz v textu na osobu, kterou přístup nevidí, je **chyba sestavení** (dnes jen varování
  „nefunkční odkaz“) – zachytí únik jmen z jiných větví v příběhu a zajímavostech, pokud jsou psaná s odkazy.
- `tools/pristupy.py` – přehled „kdo co vidí“: za každý přístup počty a seznam osob (přímá / rozšířená / vlastní
  větev, s plnými údaji), dokumenty, zajímavosti a příběhy. Pomůcka k testům na Netlify (zadání: testuje správce).

## 4. Projekt (tento rodokmen)

1. **Přístupy:** správce (`vse`), větve – např. větev B (kořen osoba B), větev A (osoba A),
   další podle rodiny; jejich práva, názvy rodů a vlastní úvod.
2. **Převod** `data/pozvanky.json` → `web.json` (nástroj).
3. **Rody u obsahu:** zajímavosti (už mají řádek `Rod:`), příběh rodu X (`rody: [8]`, oddíly o žijících jako
   soukromé nebo do vlastní větve), otázky pro rodinu a prameny.
4. **Dokumenty:** projít 41 souborů v `dokumenty/` – osoby, RČ, začernění, výběr přístupů, souhlasy.
5. **Souhlasy** žijících, jejichž údaje a doklady mají být vidět.
6. **Data větví:** potomci sourozenců (dnes skoro nic) – podle toho, co rodina pošle.

## 5. Fáze a pořadí

| Fáze | Skill | Projekt | Ověření |
| --- | --- | --- | --- |
| **1. Model a konfigurace** | `prava`, `odkazy` ve `web.json`, převod `pozvanky.json`; množiny přímá/rozšířená/vlastní (+ rodiče partnerů); stránky přímé linie; menu podle obsahu; přehled `pristupy.py` | přístupy větví, převod odkazů | testy + náhled každého přístupu + testovací web |
| **2. Soukromí osob** | vlastní větev + `prava.soukrome` + souhlas; ruční `soukrome` | souhlasy | testovací web |
| **3. Rody a texty** | zakladatelé rodů u obsahu, rody přístupu + varování, komponenta rodu, Zajímavosti / Co hledáme / Příběhy po rodech, úvod společný + vlastní, chyba sestavení u odkazu mimo přístup | rody u zajímavostí, příběhu, otázek; názvy rodů a úvody přístupů | testovací web |
| **4. Dokumenty** | `rc`, úmrtní list, `--zacernit`, `pristupy`, Dokumenty po rodech | 41 dokumentů | testovací web |
| **5. Poznámky** | poznámky napříč větvemi podle stránek, soukromá poznámka | – | testovací web |

Každá fáze: skill + testy → aktualizace projektu → náhled přístupů → **testovací web na Netlify (bez `--prod`)** →
ostrý web po dávkách (kredity). Po fázích 1–3 je web pro větve použitelný; 4 a 5 rozšiřují.

## 6. Rizika řešení

- **Rody relativní ke kořeni** – vazba obsahu přes zakladatele (1.4) je nová a nejsložitější část; chyby se projeví
  tím, že obsah u větve chybí nebo přebývá. Proto přehled `pristupy.py` už ve fázi 1 a testy s ukázkou o dvou větvích.
- **Volný text** zůstává největším rizikem úniku – kontrola zachytí jen odkazy na osoby, ne jména napsaná bez odkazu.
  V textech o žijících vždy odkazovat na osobu (pak se v cizí větvi sestavení zastaví).
- **Počet verzí webu** roste s počtem přístupů – sestavení trvá déle (dnes 3 verze), nasazení nahrává jen změny.
- **Zpětná kompatibilita** – projekty s dnešními přístupy (bez `prava`) musí fungovat dál: převod při aktualizaci
  projektu, staré `texty`/`poznamky` = `prava`.
- **Odložené body** (kořen bez práva `soukrome`, partneři předků, ověření kdo co vidí) – rozhodne test na Netlify.

## 7. Rozhodnutí (10. 11. 2026)

1. **Soukromý údaj** se značí prefixem `(soukromé)` ve faktu osoby (zatím; lze změnit po testech).
2. **Zakladatel rodu** u obsahu se zapisuje **číslem osoby** z rodokmenu správce (`rody: [8, 10]`).
3. **Přístupy větví** založí správce později; fáze 1 se vyvíjí a testuje na ukázce se dvěma větvemi.

## 8. Rozdělení úloh pro agenty

Agent se vyplatí jen tam, kde je úloha **samostatná** (vlastní soubory, jasný vstup a výstup) a dá se **zkontrolovat**.
Jádro (pohled, pravidla soukromí, vazba rodů) je provázané v `pohled.py` a `export_web.py` – tam by souběžná práce
víc pokazila, než ušetřila; dělá ho koordinátor. Každý agent startuje bez kontextu, proto dostane přesné zadání
(soubory, datový kontrakt, co nesmí měnit) a jeho výsledek koordinátor ověří, než se sloučí.

### Role a modely

| Role | Model | Proč tento model | Úlohy |
| --- | --- | --- | --- |
| **Koordinátor** (hlavní konverzace) | Opus | návrh, provázaná logika, rozhodování, ověřování | datový kontrakt `site.json` a `web.json`, `pohled.py`, pravidla soukromí, vazba rodů, sloučení, zápis do projektu |
| **Průzkumník** | Haiku | mechanické hledání, levné a rychlé | soupis míst ve skillu, která čtou osoby, dokumenty, rody, otázky (stránky, komponenty, export) – podklad pro kontrakt |
| **Tester ze zadání** | Sonnet | píše testy podle zadání, ne podle kódu – nezávislá kontrola | ukázka se dvěma větvemi, testy „kdo koho vidí“, soukromí, rody, dokumenty, úniky v sestaveném webu |
| **Web (Astro)** | Sonnet | šablony podle hotového kontraktu, dobře ohraničené | menu podle obsahu, stránky přímé linie, komponenta rodu, Dokumenty / Co hledáme / Zajímavosti po rodech, přepínač kořene, úvod |
| **Čtenář dokumentů** (2–3 souběžně) | Sonnet | čtení fotek a rukopisů, dávky jdou souběžně | 41 dokumentů po dávkách: co to je, zmíněné osoby, rodná čísla a jejich poloha, návrh popisu a přístupů – jen návrh do `pracovni/` |
| **Recenzent** | Opus | hledá chyby a úniky, které autor přehlédne | revize změn každé fáze před sloučením (nebo `/code-review`) |

### Po fázích

| Fáze | Souběžně | Postupně | Ověření |
| --- | --- | --- | --- |
| **1. Model a konfigurace** | Průzkumník (soupis) · Tester (ukázka se 2 větvemi + testy rozsahu) | Koordinátor: kontrakt, `prava`, `odkazy`, převod `pozvanky.json`, množiny osob → Web: menu, stránky přímé linie | Recenzent, testy, náhled přístupů, testovací web |
| **2. Soukromí osob** | Tester (testy soukromí a souhlasu) | Koordinátor: vlastní větev + `soukrome` + souhlas + ruční značení | Recenzent, testovací web |
| **3. Rody a texty** | Web (komponenta rodu, stránky po rodech) · Tester (testy rodů) | Koordinátor: zakladatelé rodů, rody přístupu, chyba sestavení u odkazu mimo přístup; zápis rodů v projektu | Recenzent, testovací web |
| **4. Dokumenty** | Čtenáři dokumentů ×2–3 (dávky po ~15) · Tester (RČ, úmrtní list, začernění) | Koordinátor: `rc`, `pristupy`, `--zacernit`; ověření návrhů čtenářů a zápis do `dokumenty.json` | kontrola každého dokladu s RČ koordinátorem, testovací web |
| **5. Poznámky** | – | Web nebo koordinátor: funkce poznámek napříč větvemi + testy | Recenzent, testovací web |

### Pravidla spolupráce

- Agenti pracující ve skillu souběžně dostanou **vlastní pracovní kopii** (git worktree); sloučí je koordinátor.
- Souběžně nejvýš 2–3 agenti, nikdy dva na stejném souboru.
- Tester nevidí implementaci, jen zadání a kontrakt – jeho testy pak nezávisle ověří, že řešení dělá, co zadání chce.
- Čtenáři dokumentů nic nezapisují do `data/`; rodná čísla jen poznačí (kde na obrázku jsou), nepřepisují je.
- Odhad: agenti zrychlí hlavně fáze 1, 3 a 4 (průzkum, testy, šablony a dokumenty souběžně s jádrem);
  fáze 2 a 5 jsou malé a provázané – tam agent nic neušetří.
