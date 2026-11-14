# Zadání: přístupy k rodinnému webu pro jednotlivé větve rodiny

Pracovní zadání k iteraci (verze 8, 9. 11. 2026 – doplněno členění Dokumentů a Co hledáme po rodech, jednotné zobrazení rodů a vazba zajímavostí na přístupy včetně více rodů a obecných). Jen **co** má web umět,
ne **jak** – řešení se navrhne až nad hotovým zadáním. Odpovědi z doptávání jsou v **Rozhodnutí**,
nejasné body v **Otevřené otázky**, body k ověření při testech v **Odloženo**.

## 1. Cíl

- V rodině je víc větví žijících příbuzných. Každá větev dostane vlastní přístup k webu.
- Větve si mají navzájem **pomáhat budovat společné části** (společné předky), ale **nemají vidět soukromé
  informace o jiných větvích** (např. potomci Emilie „Milušky“ Pšornové nevidí, co dodají potomci Libuše Pátkové).
- Může tedy být víc rodů, víc příběhů a víc zajímavostí, které se vážou na jednotlivé části rodiny.

## 2. Pojmy

- **Kořen přístupu** – osoba nebo osoby, od kterých se přístup odvozuje:
  - **jedna osoba**;
  - **dva rodiče** (pár) – platí totéž jako u jedné osoby, výsledek je **sjednocení** obou;
  - **víc osob obecně**, např. dva potomci s různými rodiči (rozvod, úmrtí a nový sňatek) – opět sjednocení.
- **Přímá linie** – kořen a jeho předci.
- **Rozšířená linie** – přímá linie a k tomu **sourozenci kořene i sourozenci všech předků**, každý se svou větví:
  zapsanými potomky až k žijícím. U každé osoby ve větvi i její **partner a rodiče partnera** (odkud pochází);
  sourozenci a další předci partnera už ne.
- **Vlastní větev** – kořen, jeho potomci a jejich partneři.
- **Soukromá informace** (`soukrome: true`):
  - **automaticky** vše o žijících nad rámec jména a roku narození (celá data, údaje, dokumenty);
  - **ručně** cokoli dalšího, co správce takto označí (text, dokument, údaj).
- **Obecný přístup** – má jen správce; vidí všechno včetně soukromého.

## 3. Které stránky ukazují kterou linii

| Linie | Stránky (položky menu) |
| --- | --- |
| **Přímá linie** | Statistiky, Rody, Mapa, Časová osa, Strom, Předci |
| **Rozšířená linie** | Úvod, Příběh, Zajímavosti, Osobnosti, Domy, Vějíř, Zápisy, Dokumenty, Co hledáme, Poznámky |

- Obsah každé stránky je omezený na relevantní data dané linie; stránka bez dat se v menu neukáže.
- **Víc kořenů:** Vějíř, Předci a Statistiky se ukážou pro **prvního v seznamu kořenů**, na ostatní jde **přepnout**;
  Strom, Mapa, Rody a Časová osa ukazují **sjednocení**.
- Statistiky se počítají vždy od kořene přístupu.
- **Úvod** má společný text, který **vidí všechny přístupy**, a za ním může pokračovat vlastní text přístupu (nový odstavec).
- **Rody** mají u každého přístupu **vlastní názvy a popisy** (rody se počítají od kořene přístupu). Když je přístup
  nemá, neukáže se k rodu nic a **sestavení webu vypíše varování**, aby to někdo doplnil.
- **Příběhy a zajímavosti větví** patří k **rodům**; přístup je vidí, když má daný rod.
- **Zajímavosti jsou vázané na přístupy:**
  - zajímavost může patřit **k jednomu rodu, k více rodům, nebo k žádnému**;
  - **s rodem (rody):** přístup ji vidí, když má **aspoň jeden** z těch rodů ve své linii; zobrazí se u ní **všechny
    rody, ke kterým patří** (barevný kruh a název rodu, jednotné zobrazení rodů níže);
  - **bez rodu:** je obecná a **vidí ji všechny přístupy** (nezávisle na právu `texty`).
  - Zajímavosti na úvodní stránce se vybírají jen z těch, které přístup vidí.
- **Dokumenty** (stránka) jsou rozdělené **po rodech**; dokument, který k žádnému rodu nepatří, je v části **Obecné**.
- **Co hledáme** má obě části – **Otázky pro rodinu** i **Otevřené otázky** – rozdělené po rodech **stejným způsobem**.
- **Jednotné zobrazení rodů a rodin:** všude, kde se obsah dělí po rodech (Dokumenty, Co hledáme, Zajímavosti,
  Příběhy…), má nadpis rodu stejnou podobu – **barevný kruh rodu** a název rodu z pohledu přístupu.

