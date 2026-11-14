# Ověření platformy Claude Code pro návrh agentů

Stav k 14. 11. 2026. Zdroje jsou výhradně oficiální dokumentace `code.claude.com/docs/en/...` načtená přes WebFetch.
Citace jsou krátké, v původní angličtině. Pokud stránka při načtení skončila useknutá, je to uvedeno u příslušné otázky.

Použité stránky: `sub-agents`, `hooks`, `hooks-guide`, `permissions`, `settings`, `settings-reference`, `skills`,
`cli-reference`, `plugins-reference`, `plugins/components`.

## 1. Může subagent spouštět další subagenty? Jiný způsob delegace než hlavní vlákno?

**Verdikt: VYVRÁCENO** (předpoklad, že orchestrátor musí běžet jako hlavní vlákno).

Subagent může spouštět další subagenty, pokud má mezi nástroji `Agent`. Výchozí hloubka jsou tři vrstvy pod hlavní
konverzací, nastavitelné proměnnou `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (hodnota 1 vnoření vypne). Omezení typů
přes `Agent(a, b)` v `tools` ale platí jen pro agenta běžícího jako hlavní vlákno; ve definici subagenta se seznam v
závorkách ignoruje. Vedle subagentů dokumentace zmiňuje ještě „agent teams“, background agents a cross-session
messaging jako samostatné mechanismy. Souběžně smí běžet 20 subagentů (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`).

> "By default, a subagent can spawn subagents of its own, up to three layers below the main conversation."
>
> "In a subagent definition, listing `Agent` in `tools` lets that subagent spawn subagents of its own while the depth limit allows it, but any type list inside the parentheses is ignored."

Zdroj: <https://code.claude.com/docs/en/sub-agents> (části o vnořených subagentech a „Restrict which subagents can be spawned“).

## 2. Může agent běžet jako hlavní vlákno relace?

**Verdikt: POTVRZENO**

Přepínač CLI `--agent <název>` nebo klíč `agent` v `settings.json`. Přepínač má přednost před nastavením. Agent
běžící takto smí spouštět subagenty nástrojem `Agent` a typy lze omezit zápisem `Agent(typ1, typ2)` v `tools`
(allowlist). Vynechání `Agent` v `tools` spouštění zakáže. Pole `autoCompactWindow` se v takovém režimu neuplatní.

> "CLI flag: `claude --agent code-reviewer`" a "Setting: `"agent": "code-reviewer"` in `.claude/settings.json`. The CLI flag overrides the setting if both are present."
>
> `--agent`: "Specify an agent for the current session (overrides the `agent` setting)"
>
> `agent` (settings index): "Start every session as a named subagent with its prompt, tools, and model"

Zdroje: <https://code.claude.com/docs/en/sub-agents>, <https://code.claude.com/docs/en/cli-reference>,
<https://code.claude.com/docs/en/settings-reference>.
Poznámka: úplný oddíl o klíči `agent` v `settings-reference` jsem nečetl (stránka je dlouhá, četl jsem jen index);
název klíče a jeho účel jsou ale potvrzené dvěma stránkami.

## 3. Pole frontmatteru subagenta; `skills:`; `model:`

**Verdikt: POTVRZENO** (s výhradou pro agenty dodávané v pluginu, viz otázka 9).

Povinné jsou jen `name` a `description`. Názvy polí jsou camelCase a rozlišují velikost písmen; neznámá pole se
tiše ignorují. Podporovaná pole: `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`,
`maxTurns`, `skills`, `hooks`, `memory`, `mcpServers`, `background`, `omitClaudeMd`, `effort`, `isolation`,
`autoCompactWindow`, `initialPrompt`, `color`, `experimental`.

- `skills:` předává do subagenta celý obsah skillu při startu (max. prvních 32 jmen). Pole řídí, co se přednačte,
  ne k čemu má subagent přístup. Skill s `disable-model-invocation: true` se do subagenta přednačíst nedá.
