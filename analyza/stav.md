# Stav práce na metodice (předání, 16. 11. 2026)

Pro sezení, které v práci pokračuje, ať nemusí číst historii rozhovoru. Údaje o rodině tu nejsou (repozitář je veřejný).
Podrobnosti: návrh `analyza/navrh-optimalizace.md`, postup a otevřené úkoly `analyza/ukoly_na_skill.md`, měření
`analyza/baseline-2026-11-15.md` a `analyza/mereni-v0-2026-11-16.md`, rozhodnutí `docs/adr/0009-kontejner-rodu.md`.

## Role a pravidla spolupráce

- **Metodik** (toto sezení, repozitář skillu) mění pravidla, kontrakty, nástroje, definice agentů a testy. Nebádá, nečte rodinná
  data, nerozhoduje, co je správné čtení. **Badatel** (sezení v projektu) bádá; o pořadí jeho práce rozhoduje fronta úkolů.
- Od badatele přicházejí technické podněty do `data/poznamky_pro_skill.md` projektu; metodik je vyřeší ve skillu, nástroje zkopíruje
  do projektu a v projektu poznámky smaže. Metodik píše badateli do `data/STAV.md` projektu (oddíl Předání od metodiky).
- Uživatel očekává, že metodik problémy vyřeší sám a celé (příčinu, ne jednotlivý příznak). Rozhoduje jen o tom, co je opravdu jeho:
  push, sloučení do `main`, vydání, soukromí a zveřejnění, změna pravidla přesnosti.
- Test napřed (musí selhat bez změny); po každé změně CHANGELOG (Nepublikováno), commit, kontrola anonymity nového commitu
  (`python -X utf8 scripts/anonymita.py pred-pushem`). Nic se nepushuje ani neslučuje do `main` bez uživatele.

## Větve skillu (nic není pushnuto)

Řetěz, každá navazuje na předchozí: `pracovni-prehled` → `e0-zmirneni` → `e1-kontrakt` → `e2-zapis` → `e3-pokracovani` →
`e4-ucastnici` → `e5-web-brana` → `e6-badatel-metodik` → **`upstream-pr`** (aktuální, `0fa9d16`). Na `upstream-pr` jsou sloučené PR
originálu #200, #197, #201, #203 a všechny opravy z podnětů bádání po E6. Netrackovaný soubor `analyza/metodika-a-nastroje.html`
(popis metodiky pro uživatele, publikovaný jako artifact) zatím necommitnutý – rozhodne uživatel.

Worktree `../rodokmen-skill-v0` (E0, pro měření v0) už není potřeba: `git worktree remove ../rodokmen-skill-v0`.

## Co je hotové

| Oblast | Stav |
|---|---|
| E0–E6 (návrh optimalizace) | hotovo, v projektu převzato; badatel a metodik jako dva hlavní agenti |
| Měření | `mereni-v0` proběhlo (7,84 mil. ekv, stav 9 z 11 podle očekávání), bádání ho ohodnotilo (7 správně, 4 správný stav bez nálezu, 0 chybně); `mereni-v1` čeká |
| Co hledáme a barva rodu (H1–H4, ADR 0009) | hotovo, v projektu převzato; stránka čeká na převod a potvrzení veřejných otázek bádáním a uživatelem |
| PR originálu | #200, #197, #201, #203 sloučeny (s úpravami pro fork); #199 uživatel nechce; ostatní nesloučené viz `ukoly_na_skill.md` |
| Cesta badatele ke všem datům | hotovo: tabulka „What you change and with which tool“ v `agents/badatel.md`, `oprava.py` (zápisy, místa, dokumenty, osoby, otázky), texty přímo, `stav.py` vypisuje platná oprávnění z hooku |
| Audit dat | `audit_dat.py` první verze (6 kontrol); zbytek v `ukoly_na_skill.md` |

## Projekt (soukromý, `../rodokmen`)

Větev `migrace-test`, poslední commit `ce09958`; nástroje ze skillu převzaté, brána byla zelená po posledním sestavení webu.
`data/web.json` je změněný někým jiným než metodikem – nesahat, necommitovat. Větev `mereni-v0` se nikdy neslučuje (poznání z ní
převedlo bádání); smazat ji může uživatel. Nástroje se do projektu kopírují `git show HEAD:skills/rodokmen/tools/<n>.py >
../rodokmen/tools/<n>.py` až po zelených testech a po ověření, že kopie v projektu odpovídá některé verzi ze skillu (nemá vlastní úpravy).

## Otevřené

- **Na uživateli:** push a sloučení větví do `main`, vydání verze; `mereni-v1` (stejné modely rolí jako v0, po dokončení sady);
  co s `analyza/metodika-a-nastroje.html`.
- **Na bádání (zapsáno v `STAV.md` projektu):** převod a potvrzení veřejných otázek, potvrzení rolí účastníků starších zápisů
  (`ucastnici.py`), dokončení sady pro v1, výsledky ve starém tvaru, nové sezení badatele (načte novou definici).
- **Na metodikovi:** zbývající kontroly auditu (místo mimo kraj, tvary příjmení, otázky vyřešené zápisem, odkaz proti svazku);
  plné rozlišení snímku v prohlížeči (`prohlizec.py`, technika dlaždic z PR #195); audit dalších stránek webu na kontejner rodu;
  kontrola omezených přístupů a indexu vyhledávání (scénář 11); tvrzení na webu; drobnosti v `ukoly_na_skill.md`.

## Na co si dát pozor

- **Paměť:** úplnou sadu testů pouštět v popředí po částech (`test_[a-i]*`, `test_[j-o]*`, `test_[p-z]*`); běh na pozadí systém
  při nedostatku paměti ukončí a znovu se sám nespouští.
- **PowerShell:** české uvozovky „“ v příkazu rozbijí parser – texty s nimi upravovat nástrojem Edit, ne náhradou v PowerShellu.
  Python kód nepsat přes heredoc (rozbije `\n`).
- **Astro:** prázdnou hodnotu atributu vynechá; obecný kontejner rodu má proto `data-rod="obecne"`. Třída `rod-box` se v kontrole
  hledá přesně (ne `rod-box-hlava`).
- **Plugin v projektu** se načítá z pracovní složky skillu (cesta v `pracovni/.plugin_root`); přepnutí větve skillu změní badateli
  agenty i hook. Hook se spouští při každém volání znovu, definice agenta jen při startu sezení.
- **Anonymita:** příklady v kódu a testech jen s vymyšlenými jmény (Novák, Vzorný); jména z poznámek badatele nepřebírat a ani
  nálezy kontroly do textů neopisovat. Dva nálezy v commitech PR #201 jsou tabulka latinských podob křestních jmen z originálu
  (shoda s příjmeními v rodokmenu je náhodná) – rozhodne uživatel při pushi.
