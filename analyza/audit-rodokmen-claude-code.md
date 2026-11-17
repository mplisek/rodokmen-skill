# Audit a optimalizace metodiky rodokmen-skill — zadání pro Claude Code

Aktualizováno 15. 11. 2026 podle upřesnění cíle a souboru `poznamky_pro_skill.md` z běhu 14.–15. 11. 2026.

**Použití:** do Claude Code vlož celou část 1. Části 2 a 3 předej jako podklady, případně přilož tento celý soubor a původní `poznamky_pro_skill.md`. Část 1 nahrazuje předchozí zadání; původní poměr pozornosti 60/25/15 a preference minimálních oprav již neplatí.

## 1. Kompletní zadání pro Claude Code

Prostuduj projekt rodokmen-skill v aktuálním pracovním prostředí a navrhni jeho optimalizovanou cílovou metodiku. Potřebné zdrojové soubory jsou již dostupné v tomto prostředí. Výstup piš česky. **Jediným výsledkem tohoto úkolu je návrhový dokument.** Kontrakty, příklady, testovací strategie a migrační plán jsou součástí návrhu; nevytvářej jejich implementaci.

### 1.1 Hlavní cíl a způsob hodnocení

**Výsledným produktem je rodokmenový web, který jasně, přesně, úplně v definovaném rozsahu a konzistentně prezentuje doložené výsledky bádání.** Plugin, agenti, skripty a metodiky jsou prostředky k tomuto cíli.

**Nejvyšší společnou prioritou jsou přesnost badatelských výsledků a celková cena bádání.** Navrhni snížení ceny za správně doložený a konzistentně publikovaný výsledek. Levný běh s chybným zápisem, ztracenou souvislostí nebo nutností opakovaného bádání není úspěch. Přesnost neposuzuj jen podle syntakticky validního JSONu nebo shody dvou přepisů.

Pracuj s hypotézou, že současná metodika jako celek může být nevhodná. Nesoustřeď se na jednu chybu, kosmetické zkrácení promptů ani na nejlevnější implementaci oprav. Můžeš doporučit zásadní změnu workflow, rozdělení odpovědností, datových rozhraní či ukládání vztahů, pokud ji podložíš. Cena přestavby je důležitá pro migraci, ale není hlavní optimalizační cíl. Zachování současné architektury není podmínka.

Nezaměňuj provozní cenu bádání, cenu jeho oprav a jednorázovou cenu vývoje. Vyhodnoť je odděleně. Nenastavuj svévolně poměr významu ceny a přesnosti; nejprve stanov nepodkročitelné kvalitativní podmínky a pak porovnej efektivní varianty.

### 1.2 Tři navazující oblasti

| Oblast | Odpovídá na | Požadovaný výsledek |
|---|---|---|
| Metodika bádání | Co zjistit, proč a kde; jaké důkazy jsou potřebné | Badatelské otázky, prameny, rozsah hledání, pravidla hodnocení důkazů, identity a nejistoty |
| Metodika skillu | Jak práci provést a řídit | Role, kontext, nástroje, kontrakty, rozhodování o pokračování a DoD, zápis, chybové stavy a měření |
| Prezentace na webu | Jak doložené poznání úplně a srozumitelně zobrazit | Konzistentní pohledy na stejné osoby, vztahy, události, zdroje a nejistoty |

Pravidla pro zadávání, analýzu, implementaci a testování změn skillu jsou způsobem údržby tohoto systému. Mají podporovat hlavní produktový cíl. Nerozděluj audit podle předem určeného procenta souborů nebo času; sleduj celý průchod výsledku a místa ztráty kvality a peněz.

### 1.3 Důkazy a způsob práce

