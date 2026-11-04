# Časová osa předků – plán stavby

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Cíl:** Stránka webu `/osa/` s pruhy životů předků a kontrola časové návaznosti (web + `kontrola.py`)
s možností odškrtnout ověřený údaj.

**Architektura:** Všechna pravidla a rozbor dat jsou v jednom modulu `tools/chronologie.py` (jen stdlib).
`kontrola.py` z něj vypisuje upozornění. `export_web.py` z něj zapíše hotová data osy do `site.json`
a Astro stránka je jen vykreslí jako statické SVG.

**Tech stack:** Python 3.9+ (stdlib), Astro (už v šabloně), žádné nové závislosti.

**Spec:** `docs/superpowers/specs/2026-11-04-casova-osa-design.md`

## Global Constraints

- Žádné nové závislosti v npm ani v Pythonu, jen standardní knihovna.
- Texty pro uživatele, komentáře i commity česky s plnou diakritikou. Commity bez traileru `Co-Authored-By`.
- Neměnit `plugin.json`, `VERZE`, README ani `CHANGELOG.md` a nezakládat tag. Verzi vydává jen autor.
- Nástroje se spouštějí `python -I -X utf8`. Sourozenecký modul se proto importuje vložením vlastní složky
  do `sys.path`, stejně jako `ebadatelna.py:31`.
- Konstanty: `ASI_ROKY = 5`, `POHROBEK_DNI = 280`, matka 15–50 let, otec aspoň 15, sňatek aspoň 15,
  žijící = `note` začíná „Žijící“, nebo nemá úmrtí a narodil se v posledních 100 letech.
- Klíče pravidel: `umrti-pred-narozenim`, `snatek-mlady`, `snatek-po-umrti`, `otec-zemrel`, `matka-zemrela`,
  `vek-matky`, `vek-otce`.
- Koncovka varování: jisté `" – jeden z údajů asi nesedí."`, nejisté `" – údaje jsou nejisté, možná nesedí."`.
  Nejisté je varování, kde je některé datum `approx`, nebo je některá dotčená osoba ve stavu `prob`, `mh` či `fam`.
- Hlásí se jen rozpor porušený pro všechny kombinace dat v intervalech.
- Osa ani varování nesmí ukázat nic, co není ve faktech, která už jdou do `site.json`.
- Dvě PR za sebou: PR 1 = úkoly 1–3 na větvi `feat/zivotni-osa-casova-osa`, PR 2 = úkoly 4–5 na větvi
  `feat/casova-osa-web` založené z PR 1 (báze PR 2 = větev PR 1).

## Review Focus

1. Číslo domu ve faktu bez data („* Holice čp. 1234“) se nesmí přečíst jako rok. Datum se proto hledá jen hned
   za značkou `*`, `×`, `†`. Test `test_cislo_domu_neni_rok` (úkol 1).
2. Neplatné datum („30. 2. 1890“) nesmí shodit export ani kontrolu, použije se celý měsíc.
   Test `test_neplatny_den` (úkol 1).
3. Osoba bez roku narození, ale se známým úmrtím („† 1940“), a osoba úplně bez dat: web nespadne, první
   dostane krátký vybledlý pruh, druhá jen jméno. Ověří se při buildu ukázky s podvrženými řádky (úkol 5).
4. Zástupná osoba („otec neuveden“) nesmí vyvolat žádné pravidlo ani řádek. Test `test_zastupna_osoba` (úkol 2).
5. Předek dvakrát v rodokmenu (`SAME`): rozpor jen jednou a odškrtnutí u aliasu platí i pro hlavní číslo.
   Testy `test_same_jednou` a `test_overeno_u_aliasu` (úkol 2).

---

## PR 1 – pravidla a kontrola

### Úkol 1: Rozbor dat na intervaly

**Files:**
- Create: `skills/rodokmen/tools/chronologie.py`
- Test: `tests/chronologie/test_chronologie.py`

