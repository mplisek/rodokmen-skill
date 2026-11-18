# Zápisová pravidla a šablony

Jednotná podoba zápisů (stejná věc se zapisuje vždy stejně) a **žádné údaje o procesu v textech, které jdou na web**.

## Co nepatří do dat ani na web

- Kdo práci udělal: „pomocník N3e“, „hlavní agent“, „sonnet“, „Claude“.
- Jak se ověřilo a jak práce probíhala: „ověřeno na snímku“, „čteno na výřezu“, „čtyři oči“, „vlna 3“, čísla úkolů (N12d, U-0412).
- Patří: **zdroj** (kniha, signatura, snímek, strana), **míra jistoty** (`doc` / `prob` / `fam`, „?“ u nejistého čtení) a **fakta**.
- Proces patří jen do front (`data/ukoly_*.md`), deníku (`data/denik.jsonl`) a zpráv commitů – nikdy do `f`, `note`, `shrnuti`, `popis`.

## Šablony

- **Fakt osoby (`f`):** `* D. M. RRRR Místo čp. N; doplněk (kniha, sn., str.)` – stálé pořadí: datum, místo, čp., rodiče/partner,
  zdroj v závorce. Datum vždy `D. M. RRRR`; u neúplného `asi RRRR` nebo `M. RRRR`.
- **Poznámka (`note`):** věcný vztah (otec/matka/manžel), rozpory zdrojů, nejistoty; ne postup bádání.
- **Záznam (`zaznamy.json`):** `nazev` = `<Druh> <jméno>, <místo> čp., <rok> (<kniha>, <strana>)`; `shrnuti` jen obsah zápisu.
- **Záznam deníku (`data/denik.jsonl`):** zapisuje se jen `python3 -I tools/denik.py pridej …` a **vždy má stejnou formu**: datum
  `RRRR-MM-DD`, zdroj s typem (`archiv`, `stopa`, `rodina`, `jiné`), rozsah (u negativního výsledku povinný), hledáno (jedna
  věta, nejvýš 160 znaků), výsledek (`nalezeno`, `vyvráceno`, `nenalezeno`, `částečně`, `nečitelné`, příznak `--overeno`), nález
  (jedna věta, nejvýš 400 znaků), citace, poznámka (rozbalitelně pod řádkem), osoby, odkaz. Oprava je **nový záznam**
  s `--opravuje <id>`, původní se nepřepisuje. Tabulka na webu se z deníku generuje. Chybný záznam se odmítne.
- **Veřejná otázka (`data/verejne_otazky.json`):** zapisuje se `python3 -I tools/otazky.py`; druh `rodina` (otázka, proč,
  co pomůže) nebo `pramen` (archiv, co hledat). Na web jde jen potvrzený záznam. Odrážky z `otazky_pro_rodinu.md`
  nebo `archivni_dotazy.md` převede na koncepty `otazky.py ze-souboru`; plán bádání `ukoly.md` se na web nepřenáší.
- **Úkol v plánu (`data/ukoly.md`):** jeden řádek – osoba (číslo z P nebo zkratka z RODINA), co hledat, kde, případně vodítko;
  hotový se maže (výsledek je v deníku). Plán je vnitřní a při sestavení webu se nečte.
- **Zpráva commitu:** `<typ>: <co se změnilo> (<osoby nebo téma>)`, bez jména pomocníka či modelu.
- **Název feature větve:** `<typ>/<téma>` (např. `skill/fronty-ukolu`), nikdy jen datum.

`tools/kontrola.py` hlásí zakázané výrazy v textech pro web; `denik.py` a `otazky.py` je **odmítnou už při zápisu** a sestavení
webu se kvůli nim zastaví (`export_web.py` hlásí CHYBA).

## Pevná pole pro kontrolní čtení

Zápis, ze kterého se stane `doc`, se čte dvakrát: první čtení (tvoje nebo pomocníka) a kontrolní čtení. Obě vyplní
**tatáž pole podle druhu zápisu** – žádná vlastní pole, žádné celé věty v jednom poli. Pole jsou formulář pro čtení
v `pracovni/`, neukládají se; do dat jde výsledek (fakta, přepis v `prepisy.json`, u zápisu `overeno`).

| Druh | Pole |
|---|---|
| křest (N) | datum narození, datum křtu, jméno dítěte, otec (jméno, stav, dům, obec), matka (jméno, rodné příjmení, otec matky), kmotři (jména) |
| sňatek (O) | datum, ženich (jméno, věk, stav, dům, obec, rodiče), nevěsta (totéž), svědci (jména) |
| úmrtí (Z) | datum úmrtí, datum pohřbu, jméno, stav nebo povolání, dům, obec, věk, příčina (krátké označení) |

- Porovná je `python3 -I tools/cteni.py porovnej pracovni/cteni_<klíč>_1.json pracovni/cteni_<klíč>_2.json` (formulář:
  `cteni.py vzor N|O|Z`). Shoda pole po běžné normalizaci (mezery, „č.“ = „čp.“, měsíc slovem = číslem, w = v,
  „80 let“ = „80“) = ověřeno; spory nástroj připíše do `pracovni/sporna_cteni.json`.
- **Neshoda = spor pro uživatele**: výřez, pole a obě čtení vedle sebe (dávka sporů, SKILL.md → Spornou věc). Žádné třetí
  ani čtvrté čtení; nový výřez jen tehdy, když je výřez špatný (useknutý, rozmazaný).
- Rozhodnutí uživatele je čtení originálu: pole je `doc`, u zápisu `overeno: "uzivatel"`.
- Neobvyklý zápis (dvojčata v jednom řádku, dodatečná legitimace, přeškrtnutý údaj, údaj jen na okraji) a druh mimo
  tabulku (pozemková kniha, rodinný doklad) rovnou k uživateli.
- Co se do pevných polí nevejde (hodina, okrajové poznámky, delší věta o příčině, kdo pohřbil), zůstává v přepisu a neověřuje
  se pole po poli. Nový druh nebo pole přidává jen správce skillu na pokyn uživatele.
