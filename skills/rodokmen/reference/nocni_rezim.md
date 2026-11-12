# Noční a víkendový režim – fronty úkolů

Platí pro práci bez člověka: úkoly, které jde dělat automaticky, běží mimo pracovní dobu a výsledky se zapisují do front.
Nástroj: `python3 -I tools/fronta.py --help`. Konfigurace: `data/rezim.json`.

## Pět front (soubory v `data/`)

| Soubor | Co v něm je | Kdo ho řeší |
| --- | --- | --- |
| `ukoly_na_noc.md` | úkol, který jde udělat automaticky, bez člověka | hlavní agent + pomocníci |
| `ukoly_k_rozhodnuti.md` | věc, kde musí rozhodnout člověk | člověk |
| `ukoly_k_badani.md` | jen online v prohlížeči, kam skript nesmí (eBadatelna, MZA, Třeboň) | člověk s asistentem |
| `archivni_dotazy.md` | co online není | žádost archivu |
| `otazky_pro_rodinu.md` | nápad na otázku pro rodinu | rodina |

**Směrování nálezu** (kam co zapsat, když při práci narazíš na něco nového):

1. Jde to skriptem z ARONu bez úsudku → **na noc**.
2. Je třeba rozhodnout (spor zdrojů, dva kandidáti, změna jména v datech, soukromí, cokoli odesílaného ven) → **k rozhodnutí**;
   původní úkol se odloží (`stav:odloženo`) a odkazuje na rozhodnutí.
3. Online jen v prohlížeči → **k bádání**.
4. Online není → **archivní dotaz**.
5. Může to vědět rodina → **otázka pro rodinu**.

**Invariant:** úkol nikdy nezmizí bez stopy. Končí tím, že je celý zapsán do dat, nebo se jeho zbytek zapsal do jiných úkolů.
Upřesnění = nový úkol, rozdělení = víc úkolů, přeřazení = `fronta.py presun`. Hotový úkol se maže (`fronta.py hotovo`).

## Formát úkolu a pravidla zápisu

```text
## U-0412 | P1 | os:57,114 | typ:křest | cíl:krest:115 | rodič:U-0398 | stav:otevřeno
Text úkolu: co hledat, kde, co už je prohlédnuto.
```

- **Priorita:** P1 odemyká chybějícího předka, P2 mění „prob“ na „doc“, P3 ověřuje rodinný údaj. Fronty se při každém zápisu třídí
  (priorita, id).
- **Duplicity:** `fronta.py pridej` porovná typ, osoby a cíl ve všech frontách; podobný úkol se nezaloží, ale **doplní**
  (osoby, text, vyšší priorita). Částečný překryv: doplň jeden z úkolů a druhý zúž (`uprav`).
- **Cíl (`cíl:krest:115`, `umrti:`, `snatek:`)** umí `fronta.py kontrola` ověřit v datech; splněný úkol ohlásí ke smazání.
- **Typ:** otevřená množina – `bádání`, `skill` (úprava skillu), `test`, `údržba`.
- Úkoly mohou vznikat z jiných úkolů (`rodič:`).

## Režimy podle času

`data/rezim.json`: `pracovni_dny`, `pracovni_od` / `pracovni_do` (výchozí všední dny 6:00–22:00), `svatky` (berou se jako víkend),
`pomocniku` (max. souběžných pomocníků), `dod` (volitelná omezení běhu; výchozím ukončením je čas). `fronta.py rezim` řekne režim
a konec okna.

- **Mimo pracovní dobu (noc, víkend, svátek)** běh spouští uživatel. Jede se do konce úkolů, **konce okna**, nebo do DOD.
  Doběhne-li úkol po začátku pracovní doby, **další se nepouští**; končí-li okno dříve, hlavní agent pouští další úkol.
  Nikdy se neptá: rozhodnutí → `ukoly_k_rozhodnuti.md`, úkol se odloží; nelze-li online → `ukoly_k_badani.md`;
  není online → `archivni_dotazy.md`; nápad pro rodinu → `otazky_pro_rodinu.md`.
- **V pracovní době** po doběhu vyhodnoť výsledky, ulož, vypiš dotazy (rozhodnutí, nové úkoly k bádání) a čekej na instrukci.
- **Po každém doběhu úkolu hlavní agent vždy zkontroluje výstupy a zápis** a výsledek zapíše tam, kam patří (data, fronty).
- Chyba portálu (brzda „zastavený“): úkol zůstane `otevřeno`, zapíše se do deníku a běh končí.

## Brzda: bádání × úprava skillu

V jednom běhu jede **buď bádání, nebo úprava skillu**, nikdy obojí. Zámek: `fronta.py zamek start badani|skill`, `stop`, `stav`
(`data/.beh.json`, vyprší s koncem okna); `fronta.py dalsi` nepustí úkol jiného druhu. Úprava skillu běží **ve feature větvi**
(`skill/<téma>`, bez push, vydání a nasazení); ráno se rozhodne, co s větví. Změna pravidel bádání (metodiky) až po rozhodnutí.

## Kdo úkol dělá

| Činnost | Kdo |
| --- | --- |
| směrování, priorita, slučování a dělení úkolů, ověření čtení, ztotožnění, spory zdrojů, zápis do dat, úpravy skillu | hlavní agent s plným kontextem |
| rutinní čtení snímků a rejstříků, hledání knih v ARONu | podagent na středním modelu (`sonnet`) |
| mechanické práce (stahování, hromadné přejmenování, oprava lintu, migrace podle šablony) | podagent na nižším modelu |
| složité čtení (kurent, špatné snímky), nejasné ztotožnění | hlavní agent, případně podagent na vyšším modelu s přesným zadáním |

Model odpovídá složitosti úkolu. Podagent **nikdy nezapisuje do `data/` ani do skillu**, píše jen do `pracovni/pom_<téma>/`.
Brzda `slusne.py` a limit souběžných pomocníků (`rezim.json`) platí dál. Jen ARON, nic se neodesílá ven.

## Nejisté čtení v noci

Do dat jdou jen **jisté** údaje (shoduje se jméno, rodiče, místo a datum). Nejisté se zapíše jako **kandidát v poznámce** osoby
(stav zůstane `prob`) a do `ukoly_k_rozhodnuti.md` přibude otázka: potvrdit, zamítnout, nebo přečíst znovu v plném rozlišení.

Šablony a zakázané údaje o procesu: `zapisy.md`.
