# Rodokmen – skill pro Claude Code

![Rodokmen z matrik a rodinný web – vějíř předků, mapa a zajímavosti](docs/banner.jpg)

Claude vás provede tvorbou rodokmenu **od rodinných vzpomínek přes digitalizované matriky až k hezkému rodinnému webu**
s vějířem předků, mapou, příběhem rodu a výřezy původních zápisů s přepisem a překladem.
Je určený pro lidi, kteří genealogii nikdy nedělali a neprogramují – technickou práci dělá Claude, vy dodáváte
znalost rodiny a rozhodujete.

Vznikl při skutečném hledání předků jedné rodiny (243 předků, 11 generací, 192 matričních zápisů za dva dny).

## Jak vypadá web
Ukázkový web s vymyšlenou rodinou Novákových (260 předků v 11 generacích) má na úvodní stránce příběh rodu, zajímavosti,
mapu, kde předci žili, osm rodů a vějíř předků. Další stránky: rodokmen po rodinách, karty osob, výřezy zápisů
s přepisem a překladem, „Co hledáme“ a deník hledání. **[Podívejte se na celou úvodní stránku ukázky →](docs/ukazka-web.png)**

## Co budete potřebovat
- **Claude Code** (aplikace pro Mac/Windows nebo příkazová řádka) a placené předplatné Claude. Rodokmen je
  dlouhá práce – počítejte s několika večery a s tím, že spotřebuje dost kreditů. Nejlevnější tarif **Pro bude
  nejspíš málo** (stačí na vyzkoušení), na celý rodokmen počítejte aspoň s nejnižším tarifem **Max**.
  Po dokončení můžete předplatné zase snížit nebo zrušit, web i data vám zůstanou.
- **Počítač s macOS nebo Windows** (obojí vyzkoušeno; Windows 11 s Pythonem z python.org a Git Bashem).
  Linux by měl fungovat, ale vyzkoušený není.
