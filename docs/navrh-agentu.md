# Návrh sady agentů, pravidel a testů (verze 0.1 k iteraci)

Stav: **návrh k diskusi, nic z toho zatím není implementováno.** Úvod a zdůvodnění jsou česky, specifikace agentů a pravidla
pro metodiku jsou anglicky (podle zadání). Každá kapitola končí otevřenými otázkami, nad kterými budeme iterovat.

## 1. Zjištění z dnešní kontroly webu

Webu na `http://localhost:4321/` jsem se z terminálu nedotázal (síťové volání na localhost blokuje hlídač), proto jsem prošel
sestavený web (`web/dist`) staticky. Skutečný test v prohlížeči (Playwright) zatím čeká, viz kapitola 7.

- **`/hledame/` (konec stránky):** do textu pro rodinu prosákla syntaxe fronty úkolů:
  `U-0013 | P2 | os:32,33 | typ:snatek | cíl:snatek:32 | stav:otevřeno`. Texty obsahují procesní věty
  („žádost jen po souhlasu“, „jsou uložené a přístupné?“). Jedny položky jsou řazené podle rodu, jiné podle archivu.
- **`/denik/`:** záznamy se liší tvarem i obsahem. Objevuje se číslo úkolu a jméno uživatele
  („Rozhodnuto (U-0011, Martin potvrdil)“), cesty do pracovní složky („snímky z pracovni/aron“), opravy uvnitř textu
  („dříve chybně …“) a drobné chyby tvaru („Nehledáno :“). Záznam nese i vyvrácený starý stav a nový stav v jedné buňce.
- **Rody:** hrubé měření v sestaveném webu (název rodu ve značce s barvou × holý text): `hledame` 12 × 10, `denik` 0 × 32,
  `dokumenty` 32 × 6, `index` 12 × 8. Ve Zajímavostech a na Rodech je to jednotné, jinde ne.
- Zápisová pravidla (`reference/zapisy.md`) a fronty (`tools/fronta.py`, `reference/nocni_rezim.md`) už existují, jsou ale
  jen doporučením. Nic je **nevynucuje** a nic nehlídá výstup na web.

Příčina je jedna: **volný text v místě, které čte člověk, a pravidlo, které hlídá jen ten, kdo si ho pamatuje.** Řešení proto
není „lepší agent“, ale (a) strukturovaná data, (b) generování textu skriptem, (c) test, který neprojde, když se pravidlo
poruší.

## 2. Zásady návrhu

1. **Skript před agentem.** Co jde zapsat deterministicky (zápis, řazení, číslování, verze, kontrola, pokrytí), dělá skript.
   Agent dělá jen úsudek (čtení rukopisu, ztotožnění osob, návrh řešení, psaní textu).
2. **Oddělení rolí:** kdo hledá, nezapisuje; kdo zapisuje, nehledá; kdo testuje, neanalyzuje; kdo analyzuje, neopravuje;
   kdo opravuje, nerozhoduje o rozsahu. Rozhoduje jen orchestrátor a uživatel.
3. **Zápis jen jednou cestou.** Do `data/` se píše výhradně přes `zapis.py` a navazující skripty (ne Edit, ne
   ručně psaný Python). Agent, který nemá právo zápisu, vrací strukturovaný výsledek do `pracovni/vysledky/<id>.json`.
4. **Veřejný text se generuje, nepíše volně.** Procesní údaje (číslo úkolu, jméno agenta, cesta, jméno uživatele) mají
   jedno místo (fronta, deník, commit) a do textů pro web se nedostanou. Hlídá to test (kapitola 5).
5. **Jazyk:** metodika, specifikace agentů, pravidla, testy a komentáře kódu **anglicky**; výsledky bádání, data a web
   **česky**. Agent odpovídá uživateli česky.
6. **Každá změna verze skillu v projektu spouští E2E** včetně kontroly pokrytí (kapitola 6).

Otevřené: (a) zásada 5 se dotkne stávajících českých návodů (`reference/*.md`, `SKILL.md`); navrhuju je převádět postupně
při každé úpravě, ne hromadně (viz 3.2).

## 3. Jazyková politika

### 3.1 Pravidlo (text pro `CLAUDE.md` a agenty)