**Interfaces:**
- Produces:
  - `MIN = date(1, 1, 1)`, `MAX = date(9999, 12, 31)`: otevřené meze intervalu.
  - `@dataclass(frozen=True) class Datum: od: date; do: date; approx: bool; text: str`.
    `text` je zápis data bez místa („14. 2. 1890“, „asi 1720“, „před 1740“).
  - `datum(fakt: str) -> Datum | None`: datum hned za značkou `*`/`×`/`†` (volitelně předpona
    `asi`, `≈`, `kolem`, `před`, `po`). Tvary „D. M. RRRR“, „M/RRRR“, „RRRR“.
  - `udalosti(P: dict, k: int) -> dict[str, Datum | None]` s klíči `narozeni`, `snatek` a `umrti`.
    Bere první fakt `*` a `†`. Když chybí, použije pole `y`. Sňatek je ten fakt `×`, ve kterém je prvních
    5 znaků příjmení osoby `P[k ^ 1]` (`n.split()[-1].strip("()?")`). Když takový není, vezme první fakt `×`.
  - `zastupna(p: dict) -> bool`: stejná podmínka jako `export_web.placeholder`.
  - `zije(p: dict, ud: dict, dnes: date) -> bool`.
  - `rok(d: date) -> float`: desetinný rok (`1890-07-02` je přibližně `1890.5`).

- [ ] **Step 1: Write the failing tests** v `tests/chronologie/test_chronologie.py`. Modul se importuje přes
  `sys.path.insert(0, <repo>/skills/rodokmen/tools)`. Testy jsou funkce `test_*` a dole je `for` přes `globals()`,
  který je spustí a vypíše `OK <n> testů`. Asserty:

```python
def test_cele_datum():
    d = datum("* 14. 2. 1890 Holice čp. 112")
    assert (d.od, d.do, d.approx, d.text) == (date(1890, 2, 14), date(1890, 2, 14), False, "14. 2. 1890")
def test_mesic():
    d = datum("× 3/1867 Holice"); assert (d.od, d.do) == (date(1867, 3, 1), date(1867, 3, 31))
def test_rok():
    d = datum("† 1855 Holice, na choleru"); assert (d.od, d.do) == (date(1855, 1, 1), date(1855, 12, 31))
def test_asi():
    d = datum("* asi 1720"); assert (d.od, d.do, d.approx, d.text) == (date(1715, 1, 1), date(1725, 12, 31), True, "asi 1720")
def test_pred_po():
    assert (datum("† před 1740").od, datum("† před 1740").do) == (MIN, date(1740, 12, 31))
    assert (datum("† po 1921").od, datum("† po 1921").do) == (date(1921, 1, 1), MAX)
def test_cislo_domu_neni_rok():
    assert datum("* Holice čp. 1234") is None and datum("kovář") is None
def test_neplatny_den():
    d = datum("* 30. 2. 1890"); assert (d.od, d.do) == (date(1890, 2, 1), date(1890, 2, 28))
def test_y_misto_faktu():
    u = udalosti({8: dict(n="A B", y="asi 1720–1785", f=[])}, 8)
    assert u["narozeni"].od == date(1715, 1, 1) and u["umrti"].do == date(1785, 12, 31) and not u["umrti"].approx
    u = udalosti({8: dict(n="A B", y="1680 – před 1740", f=[])}, 8)
    assert u["narozeni"].od == date(1680, 1, 1) and u["umrti"].od == MIN
    u = udalosti({8: dict(n="A B", y="† 1940", f=[])}, 8); assert u["narozeni"] is None and u["umrti"].od.year == 1940
    u = udalosti({8: dict(n="A B", y="* 1895", f=[])}, 8); assert u["umrti"] is None
def test_snatek_s_druhym_rodicem():
    P = {8: dict(n="Jan Novák", f=["× 1915 Praha Anna Malá", "× 20. 6. 1919 Holice Josefa Pokorná"]),
         9: dict(n="Josefa Pokorná", f=[])}
    assert udalosti(P, 8)["snatek"].od == date(1919, 6, 20)
def test_zije():
    d = date(2026, 11, 4)
    assert zije(dict(note="Žijící – údaje jen základní."), {"umrti": None, "narozeni": None}, d)
    assert zije({}, {"umrti": None, "narozeni": datum("* 1950")}, d)
    assert not zije({}, {"umrti": None, "narozeni": datum("* 1900")}, d)
```

