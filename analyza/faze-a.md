# Fáze A: vynucování formy (deník, veřejné otázky, fronty)

Stav: **plán fáze ke schválení rozhraní.** Nic z toho zatím není implementováno. Vychází z `analyza/navrh-agentu.md`
(rozhodnutí Q1–Q19) a z glosáře `GLOSSARY.md`; rozhodnutí jsou v `docs/adr/`.

## 1. Příčina dnešního úniku na web (zjištěno v kódu)

`export_web.py` kopíruje soubory **front** přímo na web: `archivni_dotazy.md` na stránku Co hledáme (část „Prameny mimo online
matriky“) a `otazky_pro_rodinu.md` na otázky pro rodinu. Fronty ale od zavedení nočního režimu (`fronta.py`) obsahují
vnitřní hlavičky (`U-0013 | P2 | os:… | stav:…`) a procesní věty, a ty se na web dostaly spolu s nimi. Deník (`research_log.md`)
jde na web také přímo jako Markdown. Oprava tedy není kosmetická, vyžaduje oddělit **vnitřní** data od **veřejných**.

## 2. Rozsah Fáze A

| Část | Obsah |
|---|---|
| A1 | modul úložiště `zaznamy_store` (jedna smlouva `pridej`, `oprav`, `vykresli`, `over` + registr schémat + zámek souboru, jen přidávání) |
| A2 | `tools/denik.py`: `pridej`, `oprav`, `vykresli`, `over`, `migruj`, `overit-migraci` |
| A3 | `tools/otazky.py` + `data/verejne_otazky.json` (dva druhy: otázka pro rodinu, pramen mimo online matriky) |
| A4 | `export_web.py` čte deník z `denik.jsonl` a otázky z `verejne_otazky.json`; fronty se na web **nikdy** nekopírují |
| A5 | zakázané vzory v textech pro web zastaví sestavení (jen pro nové úložiště) |
| A6 | `fronta.py`: pole `zavisi_na`, příkaz pro výběr frontieru, kontrola, že vnitřní pole se nedostala do veřejných textů |
| A7 | testy (kapitola 4) a zjištění nepokrytých míst |

Mimo Fázi A (jsou v jiných fázích): značka rodu a oprava stránek (B), `rules/` a `jazyk.py` (E), agenti (C), `pokryti.py` a E2E brána (D).

## 3. Schémata

### 3.1 Deník (`denik.jsonl`)

```text
id          pořadové číslo (dnešní „#“ zachováno)
datum       YYYY-MM-DD
zdroj       { typ: archiv|stopa|rodina|jiné, text }   (archiv: archiv, signatura knihy, snímek)
rozsah      co přesně se prošlo (u negativního výsledku povinné)
hledano     jedna věta, nejvýš 160 znaků
vysledek    nalezeno | vyvráceno | nenalezeno | částečně | nečitelné
overeno     true|false
nalez       jedna věta, nejvýš 400 znaků (u výsledku nalezeno/vyvráceno)
citace      doslovný přepis a překlad
poznamka    zbytek (web ho ukáže rozbalitelně)
osoby       klíče osob
odkaz       klíč záznamu nebo výřezu
opravuje    id opravovaného záznamu
puvodni     původní text řádku (jen u migrovaných, nevykresluje se)
proces      procesní údaje z původního textu (nevykresluje se)
```

Zakázané vzory (kontrola v polích, která jdou na web): číslo úkolu, jména agentů a modelů, jméno uživatele, cesty, „ověřeno na
snímku“, „čtyři oči“, „vlna“, „dříve chybně“, mezera před dvojtečkou, šipky. Mapování starých hodnot výsledku: `potvrzeno`
a `nalezeno (ověřeno)` na `nalezeno` + `overeno`, `nedočteno` na `částečně`, řádky bez klíče ručně.

### 3.2 Veřejná otázka (`verejne_otazky.json`)

```text
id, druh (rodina | pramen), rod (číslo nebo prázdné), osoba?, otazka, proc (proč to zajímá),
pomuze (co by pomohlo), potvrzeno (datum a kdo), z_ukolu? (id vnitřního úkolu, jen v datech)
```

Pro druh `pramen` se místo `otazka` používá `archiv` a `co_hledat`. Na web jde jen záznam s `potvrzeno`.

## 4. Rozhraní, na kterých se testuje (ke schválení)

Testy jen na těchto okrajích, žádné mockování vlastních modulů; vstupy jsou dočasné projekty s vymyšlenými daty.

| # | Rozhraní | Co se ověřuje | Co nechytí |
|---|---|---|---|
| 1 | příkazy `denik.py` (argumenty a stdin na soubor `denik.jsonl` a vykreslenou tabulku) | schéma, délky, výčty, zakázané vzory, odmítnutí chybného zápisu bez změny souboru, oprava jako nový záznam, stabilní vykreslení | vzhled na webu |
| 2 | `denik.py migruj` a `overit-migraci` nad vzorkem ve tvaru dnešního `research_log.md` (včetně řádků se 6 sloupci, bez klíče výsledku a s procesním textem) | počet řádků, žádný řádek se neztratí, `puvodni` doslova, mapování hodnot, selhání při nezpracovaném řádku | skutečná data projektu |
| 3 | příkazy `otazky.py` | schéma, jen potvrzené jde na web, vznik z úkolu ručním potvrzením | – |
| 4 | `export_web.py`: soubory v `generated/` a návratový kód (CHYBA při zakázaném vzoru v novém úložišti, fronty se nekopírují) | únik řádku fronty na web, tabulka deníku, zpětná kompatibilita | vzhled |
| 5 | příkazy `fronta.py` (`zavisi_na`, frontier, kontrola úniku) | přidělování jen hotových závislostí, vnitřní pole mimo veřejné texty | – |

Každý test je nejdřív červený. Test úniku (rozhraní 4) musí padat na vzorku napodobujícím dnešní stav, jinak nic nehlídá.

## 5. Migrace dat projektu

Provádí se **zvlášť a až po tvém schválení** (je to jiný repozitář). Skript `denik.py migruj` vytvoří `denik.jsonl` a protokol
řádků k ručnímu rozhodnutí (dnes odhadem 18 řádků s 6 sloupci a 11 bez klíče výsledku). Původní `research_log.md` zůstane
v gitu i jako archivní kopie. Do ověření `overit-migraci` se web čte jako dosud.

## 6. Zpětná kompatibilita při aktualizaci skillu

Dokud v projektu neexistuje `denik.jsonl`, `export_web.py` vykreslí deník jako dosud z `research_log.md` a vypíše výzvu
„spusť `denik.py migruj`“. Přísná kontrola (chyba místo varování) platí až pro projekty, které už nové úložiště mají. Aktualizace
skillu tak nerozbije sestavení webu před migrací.

## 7. Co potřebuju potvrdit

Viz otázky v odpovědi uživateli: rozsah fronty (A6), zpětná kompatibilita (6), druhy veřejných otázek (3.2) a rozhraní (4).
