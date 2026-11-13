# Zápisová pravidla a šablony

Jednotná podoba zápisů (stejná věc se zapisuje vždy stejně) a **žádné údaje o procesu v textech, které jdou na web**.

## Co nepatří do dat ani na web

- Kdo práci udělal: „pomocník N3e“, „hlavní agent“, „sonnet“, „Claude“.
- Jak se ověřilo a jak práce probíhala: „ověřeno na snímku“, „čteno na výřezu“, „čtyři oči“, „vlna 3“, čísla úkolů (N12d, U-0412).
- Patří: **zdroj** (kniha, signatura, snímek, strana), **míra jistoty** (`doc` / `prob` / `fam`, „?“ u nejistého čtení) a **fakta**.
- Proces patří jen do front, deníku (`research_log.md`) a zpráv commitů – nikdy do `f`, `note`, `shrnuti`, `popis`.

## Šablony

- **Fakt osoby (`f`):** `* D. M. RRRR Místo čp. N; doplněk (kniha, sn., str.)` – stálé pořadí: datum, místo, čp., rodiče/partner,
  zdroj v závorce. Datum vždy `D. M. RRRR`; u neúplného `asi RRRR` nebo `M. RRRR`.
- **Poznámka (`note`):** věcný vztah (otec/matka/manžel), rozpory zdrojů, nejistoty; ne postup bádání.
- **Záznam (`zaznamy.json`):** `nazev` = `<Druh> <jméno>, <místo> čp., <rok> (<kniha>, <strana>)`; `shrnuti` jen obsah zápisu.
- **Řádek deníku (`research_log.md`):** stálé sloupce; výsledek v pořadí *nalezeno / vyvráceno / nenalezeno*, nakonec odkaz na zdroj.
- **Úkol:** hlavička z `nocni_rezim.md` + věta „cíl“ + věta „zdroj/postup“.
- **Zpráva commitu:** `<typ>: <co se změnilo> (<osoby nebo téma>)`, bez čísla úkolu a bez jména agenta či pomocníka.
- **Název feature větve:** `<typ>/<téma>` (např. `skill/fronty-ukolu`), nikdy jen datum.

`tools/kontrola.py` hlásí zakázané výrazy v textech pro web.
