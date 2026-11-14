# 0001: Úzký hlídač místo plošného zákazu

Stav: schváleno. Rozhodnutí: Q1, Q2, Q12.

## Kontext

Plošný zákaz `curl`/`wget` v oprávněních blokoval i `localhost` a vlastní nasazení a brání testování. Pravidlo `deny` má přednost před každým povolením, nejde zúžit.

## Rozhodnutí

Plošný zákaz se odstraní. Ochranu archivů dělá úzký hlídač (`hlidac_site.py`), který neblokuje localhost ani vlastní nasazení (Netlify, Cloudflare, vlastní domény z `web.json`). Ruční zápis do chráněných souborů blokuje samostatný úzký hook. Testy a kontroly nasazeného webu jsou volné, samotné nasazení vždy se souhlasem uživatele.

## Důsledek

Hlídač se zapíná sám a starý zákaz se při aktualizaci projektu vyjme, ochrana archivů neklesne. Hotovo ve Fázi 0.