- [ ] **Step 2: Run** `python -I -X utf8 tests/chronologie/test_chronologie.py`. Expected: FAIL
  s `ModuleNotFoundError: No module named 'chronologie'`.
- [ ] **Step 3: Implement** funkce z Interfaces v `skills/rodokmen/tools/chronologie.py`. Hlavička obsahuje
  docstring jako ostatní nástroje: co modul dělá a kdo ho používá. Regulární výraz faktu je ukotvený na začátek:
  `^[*×†]\s*(asi|≈|kolem|před|po)?\s*(datum)`. Pole `y` se dělí podle `–`. Hlava je narození, ocas úmrtí,
  začíná-li `y` znakem `†`, je to jen úmrtí, začíná-li `*`, jen narození. Předpona `asi` platí jen pro část,
  u které stojí, stejně jako `export_web.years()`.
- [ ] **Step 4: Run** stejný příkaz. Expected: `OK 10 testů`.
- [ ] **Step 5: Commit** `git add skills/rodokmen/tools/chronologie.py tests/chronologie/test_chronologie.py` a
  `git commit -m "chronologie.py: rozbor dat narození, sňatku a úmrtí na intervaly"`.

### Úkol 2: Pravidla kontroly

**Files:**
- Modify: `skills/rodokmen/tools/chronologie.py`
- Test: `tests/chronologie/test_chronologie.py`

**Interfaces:**
- Consumes: `datum`, `udalosti`, `zastupna` z úkolu 1.
- Produces:
  - `PRAVIDLA: tuple[str, ...]`: 7 klíčů z Global Constraints.
  - `@dataclass(frozen=True) class Varovani: k: int; pravidlo: str; text: str; mozna: bool; osoby: tuple[int, ...]`.
    `k` je osoba s ⚠ (u pravidel rodič–dítě je to dítě). `osoby` jsou dotčená čísla v pořadí dítě, otec, matka.
    Pro jednoosobová pravidla je to jen `k`.
  - `kontrola(P: dict, SAME: dict | None = None) -> list[Varovani]`: bez odškrtnutých. Projde jen hlavní čísla
    (ne aliasy a ne zástupné osoby) a rodiče přeloží přes `SAME`. Výsledek je seřazený podle `k`, každý pár
    `(pravidlo, k)` je v něm jen jednou. Odškrtnuté = `pravidlo` je v `overeno` osoby `k` nebo v `overeno`
    kteréhokoli aliasu, který na `k` ukazuje.

Podmínky (`b`, `m` a `d` jsou intervaly `Datum`, věk = celé roky mezi dvěma daty):
`umrti-pred-narozenim`: `d.do < b.od`. `snatek-mlady`: věk(`b.od`, `m.do`) < 15. `snatek-po-umrti`: `m.od > d.do`.
`otec-zemrel`: `(dítě.b.od − otec.d.do).days > POHROBEK_DNI`. `matka-zemrela`: `dítě.b.od > matka.d.do`.
`vek-matky`: věk(`m.b.od`, `dítě.b.do`) < 15, nebo věk(`m.b.do`, `dítě.b.od`) > 50. `vek-otce`: věk(`o.b.od`, `dítě.b.do`) < 15.
Otevřené meze `MIN` a `MAX` musí podmínky automaticky nesplnit. Věk se proto počítá jen, když ani jedna mez není
otevřená.

