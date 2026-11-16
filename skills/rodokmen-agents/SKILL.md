---
name: rodokmen-agents
description: Working rules for agents (orchestrator and sub-agents) that research Czech parish registers and maintain a family-tree website. Preloaded into agents, not for the user; the user guide is the "rodokmen" skill.
user-invocable: false
---

# Rodokmen: rules for agents

This skill is thin on purpose. It names the roles, the shape of the files agents exchange and **where the rules are**. It never
repeats a rule: read the rule by its id in `rules/`. The human-facing guide and the portal manuals are in the `rodokmen` skill
(Czech) and stay the source of truth for procedures.

## Language

- This layer (rules, agent definitions, instructions) is English. Research results, data and web texts are Czech.
- Talk to the user in Czech.
- Identifiers stay as they are (`doc`, `prob`, `fam`, file and field names).

## Roles

| Role | Does | Never does |
|---|---|---|
| badatel (former name orchestrator) | main entry for research in a project: plan, assignment, identity, what is accepted, when it is done; records it with the validating tools | reads images, edits data by hand, changes rules or tools |
| metodik | main entry for the methodology in the skill repository: rules, contracts, tools, agent definitions, tests, from technical notes | researches, reads family data, approves findings |
| researcher, browser-reader | reads the assigned range and returns observations as a finding file | writes to `data/`, decides identity, closes the task |
| verifier | second reading of one record without seeing the first answer; returns only its transcription | judges agreement, decides identity |
| failure-analyst | turns a failure into a fix ticket | edits files |
| fixer | applies a fix ticket to the listed files of the skill | decides scope, writes research data |
| committer | (kept for one version; research commits are done by `tools/commit.py`) commits the files a ticket lists | pushes, switches branches, adds anything unlisted |
| test-runner, test-author | run tests and report; write tests from templates | analyse or change product code |

## Files agents exchange

- **Assignment** `pracovni/zadani/<id>.json` (schema `zadani/1`) from the orchestrator, **finding** `pracovni/vysledky/<id>.json` (`nalez/1`) from
  a reader, **verification** `pracovni/vysledky/<id>_overeni_<reading>.json` (`overeni/1`) from the verifier. Their shape lives in one place,
  `tools/vysledek.py` (`vzor` prints a filled example, `over` checks a file, `souhrn` summarises a finding, `porovnej` compares two readings);
  `tools/zadani.py` writes and extends an assignment. Persons are always keys from `data/osoby.py`, volumes keys from `data/svazky.json`.
- **Decision card** from the orchestrator: goal, agent, model and why, context pack, forbidden inputs, done-when, maximum attempts,
  when to ask the user.
- **Fix ticket** from the analyst: symptom, root cause with evidence, change, allowed files, tests to run, regression test, size
  (S, M, L), what not to touch. Every reported bug gets a regression test before it is closed.

## Writing data

All writes go through scripts. An accepted reading is written by one call of `tools/zapis_vysledku.py` from the orchestrator's decision
(`rozhodnuti/1`): diary row, record and transcription, book map, task closure, follow-ups, all or nothing; `tools/commit.py` commits exactly
those files. Single items: `zapis.py` (records, volumes, transcripts, documents), `denik.py` (research log), `otazky.py` (public questions),
`fronta.py` (queues), `podnet.py` (a technical note for the skill). Queue files `data/ukoly_*.md` are internal and never reach the web. Hooks refuse manual writes to protected files and
tell you which script to use. Rule ids: R-WRITE, R-PROC.

## Rules by topic

Read the file when its situation applies; each rule has `when`, `do`, `why` and `source` (the section of the guide it comes from).

| Topic | File | Read when |
|---|---|---|
| confidence of data (R-CONF) | `rules/confidence.md` | recording any fact about a person |
| identification of persons (R-ID) | `rules/identity.md` | two persons may be one, or sources disagree |
| negative results (R-NEG) | `rules/negative.md` | about to write "not found" |
| books and pages (R-BOOK) | `rules/books.md` | choosing a register, converting folio to image |
| helper agents (R-HELP) | `rules/helpers.md` | briefing or reviewing a helper |
| writing data and web texts (R-WRITE) | `rules/writing.md` | writing data, public questions, log rows |
| process information (R-PROC) | `rules/process.md` | any text that reaches the website |
| archives (R-ARCH) | `rules/archives.md` | any request to an archive or portal |

## Keeping the rules current

`rules/zdroje.json` stores a fingerprint of the source section of every rule. When the guide changes, the rule is stale until
someone reviews it and confirms it (`scripts/pravidla.py overit`, `potvrdit <id>`). New rules from the upstream project are translated
into English before they are stored here.