## 4. Co přístup vidí o osobách

| Osoba | Bez práva `soukrome` | S právem `soukrome` |
| --- | --- | --- |
| zemřelí v rozšířené linii | vše | vše |
| žijící ve **vlastní větvi** | jméno a rok narození | vše (pokud má souhlas – kap. 7) |
| žijící v ostatních větvích rozšířené linie | jméno a rok narození | jméno a rok narození |
| osoby mimo rozšířenou linii | nic | nic |

Příklad: Pšornovi (kořen Emilie Pšornová) vidí přes její sestru Bohumilu Markovou i Martinovu rodinu – jen jména
a roky narození, ani s právem `soukrome` víc.

## 5. Práva přístupu

Každý přístup má objekt **`prava`**; nevyplněné právo = `false`. Obecný přístup má všechna práva.

| Právo | Význam |
| --- | --- |
| `soukrome` | vidí soukromé informace **své vlastní větve** (kap. 4) |
| `texty` | vidí texty **bez vazby na osobu nebo rod** (výzkumný deník, obecné poznámky…; obecné zajímavosti **ne**, ty vidí všichni); texty s vazbou se řídí linií a označením `soukrome` |
| `poznamky` | smí **psát** poznámky a **vidí všechny poznámky ke stránkám, které sám vidí** (i od jiných větví ke společným předkům); poznámky se řídí i označením `soukrome` |

## 6. Vstup na web

- Přístup se definuje **odpovědí na otázku**, **osobním odkazem**, nebo **kombinací obou**.
- Konfigurace všech přístupů (i přes odkaz) je ve `web.json` pod `pristupy`.
- Příbuzní dodávají podklady **poznámkami na webu**, soubory posílají **správci mimo web** (e-mail, WhatsApp);
  data mění jen správce.

## 7. Dokumenty a souhlas

- Projdou se všechny dokumenty ve složce `dokumenty/` (bez podsložek), znovu se načtou a založí.
- Každá osoba zmíněná na dokumentu má k dokumentu vztah: dokument se ukáže na její stránce, případně na stránce rodu.
- Zobrazují se všechny dodané dokumenty, i o žijících – dokument o žijícím je soukromá informace (kap. 2, 4).
- **Rodná čísla:** doklad s rodným číslem se zveřejní, až **všichni, jejichž RČ na něm je, jsou doloženě mrtví**
  (úmrtní list), **nebo když jsou RČ žijících v obrázku začerněná**.
- **Dokument s žijícími z více větví** (parte s pozůstalými, schéma potomků): **správce u každého rozhodne**,
  které přístupy ho vidí.
- **Souhlas žijících se eviduje u osoby** (kdo, kdy, s čím). Bez souhlasu se soukromé údaje a doklady té osoby
  neukážou ani přístupu s právem `soukrome`.
- **Adresy žijících:** zatím bez zvláštního pravidla – dům a bydliště vidí každý, kdo vidí danou osobu.

## 8. Rizika, která má zadání pokrýt

- Únik informací o jiné větvi přes volný text (příběh, zajímavosti, poznámky), přes počty (statistiky,
  „měli devět dětí“) nebo přes dokumenty, na kterých je víc osob.
- Rodná čísla dalších žijících osob na dokladech (rodiče, manželé), nejen osoby, které se doklad týká.
- Adresy a domy, kde bydlí žijící příbuzní (zatím vědomě bez pravidla).
- Hesla (odpovědi) předávaná v rodině; zrušení přístupu jednomu člověku.
- Souhlas žijících (i třetích osob na dokladech, např. bývalých manželů).
- Chyba v nastavení přístupu otevře celou větev – musí jít ověřit, kdo co vidí.

## 9. Otevřené otázky

(Zatím žádné – další kolo doptávání podle potřeby.)

## 10. Odloženo k ověření ve fázi testů

- **Kořen jako žijící osoba bez práva `soukrome`:** vidí sám sebe a své děti jen jménem a rokem. Zatím ano,
  ověřit na testovacím webu, jestli to tak má zůstat.
- **Partner a rodiče partnera u předků** (druhé manželky a manželé předků, nevlastní rodina): zatím platí stejně
  jako ve větvích, ověřit na testovacím webu.
- **Ověření „kdo co vidí“:** správce otestuje přístupy na testovacím webu na Netlify.

## 11. Rozhodnutí

