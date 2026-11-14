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
  co pomůže) nebo `pramen` (archiv, co hledat). Na web jde jen potvrzený záznam. Vnitřní úkol z `ukoly_*.md` se na web
  nepřenáší, jen z něj lze vytvořit koncept (`otazky.py z-ukolu`).
- **Úkol:** hlavička z `nocni_rezim.md` + věta „cíl“ + věta „zdroj/postup“; závislost na jiném úkolu `zavisi:U-0001`
  (`fronta.py frontier` vypíše úkoly, jejichž závislosti jsou hotové). Soubory `ukoly_*` jsou vnitřní a při sestavení webu se nečtou.
- **Zpráva commitu:** `<typ>: <co se změnilo> (<osoby nebo téma>)`, bez čísla úkolu a bez jména agenta či pomocníka.
- **Název feature větve:** `<typ>/<téma>` (např. `skill/fronty-ukolu`), nikdy jen datum.

`tools/kontrola.py` hlásí zakázané výrazy v textech pro web; `denik.py` a `otazky.py` je **odmítnou už při zápisu** a sestavení
webu se kvůli nim zastaví (`export_web.py` hlásí CHYBA).
