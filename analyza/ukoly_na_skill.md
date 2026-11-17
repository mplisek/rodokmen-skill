# Úkoly na skill (metodika)

Postup, jak pokračovat v úpravě metodiky. Cíl a zdůvodnění: `analyza/navrh-optimalizace.md` (pět příčin P1–P5, etapy E0–E7),
výchozí měření: `analyza/baseline-2026-11-15.md`. Hotový úkol se odsud maže, výsledek je v CHANGELOG.

## Dělba: metodik a badatel

- **Metodik** = sezení nad tímto repozitářem. Mění pravidla, kontrakty, nástroje, definice agentů a testy. Nebádá, nevybírá ani
  nepotvrzuje badatelské případy, neopravuje deník a nerozhoduje, co je správné čtení.
- **Badatel** = sezení nad projektem. O pořadí jeho práce rozhoduje fronta úkolů. Pravidla a nástroje nemění.
- **Od badatele k metodikovi:** technický podnět bez rodinných údajů do `data/poznamky_pro_skill.md` projektu. Metodik ho převezme sem
  (nebo rovnou vyřeší) a v projektu smaže.
- **Od metodika k badateli:** co metodika od bádání potřebuje, je úkol ve frontě projektu (`fronta.py pridej`, bez rodinných údajů)
  a řádek v CHANGELOG. `data/STAV.md` je od E7 jen předání mezi bádacími sessions a zapisuje ho `tools/stav.py`. Nové nástroje jdou do projektu jako kopie až po zelených testech; rozpracovaný úkol dojede podle verze, se kterou začal.
- Metodika **nečeká** na bádání. Jediná vazba: měřicí běh `mereni-v0` má proběhnout dřív, než se do projektu zkopírují nástroje E1.
  Do té doby zůstávají E1 a další ve větvi skillu.

## Jeden krok metodiky

Každá etapa i každý jednotlivý úkol jde stejně:

1. Větev z poslední hotové (`e0-zmirneni` → `e1-kontrakt` → …). Nic se nepushuje, neslučuje do `main` ani nevydává bez pokynu uživatele.
2. Zadání podle šablony v návrhu (oddíl 10.2): co, proč, dopad na K1–K8 a na cenu, hotovo když.
3. Test napřed. Musí chybu skutečně vyvolat (selže před změnou), ne jen hledat slovo v dokumentaci.
4. Změna. Pravidlo má jedno místo: badatelská pravidla `rules/*.md`, tvary dat `schemata/`, směrování `reference/nocni_rezim.md`;
   definice rolí na ně odkazují, neopisují je.
5. Ověření: úplná sada (`python -X utf8 -m unittest discover -s skills/rodokmen/tests`), `scripts/pokryti.py`, markdownlint,
   `scripts/anonymita.py pred-pushem` pro nový commit.
6. CHANGELOG (Nepublikováno), commit, tento soubor aktualizovat.
7. Po etapě stop: uživatel rozhodne o kopii do projektu a o další etapě. Mění-li etapa kontrakt nebo roli, do `STAV.md` projektu
   přibude věta, co se pro bádání mění.

## Stav etap (16. 11. 2026)

Hotové a commitnuté ve větvích `e0-zmirneni` → `e1-kontrakt` → `e2-zapis` → `e3-pokracovani` → `e4-ucastnici` → `e5-web-brana` →
`e6-badatel-metodik` (každá navazuje na předchozí, nic není pushnuto ani sloučeno do `main`): E0 zmírnění, E1 kontrakt čtení, E2 zápis
bez pomocných agentů, E3 pokračování a výřezy, E4 účastníci zápisu a tvrzení, E5 kontrola webu z obou stran a brána, E6 badatel a metodik.
Popis je v CHANGELOG (Nepublikováno) a v `reference/nocni_rezim.md`.

Do projektu se z toho zatím zkopírovalo jen E0 a `spotreba.py`. Zkušební měřicí běh `mereni-v0` proběhl 16. 11. 2026
(`analyza/mereni-v0-2026-11-16.md`: 7 837 tis. ekv, stav 9 z 11 případů podle očekávání; přesnost čeká na hodnocení bádáním).
Nástroje E1–E6 uživatel schválil a 16. 11. 2026 jsou zkopírované do projektu; brána zelená, kontrola webu ověřila přes tisíc vztahů
z obou stran. Další měření `mereni-v1` až po dokončení sady bádáním a se stejnými modely rolí jako v `mereni-v0`.

## E7 předání do další session (17. 11. 2026, větev `e7-predani`)