```text
LANGUAGE POLICY
- Methodology, agent/skill specifications, rules, templates (structure), test descriptions and code comments: ENGLISH.
- Research results (data/, research log, queues' business text), web content, messages to the user: CZECH.
- Anything taken over from the upstream repo or a PR is translated to English before it is stored
  (the original Czech text is not kept in the repo; the PR/commit reference is).
- Data keys, file names and enumerations stay as they are (doc/prob/fam, osoby.py, ...): they are identifiers, not prose.
- The only legal Czech inside a methodology file is a quoted source term (a place name, an archive's wording) in quotes.
```

### 3.2 Jak se vynutí

- **Skript `tools/jazyk.py`** vyhodnotí podíl českých znaků s diakritikou v `reference/*.md`, `SKILL.md` a ve specifikacích
  agentů. Soubor je „česky“, když překročí práh a nemá výjimku v `tools/jazyk_vyjimky.json` (zatím všechny existující
  návody, seznam se zkracuje).
- **Test `tests/jazyk/`:** nový nebo změněný soubor metodiky v češtině = chyba. Nový návod tak vznikne anglicky.
- **Agent `upstream-sync` (kapitola 4)** překládá vše převzaté; překlad je součást jeho výstupu, ne samostatný krok.
- Existující návody: při každé úpravě souboru se převede celý soubor (úkol do fronty „migrate <file> to EN“, priorita P3).

Otevřené: (b) SKILL.md `description` obsahuje české spouštěcí fráze („rodokmen“, „předci“). Navrhuju je nechat česky, protože
podle nich se skill spouští, a anglicky psát jen tělo. (c) Je anglická metodika pro modely Sonnet a Haiku stejně spolehlivá
jako česká u české paleografie? Slovníček latinských a německých výrazů s českým výkladem by zůstal v kvótách.

## 4. Sada agentů

Poznámky k platformě: **podagent v Claude Code nemůže spouštět další podagenty.** Orchestrátor proto musí běžet jako hlavní
vlákno (`claude --agent orchestrator`, nebo pravidlo v `CLAUDE.md`, nebo skill), ne jako podagent. Ostatní jsou podagenti
v `.claude/agents/<name>.md` (frontmatter `name`, `description`, `tools`, `model`).

### 4.1 Přehled (role, model, práva)

| Agent | Role | Model (výchozí → eskalace) | Zapisuje | Hledá/čte archivy |
|---|---|---|---|---|
| `orchestrator` | triage, rozdělení, volba modelu a kontextu, brána kvality | nejsilnější | nic | nic |
| `researcher` | bádání v ARON a dalších povolených portálech | sonnet → opus u kurentu | jen `pracovni/vysledky/` | ano |
| `browser-reader` | čtení zakázaných portálů v prohlížeči (Třeboň, Praha, MZA, Opava), jeden naráz | sonnet | jen `pracovni/` | ano (prohlížeč) |
| `verifier` | nezávislé druhé čtení nálezu na snímku (čtyři oči) | sonnet (jiné sezení než čtenář) | nic | jen snímek |
| `record-writer` | převod ověřeného výsledku na zápis přes skripty | haiku → sonnet | `data/` jen přes `zapis.py` | nic |
| `upstream-sync` | sledování originálu a PR, překlad do EN, slučování | opus (konflikty), sonnet (rutina) | větev skillu | jen git/GitHub |
| `skill-dev` | změna nástrojů, šablony, testů | sonnet → opus | skill repo (větev) | nic |
| `web-steward` | texty, stránky a vzhled webu, jednotnost | sonnet | šablona + `data/web.json` | nic |
| `test-runner` | spouští testy a E2E, vrací strukturovanou zprávu | haiku | `pracovni/testy/` | nic |
| `test-author` | píše nové testy podle šablony a seznamu nepokrytého | sonnet | `tests/` | nic |
| `failure-analyst` | rozbor selhání, návrh opravy jako zadání | opus (nejasné), sonnet (jasné) | nic (jen zpráva) | nic |
| `fixer` | provede opravu přesně podle zadání | sonnet → opus | jen soubory ze zadání | nic |
| `privacy-reviewer` | soukromí před zveřejněním (žijící, RČ, souhlasy) | sonnet | nic | nic |

Co z toho **nemá být agent, ale skript:** `release` (zvednutí verze na třech místech, kontrola CHANGELOGu, tag), `kontext`
(sestavení kontextového balíčku z dat), `denik` a `fronta` (zápisy), `pokryti` (kontrola pokrytí), `jazyk`, `sync_report`
(co je nového v originálu), `triage_rules` (třídění selhání podle vzoru). Agent je používá, nenahrazuje je.

