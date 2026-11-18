# Stav rodokmenu a pravidla práce

Tento soubor je vstupní bod. Po každém restartu (nová konverzace, zkrácený kontext) ho Claude čte jako první,
pak poslední řádky deníku (`python3 -I tools/rejstrik.py denik --posledni 3`) a sekci „Rozpracováno“.

## Pro koho

- Výchozí osoba: (doplnit – jméno, rok a místo narození)
- Kdo s Claudem pracuje a jak chce komunikovat: (doplnit)

## Kde co je

| Soubor | Obsah |
|---|---|
| `data/osoby.py` | Přímí předci podle Kekulého čísla + rody, boční příbuzní, otevřené otázky, hypotézy. |
| `data/zaznamy.json` | Každý použitý zápis z matriky (klíč = název obrázku). |
| `data/svazky.json` | Matriční svazky (archiv, signatura, odkaz). |
| `data/prepisy.json` | Přepis originálu a český překlad každého zápisu. |
| `data/zvyrazneni.json` | Rámečky – které místo výřezu čteme. |
| `data/research_log.md` | Deník VŠECH hledání, i neúspěšných (ukázka ve starém tvaru; nový projekt má `data/denik.jsonl`, převod `tools/denik.py migruj`). |
| `data/ukoly.md` | Plán bádání: co hledat dál (prostý seznam, hotové se maže). |
| `data/udaje_od_rodiny.md` | Co řekla rodina, rodinné dokumenty. |
| `data/zajimavosti.md`, `data/pribeh.md` | Texty na web. |
| `data/archivni_dotazy.md` | Co by šlo zjistit jen v archivu nebo na úřadě. |
| `data/zadosti.md` | Poslané žádosti archivům a úřadům a jejich stav (nejde na web). |
| `data/mista.json`, `data/dokumenty.json`, `data/web.json` | Mapa, rodinné fotky a dokumenty, nastavení webu. |
| `vyrezy/`, `zdroje/` | Výřezy zápisů pro web (1800 px) a v plném rozlišení. |
| `dokumenty/` | Rodinné dokumenty a fotky od uživatele (originály). |
| `pracovni/` | Pracovní soubory (stažené stránky, kontrolní obrázky) – nejdou na web. |
| `web/` | Rodinný web. `cd web && npm run nahled` (data + sestavení + náhled); po změně dat stačí `npm run data && npm run build`. |

## Pravidla

1. Než něco ohlásím jako nové, prohledám data (`tools/rejstrik.py osoba` / `hledej`; jméno, místo, rok).
2. Údaj je „doloženo“ (doc) jen tehdy, když jsem ho přečetl přímo na snímku a druhé čtení se shoduje, nebo spor rozhodl uživatel.
3. Každé hledání (i neúspěšné) zapíšu do deníku (`tools/denik.py pridej`).
4. Nejistá čtení označím (?) – nic nedomýšlím.
5. Ke každému novému zápisu: výřez (`tools/vyrez.py`), rámeček (`tools/ramecek.py`) a přepis s překladem.
6. Po změně dat spustím `python3 -I tools/kontrola.py`.

### Pravidla od uživatele

Co uživatel řekl, jak pracovat (datum a pravidlo); platí pro každé další sezení.

- (zatím nic)

## Rozpracováno (aktualizovat průběžně)

Předání do dalšího sezení: co je rozdělané, poslední krok, co dál. Plán dalšího hledání je v `ukoly.md`, ne tady.

- (zatím nic)

## Čeká na rozhodnutí

Sporná čtení a otázky, které rozhodne uživatel (do té doby `prob`).

- (zatím nic)
