# Úkoly na skill (metodika)

Úkoly pro úpravu skillu vzniklé při práci v repozitáři skillu. Úkoly z kontextu projektu patří do `data/poznamky_pro_skill.md`
v projektu. Hotový úkol se maže, výsledek je v CHANGELOG. Návrh a zdůvodnění: `analyza/navrh-router-uloh.md`.

## S-007 | P2 | typ:skill

Před každým čtením (noc i den) kontrola cache a historie, zda byl výřez už čten pro tuto otázku (`pracovni_prehled.py`, `cache.py najdi`, deník).
Zapsat do `researcher.md` a `orchestrator.md`.

## S-008 | P3 | typ:skill

Čekání a termíny: `stav:čeká` a `do:<datum>`, přehled čekajících odděleně od úkolů k řešení.

## S-009 | P3 | typ:skill

Odesílání ven: v `nocni_rezim.md` a definicích agentů výslovně: dotazy na archivy a otázky pro rodinu agent jen připraví, odešle člověk, úkol zůstane
ve frontě do potvrzení odeslání.

## S-010 | P3 | typ:skill

Úkoly pro skill: v projektu `data/poznamky_pro_skill.md`, v metodice `analyza/ukoly_na_skill.md`. Zrušit typy `skill` a `test` v projektových frontách
(`fronta.py`, šablona, `nocni_rezim.md`) a zámek `bádání × skill` přepsat tak, aby odpovídal.

## S-011 | P2 | typ:skill

Mapa knihy (kap. 6.2): `tools/mapa.py` (`hledej`, `zapis`, `stav`), mapa na svazek v `rodokmen_snimky/mapy/<portál>/<svazek>.jsonl` mimo úklid cache,
identita snímku (portál, svazek, snímek) při každém uložení do cache (`cache.py`, `aron_img.py`, `cache.py uloz` z prohlížeče), naplnění z názvů
v `pracovni/aron/`, výsledkový soubor čtenáře nese údaje o stránce a adresu, `cache.py stav` ukáže stažené snímky na nalezený záznam. Zapsat do
`researcher.md`, `browser-reader.md`, `orchestrator.md` (před stažením se zeptat mapy). Testy s falešným svazkem a mapou, bez sítě.