### 4.2 `orchestrator` (specifikace)

```yaml
name: orchestrator
description: >
  Decides, never does. Triages every task, picks the specialist agent, estimates complexity,
  chooses the model, defines the context pack, enforces quality gates. Use for any multi-step work.
tools: Agent, Read, Glob, Grep, Bash(python3 -I tools/fronta.py list|stav|prehled), Bash(python3 -I tools/kontext.py *)
model: strongest available
```

Rules:

- Has **no** Write, Edit, WebFetch, browser or archive tools. Reads files only to decide. Everything it wants changed
  goes through a specialist.
- For each task produce a **decision card** (kept in the queue entry, one screen):
  `goal`, `agent`, `model + why`, `context pack (files, persons, sources: list)`, `inputs forbidden`, `done when`,
  `max iterations`, `escalate to user when`.
- **Complexity score** (0–6, one point each): paleography needed; more than one candidate person; new archive or portal;
  touches data and code; touches privacy; unclear success criterion. Routing: 0–1 → haiku/sonnet small; 2–3 → sonnet;
  4–6 → opus, or split the task. A task with score ≥ 4 is first split; the score is recorded.
- **Context pack** is built by `tools/kontext.py` (deterministic): the person record, linked records, open questions, the
  methodology sections named by `topic`, and the writing rules. The orchestrator only **chooses the topics**; it never pastes
  data by hand. Principle: smallest pack that lets the agent finish; never the whole `osoby.py`.
- **Parallelism:** at most 2 archive readers, at most 1 browser reader, any number of readers of local files.
- **Stop conditions:** same failure twice, or a rule from `soukromi.md` / archive rules (`ZAKAZ`) involved → ask the user.
- Never approves its own plan for anything outward-facing (push, release, deploy, e-mail to an archive): asks the user.

### 4.3 Bádání: `researcher`, `browser-reader`, `verifier`, `record-writer`

```yaml
name: researcher
description: Reads parish registers on portals allowed for scripts (ARON, Porta fontium, ...). Returns findings only.
tools: Read, Glob, Grep, Bash(python3 -I tools/aron_*.py *, tools/vyrez.py *, tools/cache.py *, tools/slusne.py *)
model: sonnet (opus only for kurrent below 1830 when the orchestrator says so)
```

- Output contract (JSON, English keys, Czech values): `{task, finding: found|disproved|not_found, persons, record_key,
  source:{book, signature, image, page}, confidence: doc|prob|fam, quote_cs, notes_cs, crops:[paths]}`.
- Never writes to `data/`. Never claims a reading it did not see. Reports **what was searched** (for the log) even on failure.
- `browser-reader`: same contract, but only for portals that are forbidden to scripts; one session at a time, pause as in
  `SKILL.md`; on CAPTCHA, block or limit stops and hands over to the user.
- `verifier`: receives only the crop and the question, **not** the reader's answer (blind second reading), returns
  agree / disagree / unreadable with its own transcription. Disagreement goes back to the orchestrator.
- `record-writer`: input is a verified result file; output is calls of `zapis.py` / `denik.py` / `fronta.py` only. It cannot
  invent text: person facts and log lines are assembled by the scripts from the result fields (see section 5).

Replace by script: transcribing the result into `osoby.py`/`zaznamy.json` (PR #187 „zápis nálezu jedním příkazem“ is
the natural base; we should take it and extend it).

### 4.4 Synchronizace s originálem: `upstream-sync`

```yaml
name: upstream-sync
description: Tracks sarsonj/rodokmen-skill (releases, PRs, issues), translates adopted content to English, merges.
tools: Read, Edit, Write, Glob, Grep, Bash(git *, gh *, python3 tools/sync_report.py, tests)
model: opus for merges with conflicts, sonnet for reports
```

- Step 1 is a **script**: `sync_report.py` lists new upstream commits, versions, PRs, issues, files touched, and which of
  ours they overlap (the overlap table I built by hand today).
- The agent proposes: take / adapt / skip per item, with the reason; the user approves.
- Adoption rule: content that enters the repo is **translated to EN** (methodology), code comments EN, CHANGELOG stays
  Czech (it is user-facing). Stores a mapping `upstream_ref -> local path` in `docs/upstream-map.json`.