- `model:` přijímá aliasy `sonnet`, `opus`, `haiku`, `fable`, plné ID modelu nebo `inherit`.
- `memory:` má hodnoty `user`, `project`, `local`. `permissionMode:` má hodnoty `default`, `acceptEdits`, `auto`,
  `dontAsk`, `bypassPermissions`, `plan`, `manual`.

> "The full content of each listed skill is injected into the subagent's context at startup, up to the first 32 distinct names in the list."
>
> `model`: "`sonnet`, `opus`, `haiku`, `fable`, a full model ID such as `claude-opus-5-5`, or `inherit`."

Zdroje: <https://code.claude.com/docs/en/sub-agents> (Supported frontmatter fields),
<https://code.claude.com/docs/en/skills> (`disable-model-invocation` blokuje přednačtení).

## 4. Omezení Bash na vzory příkazů v `tools:` nebo v pravidlech oprávnění

**Verdikt: ČÁSTEČNĚ**

- Pole `tools:` subagenta je seznam názvů nástrojů. Jediný dokumentovaný specifikátor je `Agent(...)`.
  Zápis typu `tools: Bash(python3 -I tools/fronta.py list:*)` dokumentace neuvádí, takže pro `tools:` je to
  NELZE OVĚŘIT (a podle textu o `disallowedTools` je pravděpodobné, že se specifikátor nepoužije).
- Pravidla oprávnění `Bash(...)` fungují v `permissions.allow` / `ask` / `deny` v nastavení. Syntaxe: `Bash(ls *)`
  (mezera před koncovou `*` je součástí pravidla, `ls *` nepokryje `lsof`), `*` může stát kdekoli; ekvivalentní
  zápis `Bash(ls:*)` se uznává jen na konci vzoru. Pravidlo bez `*` odpovídá přesně jednomu příkazu. Takže
  `Bash(python3 -I tools/fronta.py list:*)` je platný zápis a znamená totéž co `Bash(python3 -I tools/fronta.py list *)`.
- Na subagenty se pravidla vztahují, ale ne per-agent: deny pravidlo Bash platí pro hlavní konverzaci i subagenty a
  allow pravidla platí pro celou relaci. Dokumentace per-agent allowlist příkazů nezná. `disallowedTools` se
  specifikátorem odebere celý nástroj, ne jen odpovídající příkazy.
- Dokumentace výslovně varuje, že vzory omezující argumenty jsou křehké a pravidlo není bezpečnostní hranice.
  Složené příkazy (`&&`, `||`, `;`, `|`, `&`, nový řádek) se rozdělují a každá část musí být povolená.
- Per-agent kontrola příkazů se v dokumentaci dělá `PreToolUse` hookem v frontmatteru agenta (příklad `db-reader`).

> "A `disallowedTools` entry with a specifier, such as `Bash(git push *)`, still removes the whole tool from the subagent, not only the matching commands."
>
> "`Bash(ls *)` requires a space after `ls`, so `lsof` doesn't match. `Bash(ls*)` has no space, so it matches `lsof` too."
>
> "The `:*` suffix is an equivalent way to write a trailing wildcard, so `Bash(ls:*)` matches the same commands as `Bash(ls *)`."
>
> "Bash permission patterns that try to constrain command arguments are fragile."

Zdroje: <https://code.claude.com/docs/en/permissions> (Wildcard patterns, Bash, Compound commands),
<https://code.claude.com/docs/en/sub-agents> (`tools`, `disallowedTools`, hooks ve frontmatteru).

## 5. Priorita pravidel: přebíjí deny vždy allow? Lze deny zúžit allow výjimkou?

**Verdikt: POTVRZENO** (deny vždy vyhrává; výjimka allow nefunguje).

Pořadí vyhodnocení je deny, pak ask, pak allow; rozhoduje první shoda a specifičnost pravidla pořadí nemění. Deny
`Bash(curl:*)` tedy nelze zúžit allow `Bash(curl http://localhost:*)`.

> "Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order."
>
> "An allow rule can't carve an exception out of a deny rule."

Zdroj: <https://code.claude.com/docs/en/permissions> (Permission system). Obrácený postup (úzký allow bez širokého
deny) je možný, jen se pak nic jiného automaticky nezakáže; širší zákaz musí řešit hook nebo režim `dontAsk`.

