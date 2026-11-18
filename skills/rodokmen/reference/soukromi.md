# Soukromí, etika a cizí služby

## Žijící lidé

- Na webu jen jméno a rok narození (`note="Žijící – údaje jen základní."`). Žádné adresy, telefony, rodná čísla,
  zdravotní údaje, rozvody, nemanželské děti u žijících či nedávno zemřelých bez souhlasu rodiny.
- `export_web.py` to u webu hlídá sám: osobě s poznámkou „žijící“ nebo narozené v posledních 100 letech bez známého
  úmrtí (žádný rok úmrtí v `y`, žádný fakt „† …“) nechá jen jméno, rok narození a vazby – bez faktů, poznámky, zápisů,
  sňatku na stránce rodiny a bez místa na mapě. Platí pro `P` i `RODINA`; počet vypíše `npm run data`.
  Zemřelému s neznámým rokem úmrtí doplň do `f` „† po 1990“ (nebo do `y` rok úmrtí), jinak zůstane skrytý.
- **Souhlas žijícího** (zapisuj jen s výslovným souhlasem dané osoby): u osoby v `P` i `RODINA`
  `souhlas={"kdo": "Eva Nováková", "datum": "2026-11-10", "rozsah": ["udaje", "doklady"]}` (kdo souhlasil – osoba sama,
  u dětí rodič). Plné údaje se pak ukážou jen správci a přístupům s právem `soukrome`, u kterých je osoba ve **vlastní
  větvi** (`web.md`, „Více přístupů“); ostatní ji dál vidí jen jménem a rokem. `rozsah` bez `udaje` = údaje skryté.
  Správce (přístup `vse` ve webu s přístupy) vidí vše i bez souhlasu; web **bez** přístupů čte celá rodina pod jednou
  odpovědí, tam se žijící bez souhlasu ukážou jen jménem i správci.
- **Ruční soukromí:** `soukrome=True` u osoby (i zemřelé) – údaje nad jméno a roky jen správci a přístupům s právem
  `soukrome`, které mají osobu ve vlastní větvi. Jednotlivý údaj stejně: v `f` text začínající `(soukromé)`
  (`"(soukromé) rozvod 1990"`); kdo smí, vidí ho bez značky, ostatním se vynechá (i z mapy a časové osy).
  `kontrola.py` hlídá tvar souhlasu i značky. Kdo co uvidí: `python3 -I tools/pristupy.py`.
- U skryté osoby zmizí i její zápisy z matrik (i sdílený zápis sňatku), sňatek na stránce rodiny, boční příbuzní
  (`SIDE`) a doklady. Doklad (`dokumenty.json`), na kterém je skrytá osoba nebo žijící bez souhlasu s `doklady`,
  se neukáže vůbec. Boční příbuzný v `SIDE`, který je žijící (`y` v posledních 100 letech), jen jménem.
- **Rodná čísla na dokladech:** u dokladu zapiš `rc` (čí RČ na něm je – i rodiče a manželé). Na web až po úmrtním
  listu každého z nich, nebo po začernění (`vyrez.py --zacernit`, `data.md`). Platí i pro správce. `kontrola.py`
  upozorní na doklad (rodný, oddací, úmrtní list…) bez `rc`. Doklad s osobou z jiné větve přístup nevidí, ledaže ho
  správce přidělí (`pristupy`).
- **Volné texty** (příběh, zajímavosti, deník, „Co hledáme“, hypotézy) se podle osob nefiltrují a značka
  `(soukromé)` v nich neplatí – řídí je jen právo `texty`. O žijících v nich nepiš nic nad jméno.
- Citlivé věci z nedávné minulosti (sebevraždy, věznění, nemoci) – zeptej se uživatele, jestli a jak je zmínit.
- Matriční údaje starší než lhůty jsou veřejné, ale ohleduplnost platí i pro ně (zbytečně nezesměšňovat).

Web pro víc rodin (manželé, sourozenci s vlastními rodinami): každá rodina může mít vlastní přístup a vidět jen svou
větev – `web.json` → `pristupy` (`web.md`, „Více přístupů“). Ostatní větve pak na serveru pro ni vůbec nejsou.

Poznámky z webu (`poznamky: true`) píše rodina – můžou obsahovat údaje o žijících. Vidí je jen přihlášení
s poznámkami zapnutými (a jen ze svého přístupu); nevhodnou smaž `npm run poznamky -- --smazat <id>`.

## Před zveřejněním webu projdi s uživatelem

`python3 -I tools/kontrola.py` hlásí `CITLIVÉ` u textů z posledních ~100 let (sebevražda, nemoc, rozvod, dluhy, nemanželské
dítě…), které jdou na web – v poznámkách osob, ve „Co hledáme“ (`ISSUES`, otázky pro rodinu, prameny mimo matriky), u bočních příbuzných, v příčinách úmrtí, v zajímavostech,
v `data/pribeh.md` i ve všech `data/pribehy/*.md`.
Co uživatel na webu schválí, zapiš úryvkem do `web.json` → `citlive_schvaleno` (`web.md`).
Databáze obětí holocaustu (`obeti.py`) a vojenské ztráty jsou citlivé: jména obětí na web jen se souhlasem rodiny.
Údaje z rodinného stromu (GEDCOM) a od rodiny bývají právě takové – pro výzkum ano, na web jen se souhlasem.

1. Seznam žijících osob na webu a co o nich web říká.
2. Rodinné fotky a dokumenty – souhlasí ti, kdo jsou na nich (nebo jejich rodina)?
3. Přihlášení: otázka a odpověď (`web.json`) nastavená a dost těžká, nebo osobní odkazy
   (`tools/pozvanky.py seznam`) jen pro lidi, kteří je mají mít?
4. Kontakt na webu – chce tam uživatel svůj e-mail?
Teprve pak zveřejni (`npm run nasadit-cloudflare`, kdo má web na Netlify `npm run nasadit` – viz `web.md`).

## Placené a cizí služby (MyHeritage, Ancestry, Geni, FamilySearch)

- Přihlášení, platby a předplatné řeší **jen uživatel**. Zkušební verze se po skončení automaticky platí – připomeň,
  kdy končí a kde ji zrušit.
- **Žádné hromadné procházení ani stahování.** Skutečná zkušenost: automatické stažení ~180 záznamů z MyHeritage vedlo
  k zablokování účtu „kvůli možnému zneužití“ – uprostřed placené zkušební doby. Čti jen jednotlivé záznamy,
  které jsou potřeba, tempem člověka; raději požádej uživatele o export (GEDCOM) nebo o konkrétní stránky.
- Údaje odtud jsou stav `mh` a vždy se ověřují v matrikách.

## Archivní portály

Jsou zdarma a veřejné, ale servery mají omezené síly: stahuj jen snímky, které opravdu čteš, žádné celé svazky naráz,
paralelně maximálně pár požadavků. Citace vždy až na úroveň snímku (aby to šlo zkontrolovat).

## Data v gitu a sdílení

Projekt obsahuje osobní údaje rodiny. Když ho uživatel chce mít na GitHubu, pak **jen jako soukromé (private) repo**.