1. Pracuj s dostupnými soubory projektu a zachovej rozpracovanou práci. Prostuduj aktuální `CLAUDE.md`, případné `AGENTS.md`, metodiky, role, hooky, nástroje, model dat, export, web a testy. Čti cíleně, ale napříč celým řetězcem. Odděl stav implementace od historických návrhů a ADR.
2. Využij přiložené `poznamky_pro_skill.md` jako případovou studii. Obsahuje pozorování, odhady, navržené opravy a neověřené příčiny; tyto kategorie nezaměňuj. Starší předaudit v části 3 je seznam kandidátů, nikoli osnova cílové architektury.
3. Ke každému zjištění uveď důkaz, příčinu, dopad na přesnost a cenu, a zda jde o potvrzení kódem/testem, hlášení z běhu nebo hypotézu. Poznámky odkazují na lokální měřicí skripty ve Windows; pokud nejsou dostupné, čísla nezávisle nepřepočítáš a musíš to uvést.
4. Prostuduj existující testy a výsledky dostupných měření. Nové testy, reprodukce, experimenty a syntetické scénáře pouze navrhni v dokumentu, nevytvářej ani nespouštěj jejich implementaci. Bez provedeného ověření netvrď, že navržené řešení funguje nebo dosáhlo úspory.
5. Současná pravidla jsou i předmětem auditu. Jejich změnu můžeš doporučit a popsat, ne je při auditu svévolně obcházet. Konflikty dokumentuj.
6. Nevytvářej ani neupravuj skripty, definice agentů, metodiku, konfiguraci, testy nebo rodinná data. Neinstaluj závislosti, neprováděj migrace, nic nepublikuj ani neposílej a nespouštěj bádání. Jediný vytvářený či upravovaný soubor je návrh `analyza/navrh-optimalizace-metodiky.md`; pokud existuje, nejprve jej přečti a zachovej relevantní obsah. Pro běžné nejasnosti uveď předpoklad a pokračuj, skutečné blokátory odděl. Po odevzdání návrhu skonči; nepřecházej automaticky k realizaci.

### 1.4 Nejprve model celého procesu

Zmapuj současný a navrhni cílový průchod:

badatelská otázka → plán a rozsah → výběr kontextu → čtení pramene → strukturovaný výsledek → vyhodnocení důkazů → rozhodnutí o pokračování/DoD → validovaný zápis → odvozené pohledy → kontrola webu.

U každého přechodu urči, kdo rozhoduje, co spotřebuje, co vytvoří, co mění, cenu a podmínku přechodu. Hledej ztráty informací, duplicitní rozhodování, zbytečné nové běhy a opakovanou rekonstrukci kontextu. Započítej i neúspěšné běhy, čekání, opravné zápisy, přenosy, technické ukládání změn a opakované publikování.

Porovnej alespoň dvě uskutečnitelné cílové varianty s dnešním stavem. Nevybírej podle počtu agentů ani podle toho, která vyžaduje nejméně upravených souborů. Doporuč jednu variantu a dolož její kompromisy. V dokumentu ji krok za krokem popiš na konkrétních scénářích níže; scénáře nyní nevykonávej.

### 1.4a Varianta dvou hlavních agentů: badatel a metodik

Výslovně posuď uživatelův nápad dvou hlavních agentů místo jediného univerzálního orchestrátoru. **Jde o variantu k vyhodnocení, nikoli závazek ji přijmout.** Pracovní názvy jsou „badatel“ a „metodik“; jejich přesné kompetence navrhni podle ceny, přesnosti a jednoduchosti použití.

- **Badatel:** možný hlavní vstup pro konkrétní výzkum, jeho průběh, výsledky a jejich promítnutí do rodokmenu. Rozliš tuto hlavní roli od úzce zaměřeného čtenáře jednoho pramene. Hlavní badatel může potřebovat strategii a stav výzkumu, zatímco pomocný čtenář jen omezené zadání.
- **Metodik:** možný hlavní vstup pro posouzení a zlepšování pravidel, kontextových rozhraní, nástrojů, výstupních kontraktů a kvality procesu. Zvaž, zda pracuje odděleně při změně metodiky či opakovaných problémech, místo aby schvaloval každý běžný nález.
- **Další role:** mohou být interní pomocníci skrytí za hlavními rolemi, podmíněně spouštění specialisté, deterministické nástroje, nebo nemusí existovat. „Skrytí“ znamená, že je uživatel nemusí vybírat a řídit; jejich činnost, cena a důkazy zůstávají dohledatelné. Každou další roli odůvodni a uveď, kdy se nevyplatí.

Porovnej tuto variantu s jedním hlavním řídicím agentem; další variantu přidej jen při podstatném přínosu. Navrhni, komu uživatel zadává bádání a komu změnu metodiky, jak se úkol směruje, co se mezi rolemi předává a jak se zabrání duplicitnímu kontextu a přehazování odpovědnosti. Dva hlavní agenti nesmějí automaticky znamenat dvojí schvalování DoD nebo dvě plné kopie historie.

Urči jednoho vlastníka každého typu rozhodnutí a odděl DoD konkrétního bádání od DoD změny metodiky. Změna pravidel během rozpracovaného bádání nesmí tiše měnit jeho zadání a podmínky přijetí. Navrhni předání podnětu metodikovi a řízené převzetí nové verze pravidel.

Pokud variantu nedoporučíš, vysvětli konkrétní důvod a navrhni lepší uspořádání. Výrazy „orchestrátor“ a „badatel“ v následujících příkladech označují funkce; nevynucují počet, názvy ani hierarchii výsledných agentů.