## 6. Hooky `PreToolUse`: matcher, vstup, blokování, subagenti

**Verdikt: POTVRZENO**

- Matcher: `"*"`, prázdný nebo vynechaný = vše; jen písmena, číslice, `_`, `-`, mezery, `,`, `|` = přesný název
  nebo seznam (`Edit|Write`, `Edit, Write`); cokoli jiného = nezakotvený JavaScript regex. Hodnota se porovnává s
  `tool_name`, takže `Edit`, `Write` a `Bash` lze rozlišit. MCP nástroje mají tvar `mcp__<server>__<tool>`.
- Vstup na stdin je JSON se společnými poli `session_id`, `transcript_path`, `cwd`, `permission_mode`,
  `hook_event_name` a dále `tool_name`, `tool_input`, `tool_use_id`. Pro Bash je příkaz v `tool_input.command`,
  pro Edit/Write je cesta v `tool_input.file_path` (příklad v hooks-guide čte `.tool_input.file_path`).
- Blokování: exit kód 2 (stderr jde Claudovi jako zpětná vazba) nebo exit 0 s JSON
  `hookSpecificOutput.permissionDecision` = `allow` / `deny` / `ask` / `defer` a `permissionDecisionReason`.
  Exit 2 blokuje i při vypsaném JSON. Exit 0 bez výstupu = žádné rozhodnutí.
- Subagenti: hooky z nastavení, managed nastavení a pluginů běží i při voláních nástrojů v subagentech a vstup
  obsahuje `agent_id` a `agent_type`, takže hook může rozlišit, který agent volá.

> "Exit with code 2 to block the action." / "The message that comes with the block is your hook's stderr."
>
> "Hooks from settings files, managed policy settings, and plugins also run inside subagents."
>
> `agent_type`: "Agent name (for example, `"Explore"` or `"security-reviewer"`)."

Zdroje: <https://code.claude.com/docs/en/hooks>, <https://code.claude.com/docs/en/hooks-guide> (Block edits to protected files).
Poznámka: stránka `hooks` byla při načtení useknutá po 100 000 znacích z asi 294 000; vše uvedené výše je z přečtené
části a potvrzuje ho `hooks-guide`. Přesný tvar `tool_input` u Edit/Write jsem odvodil z příkladu v hooks-guide.

## 7. Hooky na hranici pushe; git `pre-push` / `core.hooksPath`

**Verdikt: ČÁSTEČNĚ** (část o Claude Code POTVRZENA; část o git hooku NELZE OVĚŘIT).

