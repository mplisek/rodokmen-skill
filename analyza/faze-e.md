# Fáze E: vrstva pravidel pro agenty, tenký skill, kontrola jazyka a anonymity

Stav: **plán fáze ke schválení rozhraní.** Nic z toho zatím není implementováno. Vychází z `analyza/navrh-agentu.md`
(kapitola 3, oddíly 3.5 a 3.6, 5.5, 9.1; rozhodnutí Q9, Q10, Q16, Q19) a z ADR 0005. Větev `faze-e-pravidla` stojí na Fázi B.

## 1. Rozsah

| Část | Obsah |
|---|---|
| E1 | `skills/rodokmen-agents/rules/*.md`: anglická pravidla pro agenty, počáteční sada osmi témat (3.6) |
| E2 | `skills/rodokmen-agents/rules/zdroje.json` a `tools/pravidla.py` (`overit`, `potvrdit`, `pokryti`): otisk zdrojového oddílu u každého pravidla |
| E3 | tenký anglický skill `skills/rodokmen-agents/SKILL.md` (nejvýš zhruba 120 řádků, jen ukazatele na pravidla) |
| E4 | `tools/jazyk.py`: anglická vrstva je anglicky (pravidla, tenký skill) |
| E5 | `scripts/anonymita.py`, `.githooks/pre-push`, `.anonymita-seznam.priklad`: kontrola anonymity před pushem (5.5) |
| E6 | testy všeho výše |

Mimo Fázi E: agenti a `kontext.py` (Fáze C), `pokryti.py` a E2E brána (Fáze D), `sync_report.py` (Fáze C, nástroj agenta `upstream-sync`).

## 2. Návrh

### 2.1 Pravidla a jejich zdroj

Každé pravidlo je odstavec v `rules/<téma>.md` s pevnými poli (ukázka s vymyšleným obsahem):

```text
## R-ID-001
when:   two people of the same name appear in one parish
do:     merge them only on two independent signs (house number, both parents, spouse, sponsors, exact birth date)
why:    two men of the same name were merged into one and "his" children were born ten months apart
source: reference/metodika.md#Ztotožnění – kdy je to tatáž osoba
```

`rules/zdroje.json` vede pro každé pravidlo `{ "source": "<soubor>#<nadpis>" nebo "fork", "checked": "<otisk>" }`.

- Zdroj v Markdownu: otisk textu oddílu pod nadpisem (po další nadpis stejné nebo vyšší úrovně), s normalizovanými mezerami a bez
  rozdílu konců řádků. Zdroj, který není Markdown (např. `tools/slusne.py`): otisk celého souboru. Pravidlo vlastní: `fork`, bez otisku.
- `pravidla.py overit`: každé pravidlo má všechna pole a existující zdroj; otisk se shoduje, jinak je pravidlo **zastaralé** a skript
  skončí chybou. Zmizelý oddíl je také chyba.
- `pravidla.py potvrdit <id>`: po revizi uloží nový otisk (uživatel nebo agent po schválení).
- `pravidla.py pokryti`: vypíše oddíly zrcadla, ke kterým není žádné pravidlo (informativně).
- Po slučování z originálu (Fáze C) se spustí `overit`; pro každé zastaralé pravidlo vznikne úkol k přezkoumání.

### 2.2 Tenký skill `rodokmen-agents`

Anglický, nejvýš zhruba 120 řádků, `user-invocable: false` (ne `disable-model-invocation`, jinak by se nepřednačetl agentům).
Obsahuje seznam rolí, formy souborů s výsledky, jazykovou politiku a **ukazatele** na pravidla podle `id`; pravidla v něm
neopakuje. Testy hlídají velikost, existenci odkazovaných souborů a pravidel a že se text nekryje s `SKILL.md`.

### 2.3 Jazyk

`jazyk.py` posoudí podíl českých znaků s diakritikou v textu souboru (bez bloků kódu a bez uvozených českých výrazů). Anglická vrstva
(`skills/rodokmen-agents/**`) nesmí překročit práh. Zrcadlo (`SKILL.md`, `reference/*.md`) se nekontroluje. Kontrola, že data a web jsou
česky, se zatím neprovádí.

### 2.4 Kontrola anonymity před pushem

Podle 5.5 a Q9, Q10: `scripts/anonymita.py` čte lokální `.anonymita-seznam` (v `.gitignore`), projde **přidané řádky a zprávy všech
commitů určených k pushi** (`origin/main..HEAD`) a při shodě skončí chybou s maskovaným nálezem. Nikdy nemění historii ani pracovní
strom. `nainstaluj` nastaví `core.hooksPath` na `.githooks/` (hook `pre-push` je v gitu); instalaci spouští **uživatel**, skript
ji neprovede sám. Bez seznamu jen varuje. `navrhni-z-projektu <cesta>` vytvoří kandidáty na seznam z dat projektu.

## 3. Rozhraní, na kterých se testuje (ke schválení)

Bez mockování vlastních modulů; dočasné složky, dočasné git repozitáře, vymyšlená data.

| # | Rozhraní | Co se ověřuje |
|---|---|---|
| 1 | příkazy `pravidla.py` nad dočasným zrcadlem a pravidly | úplnost polí, existence zdroje, shoda otisku, zastaralé pravidlo po změně oddílu, zmizelý oddíl, `potvrdit`, `pokryti`, normalizace mezer a konců řádků |
| 2 | skutečná `rules/` a `SKILL.md` tenkého skillu v repozitáři | všechna pravidla platná, otisky sedí se současným zrcadlem, velikost skillu, odkazy, frontmatter, žádné kopie textu `SKILL.md` |
| 3 | příkaz `jazyk.py` nad vzorovými soubory | anglický text projde, český neprojde, výjimka v uvozovkách a v kódu |
| 4 | příkazy `anonymita.py` v dočasném git repozitáři | shoda v koncovém stavu, shoda jen v prostředním commitu (musí selhat), shoda ve zprávě commitu, vyjmutá cesta, skloňování kmene, chybějící seznam jen varuje, historie ani strom se nezmění |

Každý test je nejdřív červený. Test 2 běží nad skutečnými daty repozitáře, takže po úpravě `matriky.md` v originále neprojde, dokud se
pravidla nepřezkoumají: to je žádoucí.

## 4. Co potřebuju potvrdit

Otázky v odpovědi uživateli: umístění pravidel a uložení otisků (2.1), rozsah oddílu pro otisk (2.1), kontrola jazyka (2.3),
kontrola anonymity (2.4) a rozhraní (3).