### 1.5 Minimum míst, která rozhodují o DoD

Cílem je minimum nezávislých míst rozhodujících o definici hotového (DoD) a jeden autoritativní zdroj pravidel, nikoli odstranění nezávislého ověření faktů.

Prověř jako návrhovou variantu tento model: badatel dostane přesnou otázku, relevantní pramen/rozsah, stručná pracovní pravidla a formát výsledku. Nemusí znát celou metodiku, fronty, publikaci ani pravidla technického ukládání změn. Vrací pozorování, důkazy, omezení a kandidáty na další krok. Orchestrátor má potřebný souhrn a rozhodne o splnění badatelského úkolu, dalším kroku a jeho efektivitě. Strojové validátory kontrolují kontrakty a integritu; nepředstírají badatelský úsudek. Nezávislý ověřovatel ověřuje vybrané čtení, nikoli současně plán, identitu a DoD.

Tento příklad ber jako hypotézu k porovnání, ne jako předepsanou architekturu. Orchestrátor se nesmí stát drahým univerzálním čtenářem ani jediným nekontrolovaným zdrojem faktické pravdy.

Navrhni rozhodovací tabulku **kdo — kdy — na základě čeho — co rozhodne — kdo provede — jak se ověří**. Rozliš:

- ukončení jednoho běhu badatele, včetně dosaženého rozpočtu;
- splnění badatelského úkolu;
- přijatelnost konkrétního tvrzení nebo vztahu;
- technickou způsobilost výsledku k uložení;
- úplnost a způsobilost publikace.

U každého rozhodnutí má být jednoznačný vlastník. Nedovol, aby každý agent předefinovával DoD podle svého omezeného kontextu. Technický validátor může zápis odmítnout bez zavedení dalšího samostatného badatelského rozhodovatele.

Definuj stavy a přechody: pokračovat ve stejném běhu/obnovit jej, založit nový běh, vyžádat jiný pramen, nezávisle ověřit, uzavřít s doloženým výsledkem, uzavřít negativně v daném rozsahu, pozastavit kvůli zdroji či rozpočtu, předat skutečné rozhodnutí člověku. Vyčerpání rozpočtu nikdy automaticky neznamená „nenalezeno“ nebo „hotovo“.

**Povinný scénář:** na okraji snímku je neúplný zápis a pokračování zřejmě leží na sousední stránce. Badatel vrátí přesný nález a chybějící část. Ukaž, jak orchestrátor rozhodne „pokračuj na vedlejší stránce“, jak se využije dosavadní kontext, kdo rozšíření autorizuje a zaúčtuje a kdy se definitivně vyhodnotí DoD. Porovnej pokračování/resume s novým agentem; ověř dostupné mechanismy daného prostředí, nevymýšlej možnosti platformy.

### 1.6 Kontext je navrhované rozhraní

Vytvoř matici kontextu pro každou roli a fázi: minimální povinné informace, podmíněně načítané informace, zakázané vstupy, zdroj, formát, orientační velikost, doba platnosti a aktualizace. Rozliš statické instrukce, stav úkolu, důkazní materiál, výstup nástroje a historii sezení.

Urči, co se předává při startu, co až podle potřeby, co zůstává v souboru a co se vrací souhrnem s odkazem. Souhrn musí zachovat nejistotu, rozpory, prohledaný rozsah, identifikátory a podklad pro další rozhodnutí. Plné důkazy musí zůstat dohledatelné. Zkrácení nesmí způsobit znovuobjevování již přečteného ani ztrátu vztahu mezi osobami.

Prověř dědění `CLAUDE.md`, `skills:`, nástrojových schémat, paměti, stavu pracovních souborů a konektorů. Navrhni, co zkrátit, přesunout nebo načítat podmíněně, a které minimum nelze odebrat. Nezrušuj plošně instrukce jen kvůli startovní režii. Posuď cache, modelové přepínání, předávku dlouhého sezení, obnovu stavu a chybějící soubor/cestu. Stav musí být spolehlivě obnovitelný i bez historie chatu.

Limity 800/600 znaků, 12 kroků/obrázků, 80 tisíc tokenů, 55 minut a 2000 px z poznámek jsou kandidáti k ověření, nikoli univerzální pravidla. U velkého snímku řeš orientační pohled versus důkazní čtení, zachování návaznosti řádku, překryv výřezů a souřadnice. Pevný strop nesmí podstatně zdražit dokončení ani odstranit potřebné důkazy.

### 1.7 Výsledky bádání a integrita zápisu

