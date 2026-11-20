# Projekt rodokmenu

Tohle je projekt rodokmenu vedený skillem **rodokmen**. Na začátku každé konverzace:

1. Načti skill `rodokmen` (pokud ještě není načtený).
2. Přečti `data/STAV.md` – stav, pravidla a co je rozpracované – a poslední řádky deníku (`python3 -I tools/rejstrik.py denik --posledni 3`).
3. Pokračuj tam, kde se skončilo. Komunikuj česky, stručně a srozumitelně pro člověka bez zkušeností s genealogií a programováním.
4. Síť na weby archivů jen přes brzdu `tools/slusne.py` (vlastní skripty, curl), i v zadání pomocníků – viz skill, „Šetrně k archivům“.
5. Co by šlo ve skillu zlepšit (chyby nástrojů, nové archivy, nápady), zapisuj do `data/poznamky_pro_skill.md` (skill ani jeho nástroje tu neupravuj) – viz skill, sekce „Poznámky pro správce skillu“.
6. Po bloku práce (kolo, před pauzou) zapiš předání do `data/STAV.md` („Rozpracováno“) a doporuč nové sezení (`/clear`) – dlouhé sezení platí celý kontext v každém tahu znovu; velikost ukáže `python3 -I tools/spotreba.py kontext`.