Přímo pro `git push` žádná událost neexistuje, ale `PreToolUse` s matcherem `Bash` a polem `if` v permission-rule
syntaxi (`"if": "Bash(git push *)"`) hook spustí jen pro push; složené příkazy se rozdělí a každá část se testuje.
Pole `if` je best-effort a dokumentace pro tvrdé povolení/zakázání doporučuje spíše systém oprávnění. Obecně platí,
že pravidlo nepokryje jinou formu téhož příkazu (např. `git -C . push`). Zvlášť si hlídejte, že shell příkazy
mohou obejít i hooky na Edit/Write ("Claude can still change the protected files with shell commands").
Související události: `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `TaskCompleted`, `SessionEnd`.
Doporučení `core.hooksPath` nebo git `pre-push` pro vynucení mimo Claude Code dokumentace Claude Code nezmiňuje;
je to tedy NELZE OVĚŘIT z těchto zdrojů (a neplatí pro push provedený mimo Claude Code).

> "`if` uses permission rule syntax to match against the tool name and arguments together, so `"Bash(git *)"` runs when any subcommand of the Bash input matches `git *`."
>
> "A push written another way, such as `git -C . push`, isn't matched"

Zdroje: <https://code.claude.com/docs/en/hooks>, <https://code.claude.com/docs/en/hooks-guide>,
<https://code.claude.com/docs/en/permissions>.

## 8. Čerstvý kontext subagenta, návrat informací, background subagenti

**Verdikt: POTVRZENO**

Subagent (mimo fork) startuje s čerstvým, izolovaným kontextem; nevidí historii konverzace, dříve vyvolané skilly ani
soubory, které už Claude četl. Úkol dostane z delegační zprávy. Výsledek se vrací do hlavní konverzace (u forku jen
jeho finální výsledek; mezikroky zůstávají mimo). Background subagent doručí výsledek jako oznámení o dokončení v
pozdějším tahu a Claude na něj před hlášením čeká. Subagent spuštěný z hlavní konverzace běží ve výchozím nastavení
na pozadí (pokud není vypnutý fork režim). Na pozadí se každá výzva k oprávnění zobrazuje v hlavní relaci.

> "Each subagent starts with a fresh, isolated context window. It doesn't see your conversation history, the skills you've already invoked, or the files Claude has already read."
>
> "A background subagent's results reach Claude as a completion notification in a later turn."

Zdroj: <https://code.claude.com/docs/en/sub-agents> (části Run subagents in foreground or background, Fork the current conversation).
Z dokumentace nevyplývá, že se vrací výhradně poslední zpráva; formulace je „results return to your main conversation“.
Přesné omezení na „jen finální zpráva“ je proto jen ČÁSTEČNĚ potvrzené (u forku výslovně ano).

## 9. Pluginy: více skillů a agentů, hooky, rozložení adresářů

**Verdikt: POTVRZENO** (s důležitým omezením polí u pluginových agentů).

Standardní rozložení kořene pluginu:

```text
my-plugin/
├── .claude-plugin/plugin.json     (volitelný manifest; jen name je povinné)
├── skills/<název>/SKILL.md        (libovolný počet skillů)
├── agents/<název>.md              (libovolný počet agentů, podsložky se stávají součástí názvu)
├── hooks/hooks.json               (kořenový klíč "hooks", stejný tvar jako v settings.json)
├── commands/, .mcp.json, .lsp.json, bin/, ...
```

Hooky lze dodat i v klíči `hooks` manifestu; obě místa se načtou společně. Názvy komponent jsou prefixované
názvem pluginu (`/<plugin>:<skill>`, agent `<plugin>:<name>`).

Pluginový agent podporuje pole: `name`, `description`, `model`, `effort`, `maxTurns`, `autoCompactWindow`, `tools`,
`disallowedTools`, `skills`, `memory`, `background`, `omitClaudeMd`, `isolation`, `color`. **Ignoruje**
`permissionMode`, `hooks`, `mcpServers`, `initialPrompt`.

> "A plugin agent's frontmatter ... **Ignored fields**: `permissionMode`, `hooks`, `mcpServers`, and `initialPrompt`. An agent file can't add hooks or MCP servers on its own, so add those as plugin hooks and MCP servers instead"

Zdroje: <https://code.claude.com/docs/en/plugins-reference> (Standard layout),
<https://code.claude.com/docs/en/plugins/components> (Skills, Agents, Hooks). Nezkoumal jsem, jak se v pluginu
jmenuje skill uvedený v `skills:` agenta (zda s prefixem pluginu); to je NELZE OVĚŘIT z přečtených stránek.

## 10. Omezení automatického vyvolání skillu

**Verdikt: POTVRZENO**

`disable-model-invocation: true` zabrání Claudovi skill načíst sám (jde spustit jen ručně přes `/název`) a zároveň
brání přednačtení skillu do subagentů. `user-invocable: false` skill skryje z nabídky `/` a uživatel ho nespustí,
vyvolat ho může jen Claude (výchozí hodnota `true`).

| Frontmatter | Uživatel | Claude |
| :- | :- | :- |
| (výchozí) | ano | ano |
| `disable-model-invocation: true` | ano | ne sám od sebe |
| `user-invocable: false` | ne | ano |

> "Set to `true` to prevent Claude from automatically loading this skill ... Also prevents the skill from being preloaded into subagents"
>
> "Set to `false` when only Claude should invoke the skill"

Zdroj: <https://code.claude.com/docs/en/skills> (Control who invokes a skill).

## Dopady na návrh

- **„Orchestrátor musí běžet jako hlavní vlákno“: vyvráceno jako technické omezení.** Subagent s `Agent` v `tools`
  může delegovat (výchozí hloubka 3). Hlavní vlákno (`claude --agent` / klíč `agent`) je ale jediné místo, kde
  funguje allowlist `Agent(typ1, typ2)`; jako zásada návrhu („orchestrátor = hlavní vlákno“) to obstojí, jako
  nutnost ne.
- **„Bash agentů omezený na `fronta.py` a `kontext.py`“: per-agent v `tools:` nepodložené.** Dokumentace zná
  `Bash(...)` jen v pravidlech oprávnění, která platí pro celou relaci; deny vždy přebije allow, takže „deny curl,
  allow curl localhost“ nejde. Per-agent omezení příkazů umožňuje jen `PreToolUse` hook, a ten se musí číst ze
  skriptu, ne z frontmatteru pluginového agenta.
- **Hooky ve frontmatteru agentů jsou v pluginu ignorovány.** Máme-li agenty dodávat v pluginu (`agents/*.md`),
  hook do agenta dát nelze; musí jít do `hooks/hooks.json` pluginu a rozlišit agenta podle `agent_type` ze vstupu.
- **„Úzký PreToolUse hook pro chráněné soubory“: podloženo.** Matcher `Edit|Write`, cesta v
  `tool_input.file_path`, blokování exit kódem 2 se zprávou na stderr, hooky běží i v subagentech. Dokumentace
  sama upozorňuje, že přes Bash lze soubory měnit jinak, takže stejný hook potřebuje i větev pro `Bash`.
- **„Tenký anglický skill přednačtený do agentů přes `skills:`“: podloženo.** `skills:` vloží celý obsah skillu do
  subagenta při startu (max. 32 jmen) a pluginový agent toto pole podporuje. Skill ale nesmí mít
  `disable-model-invocation: true`, jinak se nepřednačte. Zbývá ověřit, jak se v pluginu zapisuje název skillu.
- **Kontrola anonymity před pushem: hook jen nepřímo.** Hook `PreToolUse` s `if: "Bash(git push *)"` je
  best-effort (např. `git -C . push` ho obejde) a nepokrývá push mimo Claude Code. `core.hooksPath` / `pre-push`
  dokumentace Claude Code nezmiňuje, takže ten argument se musí opřít o dokumentaci gitu, ne o tuto ověřovací zprávu.
- **Model v agentech: aliasy `sonnet`, `opus`, `haiku`, `fable`, `inherit` jsou podporované;** pole `maxTurns`,
  `memory` i `effort` jsou k dispozici i pro pluginové agenty.
- **Návrat informací:** subagent má čerstvý kontext a vrací se jeho výsledek (u forku výslovně jen finální výsledek);
  vše potřebné musí orchestrátor předat v delegační zprávě, protože nevidí historii ani dříve načtené skilly.

## Doplnění: název skillu v `skills:` u pluginového agenta

Verdikt: NELZE OVĚŘIT. Oficiální dokumentace neříká, zda stačí holý název skillu, nebo je u skillu ze stejného pluginu (či u projektového agenta s pluginovým skillem) nutný tvar `plugin:skill`. Nehádáme.

Co dokumentace říká: pole `skills` je u pluginových agentů podporované („Supported fields: ... `skills` ...“, ignorují se jen `permissionMode`, `hooks`, `mcpServers`, `initialPrompt`). Jediný příklad používá holé názvy (`skills: [api-conventions, error-handling-patterns]`). Chybějící skill se přeskočí: „If a listed skill is missing or disabled ... Claude Code skips it and logs a warning to the debug log.“ Tvar `plugin:název` je v dokumentaci uveden jen pro agenty (`my-plugin:security-reviewer`) a pro příkazy skillů (`/my-plugin:review`), ne pro pole `skills:`.

Důsledek: při použití holého názvu u pluginového agenta je třeba ověřit prakticky (debug log), jinak se skill může tiše nenačíst.

URL: https://code.claude.com/docs/en/sub-agents (sekce Preload skills into subagents), https://code.claude.com/docs/en/plugins/components.md (sekce Agents, Frontmatter fields in plugin agents)