- Conflict policy: prefer upstream for areas we do not extend; keep ours where the fork has a feature (`--stranka`, privacy
  views); every conflict resolution is recorded in the merge commit message.
- Never pushes or releases: hands a green branch to the orchestrator.

### 4.5 Úprava skillu: `skill-dev`

- Works on a branch; every new tool function comes with a test (rule from `CLAUDE.md`); runs unit tests and linter
  before reporting; never touches `data/` of a real project.
- Uses `test-runner` for the full suite; does not interpret CI failures itself (see 4.7).

### 4.6 Správa webu: `web-steward`

- Owns the **web style rules** (kapitola 5.3) and the templates; changes content only through `data/` scripts.
- Text for the family is written in Czech from the structured fields; free-form hand edits of generated pages are refused.
- Hands every visual change to `test-runner` (E2E + consistency checks) before reporting done.

### 4.7 Testy a oprava: `test-runner`, `failure-analyst`, `fixer`, `test-author`

Doporučení k vaší otázce „kdo opraví chybu“:

```text
test-runner  ->  failure report (structured, no opinion)
                     |
        mechanical class? (lint, formatting, generated file, snapshot refresh)
                     |-- yes --> scripted fix (tools/fix_auto.py), then test-runner again; no agent
                     |-- no  --> failure-analyst: diagnosis + FIX TICKET
                                     |
                       ticket size = S (<= 1 file, no behaviour change) --> fixer (sonnet)
                       ticket size = M (code + test, one area)           --> fixer (sonnet/opus)
                       ticket size = L (design, several areas, privacy)   --> back to orchestrator (user decides)
                                     |
                              fixer applies ONLY the files in the ticket
                                     |
                              test-runner (same tests + full gate)
                                     |-- green --> done
                                     |-- red twice --> orchestrator escalates to user
```

- **The analyst never edits and the fixer never decides scope.** One agent doing both is faster for trivial things, but it
  makes the analyst mark its own homework and hides design changes inside "fixes". The small size class keeps the cost low.
- **Fix ticket contract:** `symptom` (failing test and line), `root cause` (with evidence: commit, line, reproduction),
  `change` (exact files and what changes), `files allowlist`, `tests to run`, `risk`, `size`, `do not touch`.
- `test-runner` is an expert at running and reporting, it returns `{suite, passed, failed:[{name, file, message}], flaky?,
  duration}` and **re-runs a failed timing test once** before reporting (we saw this today on Windows runners).
  It marks `flaky` instead of guessing.
- `test-author` writes tests from templates and from the coverage list (kapitola 6); it never edits product code.

### 4.8 `privacy-reviewer`

- Runs before any build marked for deployment: checks that restricted accesses show no living persons beyond the consent,
  no RČ, no process text, no images of blocked documents. It uses `kontrola.py` and the E2E privacy suite; the agent only
  judges borderline text. Output is a pass/fail with citations, never edits.

### 4.9 Rozhodovací příklady

| Task | Score | Agent / model | Context pack |
|---|---|---|---|
| Find baptism of Anna Matějková, ARON, 1801 | 2 | `researcher` / sonnet | person 231, parish books, rule `matriky#kurrent` |
| Read a faded kurrent index 1815, Třeboň | 4 | `browser-reader` / opus, then `verifier` | crop, question, kurrent traps |
| Merge upstream 0.10.2 | 3 | `upstream-sync` / sonnet (opus on conflict) | `sync_report`, our overlap list |
| Fix wrong spacing in deník entry | 1 | scripted (`denik.py fix`) | none |
| Test fails: new page `/jmena/` not covered | 2 | `test-author` / sonnet | coverage list, test template |

## 5. Pravidla, šablony a testy pro deník, fronty a web

### 5.1 Strukturovaná data místo volného textu

Dnes je zdroj pravdy volný Markdown (`research_log.md`, `ukoly_*.md`) a web z něj text přebírá. Navrhuju obrátit směr:

- `data/denik.jsonl` (jeden záznam na řádek, jen přidávání; oprava = nový záznam s polem `opravuje`).
- `data/ukoly.jsonl` (vnitřní fronty) a **odděleně** `data/verejne_otazky.json` (co čte rodina na „Co hledáme“).
- Markdown, tabulky a stránky webu se z toho **generují**. Ruční úprava generovaného souboru je chyba.