Texty (bez koncovky, za ni se připojí jedna ze dvou koncovek z Global Constraints). `syn`/`dcera` a `narodil`/`narodila`
plynou z čísla dítěte, u osoby 1 z `sex`:
- `otec-zemrel`: `"{otec} zemřel {d.text}, {syn} {dítě} se {narodil} {b.text}"`
- `matka-zemrela`: `"{matka} zemřela {d.text}, {syn} {dítě} se {narodil} {b.text}"`
- `vek-matky`: `"{matka} by při narození {syna|dcery} {dítě} ({b.text}) bylo {věk} let"`, kde věk je nejvyšší
  možný (u < 15) nebo nejnižší možný (u > 50)
- `vek-otce`: `"{otec} by při narození {syna|dcery} {dítě} ({b.text}) bylo nejvýš {věk} let"`
- `snatek-mlady`: `"{n} by při sňatku ({m.text}) bylo nejvýš {věk} let"`
- `snatek-po-umrti`: `"{n}: sňatek ({m.text}) je až po úmrtí ({d.text})"`
- `umrti-pred-narozenim`: `"{n}: úmrtí ({d.text}) je dřív než narození ({b.text})"`

- [ ] **Step 1: Write the failing tests.** Pomocná funkce `rod(**k)` sestaví `P` z dvojic `číslo: (jméno, fakty, st)`.

```python
def test_otec_zemrel_text():
    P = {8: dict(n="Jan Novák", f=["* 1890"]), 16: dict(n="Václav Novák", f=["† 1887"]), 17: dict(n="Barbora Malá", f=[])}
    v = kontrola(P)
    assert [(x.k, x.pravidlo, x.osoby) for x in v] == [(8, "otec-zemrel", (8, 16, 17))]
    assert v[0].text == "Václav Novák zemřel 1887, syn Jan Novák se narodil 1890 – jeden z údajů asi nesedí." and not v[0].mozna
def test_pohrobek_jen_roky():          # † 1889, * 1890 → nehlásí
def test_pohrobek_cela_data():         # † 1. 1. 1890, * 1. 12. 1890 → hlásí; † 1. 4. 1890, * 1. 12. 1890 → nehlásí
def test_matka_zemrela():              # † 1890 / * 1890 nehlásí; † 1889 / * 1890 hlásí
def test_vek_matky():                  # matka * 1875, dítě 1890 nehlásí; * 1876 hlásí; * 1830 hlásí; * 1839 nehlásí
def test_vek_otce():                   # otec * 1877, dítě 1890 hlásí "…bylo nejvýš 13 let…"
def test_snatek_mlady():               # * 1900, × 1913 → hlásí u téže osoby
def test_snatek_po_umrti():            # × 1920, † 1918 → hlásí
def test_umrti_pred_narozenim():       # * 1900, † 1890 → hlásí
def test_nejiste_mirnejsi():           # otec st="prob" → mozna True, text končí " – údaje jsou nejisté, možná nesedí."
def test_otevrene_meze():              # otec "† před 1740", dítě "* 1745" → hlásí; otec "† po 1700", dítě 1745 → nehlásí
def test_overeno():                    # dítě 8 s overeno={"otec-zemrel": "x"} → []
def test_overeno_u_aliasu():           # alias 20 (SAME {20: 8}) má overeno → u 8 nehlásí
def test_same_jednou():                # SAME {12: 8}, rozpor otce 16 → právě jedno varování
def test_zastupna_osoba():             # 16 = "otec neuveden" → []
def test_ukazka_bez_varovani():        # exec skills/rodokmen/template/ukazka/osoby.py → kontrola(P, SAME) == []
```

V `test_otevrene_meze` platí: „† před 1740“ a dítě 1745 se **hlásí**, protože otec zemřel nejpozději 1740.
„† po 1700“ a dítě 1745 se nehlásí.

