# Úkoly na skill (metodika)

Úkoly pro úpravu skillu vzniklé při práci v repozitáři skillu. Úkoly z kontextu projektu patří do `data/poznamky_pro_skill.md`
v projektu. Hotový úkol se maže, výsledek je v CHANGELOG. Návrh a zdůvodnění: `analyza/navrh-router-uloh.md`.

## S-001 | P1 | typ:skill | stav:schváleno (Q1, Q2, Q4, Q6; Q3 s úpravou)

Router úkolů: vstupní fronta `ukoly_vstup.md`, krok routeru v `agents/orchestrator.md`, příkazy `fronta.py smeruj | rozdel | zaparkuj`,
zákaz zakládání přímo do cílové fronty. DOD povinná. Testy v `skills/rodokmen/tests/`.

## S-002 | P1 | typ:skill

`reference/nocni_rezim.md`: nahradit směrování rozhodovacím postupem z kap. 2 návrhu (včetně pravidla pro rodinu: nejvýš 3–4 generace a zajímavosti,
a pravidla „věcné otázky se zdroji nejsou rozhodnutí“). Přepsat odstavec „Nejisté čtení v noci“ (druhé čtení naslepo, teprve spor do rozhodnutí).
Přezkoumat pravidla agentů, jejichž zdrojový oddíl se změní (`pravidla.py overit`).

## S-003 | P1 | typ:skill

Struktura úkolu v `ukoly_k_rozhodnuti.md`: povinná pole otázka, možnosti, důkazy, co se zkusilo, doporučení a výchozí postup. `fronta.py pridej`
úkol bez nich odmítne; `fronta.py kontrola` varuje u úkolů začínajících slovesy ověřit, zkontrolovat, porovnat, přečíst, potvrdit.

## S-004 | P2 | typ:skill

Selhání: tabulka přechodů (kap. 4.1), počet opakování v `rezim.json` (`opakovani`), společné rozhodnutí za portál po vyčerpání pokusů, zákaz automatického
opakování po 403 a zablokování (brzda „zastavený“).

## S-005 | P2 | typ:skill

Rozpočet: pásma S až XL a práh v `rezim.json` (`rozpocet`), odhad v routeru podle složitosti, řazení priorita a cena, kalibrace pásem ze skutečné
spotřeby. Úkol nad prahem jde do rozhodnutí.

## S-006 | P2 | typ:skill

Historie a metadata: `data/ukoly_historie.jsonl` (jen přidávání), pole `ukol`, `nastroj`, `model` a strukturovaný `rozsah` v deníku,
`fronta.py znovu --vysledek nečitelné,nenalezeno --starsi-nez <verze>` (kap. 6.1).

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
