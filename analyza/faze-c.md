# Fáze C: agenti, kontextový balíček a zpráva o originálu

Stav: **implementováno** (Q-C1 až Q-C5 potvrzeny: ano). Odchylky od plánu: hook je `hooks/hlidac_orchestratora.py` a `hooks/hooks.json`
(spouští `python3`, při selhání `python`); `browser-reader` má místo `tools:` seznam `disallowedTools` (aby zdědil nástroje prohlížeče z relace). Vychází z `analyza/navrh-agentu.md`
(kapitola 4, 4.7, 9.1; rozhodnutí Q6, Q7) a z `analyza/overeni-platformy.md`. Větev `faze-c-agenti` stojí na Fázi E.

## 1. Rozsah

| Část | Obsah |
|---|---|
| C1 | `skills/rodokmen/tools/kontext.py`: deterministické sestavení kontextového balíčku podle témat |
| C2 | `scripts/sync_report.py`: co je nového v originále (commity, verze, PR, issues, překryv s forkem); nástroj pro `upstream-sync` |
| C3 | `agents/*.md` v pluginu (anglicky), počáteční sada 9 agentů z 4.1 |
| C4 | hook `PreToolUse` pro orchestrátora (Bash jen `fronta.py` výpis a `kontext.py`) |
| C5 | kontroly definic agentů: pole, nástroje, jazyk, odkazy na pravidla a skripty |
| C6 | testy všeho výše, dokumentace, CHANGELOG |

Mimo Fázi C: `pokryti.py` a E2E brána (Fáze D), agenti `record-writer`, `skill-dev`, `web-steward`, `privacy-reviewer`
(zatím skripty, 4.1).

## 2. Návrh rozhraní (ke schválení)

### 2.1 `kontext.py`

```text
kontext.py --osoba 17 --tema identity,books [--limit 6000]
```

- Výstup je Markdown na stdout: záznam osoby (jen pole nutná k úkolu, ne celé `osoby.py`), navázané zápisy, otevřené otázky
  osoby, pravidla vybraná podle témat z `rules/` (celé bloky `R-…`), zakázané vstupy.
- Témata = názvy souborů v `rules/` (`confidence, identity, negative, books, helpers, writing, process, archives`); neznámé téma
  je chyba s výpisem platných.
- **Orchestrátor vybírá jen témata, skript balíček sestaví.** Stejný vstup dává stejný výstup (řazení podle id).
- Jen čtení; nikdy nezapisuje, nečte `ukoly_*.md` ani veřejné otázky mimo otevřené otázky osoby.
- `--limit` omezuje znaky; po překročení skript skončí chybou a řekne, co zúžit (neořezává mlčky).

### 2.2 `sync_report.py`

```text
sync_report.py [--od <ref>] [--json]
```

- Čte **jen lokální git** po `git fetch upstream` (síť a GitHub API nepoužívá; PR přes `refs/upstream-pr/*`, pokud jsou stažené).
- Výstup: verze originálu a forku, nové commity `HEAD..upstream/main`, dotčené soubory, **překryv** (soubory změněné i ve forku
  od společného předka), pravidla `rules/` s dotčeným zdrojovým oddílem (volá logiku `pravidla.py`).
- Nikdy nesloučí ani nepushne; do originálu nezapisuje nic.

### 2.3 Definice agentů

- `agents/<jméno>.md` v kořeni pluginu: `name`, `description` (začíná rozhodujícím slovem), `tools`, `model`, `skills:
  [rodokmen-agents]`. Anglicky, každý končí **kritériem dokončení**.
- Pluginoví agenti ignorují `hooks` ve frontmatteru, proto hlídání patří do hooků pluginu (C4), ne do definic.
- `orchestrator` se spouští jako hlavní vlákno (`claude --agent rodokmen:orchestrator`); nemá `Edit`, `Write`, web.
- Výstupy specialistů jsou JSON v `pracovni/vysledky/<id>.json` (schéma z 4.3); schéma kontroluje test, ne agent.

### 2.4 Hook orchestrátora

`PreToolUse` na `Bash`: čte `agent_type`; pro `orchestrator` povolí jen příkazy `python …/fronta.py (vypis|seznam)` a
`python …/kontext.py …`, vše ostatní odmítne s hláškou. Pro ostatní agenty nedělá nic. **Pokud se ukáže křehký, náhradou je
„žádný Bash“ + malý agent `clerk`** (4.2).

## 3. Švy a testy (nejdřív červené)

| Šev | Test |
|---|---|
| `kontext.py` | stejný vstup = stejný výstup; neznámé téma = chyba; limit = chyba; nečte `ukoly_*.md`; obsahuje pravidla jen z vybraných témat |
| `sync_report.py` | v dočasném repozitáři s „upstream“: nové commity, překryv, dotčené pravidlo; nic nezapisuje |
| definice agentů | všechna povinná pole, `tools` jen ze seznamu, `orchestrator` bez `Edit/Write`, jazyk anglicky (`jazyk.py`), odkazy na existující skripty a `R-…` |
| hook orchestrátora | povolí `fronta.py vypis`, `kontext.py`; odmítne `rm`, `git`, `curl`, zápisové příkazy `fronta.py`; ostatním agentům nevadí |

## 4. Otázky k potvrzení

- **Q-C1:** Agenti ve složce `agents/` pluginu (ne v `.claude/agents/` projektu), takže se aktualizují s pluginem. Ano?
- **Q-C2:** `sync_report.py` ve `scripts/` (údržba repozitáře, jako `pravidla.py`), `kontext.py` v `tools/` (běží v projektu). Ano?
- **Q-C3:** `kontext.py` čte osoby přes stávající `osoby.py` (ne přímo ze souborů dat). Ano?
- **Q-C4:** Hook orchestrátora zapsat do `hooks/hooks.json` pluginu (běží pro všechny projekty s pluginem, ale jen pro
  `agent_type == orchestrator`). Ano?
- **Q-C5:** Po fázi neměním tvůj projekt `..\rodokmen`; agenti se tam projeví až po aktualizaci pluginu. Ano?