Kdo píše: výhradně `tools/denik.py`, `tools/fronta.py` a `tools/otazky.py`, které přijmou pole, ověří je a vyrobí text
ze šablony. Agent zadává pole, ne věty.

### 5.2 Šablony (pole a vyplňování)

**Záznam deníku** (`denik.py pridej`):

```text
datum      YYYY-MM-DD
zdroj      <archive> | <book signature> | <image>           (exactly this order)
hledano    one sentence, what was searched                   (<= 160 chars, no names of agents/users/tasks)
vysledek   found | disproved | not_found | partial
nalez      one sentence, only if found/disproved             (Czech, uses D. M. RRRR dates)
osoby      list of person keys
odkaz      record key or crop file
opravuje   optional id of the entry corrected
```

Zakázané ve všech textových polích (kontroluje skript a `kontrola.py`): číslo úkolu (`U-\d+`, `N\d+[a-z]`), jména agentů
a modelů, jméno uživatele, cesty (`pracovni/`, `C:\`), „ověřeno na snímku“, „čtyři oči“, „vlna“, vyplněné věty typu
„dříve chybně“ (to je `opravuje`), mezera před dvojtečkou, přechody `->`.

**Úkol ve frontě** (`fronta.py pridej`): `id, priorita, typ, osoby, cil, zdroj_postup, stav, termin?` a pro rozhodnutí
`rozhodnuti` (kdo, kdy, co). Celý řádek je **jen vnitřní**: generátor stránky „Co hledáme“ ho nikdy nečte.

**Veřejná otázka** (`otazky.py pridej`): `rod, osoba?, otazka, proc_to_zajima, co_pomuze` (3 krátké věty česky). Žádné
signatury a postup. Vnitřní úkol se na veřejnou otázku převádí jednou větou a ručním potvrzením.

### 5.3 Jednotná prezentace webu

- **Jeden zdroj značky rodu:** komponenta `Rod` (barevný kruh + název z `lines[slug]`). **Holý název rodu v textu je
  zakázán** – generátor textů (`export_web.py`) při sestavení nahradí každý výskyt názvu rodu značkou, takže autor textu nic
  nemusí značkovat. Rozhodnutí k potvrzení: značka vždy ve tvaru *kruh + „Plíškové“*, bez slova „rod“ před názvem.
- **Barvy** jen z `lines[*].color`; žádná barva rodu mimo komponentu a statistiky.
- **Řazení:** na všech stránkách, kde se dělí podle rodu, je pořadí rodů stejné (podle čísla předka) a oddíl „bez rodu“
  je poslední.
- **Datum, jména míst a čísla domů** vždy stejným tvarem (D. M. RRRR; „čp. N“).
- **Žádný procesní text** na žádné stránce (vzor z 5.2).

### 5.4 Testy (vše spustitelné bez sítě)

| Test | Co hlídá | Poznámka |
|---|---|---|
| `tests/denik/test_schema.py` | pole, délky, zakázané vzory, pořadí zdroje | jednotkové |
| `tests/denik/test_render.py` | vykreslení do Markdownu/webu = referenční soubor | „golden file“ |
| `tests/fronta/test_schema.py` | pole úkolu, stavy, duplicity | rozšíření stávajících |
| `tests/web/test_jednotnost.py` | žádný holý název rodu, správná barva značky, stejné pořadí rodů | nad sestaveným webem |
| `tests/web/test_proces_text.py` | žádné `U-\d+`, jména agentů, cesty na žádné stránce | nad sestaveným webem |
| `tests/web/test_soukromi_e2e.py` | v omezených verzích žádný žijící bez souhlasu, žádné RČ | stávající pravidla + E2E |
| `tests/jazyk/test_jazyk.py` | metodika anglicky, web česky | kapitola 3 |
| `tests/pokryti/test_pokryti.py` | každá stránka a nástroj má test | kapitola 6 |

Test ověřím nejdřív proti dnešním datům: `hledame` a `denik` ho musí **neprojít** (jinak test nic nehlídá).

## 6. E2E při aktualizaci verze skillu v projektu

Spouští se automaticky po každé aktualizaci projektu na novou verzi (`novy_projekt.py` s novým `VERZE`), řídí ho orchestrátor.

1. `test-runner`: jednotkové testy skillu, `kontrola.py`, export, sestavení všech verzí webu (`npm run build`).
2. **Kontrola pokrytí (`tools/pokryti.py`):**
   - **Stránky:** seznam tras z `web/src/pages` a z vygenerovaných dat (osoba, místo, rod, příběh) proti registru
     `tests/e2e/stranky.json` (vzor trasy → test). Nová nebo změněná trasa bez testu = **selhání brány**.
   - **Nástroje:** každý `tools/*.py` má test (nebo záznam ve výjimkách s důvodem).
   - **Návody:** každý soubor metodiky odpovídá jazykové politice.
   - Při nepokrytí skript **sám vytvoří úkoly** do fronty „doplnit test pro `<trasa>`“ (typ `test`, priorita P2) a příkaz
     pro orchestrátora (`doplň testy`), který je přidělí `test-author`.
3. E2E v prohlížeči (Playwright, nejdřív proti dočasnému kopii webu mimo projekt kvůli zámku `dist`):
   - **Všechny verze webu** (správce, každý přístup): odkazy, styly, konzole bez chyb, žádné horizontální přetečení
     při šířkách 420 / 900 / 1400 (nástroj, který jsem dnes psal ručně).
   - **Jednotnost**: testy z 5.4 (značky rodů, procesní text, jazyk).
   - **Soukromí**: přihlášení do přístupu s omezeným právem, kontrola, že skryté osoby a doklady nejsou v DOM ani
     v obrázcích.
   - **Brána** (přihlášení, odpověď, odkaz s tokenem) a vyhledávání.
   - **Vizuální referenční snímky** klíčových stránek (úvod, rod, osoba, statistiky, hledáme, deník); odchylka nad práh =
     ke kontrole, ne automatická chyba.
4. Výsledek jako jedna zpráva: zelená / červená / **nepokryto**. Červená jde analytikovi (4.7), nepokryto autorovi testů.
   Do nasazení (testovací nebo ostrého) se nejde, dokud není zelená a nepokryto = 0.

Otevřené: (d) Playwright je v projektu přes systémový Edge (CDP), v CI Chromium; stačí jedna sada skriptů pro oba?
(e) Vizuální snímky mají vlastní údržbu (aktualizace při záměrné změně): chceme to, nebo jen strukturní kontroly?

## 7. Plán implementace (po schválení)

1. **Fáze A – pravidla a skripty** (bez agentů): `denik.py`, `otazky.py`, rozšíření `fronta.py`, `kontext.py`, `jazyk.py`,
   `pokryti.py`, generování `Co hledáme` a Deníku, testy z 5.4. Migrace stávajícího deníku na `denik.jsonl`.
2. **Fáze B – web:** komponenta `Rod`, automatické značkování, kontrola jednotnosti. Oprava `hledame` a `denik`.
3. **Fáze C – agenti:** definice v `.claude/agents/` (anglicky), `orchestrator` jako hlavní vlákno, pravidlo jazyka v `CLAUDE.md`.
4. **Fáze D – E2E brána** po aktualizaci verze a její zapojení do `novy_projekt.py` (výstup „spusť E2E“).
5. Průběžně: převod návodů do EN při každé úpravě; `upstream-sync` začne dělat zprávy hned (nízké riziko).

Pořadí podle užitku: A a B řeší dnešní bolest (deník, Co hledáme, rody), C a D přinášejí řízení a bezpečnost.

## 8. Rozhodnutí, která potřebuju od vás

1. **Orchestrátor jako hlavní vlákno** (kvůli omezení platformy), s úzkou výjimkou pro `fronta.py`/`kontext.py` v Bashi? Nebo
   zcela bez Bashe a zápisy do front přes malého agenta `clerk`?
2. **Obrácení datového toku deníku** (JSONL jako zdroj, Markdown a web generované) – souhlasíte s migrací stávajícího
   `research_log.md`?
3. Značka rodu: *kruh + „Plíškové“* (bez slova „rod“) na všech stránkách?
4. Převod stávajících českých návodů do EN: postupně při úpravě (doporučuju), nebo jednorázově?
5. Oprava selhání: stačí třídění **mechanické / S / M / L** z 4.7, nebo chcete u L vždy schválení vy?
6. E2E: povinné vizuální snímky, nebo jen strukturní kontroly?
7. Veřejné otázky na „Co hledáme“: potvrzujete, že vnitřní fronta se na web nikdy nepřenáší automaticky?
