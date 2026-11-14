# 0007: Třídění selhání a regresní testy

Stav: schváleno. Rozhodnutí: Q7.

## Kontext

Selhání testu řeší stejné sezení, které ho zavedlo; chyby se vracejí.

## Rozhodnutí

Selhání se třídí na mechanická (skript), S, M a L. Analytik napíše zadání opravy, opravář změní jen uvedené soubory, u L rozhoduje uživatel. Každá nahlášená chyba dostane regresní test dřív, než se uzavře. E2E má strukturní kontroly bez vizuálních snímků.

## Důsledek

Zadání opravy má povinné pole regresního testu.
