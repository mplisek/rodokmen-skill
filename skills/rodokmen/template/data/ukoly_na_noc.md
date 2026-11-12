# Úkoly na noc

Úkoly, které jde dělat automaticky bez člověka (jen ARON, viz `reference/nocni_rezim.md`).

Formát úkolu: hlavička `## U-0001 | P1 | os:57,114 | typ:křest | cíl:krest:115 | rodič:U-0000 | stav:otevřeno`
a pod ní volný text. Spravuje `tools/fronta.py` (přidání, slučování duplicit, třídění, mazání hotových); pravidla jsou v
`reference/nocni_rezim.md`. Hotový úkol se maže – jeho výsledek je v datech nebo v následných úkolech.