- Programy **Python 3, Node.js, ImageMagick a git**. Nemusíte je instalovat předem – Claude zkontroluje, co chybí,
  a pomůže s instalací (na Macu přes [Homebrew](https://brew.sh), na Windows přes winget).
- Volitelně účet na [Netlify](https://www.netlify.com) (zdarma), pokud chcete web zveřejnit pro rodinu.

## Instalace

### Varianta A – jako plugin (doporučeno)
V Claude Code napište:
```
/plugin marketplace add sarsonj/rodokmen-skill
/plugin install rodokmen@rodokmen-skill
```
Aktualizace později: `/plugin marketplace update rodokmen-skill`.

### Varianta B – ručně
Stáhněte repozitář (zelené tlačítko **Code → Download ZIP** na GitHubu, nebo `git clone`) a zkopírujte složku
`skills/rodokmen` do `~/.claude/skills/` (na Windows `C:\Users\<jméno>\.claude\skills\`). Výsledek:
`~/.claude/skills/rodokmen/SKILL.md`.

Pak Claude Code restartujte.

## První spuštění
1. Spusťte Claude Code (klidně v domovské složce) a napište třeba:
   > Chci udělat rodokmen své rodiny.

   nebo přímo `/rodokmen`.
2. Claude zkontroluje programy, založí složku projektu (např. `~/Rodokmen`) a začne se ptát na rodinu.
   Připravte si, co víte o rodičích, prarodičích a pradědečcích, a rodinné dokumenty (rodné a oddací listy, parte,
   fotky, kroniky) – stačí vyfotit mobilem.
3. **Příště otevírejte Claude Code přímo ve složce projektu** (`cd ~/Rodokmen && claude`, nebo v aplikaci
   vyberte tuto složku). Claude si přečte, kde jste skončili, a naváže.

Chcete nejdřív vidět, jak web vypadá? Řekněte: *„Ukaž mi ukázkový web.“* Claude založí ukázkový projekt
s vymyšlenou rodinou a spustí náhled.

## Jak to probíhá
| Fáze | Co děláte vy | Co dělá Claude |
|---|---|---|
| 0. Příprava | potvrdíte instalaci programů | založí projekt |
| 1. Rozhovor | vyprávíte, dodáte dokumenty, zeptáte se příbuzných | zapisuje, čte dokumenty, navrhuje otázky |
| 2. Matriky | rozhodujete sporná místa | hledá svazky, stahuje a čte zápisy, dělá výřezy, přepisy a překlady, vede deník hledání |
| 3. Příběhy | doplníte rodinné historky, schválíte texty | průběžně sbírá zajímavosti, napíše „Příběh <vašeho rodu>“ |
| 4. Web | díváte se a říkáte, co upravit | staví web a ukazuje náhled |
| 5. Zveřejnění | založíte účet na Netlify, schválíte obsah | nasadí web s přihlášením rodinnou otázkou |

Matriky jsou online jen do určitého data: narození starší než 100 let, sňatky 75 a úmrtí 30 let.
O mladší údaje se žádá na matričním úřadě. Claude vám řekne, kdy to je potřeba.

## Co je v repozitáři
```
skills/rodokmen/
  SKILL.md           průvodce pro Clauda (fáze, pravidla)
  reference/         podrobné návody: čtení matrik, portály archivů, formát dat, web, soukromí,
                     metodická příručka (playbook, anglicky)
  tools/             nástroje v Pythonu (ARON, výřezy, rámečky, mapa, kontrola dat, export do webu, vějíř)
  template/          šablona projektu: prázdná data, ukázková rodina, web (Astro)
.claude-plugin/      instalace jako plugin
```

## Co umí a co ne
- **Hotové nástroje** (bez prohlížeče) mají: východní Čechy (SOA Zámrsk, ARON), jižní Čechy (SOA Třeboň,
  včetně dobrovolnických rejstříků), západní Čechy (SOA Plzeň, Porta fontium), střední Čechy (SOA Praha, eBadatelna –
  i urbáře a gruntovní knihy) a Prahu (AHMP a policejní přihlášky 1850–1914). Pro severní Čechy (SOA Litoměřice)
  stahuje snímky nástrojem, knihu ale najde přes prohlížeč. Pro Rakousko je postup přes Matriculu.
- Ostatní archivy (Brno, Opava) Claude obsluhuje obecným postupem přes prohlížeč.
  Funguje to, ale je to pomalejší.
- U úředníků, vojáků a lékařů hledá i v **dobových novinách** (ANNO, Kramerius) – kariéra, vyznamenání, parte.
- Umí načíst **rodinný strom z MyHeritage** a dalších služeb (export GEDCOM, z MyHeritage i zálohu stromu z programu
  Family Tree Builder) a udělat z něj plán hledání.
- Průběžně sbírá **zajímavosti** (svatby na poslední chvíli, rod sto let v jednom domě…) a s vámi napíše
  **Příběh vašeho rodu** – hlavní článek webu.
- Claude čte staré písmo dobře, ale ne bezchybně. Proto ke každému zápisu ukládá výřez s vyznačeným místem,
  aby se to dalo zkontrolovat, a nejistá místa označuje otazníkem.
- Placené služby (MyHeritage, Ancestry) Claude hromadně neprochází – vede to k zablokování účtu.

## Soukromí
Projekt obsahuje osobní údaje vaší rodiny. Zůstává na vašem počítači. Web je chráněný rodinnou otázkou
a není indexovaný vyhledávači. Žijící lidé jsou na něm jen se jménem a rokem narození.
Pokud projekt chcete zálohovat na GitHub, použijte **soukromý** repozitář.

## Zpětná vazba a vaše zkušenosti
Budu rád, když se mi ozvete na **sarsonj@gmail.com**: co fungovalo, co ne, jaký archiv jste použili, co vám na webu chybělo.
Užitečné změny rád zapracuji do skillu, aby je měli k dispozici i ostatní. Další verze tak bude lepší pro každého,
kdo hledá své předky.

Nemusíte nic sepisovat sami. Claude si během práce zapisuje do `poznamky_pro_skill.md` (v projektu), co by šlo zlepšit:
chyby, nové archivy, postupy a nápady, bez údajů o vaší rodině. Občas vám je nabídne k odeslání. Nic se neposílá samo:
když budete chtít, zkopírujte je do e-mailu.

## Bezpečnost
Skill je obyčejný text (návod pro Clauda) a pár skriptů v Pythonu. Všechno si můžete před instalací prohlédnout
tady v repozitáři.
- **Žádný automaticky spouštěný kód.** Plugin nemá hooky ani MCP servery. Skripty spouští jen Claude, když je
  při práci potřebuje, a Claude Code se vás na ně zeptá.
- **Kam skripty sahají:** jen do složky projektu rodokmenu. Na disku nic nemažou ani nepřepisují mimo ni.
- **Na které servery chodí:** archivní portály (ARON SOA Zámrsk, SOA Třeboň, SOA Plzeň – Porta fontium, SOA Praha –
  eBadatelna, AHMP, Národní archiv, SOA Litoměřice, Matricula), noviny (ANNO, Kramerius), OpenStreetMap (mapa
  a souřadnice obcí) a při instalaci webu registr npm.
  Na Netlify jen tehdy, když web sami zveřejníte. Nikam jinam nic neposílají, ani vaše data, ani poznámky.
- **Doporučení:** nechte v Claude Code zapnuté schvalování příkazů, aspoň dokud si nezvyknete, co Claude dělá.
  Obecně instalujte skilly a pluginy jen od lidí, kterým věříte. Skill nikdo předem nekontroluje a Claude se
  jeho návodem řídí.

## Licence
Skill je pod licencí [MIT](LICENSE): smíte ho volně používat, upravovat a šířit dál, jen zachovejte uvedení autora.
Výjimkou je metodická příručka `skills/rodokmen/reference/playbook.md`. Je to převzatá rešeršní zpráva bez uvedeného
autora, licence MIT se na ni nevztahuje (podrobnosti na začátku souboru).
