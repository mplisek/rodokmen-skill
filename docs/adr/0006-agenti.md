# 0006: Sada agentů

Stav: schváleno. Rozhodnutí: Q6, Q11, Q16, Q17.

## Kontext

Práci řídí jedno sezení, které hledá, zapisuje i testuje; pravidla se porušují.

## Rozhodnutí

Devět agentů (orchestrátor, researcher, browser-reader, verifier, upstream-sync, test-runner, failure-analyst, fixer, test-author). Orchestrátor nic nezapisuje; jeho Bash omezí hook v pluginu podle `agent_type`, a když selže v testu, nahradí ho agent `clerk`. Hooky a oprávnění patří do pluginu, nikdy do definice agenta.

## Důsledek

Další čtyři agenti zatím nahrazují skripty a kontroly.