- [ ] **Step 2: Run** `python -I -X utf8 tests/chronologie/test_chronologie.py`. Expected: FAIL s `ImportError` na `kontrola`.
- [ ] **Step 3: Implement** `PRAVIDLA`, `Varovani` a `kontrola` v `chronologie.py` podle podmínek a textů výše.
- [ ] **Step 4: Run** stejný příkaz. Expected: `OK 26 testů`.
- [ ] **Step 5: Commit** `git commit -m "chronologie.py: pravidla časové návaznosti a odškrtnutí ověřených údajů"`.

### Úkol 3: `kontrola.py`, pole `overeno` a návody → PR 1

**Files:**
- Modify: `skills/rodokmen/tools/kontrola.py` (import nahoře, nový blok před `mista = jload(...)`)
- Modify: `skills/rodokmen/reference/data.md` (popis polí osoby)
- Modify: `skills/rodokmen/template/data/osoby.py` (hlavička, popis polí)
- Modify: `skills/rodokmen/SKILL.md:311` (řádek `kontrola.py` v tabulce)

**Interfaces:**
- Consumes: `chronologie.kontrola`, `chronologie.PRAVIDLA`.

- [ ] **Step 1: Implement v `kontrola.py`.** Import se přidá podle vzoru `ebadatelna.py:31`. Pro každé `Varovani`
  přibude `warn.append(f"časová návaznost u osoby {v.k}: {v.text} Pokud údaj platí, přidej k osobě {v.k} do overeno: \"{v.pravidlo}\": \"proč údaj platí\"")`.
  U osoby s `overeno`, které není `dict`, nebo má klíč mimo `PRAVIDLA`, přibude upozornění
  `osoba {k}: overeno – neznámé pravidlo '{klíč}' (platná: …)`. Docstring dostane jednu větu o časové návaznosti.
- [ ] **Step 2: Ověř na ukázce.** Postup: `python -I -X utf8 skills/rodokmen/tools/novy_projekt.py <tmp>/p --ukazka`
  a pak `python -I -X utf8 <tmp>/p/tools/kontrola.py`. Expected: ve výpisu není žádný řádek `časová návaznost`.
  Potom v `<tmp>/p/data/osoby.py` změň u osoby 16 `'† 1921 Holice'` na `'† 1887 Holice'` a spusť kontrolu znovu.
  Expected: `upozornění: časová návaznost u osoby 8: Václav Novák zemřel 1887, syn Jan Novák se narodil 14. 2. 1890 – jeden z údajů asi nesedí. …`.
  Po přidání `'overeno': {'otec-zemrel': 'test'}` k osobě 8 řádek zmizí.
- [ ] **Step 3: Návody.** V `data.md` a v hlavičce `osoby.py` popiš pole `overeno` s příkladem
  `overeno={"vek-matky": "věk 51 let potvrzuje křest i úmrtí matky"}` a seznamem klíčů. Přidej jednu větu o tom,
  že přesnost dat ve faktech (celé datum, rok, „asi“) určuje, co kontrola pozná. V `SKILL.md` doplň do řádku
  `kontrola.py` „i časovou návaznost (narození, sňatky, úmrtí)“.
- [ ] **Step 4: Run** `python -I -X utf8 tests/chronologie/test_chronologie.py`. Expected: `OK 26 testů`.
- [ ] **Step 5: Commit, push a PR 1.** `git commit -m "kontrola.py hlídá časovou návaznost, pole overeno pro ověřené údaje"`,
  `git push -u origin feat/zivotni-osa-casova-osa`, `gh pr create --draft --base main --body-file <soubor>`.

---

## PR 2 – osa na webu

### Úkol 4: Řádky osy a export do `site.json`

**Files:**
- Modify: `skills/rodokmen/tools/chronologie.py`
- Modify: `skills/rodokmen/tools/export_web.py` (import, `placeholder`, nový klíč `timeline` v `site`)
- Test: `tests/chronologie/test_chronologie.py`