Navrhni přesný verzovaný kontrakt zadání, dílčího výsledku, výsledku ověření, rozhodnutí o pokračování a přijatého výsledku. Ukaž kompletní malé příklady, ne jen názvy polí.

Výsledek rozlišuje doslovný přepis, normalizaci, interpretaci, tvrzení, identitu osoby, vztah, zdroj a nejistotu. Obsahuje stabilní ID úkolu/osob/pramenů, přesnou polohu důkazu, prohledaný rozsah, mezery, rozpor a návrh dalšího kroku. Slepý verifier dostává pouze nezbytné zadání a obraz, nikoli první přepis; porovnání obou čtení je další jasně určená operace.

Validace musí odhalit i formálně platný výsledek s chybnou osobou, záměnou signatury a interního ID, nepřípustným typem stránky či nesprávným rozsahem hledání. U stejnojmenných osob nebo špatně zvoleného rejstříku nestačí kontrola datových typů. Definuj vazby mezi úkolem, osobami, pramenem a tvrzením.

Prozkoumej životní cyklus vztahu jako samostatně identifikovatelného tvrzení s důkazem. Nevnucuj předem novou databázi, ale porovnej způsob, který zabrání ručnímu dvojímu zápisu téže skutečnosti. Urči aktualizaci, zpochybnění a nahrazení tvrzení, původ změn, duplicitní výsledky, idempotentní opakování a obnovu po částečném selhání deník/mapa/data/fronta.

U slučování a dělení úkolů musí přežít cíl, osoby, rozsah, cena, DoD a původ. Překryv osob sám nedokazuje totožnost dvou úkolů. Zápis opravy nesmí vyžadovat další drahé rozhodování jen kvůli nejasnému protokolu, zároveň nesmí tiše přepsat původní důkaz.

### 1.8 Web jako hlavní akceptační výstup

**Povinný scénář A–B:** na stránce osoby A je doložen vztah k B, ale stránka B jej neuvádí. Nesoustřeď se jen na vzhled. Prověř, zda vztah chybí v datech, je jen ve volném textu, ztrácí se exportem, filtrem nebo šablonou. Najdi obecné pravidlo, které podobným chybám zabrání napříč webem.

Definuj kanonický význam vztahu a projekci do obou pohledů: „A je rodič B“ musí na B vést k „B je dítě A“, ne ke kopii stejné věty. Obdobně prověř partnerství, svědectví a další podporované vztahy. Zachovej zdroj, časovou platnost a nejistotu. Hypotetický vztah nesmí být v opačném pohledu publikován jako jistý. Více rolí týchž osob se nesmí slít.

Sepiš matici **typ informace → autoritativní data → povinné pohledy → pravidlo zobrazení → přípustná výjimka → test**. Pokryj vztahy, události, jména, data, místa, zdroje, rozpory a veřejné otázky. Ne všechny údaje patří na každou stránku, ale každé vynechání musí odpovídat pravidlu, ne náhodě. Soukromí a přístupová oprávnění mají přednost před zobrazováním opačné vazby; výjimka musí být testovaná bez úniku identity.

Navrhni automatické kontroly úplnosti, správného směru vztahu, konzistence hodnot a odkazů napříč osobou, rodinou, rodem, stromem, osou a zdrojem. Testovací očekávání musí být odvozena nezávisle od stejného exportéru, který testuješ. Navrhni také kontrolu přístupových variant, vyhledávacích indexů a aktuality publikovaného buildu.

### 1.9 Skript, agent a člověk

Rozhodni podle povahy a opakovatelnosti operace, ne podle pravidla „na všechno skript“. Deterministické kontroly, validované zápisy, cache, exporty a technické transakce porovnej s agentním provedením. Čtení rukopisu, interpretaci rozporů a volbu dalšího výzkumu nepovažuj automaticky za deterministické.

Posuď možnost, aby orchestrátor spouštěl úzce vymezené validující skripty, místo aby na každý zápis zakládal nového agenta. Odděl rozhodnutí od mechanického provedení. Uveď oprávnění, kontrolu vstupů, auditní stopu a chování při selhání. Neuděluj neomezený zápis jen proto, že je levnější.

Nápady `zapis_vysledku.py`, `spotreba.py`, `vyrez.py --radek` nebo odstranění pomocníka pro technické ukládání změn jsou varianty, nikoli objednané implementace. Zvaž sjednocení existujících nástrojů a stabilní rozhraní. Technická chyba prostředí musí být odlišena od chyby bádání a blokovaného portálu.

### 1.10 Cena a vyhodnocení variant