| Datum | Bod | Rozhodnutí |
| --- | --- | --- |
| 7. 11. 2026 | Model | Kořen = jedna osoba, pár rodičů nebo víc osob (sjednocení). Přímá × rozšířená linie podle stránek (kap. 3). Práva v objektu `prava` (`soukrome`, `texty`, `poznamky`), nevyplněné = `false`. |
| 7. 11. 2026 | Rozšířená linie | Sourozenci **kořene i všech předků**, každý s potomky až k žijícím. |
| 7. 11. 2026 | Soukromé | **Automaticky** vše o žijících nad rámec jména a roku narození + **ručně** cokoli dalšího. |
| 7. 11. 2026 | Partneři | Ve větvích je vidět partner **i jeho rodiče**; dál ne. |
| 7. 11. 2026 | Víc kořenů | Vějíř, Předci a Statistiky zvlášť pro kořeny; Strom, Mapa, Rody a Časová osa sjednocení (upřesněno 9. 11.). |
| 7. 11. 2026 | Žijící z jiných větví | V rozšířené linii jsou vidět, bez práva `soukrome` jen jménem a rokem narození. |
| 7. 11. 2026 | Právo `texty` | Řídí texty bez vazby na osobu nebo rod. |
| 7. 11. 2026 | Právo `poznamky` | Psát + vidět všechny poznámky ke stránkám, které přístup vidí; řídí se i `soukrome`. |
| 7. 11. 2026 | Obecný přístup | Má jen správce. |
| 7. 11. 2026 | Rozsah práva `soukrome` | Jen **vlastní větev**; žijící z ostatních větví vždy jen jménem a rokem. |
| 7. 11. 2026 | Dokument s žijícími z více větví | Správce rozhodne u každého dokumentu, které přístupy ho vidí. |
| 7. 11. 2026 | Rodná čísla | Zveřejnit, až všichni s RČ na dokladu jsou doloženě mrtví, nebo když jsou RČ žijících začerněná. |
| 7. 11. 2026 | Adresy žijících | Zatím bez zvláštního pravidla. |
| 7. 11. 2026 | Úvod | Společný text + pokračování vlastním textem přístupu. |
| 7. 11. 2026 | Rody | Vlastní názvy a popisy u každého přístupu. |
| 7. 11. 2026 | Dodávání podkladů | Poznámky na webu + soubory správci mimo web; data mění jen správce. |
| 7. 11. 2026 | Souhlas | Eviduje se u osoby; bez souhlasu se soukromé údaje a doklady neukážou ani s právem `soukrome`. |
| 9. 11. 2026 | Víc kořenů (upřesnění) | Vějíř, Předci a Statistiky pro **prvního v seznamu kořenů**, na ostatní jde přepnout. |
| 9. 11. 2026 | Společný úvod | Vidí ho **všechny přístupy**. |
| 9. 11. 2026 | Rody bez popisu u přístupu | Neukáže se nic; **sestavení webu vypíše varování**. |
| 9. 11. 2026 | Příběhy a zajímavosti větví | Patří k **rodům**. |
| 9. 11. 2026 | Víc odkazů do jednoho přístupu | **Není potřeba**, přístupy nejsou osobní (jeden přístup = jedna větev). |
| 9. 11. 2026 | Ověření „kdo co vidí“ | Správce otestuje na **testovacím webu na Netlify**. |
| 9. 11. 2026 | Kořen bez `soukrome`, partneři předků | Zatím ano; **odloženo k ověření ve fázi testů** (kap. 10). |
| 9. 11. 2026 | Dokumenty po rodech | Stránka Dokumenty rozdělená po rodech, bez rodu v části Obecné. |
| 9. 11. 2026 | Co hledáme po rodech | Otázky pro rodinu i Otevřené otázky rozdělené po rodech stejně. |
| 9. 11. 2026 | Jednotné zobrazení rodů | Nadpis rodu všude stejně: barevný kruh rodu + název rodu z pohledu přístupu. |
| 9. 11. 2026 | Zajímavosti vázané na přístupy | Zajímavost patří k jednomu rodu, k více rodům, nebo k žádnému. S rodem ji vidí přístup, který má **aspoň jeden** z jejích rodů, a zobrazí se u ní **všechny její rody** (barevný kruh + název). **Bez rodu ji vidí všechny přístupy**, nezávisle na právu `texty`. |

## Související nález v datech (mimo zadání)

- **Culkovi, osoba 37:** opraveno 9. 11. 2026 – matkou Josefa Culka (18) je Josefa Ronnerová (37), její rodiče 74 a 75;
  Marie Stehnová a její rodiče přesunuti mezi příbuzné (první žena Ignáce Culka).