**Interfaces:**
- Consumes: `udalosti`, `zije`, `zastupna`, `rok`, `kontrola` z úkolů 1–2.
- Produces:
  - `radky(P: dict, SAME: dict | None = None) -> list[tuple[int, int]]`: dvojice `(pozice, hlavní číslo)`
    v pořadí in-order (větev otce `2k`, `k`, větev matky `2k+1`). Na místě aliasu se zrcadlí celá větev hlavní
    osoby stejným vzorcem jako `fan_chart.py:86` (`(a << d) | (k - (c << d))`). Zástupné osoby se vynechají.
  - `site["timeline"]` v `site.json`:
    `{"from": int, "to": int, "rows": [Row], "warnings": [Warn]}`, kde `from` je nejstarší rok zaokrouhlený
    dolů na desetiletí a `to` je dnešní rok.
    `Row = {"k": pozice, "slug": str, "name": str, "line": int | None, "years": str, "birth": Ev | None,
    "marriage": Ev | None, "death": Ev | None, "living": bool, "uncertain": bool, "warn": bool}`.
    `Ev = {"from": float | None, "to": float | None, "text": str}`, `None` = otevřená mez, hodnoty přes `rok()`.
    `uncertain` = `st` je `prob`, `mh` nebo `fam`, nebo je některé datum `approx`.
    `Warn = {"k": int, "slug": str, "rule": str, "text": str, "maybe": bool, "people": [slug]}`.

- [ ] **Step 1: Write the failing test**

```python
def test_radky_poradi():
    P = {k: dict(n=f"O{k}", f=[]) for k in range(1, 8)}
    assert [p for p, _ in radky(P)] == [4, 2, 5, 1, 6, 3, 7]
def test_radky_same_zrcadli_vetev():
    P = {k: dict(n=f"O{k}", f=[]) for k in (1, 2, 3, 4, 5, 6, 7, 8, 9)}; P[6] = dict(n="TÁŽ", f=["TÁŽ OSOBA jako 4"])
    r = radky(P, {6: 4})
    assert (12, 8) in r and (13, 9) in r and (6, 4) in r
    assert [p for p, _ in r] == [8, 4, 9, 2, 5, 1, 12, 6, 13, 3, 7]
def test_radky_bez_zastupnych():
    P = {1: dict(n="A", f=[]), 2: dict(n="otec neuveden", f=[]), 3: dict(n="B", f=[])}
    assert [p for p, _ in radky(P)] == [1, 3]
```

- [ ] **Step 2: Run** testy. Expected: FAIL s `ImportError` na `radky`.
- [ ] **Step 3: Implement** `radky` v `chronologie.py`. V `export_web.py` sestav `site["timeline"]`
  z `radky(P, SAME)`, `udalosti` (pro hlavní číslo), `zije` a `kontrola(P, SAME)`. Slugy a jména vezmi
  z `people`, `line` z pozice (`line_of(pozice)`). `export_web.placeholder` přepiš na volání `chronologie.zastupna`.
- [ ] **Step 4: Run** testy. Expected: `OK 29 testů`. Pak v ukázkovém projektu z úkolu 3 spusť
  `npm install` a `npm run data` ve `web/`. Expected: `web/src/data/site.json` má `timeline.rows` s 261 řádky
  (262 osob ukázky bez zástupné osoby 58) a `timeline.warnings == []`.
- [ ] **Step 5: Commit** `git commit -m "export_web.py: data pro časovou osu v site.json"`. Před prvním commitem
  vytvoř větev `git switch -c feat/casova-osa-web`.

### Úkol 5: Stránka `/osa/` → PR 2

**Files:**
- Create: `skills/rodokmen/template/web/src/pages/osa.astro`
- Modify: `skills/rodokmen/template/web/src/layouts/Base.astro:9` (`['/osa/', 'Časová osa']` hned za Vějíř)
- Modify: `skills/rodokmen/template/web/src/styles/global.css` (třídy `.osa-*` na konci)
- Modify: `skills/rodokmen/template/web/src/lib/data.js` (export `timeline`)
- Modify: `skills/rodokmen/reference/web.md` (seznam stránek v úvodu)