Rozlož cenu celého toku na skutečné bádání, kontrolu, orchestraci, předávání, zápis, technické uložení změn, export a opravy. Jednotkou hodnocení není levný agent, ale dokončená badatelská otázka a správně promítnuté poznání na webu; zahrň i užitečně uzavřený negativní výsledek.

Převzaté „ekv“ z poznámek je vážená metrika, ne skutečný účet. Pro srovnání ji můžeš zachovat se stejnými vahami. Peněžní cenu dopočítej jen s doloženým modelem, sazbami a přesnou definicí vstup/cache/output polí; pozor na dvojí započtení cache. Odhady úspor nelze prostě sčítat, protože se překrývají. Úspora ve startovním kontextu nemusí znamenat úsporu celého úkolu.

Navrhni opakovatelné srovnání dnešní a cílové metodiky na stejné sadě případů, včetně neúspěchů a oprav. Uváděj celkovou cenu, cenu správného uzavření, přesnost tvrzení, úplnost vazeb na webu, počet ručních oprav, restartů, předání a duplicitních čtení. Model, prostředí a obtížnost musejí být srovnatelné. Urči, která data chybějí, co je změřeno a co odhad. Neuváděj garantovaná procenta úspory bez podkladu.

### 1.11 Testy cílové metodiky

Kromě unit a kontraktních testů navrhni průchodové scénáře:

1. Jeden jasný záznam → přesně přijatá tvrzení → správné osoby a vztahy na webu.
2. Neúplný zápis → sousední stránka → pokračování s minimálním opakováním kontextu.
3. Stejné jméno, jiná osoba → žádné předčasné sloučení.
4. Dva úkoly se stejnou osobou a jiným cílem → nesloučí se; rozdělení nedědí nesprávné osoby.
5. Neúplný rejstřík / jen ženichové → nesprávně uzavřené hledání nevěsty je odmítnuto.
6. Nečitelný obraz, nedostupný portál, vyčerpaný rozpočet → odlišné stavy, žádné falešné „nenalezeno“.
7. Slepé přepisy se rozcházejí → zachovaná nejistota, přesný další krok.
8. Výsledek s chybnými identifikátory či formátem stránky → odmítnutí před zápisem; srozumitelná oprava.
9. Opakovaný výsledek / přerušený zápis → žádné duplicity, konzistentní fronta a deník.
10. Vztah A–B → odpovídající inverzní vztah na B, stejné důkazy a jistota; změna vztahu se promítne všude.
11. Omezený přístup → žádný únik údajů ani přes opačnou vazbu či vyhledávání.
12. Zelená brána a následná změna dat/šablony/dist → neplatná publikace je zablokována.
13. Restart orchestrace → obnovené DoD, důkazy a další krok bez úplného nového čtení projektu.

Odděl strojově kontrolovatelnou integritu od kvality badatelského úsudku. Pro čtení a interpretaci navrhni malou referenční sadu s odborně ověřeným výsledkem; testy v CI samy nepotvrzují správnost genealogie. Chyba musí být testem skutečně vyvolatelná, ne jen rozpoznatelná podle klíčového slova v dokumentaci.

### 1.12 Jak metodiku dále vyvíjet

Navrhni jednotný proces požadavek → analýza dopadu na produkt a cenu → návrh metodiky/kontraktu → implementace → ověření → migrace. Připrav krátké šablony zadání, analýzy, implementačního ticketu a testovacího protokolu.

Urči autoritativní místo pro každé pravidlo, jeho vlastníka a vazbu na test; definice rolí a kontextové balíčky z něj mají čerpat bez ručního rozmnožování různých verzí. Posuď kompatibilitu s aktualizacemi původního projektu, změny schémat, aktualizaci existujících projektů a zachování důkazů. Návrh může změnit ADR; uveď proč a jaké rozhodnutí nahrazuje.

Etapy migrace mohou být malé a bezpečné, ale cílový návrh nesmí být omezen na drobné záplaty. Rozliš okamžité zmírnění škody od odstranění systémové příčiny. Pořadí odvoď z přínosu pro přesnost, provozní cenu a závislostí, nikoli jen z jednoduchosti změny.

### 1.13 Výstup a DoD tohoto auditu

Odevzdej jeden dokument, který obsahuje:

