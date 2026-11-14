# Glosář

Pojmy, které se v návrhu, kódu a webu používají a dřív kolísaly. Jeden pojem = jedno slovo; anglický ekvivalent je pro pravidla
a agenty (`rules/`, definice agentů). Příklady jsou vymyšlené.

| Pojem | EN | Význam | Neplést s |
|---|---|---|---|
| **rod** | line | skupina předků pod jedním zakladatelem (u dědečků začíná dědečkem po mužské linii, u babiček jejich rodiči); má barvu a číslo (8–15) | *větev* |
| **větev** | branch | část rodiny, která má vlastní přístup na web (třeba rodina jedné vnučky) | *rod* |
| **přístup** | access | nastavení, kdo co na webu vidí (kořen, práva, souhlasy, odpověď na bráně) | *verze webu* |
| **verze webu** | web version | sestavený web pro jeden přístup (`dist/_p/<id>/`) | *pohled* |
| **pohled** | view | výpočet, které osoby a údaje přístup vidí (`pohled.py`) | *verze webu* |
| **zápis** | register entry | jeden zápis v matrice (křest, sňatek, úmrtí) | *záznam* |
| **záznam** | record | položka `zaznamy.json` s výřezem a přepisem zápisu | *zápis* |
| **jistota** | confidence | `doc` (doloženo zápisem), `prob` (pravděpodobné), `fam` (od rodiny) | – |
| **deník** | research log | tabulka všech hledání včetně neúspěšných (`denik.jsonl`) | *fronta* |
| **úkol** | task | položka vnitřní fronty (id, priorita, osoby, cíl, stav) | *veřejná otázka* |
| **fronta** | queue | seznam úkolů jednoho druhu (noc, k rozhodnutí, k bádání) | *deník* |
| **veřejná otázka** | public question | text pro rodinu na stránce Co hledáme, potvrzený ručně | *úkol* |
| **zrcadlo** | mirror | soubory převzaté z originálu (`SKILL.md`, `reference/*.md`), česky, slučují se gitem | *pravidla* |
| **pravidlo** | rule | krátké anglické pravidlo pro agenty v `rules/` s odkazem na zdrojový oddíl a otiskem | *návod* |
| **návod** | guide | text pro badatele a obsluhu, česky | *pravidlo* |
| **hlídač** | guard | hook, který zablokuje vybrané příkazy nebo zápisy; nikdy neblokuje testování vlastní práce | *brzda* |
| **brzda** | throttle | `slusne.py`: tempo a zastavení dotazů na archivy | *hlídač* |
| **chráněný soubor** | protected file | generovaný nebo jednou cestou zapisovaný soubor, do kterého se ručně nepíše | – |
| **frontier** | frontier | úkoly, jejichž závislosti jsou hotové a lze je přidělit | – |
| **balíček** | context pack | nejmenší kontext, se kterým agent úkol dokončí (skládá ho skript) | – |
| **rozhraní** | seam | okraj, na kterém se testuje (příkaz, soubor, sestavená stránka) | – |
| **červený test** | red test | test, který před opravou na chybě padá | – |
| **brána** | gate | kontrola, kterou musí práce projít, než se pokračuje | – |