**Interfaces:**
- Consumes: `site.timeline` z úkolu 4, `lineByK[k].color` z `data.js`.

Kreslení (statické SVG při buildu, bez klientského JS):
- Měřítko `4 px` na rok, řádek `18 px`. Kontejner `.osa-wrap` má `overflow: auto; max-height: 85vh` (vzor `.fan-wrap`).
  Řádek s roky je samostatné SVG, má `position: sticky; top: 0` a je uvnitř kontejneru.
- Pruh `<a href="/osoba/{slug}/"><rect>…<title>{name}, {years}, věk při sňatku/úmrtí</title></a>` vede od `birth`
  k `death`. Barva je `lineByK[line].color`, u `line == null` je to `var(--unk)`. Text uvnitř pruhu: `{name} {years}`.
- Otevřená nebo široká mez (`from`, nebo `to` je `null`, nebo `to − from > 1`) se kreslí lineárním přechodem
  do průhlednosti přes šířku intervalu. Pruh s `living` je čárkovaný a vede do `timeline.to`. Pruh bez úmrtí,
  který není `living`, vede k poslední známé události (sňatek, narození dítěte z osy, `death.from`) a dalších
  5 let vybledá. Bez narození a se známým úmrtím má pruh 10 let a začátek vybledlý. Bez dat je jen jméno.
- Kroužek `r=3` v `marriage` na pruzích obou manželů. Svislá čára v `birth` dítěte jde od řádku `2k` k řádku
  `2k+1`, je-li aspoň jeden z nich na ose. Čáry se kreslí pod pruhy.
- `warn` znamená ⚠ v `var(--prob)` před pruhem. Pod osou je `<h2>Co časově nesedí</h2>` se seznamem
  `warnings[].text` a odkazy na `people`. Když je seznam prázdný, ukáže se věta „Kontrola nenašla nic, co by
  časově nesedělo.“
- Úvodní `<p class="lead">` vysvětlí čtení osy jednou větou: otec nad dítětem, matka pod ním, kroužek = sňatek,
  čára = narození dítěte.

- [ ] **Step 1: Implement** soubory výše.
- [ ] **Step 2: Build ukázky.** V projektu z úkolu 3 (už s novou šablonou: znovu `novy_projekt.py` na stejnou
  složku) spusť `npm run data` a `npm run build`. Expected: build skončí bez chyby a `dist/osa/index.html` existuje.
- [ ] **Step 3: Okrajové řádky (Review Focus 3).** Do kopie dat přidej osobu jen s `y="† 1940"`, osobu bez dat
  a chybu u osoby 16 z úkolu 3. Pak spusť `npm run data && npm run build` a stránku si prohlédni
  (`npm run nahled`, snímek obrazovky). Expected: bez chyby buildu, ⚠ u Jana Nováka a jedna položka v „Co časově nesedí“.
- [ ] **Step 4: Aktualizace z 0.7.0** (`CLAUDE.md` v kořeni). Postup: `git archive e386dfa skills/rodokmen | tar -x -C <tmp>/old`,
  pak `python -I -X utf8 <tmp>/old/skills/rodokmen/tools/novy_projekt.py <tmp>/p07 --ukazka`, nakonec
  `novy_projekt.py` z této větve na `<tmp>/p07`. Ve `web/` pak spusť `npm install && npm run data && npm run build`.
  Expected: build projde, `/osa/` existuje a v menu je „Časová osa“.
- [ ] **Step 5: Commit, push a PR 2.** `git commit -m "Web: stránka Časová osa s pruhy životů a hlášením nesrovnalostí"`,
  `git push -u origin feat/casova-osa-web` a `gh pr create --draft --base feat/zivotni-osa-casova-osa --body-file <soubor>`.