Z poznámky projektu 16. 11. (jeden záznam o stavu a předání). Příčina potvrzená kódem: STAV.md se vedl ručně, `stav.py` ho nečetl,
odkazy do `pracovni/` nikdo neodmítl. Hotovo: `stav.py predani|pravidlo|kontrola|vyrad|vzor|uklid` (uklid z podnětu 17. 11.: mazání v `pracovni/` hlídač zamítal), Edit v `tools:` badatele (podnět 17. 11.: tabulka slibovala
Edit, nástroj chyběl, zápis do `udaje_od_rodiny.md` se odkládal), hlídač zamítá ruční Edit/Write STAV.md,
šablona s oddílem Pravidla od uživatele, test `test_e7_predani.py`. Zbývá:

- zkopírovat `tools/stav.py` a šablonu do projektu (rozhodne uživatel), v projektu `tools/brana.py`;
- migraci STAV.md projektu dělá bádání (`stav.py kontrola`, úkoly do front, `vyrad`, `predani`), pak smazat poznámku v projektu;
- zrušení nebo změna pravidla od uživatele zatím nemá příkaz (jen nové pravidlo, které starší nahrazuje).

## Otevřené po E0–E6

- Pokus na platformě: jde v pomocníkovi pluginu pokračovat zprávou se zachovaným kontextem (nástroj `SendMessage`), když je řídicí agent
  hlavní vlákno s vlastním seznamem `tools:`? Dnes je pokračování řešeno novým čtenářem, který dostane nález a čte jen rozšíření. Když pokus
  vyjde, přidat `SendMessage` do `tools:` řídicího agenta a do testu definic.
- Úplná sada testů po E6 prošla 16. 11. 2026 ve třech částech (662 testů, včetně sestavení ukázkového webu); na pozadí vcelku ji systém
  jednou ukončil pro nedostatek paměti, proto po částech.
- Přístupy a vyhledávání (scénář 11): kontrola vztahů běží jen nad celým webem (verze `vse`). Pro omezené přístupy chybí kontrola proti
  jejich vlastním datům a hledání jmen, která přístup vidět nemá, v HTML a v indexu vyhledávání.
- Tvrzení (`data/tvrzeni.jsonl`) se zatím jen ukládají a kontrolují; na web se nepromítají. Až bude vidět, kolik faktů v `f` z nich jde
  generovat, rozhodnout o dalším kroku (návrh, oddíl 6.7, možnost c).
- Role účastníků mimo zápisy: kmotr a svědek se na stránce osoby ukáže u zápisu („Role v zápisu“), samostatný oddíl „kmotřenci“ není.
- Po měřicím běhu: zkopírovat nástroje E1–E6 do projektu, v projektu `tools/brana.py`, pak `tools/ucastnici.py navrh` (role k ruční
  kontrole potvrzuje bádání) a měření `mereni-v1` na téže sadě.

## Z měřicího běhu mereni-v0 (16. 11. 2026)

- `pracovni_prehled.py --hledej`: přepínač jen pro soubory, bez řádků deníku (prozrazuje dřívější nález při slepém čtení).
- `kontext.py`: volba bez propojených zápisů a textové klíče osob v `--osoba`.
- `aron_img.py`: osmiznakové apu vrací 404; sjednotit s ostatními nástroji, regresní test.
- Zadání čtenáře: výčet snímků rozsahu a v nálezu výčet skutečně přečtených snímků, aby `nenalezeno` šlo zkontrolovat proti rozsahu.
- Výřez pro ověřovatele: kontrola, že neuřízl sloupec (dnes hlídá jen rozměr).
- Měření: pevně zadat modely rolí (v `mereni-v0` běžel ověřovatel a dva čtenáři na opus), aby `mereni-v1` šlo srovnat.

- `prohlizec.py`: uložit celý snímek v plném rozlišení nebo posouvat zvětšený pohled (podnět z bádání 16. 11. 2026: kurent na eBadatelně
  ze snímku obrazovky do 100 % přečíst nejde). Nejdřív zjistit, jak prohlížeč snímků portálu obrázek načítá (jeden obrázek, dlaždice,
  plátno) – z běhu čtenáře v prohlížeči (`prohlizec.py text`, výpis prvků), ne skriptem proti portálu. Do té doby obchůzka: plný snímek
  uloží uživatel do `pracovni/vlastni_snimky/`.

## Stránka Co hledáme a barva rodu na celém webu (rozhodnutí uživatele 16. 11. 2026)

Příčina: po migraci se veřejné části souborů otázek pro rodinu a dotazů na archivy staly frontami úkolů; export fronty správně
nečte (ADR 0003), ale do `data/verejne_otazky.json` je nikdo nepřevedl, takže stránka přišla o dvě sekce. Rod se navíc vede dvojím
klíčem (číslo k ve veřejných otázkách, slug v otevřených otázkách) a kontejnery vázané na rod mají barvu rodu jen někde.