1. Přesné pochopení produktu a priorit; nejvýše pět systémových příčin, nejen seznam symptomů.
2. Současný tok, jeho náklady a ztráty kvality; důkazy z kódu a případové studie rozlišené.
3. Porovnání alespoň dvou cílových variant, povinně i „badatel + metodik“, a doporučení, včetně provozní ceny, přesnosti, rizik, údržby a migrační ceny. Uveď hlavní uživatelské vstupy a případné interní pomocníky.
4. Matici rolí, vlastníků DoD, rozhodovacích pravidel a stavových přechodů.
5. Matici kontextu: co, komu, kdy a proč; pokračování, cache, předávka a obnova.
6. Kontrakty a kompletní ukázky zadání, dílčího nálezu, pokračování, ověření a přijatého tvrzení/vztahu.
7. Pravidla úplnosti a konzistence webu včetně A–B, výjimek a kontrol.
8. Testovací a měřicí plán s doloženým baseline, cílovými kvalitativními podmínkami a metodou ověření úspor.
9. Migrační plán a implementační backlog navázaný na cílovou architekturu; soubory/komponenty, závislosti, testy, návrat při chybě.
10. Čtyři navržené šablony pro další vývoj metodiky, dostupné dosavadní výsledky testů, plán budoucího ověření, omezení a zbývající skutečná rozhodnutí.

Audit je hotový, když z návrhu jde jednoznačně určit další krok a odpovědného vykonavatele u každého povinného scénáře; je zřejmé, co dostane do kontextu; je určeno místo přijetí výsledku; a návrh testů přesně určuje, jak odhalit ztracený či opačně interpretovaný vztah A–B. V tomto úkolu se testy neimplementují a jejich účinnost se neprohlašuje za ověřenou. Musí být jasné, jak ověřit cenu a kvalitu vůči dnešku. Nestačí seznam oprav T1–T7 ani obecné doporučení „zkrátit prompty, přidat schéma a testy“.

## 2. Podklady z běhu 14.–15. 11. 2026

Zdroj: uživatelem přiložený `poznamky_pro_skill.md`. Následující údaje jsou převzaté, nikoli v této aktualizaci nezávisle reprodukované. Soubor obsahuje pozorování, návrhy i otevřená rozhodnutí; navržené limity a skripty nejsou automaticky schválenou cílovou metodikou.

### 2.1 Uvedené měření

Vážená metrika: `ekv = vstup + 1,25 × zápis cache + 0,1 × čtení cache + 5 × výstup`. Definici vstupu a případný překryv s cache je třeba ověřit v měřicích skriptech.

| Ukazatel | Hodnota uváděná v poznámkách | Co z ní zkoumat |
|---|---|---|
| Celý běh | 10,88 mil. ekv | Cena dokončených výsledků včetně neúspěchů a oprav |
| Orchestrátor | 4,73 mil. ekv, 43 % celku | Zda skutečně rozhoduje, nebo draze rekonstruuje a přenáší stav |
| Ztráty cache orchestrátoru | 1,18 mil. ekv; 3 změny modelu a pauza 78 min | Příčinu a výhodnost nové relace versus pokračování |
| Další režie orchestrátoru | karty 0,49 mil.; velké soubory 0,46 mil.; zprávy 0,33 mil. ekv | Úplnost a cenu rozhodovacího kontextu |
| Start pomocníka | 10,4–12 tis. tokenů; verifier 8,5 tis.; browser-reader 37 tis. | Nástroje, děděné instrukce a nezbytné minimum role |
| Mediány operací | technické uložení změn 47 tis.; fronta 65 tis.; verifier 43 tis.; deník 155 tis.; rejstřík 360 tis.; kniha 320 tis.; browser 72 tis. ekv | Mechanické operace versus náklady na odborný úsudek |
| Browser | 3 běhy bez výsledku | Kontrola prostředí před placeným během a klasifikace blokace |
| Nápověda a vyhledávání | 48× help ~185 tis.; 70× grep velkých souborů ~215 tis. ekv | Objevitelnost stabilního rozhraní, opakované dohledávání |
| Zlepšení proti starším běhům | start 31,8 → 12,5 tis.; ekv/pomocník 565–647 → 132 tis. | Již dosažený přínos; srovnatelnost úloh není doložena surovými logy |

Rozklad startu researcheru podle poznámek: nástroje 4,5 tis., agentní skill 1,5 tis., CLAUDE.md/paměť 1,3 tis., role 1,3 tis., prostředí 0,8 tis., stav pracovních souborů 0,5 tis., karta 0,9 tis.; od dalšího kroku konektor ~1 tis. Nejde o nově změřené hodnoty v tomto auditu.

### 2.2 Případy k systémové analýze

