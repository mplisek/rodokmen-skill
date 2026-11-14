# Fáze D: kontrola pokrytí a brána po aktualizaci verze

Stav: **implementováno** (Q-D1 až Q-D5 potvrzeny: ano). Odchylky: záznamy tras mají navíc pole `kryje` (co test opravdu hlídá; většinu stránek kryje jen obecný test_jednotnost_web); `pokryti.py` hledá testy i v kořenovém `tests/` originálu. Vychází z `analyza/navrh-agentu.md`
(kapitola 6, 4.7, Q7, otevřené body (c) a (d)). Větev `faze-d-brana` stojí na Fázi C.

## 1. Rozsah

| Část | Obsah |
|---|---|
| D1 | `scripts/pokryti.py`: nástroje, stránky, jazyk a pravidla proti testům; report a návratový kód |
| D2 | `skills/rodokmen/tests/e2e/stranky.json`: registr tras webu → test, který je hlídá |
| D3 | `tools/brana.py` v projektu: strukturní brána po aktualizaci verze, výsledek zelená / červená / nepokryto |
| D4 | zapojení: `novy_projekt.py` po změně `VERZE` poznačí, že brána čeká; `hlidac_site.py` nepustí nasazení, dokud není zelená |
| D5 | testy všeho výše, dokumentace, CHANGELOG, aktualizace agentů (`test-runner`, `test-author`, `orchestrator`) |

Mimo Fázi D: E2E v prohlížeči (Playwright) a referenční snímky (viz Q-D1).

## 2. Návrh rozhraní (ke schválení)

### 2.1 `scripts/pokryti.py` (repozitář skillu, ne projekt)

```text
pokryti.py [--repo SLOŽKA] [--json]
```

Čtyři kontroly, každá vrací seznam „nepokryto“ s důvodem:

- **Nástroje:** každý `skills/rodokmen/tools/*.py` je zmíněn v nějakém `tests/test_*.py` (název souboru bez `.py`) nebo je v registru
  výjimek `tests/e2e/vyjimky.json` s důvodem (smoke-test, ruční nástroje portálů).
- **Stránky:** trasy z `template/web/src/pages` (soubor `.astro` → vzor trasy, `[x]` → `*`) proti `tests/e2e/stranky.json`
  (`{"vzor": "/osoba/*", "test": "test_znackuj_rody"}`); trasa bez záznamu, nebo záznam s neexistujícím testem = nepokryto.
- **Jazyk:** volá `jazyk.py` (anglická vrstva včetně `agents/`).
- **Pravidla:** volá `pravidla.py overit`.
- Výstup: text nebo JSON `{nastroje, stranky, jazyk, pravidla, nepokryto: [...]}`; kód 0 = vše pokryto, 1 = nepokryto.
  Nezakládá úkoly (projekt ve skill repozitáři nemá frontu); úkoly „doplnit test pro `<trasa>`“ zakládá orchestrátor z JSONu přes `fronta.py`.

### 2.2 `tools/brana.py` (projekt)

```text
brana.py [--web SLOŽKA se sestavenými stránkami] [--json]
```

Spouští po sobě bez sítě: `kontrola.py`, `fronta.py kontrola`, `denik.py over`, `otazky.py` kontrolu a `kontrola_webu.py` nad
sestavenými stránkami (každý přístup zvlášť, pokud `web/dist*` jich je víc). Výsledek:

- **zelená:** vše prošlo; zapíše `pracovni/brana.json` `{verze, otisk_dat, cas, vysledek: "zelena"}`;
- **červená:** seznam selhání se zdrojem (kontrola, soubor, zpráva);
- **nepokryto:** brána nemá co kontrolovat (chybí sestavený web) – ne zelená.

Sestavení webu neprovádí (`npm run build` je pomalý a patří uživateli nebo agentovi); brána jen ověří, že sestavení existuje a je čerstvé.

### 2.3 Zapojení

- `novy_projekt.py`: při změně `VERZE` v projektu vypíše „spusť bránu“ a smaže `pracovni/brana.json` (starý zelený výsledek neplatí).
- `hlidac_site.py`: příkaz pro nasazení (`netlify deploy`, `wrangler … deploy`) odmítne, když `pracovni/brana.json` chybí, není zelená
  nebo má jinou `verzi` než `VERZE` projektu. Hláška řekne, jak bránu spustit. Testovací nasazení (bez `--prod`) stejně.
- `orchestrator`: po aktualizaci verze spustí `test-runner` s bránou; červená jde `failure-analyst`, nepokryto `test-author`.

## 3. Švy a testy (nejdřív červené)

| Šev | Test |
|---|---|
| `pokryti.py` | dočasný repozitář: nástroj bez testu, trasa bez záznamu, záznam s neexistujícím testem, výjimka s důvodem; vše pokryto = kód 0 |
| registr tras | skutečný repozitář: každá trasa z `template/web/src/pages` je v `stranky.json`, každý odkazovaný test existuje |
| `brana.py` | dočasný projekt: zelená zapíše `brana.json`; červená u procesního textu; nepokryto bez sestavení; `--json` |
| zapojení | změna `VERZE` smaže `brana.json`; hlídač nepustí nasazení bez zelené, pustí s platnou, nepustí se starou verzí; ostatní příkazy nevadí |

## 4. Otázky k potvrzení

- **Q-D1:** Prohlížečové E2E (Playwright, 3 šířky, konzole, odkazy) a referenční snímky **v této fázi nedělám**: potřebují prohlížeč
  a v CI jiný než v projektu (otevřené body (c), (d)). Fáze D dodá strukturní bránu; Playwright zůstane samostatnou případnou Fází D2
  po tvém rozhodnutí. Ano?
- **Q-D2:** `pokryti.py` ve `scripts/` (údržba repozitáře), `brana.py` v `tools/` (běží v projektu). Ano?
- **Q-D3:** `pokryti.py` jen hlásí; úkoly do fronty zakládá orchestrátor z JSONu. Ano?
- **Q-D4:** Hlídač nasazení blokuje i testovací nasazení bez zelené brány (zelená je levná a nic nestojí). Ano?
- **Q-D5:** Skutečný stav: pokrytí tras a nástrojů dnes pravděpodobně neprojde (nástroje portálů bez testů); počáteční výjimky
  zapíšu do `vyjimky.json` s důvodem a ukážu ti je ke schválení, nic nedoplňuju hromadně. Ano?
