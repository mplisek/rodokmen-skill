# Fáze B: jednotná značka rodu, kontrola procesního textu, hlídač zápisů

Stav: **plán fáze ke schválení rozhraní.** Nic z toho zatím není implementováno. Navazuje na `analyza/navrh-agentu.md`
(Q2, Q5, Q16), `docs/adr/0001` a `0004` a na Fázi A (větev `faze-a-formy`).

## 1. Dnešní stav (zjištěno v kódu)

- **Značka rodu existuje**, ale jen na dvou místech: komponenta `components/Rod.astro` (barevný kruh a název s odkazem) a stejný
  markup, který export vkládá do Markdownu (`znak_rodu` v `export_web.py`, styl `.rod-znak`). Používá se jen tam, kde autor
  textu napsal odkaz `[Rod](/rod/<slug>/)`; holý název rodu v textu zůstane holý.
- **Měření na sestaveném webu** (název rodu ve značce × holý text): `hledame` 12 × 10, `denik` 0 × 32, `dokumenty` 32 × 6,
  `index` 12 × 8; Zajímavosti a Rody jsou jednotné. Holý text pochází z volných textů (deník, otázky, popisy dokumentů,
  úvodní karty), ne z jedné stránky.
- **Sestavení** je `astro build`, pak `pagefind` (`scripts/build.mjs`, funkce `sestav`). Mezi nimi je místo, kde jde
  provést jednotný průchod hotovými stránkami.
- Hlídač zápisů (Q2) zatím není; ve Fázi 0 vznikl jen hlídač sítě (hook v `.claude/settings.json` projektu, který zapisuje
  `novy_projekt.py` s absolutní cestou k Pythonu).

## 2. Návrh řešení

### 2.1 Jednotná značka rodu (ADR 0004)

Jednotný **průchod hotovými stránkami po `astro build` a před `pagefind`**: ve všech textových uzlech stránek nahradí holý název
rodu značkou (kruh v barvě rodu a název s odkazem na stránku rodu). Nenahrazuje v odkazech, v již hotových značkách, v nadpisech
stránek rodu samotného, v atributech, v `script` a `style` ani v `title`. Názvy, barvy a adresy rodů bere z dat dané verze webu
(každý přístup má vlastní názvy rodů), takže značka je ve všech verzích webu stejná. Markup zůstane shodný s `Rod.astro`.

- Výhoda: autor textu nic neznačkuje a pokryje se i text, který generuje export a Astro stránky, jednou funkcí.
- Mez: nahrazují se jen přesné tvary názvu (první pád množného čísla, např. „Novákové“). Skloněné tvary („Novákových“) se nenahradí,
  ale test je ohlásí jako **upozornění**, ne jako chybu, aby se dalo posoudit, zda je pravidlo nutné rozšířit.

### 2.2 Pravidla jednotnosti (kontrolují testy)

- Žádný název rodu mimo značku (až na výjimky výše).
- Barva značky je vždy barva rodu z dat verze webu a ve všech výskytech téhož rodu stejná.
- Pořadí rodů tam, kde se dělí podle rodu (Co hledáme, Dokumenty, Rody, Zajímavosti), je stejné (podle čísla zakladatele),
  oddíl „bez rodu“ je poslední.
- Žádný procesní text na žádné stránce: čísla úkolů, jména agentů a modelů, cesty do `pracovni/`, údaje o procesu
  (stejné vzory jako `zaznamy_store.ZAKAZANE`).

### 2.3 Hlídač zápisů do chráněných souborů (Q2)

Hook `PreToolUse` (`Edit|Write` a větev pro `Bash`) zablokuje **ruční** zápis do chráněných souborů a řekne, kterým skriptem se to
dělá. Neblokuje nic jiného (localhost, testy, build). Navrhovaný seznam chráněných souborů:

- `data/denik.jsonl` (zapisuje `denik.py`), `data/verejne_otazky.json` (zapisuje `otazky.py`),
- generované: `web/src/generated/**`, `web/src/data/**` (zapisuje `export_web.py`).

Fronty `data/ukoly_*.md` se **nechrání** (ruční poznámky do nich jsou běžné, `fronta.py` je jen doplňuje).

## 3. Rozhraní, na kterých se testuje (ke schválení)

Bez mockování vlastních modulů; vstupem jsou dočasné projekty s vymyšlenými daty a vzorové HTML.

| # | Rozhraní | Co se ověřuje |
|---|---|---|
| 1 | příkaz průchodu (`znackuj_rody`) nad vzorovými stránkami v dočasné složce | nahrazení holého názvu; nic v odkazech, hotových značkách, atributech a `script`; přesná shoda tvaru; stejný výsledek při opakování (idempotence); názvy rodů podle verze |
| 2 | sestavený web demo projektu (`dist/`, všechny verze) | žádný holý název rodu, barva značky = barva rodu, stejné pořadí rodů, žádný procesní text na žádné stránce |
| 3 | vstup a výstup hooku (příkaz nebo úprava souboru → povolit / zablokovat + hláška) | zablokuje ruční zápis do chráněného souboru a pustí zápis skriptem, localhost, test a build |
| 4 | obsah `settings.json`, který vytvoří `novy_projekt.py` | hook zápisů je zapsaný vedle hlídače sítě, vlastní pravidla uživatele zůstanou, `--bez-hlidace` zůstane vypnuté |

Každý test je nejdřív červený. Testy 2 musí padat na vzorku napodobujícím dnešní stav (holý název v textu deníku, otázek a popisu
dokumentu), jinak nic nehlídají.

## 4. Co potřebuju potvrdit

Otázky v odpovědi uživateli: způsob značkování (2.1), umístění hooku (project settings × plugin), seznam chráněných souborů (2.3)
a rozhraní (3).