| Pozorování z běhu | Systémová otázka pro audit |
|---|---|
| Čtyři výsledky researcheru odmítla mapa: typ/kvalita stránky a signatura místo interního ID | Kdo poskytuje výstupní kontrakt, kdy se validuje a proč se chyba zjistí až po drahém bádání? |
| Sloučení různých úkolů napříč frontami kvůli překryvu osob; rozdělené úkoly dědily nesprávné osoby | Jaká je identita úkolu a jak se zachovává jeho záměr, rozsah a DoD? |
| Deník přijal jméno místo ID osoby; opravný zápis opět přiřadil nesprávné osoby | Jak ověřit sémantické přiřazení a bezpečně provést opravu bez řetězce dalších omylů? |
| Rejstřík ženichů byl použit k hledání nevěsty | Jak se do zadání dostane pokrytí zdroje a jak brání falešně negativnímu závěru? |
| Verifier dostal 13 obrázků nad 2000 px, včetně celých skenů; nevhodný výřez způsobil dva další běhy za 286 tis. ekv | Jak připravit čitelný důkaz při zachování řádku a jak technicky ověřit jeho vhodnost před předáním? |
| Obrázky v kořeni, TEMP i veřejných složkách; rozpočtový soubor v data/ | Kdo vlastní pracovní artefakty, cache a publikační hranici? |
| Orchestrátor po selhání balíčku četl osoby 5×, deník 4×, použil 26 grepů a celý sken | Jaká je bezpečná a levná cesta při chybě kontextového rozhraní? |
| 11 zablokovaných příkazů pro technické ukládání změn, nejednotné podpisy a popisy změn | Je technická operace nesprávně delegována na generativní rozhodování? |
| Interaktivní alias rm způsobil čekání; find nad 15 GB na OneDrivu byl pomalý | Jak odlišit prostředí, I/O a chybu nástroje od chyby agentní metodiky? Automatické rm -f není obecné řešení. |
| Chybějící vstupní fronta, odhadovaná spotřeba, 473 startů python aliasu po ~0,5 s | Jak se ověří připravenost projektu a měří skutečný průchod procesu? |

Navržené úspory v původních poznámkách (hygiena sezení, skripty místo agentů, omezení kontextu, karet a výřezů) se mohou překrývat. Jejich součet nepředstavuje doloženou dosažitelnou úsporu. Modely, pevné limity, zrušení rolí a nové skripty musí vzejít z porovnání cílových variant.

## 3. Původní předaudit — historický podklad

Následující zjištění vycházejí z dřívějšího prostudování souborů a cílených kontrol z 15. 11. 2026. V aktuálně dostupných souborech již mohou být vyřešena. Při této úpravě zadání nebyl projekt znovu testován. Návrhy oprav v této příloze jsou původní dílčí návrhy, nikoli omezení systémového zadání v části 1; musí se přehodnotit v cílové metodice.

Jde o cílený předaudit architektury instrukcí, předávání výsledků a kontrol, nikoli úplný audit všech nástrojů. Zdrojem byly tehdy dostupné soubory projektu. Projekt nebyl upraven. Nebyl proveden plný build webu, celá testovací sada, živé bádání ani skutečné nasazení.

Prošly `scripts/pokryti.py --json` a tři sady v `skills/rodokmen/tests/`: `test_agenti_definice.py` (18), `test_hlidac_orchestratora.py` (14), `test_kontext.py` (9). Celkem 41 testů. Zelený výsledek není důkazem správnosti celého workflow.

Priority níže jsou návrh: P1 = zásadní rozpor nebo mezera v kontrole, P2 = zlepšení spolehlivosti či efektivity. Žádný bod zde není označen jako havárie P0.