Rozhodnutí uživatele: bližší předci pod „Obecné“; veřejné otázky se potvrzují po rodech; na web všechny dotazy na archivy, i ty,
které čekají na souhlas s odesláním; dotazy na archivy členěné podle archivů, rody uvnitř archivu barvou kontejneru; otázky pro
rodinu a otevřené otázky jeden kontejner na rod v barvě rodu; obecné pravidlo celého webu: kontejner vázaný na rod má barvu rodu,
obecný je neutrální.

Stav 16. 11. 2026: H1–H4 hotové (ADR 0009, CHANGELOG), v projektu převzaté, brána zelená. Zbývá: stránky Domy, Příběh, Deník,
Osoba a Rod projít, jestli mají kontejner vázaný na jeden rod (zatím jen Co hledáme a Zajímavosti; Jména mají karty jmen přes víc
rodů = obecné, Mapa barví body rodu už dřív); kontrola omezených přístupů proti jejich vlastním datům a hledání skryté osoby v indexu
vyhledávání (scénář 11).

Kroky (každý s testem, který chybu vyvolá):

1. **H1 barva rodu:** jeden zdroj barev (data rodů v exportu), jedna komponenta kontejneru rodu podle vzoru stránky Zajímavosti,
   použitá na stránkách Co hledáme, Zajímavosti, Jména, Domy, Mapa, Příběh, Deník, Osoba, Rod; kontrola webu: kontejner s rodem bez
   barvy rodu = chyba; pravidlo do dokumentace šablony.
2. **H2 klíč rodu a veřejné otázky:** rod jedním klíčem (slug; číslo k se při čtení převede); `otazky.py z-fronty` převede veřejné
   části obou front na nepotvrzené koncepty (rodina: rod podle nadpisu oddílu; archivy: archiv podle nadpisu, rod podle prefixu
   položky; karty úkolů jen s ručně psaným veřejným textem); `potvrd --rod <slug>|--obecne --kdo …` po rodech; příznak „čeká na
   souhlas s odesláním“; kontrola soukromí; badatel smí `z-fronty`, `uprav` a `potvrd` jen se jménem toho, kdo potvrdil.
3. **H3 export a stránka:** jedna struktura pro stránku (rodina a otevřené otázky jako kontejnery po rodech s Obecné první, prameny
   jako archivy s položkami nesoucími rod); stránka jen vykresluje; nepotvrzené a prázdné se nevykreslí.
4. **H4 kontroly:** jeden kontejner na rod, prameny po archivech, žádný nepotvrzený text na webu, omezené přístupy neprozradí skrytou
   osobu (navazuje na scénář 11).

## Cesta badatele ke všem datům (16. 11. 2026)

Příčina opakovaných podnětů „nemám nástroj“: hook povoloval jen cesty z naměřeného průchodu čtení → nález → deník, ne všechna data,
která bádání mění (osoby, dokumenty, místa, otázky, STAV a další texty); dlouhé sezení navíc mělo definici agenta z doby startu.
Opraveno najednou: tabulka „What you change and with which tool“ v definici badatele, `oprava.py` pro všechny strukturované
položky, texty přímo, `stav.py` vypisuje platná oprávnění z hooku. Pravidlo pro další změny: nový druh dat = řádek v té tabulce,
nástroj s kontrolou a povolení v hooku v jednom kroku, test v `test_hlidac_orchestratora.py`.

Audit dat (`audit_dat.py`) zatím nekontroluje: místo mimo kraj farnosti, tvary příjmení napříč zápisy, otevřené otázky vyřešené
zápisem, odkaz zápisu proti svazku, tvrzení doc bez druhého čtení; kontrola roku zápisu potřebuje potvrzené účastníky zápisů.

## Drobnosti mimo etapy (z poznámek projektu 15. 11. 2026)

- Hook proti holému `rm` (alias `rm -iv` čeká na potvrzení a běh visí) a proti `find .` z kořene projektu (15 GB `pracovni/` na OneDrivu);
  nabídnout `cache.py najdi` a `pracovni_prehled.py`.
- Zrušit `skills:` u committer, verifier, fixer, test-runner (start pomocníka); ověřit měřením, o kolik start klesne.
- Staré názvy souborů v hlášeních `kontrola.py` a `export_web.py`.
- Kontrola prohlížeče skriptem před spuštěním browser-readeru (tři běhy naprázdno).
- Jednotný podpis commitů a zákaz čísel úkolů ve zprávě (dnes hlídá jen text definice; s `commit.py` v E2 odpadne).

## Čeká na uživatele

- Vypnout konektor dokumentů pro projekt, zkrátit `CLAUDE.md` projektu (nasazení jinam), alias `rm` v `~/.bashrc`: jde o prostředí uživatele.
- Model řídicího agenta na celé sezení: rozhodnout po měření na sadě.
- Push a sloučení větví `e0-zmirneni` a dalších, vydání verze.