| ID | Priorita a stav | Důkaz a dopad | Doporučená oprava a ověření |
|---|---|---|---|
| A1 | P1, potvrzený rozpor instrukcí | `agents/orchestrator.md`, Procedure 6 a Router: fixer zapisuje ověřená data. `agents/fixer.md`: zákaz zasahovat do `data/` reálného projektu. Agent nemá jednoznačnou povolenou cestu k dokončení úkolu. | Vyjasnit matici rolí a zápisových oprávnění. Rozlišit opravu pluginu a řízený zápis badatelských dat. Preferovat úpravu existujícího workflow před automatickým přidáním dalšího agenta. Testovat celý přechod nález → ověření → zápis → kontrola. |
| A2 | P1, potvrzené chování | `hooks/hlidac_orchestratora.py`, `orchestrator_smi`: povoluje `python tools/fronta.py dalsi` jako čtecí příkaz. `skills/rodokmen/tools/fronta.py`, větev `a.cmd == "dalsi"`: zapisuje spotřebu, nastavuje `probíhá`, ukládá frontu a historii. | Oddělit nezapisující náhled a přidělení úkolu, nebo výslovně přiznat omezenou mutaci. Test porovná soubory před a po čtecích příkazech a zkontroluje druhé přidělení. |
| A3 | P1, potvrzené chování izolované funkce | `tools/brana.py` ukládá `otisk_dat`; `tools/hlidac_site.py:186–208` při nasazení porovnává jen zelený stav a verzi. Izolovaný projekt s `data/`, `tools/`, `.skill_verze` a zelenou značkou s neplatným otiskem prošel `brana_duvod(..., "netlify deploy --prod", ...)` bez zamítnutí. | Svázat bránu s daty, zdroji webu a skutečně publikovaným artefaktem. Samostatně ověřit čerstvost buildu: ani nově spočtený otisk dat nedokazuje, že jim staré HTML odpovídá. Testovat změnu dat, šablony i dist po zelené bráně. Nejde o provedené nasazení. |
| A4 | P1, potvrzená slabost testu; rozsah validace dále ověřit | `test_agenti_definice.py`, `test_vystup_vysledku_ma_schema_v_dokumentaci`, kontroluje jen výskyt `pracovni/vysledky`. `skills/rodokmen-agents/SKILL.md` a `agents/researcher.md` uvádějí pole výsledku slovně. Nenalezl jsem společné verzované strojové schéma celého výsledku. | Jeden kontrakt výsledku s povinnými poli, typy, stavy a negativními příklady; validovat na hranici před zápisem. Nejprve dohledat existující dílčí validace a využít je. Test musí odmítnout chybějící zdroj, neznámý stav a neslučitelnou kombinaci výsledku a rozsahu. |
| A5 | P1, potvrzený rozpor protokolu | `agents/verifier.md` zakazuje vidět první odpověď, ale žádá výsledek `shoda / neshoda / nečitelné`. Slepý čtenář nemůže posoudit shodu s utajenou odpovědí. | Verifier vrací samostatný přepis a nejistoty po polích. Shodu vyhodnocuje další krok, který má oba přepisy. Oddělit shodu čtení od rozhodnutí o identitě osoby. Test vstupního balíčku ověří nepřítomnost prvního přepisu a test porovnání zachytí rozpor. |
| A6 | P2, potvrzená mezera metriky | `scripts/pokryti.py`, `kontrola_nastroju`: stačí zmínka názvu nástroje v textu testů. `kontrola_stranek`: ověřuje existenci testovacího souboru. Registr `skills/rodokmen/tests/e2e/stranky.json` u řady tras výslovně přiznává, že nekryje obsah. | Označit výsledek jako evidenci testů, nikoli funkční pokrytí. Evidovat konkrétní invariant a vykonávaný scénář; ukázat, že úmyslná chyba způsobí selhání testu. Nevyžadovat mechanicky vysoké procento pokrytí. |
| A7 | P2, potvrzená redukce kontroly | `tools/brana.py` a `test_jednotnost_web.py` předávají omezeným přístupům neexistující `--site`. `tools/kontrola_webu.py:43` bez dat rodů nekontroluje jejich značky. Kontrola tedy není pro všechny přístupy stejně silná. | Každou přístupovou variantu ověřovat vůči jejím vlastním očekávaným datům. Testovat konzistenci údajů i nepřítomnost nepovolených údajů v HTML, indexech hledání a dalších publikovaných souborech. |
| A8 | P2, potvrzený nesoulad dokumentace a běhu | `CLAUDE.md` popisuje unittest discovery jako běh bez sítě; zahrnutý `test_jednotnost_web.py` spouští `npm ci` a build. CI následně provádí další instalace a sestavení ukázky. | Oddělit rychlé offline testy, integrační build a živé smoke testy; určit jeden příkaz pro každou sadu. Sdílet build fixture pouze tam, kde to nenaruší izolaci. Měřit čas i počet sestavení. |
| A9 | P2, podnět k měření | `tools/kontext.py` má limit znaků, ne tokenů; orchestrátor předává i malé změny mezi specialisty a požaduje samostatné technické uložení změn po každém dokončeném ověření. Samotná angličtina ani menší balíček nezaručují nižší celkové náklady. | Porovnat skutečné celkové náklady úkolu včetně předávání, opakování a oprav. Zavést jednoduchou cestu pro nízkorizikové změny a plnou cestu pro nejistotu/identitu/soukromí. Bez měření neslibovat procentní úsporu. |

Další drobná zjištění k prověření: dokumentace používá zkrácené `tests/e2e/...`, skutečný registr je v `skills/rodokmen/tests/e2e/`; hlídač odmítá `fronta.py cekajici` a `fronta.py plan noc`, přesto je orchestrátor zmiňuje. U těchto příkazů určit vykonavatele a prověřit, zda má být čtení či mutace. Pravidla a procedury nerozmnožovat opravami na několika místech.
