# Stavby a domy předků: kdo je držel, kdo v nich žil

Matriky říkají, **kdo** a **kde** (obec, číslo popisné). Tahle kapitola je o domě samotném: komu patřil, kdo v něm
bydlel nebo pracoval, kdy vznikl a co se s ním stalo. Hodí se u domů, které stojí za příběh: hostinec, mlýn, kovárna,
rychta, fara, škola, panský dvůr, rodová usedlost, nebo dům, který po předcích drželi jiní lidé (jiná větev rodu).

Nápad na strukturu dat a přehled pramenů vznikl podle skillu **dejiny-domu** (github.com/vzoha/dejiny-domu-skill,
odvozen od tohoto skillu). Ten je určený na jeden dům a celou ves; tady je dům jen jedna z podrobností rodokmenu.

## Co kde je
| Co | Kde |
|---|---|
| poloha domu, jistota, výřez skici | `data/domy/` (výstup skillu **stare-adresy**, `adresy.json`, `domy.geojson`) |
| dějiny domu: držitelé, obyvatelé, události, otevřené otázky | `data/stavby.py` (formát níže) |
| zápisy, které údaj dokládají | `data/zaznamy.json` (klíč v poli `r`) |
| lidé | `data/osoby.py` (odkaz Kekulého číslem nebo klíčem z `RODINA`) |

Nástroj: `python3 -I tools/stavby.py kandidati` (náměty z rodokmenu), `kontrola` (hlídá data), `export` (pro web; volá ho
`export_web.py`). Na webu je to rozbalovací „Dějiny domu“ u domu na stránce **Domy**.

## Formát `data/stavby.py`
Slovník `D`, klíč = **id adresy** z `data/domy/adresy.json` (`kremenice-2`). Hlavička souboru má vzor a krátký popis polí.
```python
D = {
 "kremenice-2": dict(
   nazev="Hostinec Markových v Křemenici", typ="hostinec", dum="kremenice-2", st="prob", verejne=True,
   popis="Rodový dům Markových, čtyři generace.",
   cisla=[("1811–dnes", "čp. 2")],
   udalosti=[dict(rok="1838", text="Dřevěná budova na skici.", st="doc", zdroj="Indikační skica CAS…, 1838")],
   drzitele=[dict(od="", do="před 1836", n="Jan Marek", os=160, jak="", st="prob", r=["klic_zapisu"], note="…")],
   obyvatele=[dict(os=40, role="hostinský", st="doc", r=["klic_zapisu"])],
   pamatka=None,
   otevrene=["Kdo dům držel před 1811? (pozemková kniha)"],
 ),
}
```
- **`typ`**: `dum`, `statek`, `chalupa`, `hostinec`, `mlyn`, `kovarna`, `rychta`, `fara`, `skola`, `panstvi`, `kostel`, `kaple`, `jine`.
- **`drzitele`** jsou jen **vlastníci**, jeden řádek = jeden držitel; `jak` = koupě, dědictví, přiženění, dražba, příděl.
  **`obyvatele`** jsou všichni, kdo v domě žili nebo pracovali (hostinský, výměnkář, čeleď, nájemník). Hostinský nemusí být
  majitel: pronajímal ho často od vrchnosti. Co zápis neříká, nepřepisuj do držitelů.
- **`os`** = Kekulého číslo z `P` (celé číslo) nebo klíč z `RODINA`. U člověka, který v rodokmenu není (jiná větev, cizí
  rod), jen `n="Jméno"`. Jiná větev rodu je prostě další držitel s vlastním jménem.
- **`cisla`**: všechna čísla popisná domu v čase (dvojice období, číslo). Ztotožnění starého a nového čísla dolož v `udalosti`.
- **Roky jsou text**: `"1838"`, `"asi 1840"`, `"před 1836"`; prázdné = neznámé. Web řadí podle prvního čtyřčíslí.
- **Stav (`st`) má každá položka zvlášť**: `doc` přečteno v pramenu (vždy s `r` nebo `zdroj`), `lit` z literatury (vždy se
  `zdroj`), `prob` pravděpodobné (v `note` proč), `fam` od rodiny, `unk` neznámé. Nejistotu nezamlčuj, web ji napíše
  („pravděpodobně“).
- **`otevrene`**: co zatím nevíme a kde to hledat. Je to hotový seznam úkolů; co jde jen přes úřad, přepiš do `data/archivni_dotazy.md`.
- **`verejne=False`**: záznam na web nejde.

## Prameny podle doby (od dneška zpátky)
Postup je stejný jako u matrik: z každého pramene vezmi číslo domu, jméno a odkaz na starší pramen.

| Doba | Pramen | Co dá k domu |
|---|---|---|
| dnes | katastr nemovitostí, RÚIAN | parcela, dnešní číslo (stare-adresy) |
| 1938–dnes | letecké snímky (ČÚZK Archiv, ortofoto) | kdy stavba přibyla nebo zmizela; viz `podminky` ČÚZK |
| ~1880–1950 | **evidenční mapa**, pozemkový katastr | parcely a budovy po stabilním katastru, nové domy a dělení parcel |
| 1870–1950 | **pozemkové knihy** (vložky), sbírka listin | vlastníci, kupní a svatební smlouvy, výměnky, dluhy; katastrální pracoviště nebo SOA/SOkA |
| 1857–1921 | **sčítání lidu** po domech | celá domácnost; **vlastník domu je až v 1910 a 1921** (dřív je „majitel bytu“ = hlava domácnosti) |
| 1784–1900 | **matriky** (číslo domu u každého zápisu) | kdo se v domě narodil, oženil, zemřel: čti podle čísla domu, ne jména |
| 1824–1843 | **stabilní katastr**: skica, císařský otisk, písemný operát | půdorys, číslo domu, materiál (žlutá dřevěná, růžová zděná); skica má i jména držitelů u polí |
| 1869–1882 | **reambulace** originální mapy | změny kreslené červeně: dům nebo přestavba **po** mapování; tak se datuje novostavba |
| 1785–1789 | josefský katastr | držitel, výměra, číslo domu (Národní archiv) |
| 1748–1757 | tereziánský katastr | usedlíci podle kategorie, výměra |
| 1550–1850 | **gruntovní knihy** panství | všichni držitelé za sebou, ceny, výminky; fond velkostatku v SOA |
| 1651, 1654 | soupis poddaných, berní rula | hospodář, kategorie usedlosti (tištěné edice) |
| vše | vlastivědy, kroniky obce a školy, noviny | události obce, požáry, dražby; Kramerius, ANNO |

Dostupnost online ověř vždy v portálu (`reference/portaly.md`); co není, patří do `otevrene` a `archivni_dotazy.md`.

## Postup krok za krokem
1. **Vyber dům.** `python3 -I tools/stavby.py kandidati` vypíše domy zmíněné v `osoby.py` podle počtu lidí a řemesla
   (hostinský, mlynář, rychtář, panský zahradník…). Domy, které nejsou v `data/domy/adresy.json`, nejdřív nech geokódovat
   skillem stare-adresy (jinak se na stránce Domy neukážou).
2. **Zjisti, co už víš.** Všechny zápisy z čísla domu (křty, sňatky, úmrtí) z projektu: kdo se kdy v domě objevuje.
   Z toho jde `obyvatele` (stav `doc`, s klíčem zápisu).
3. **Zjisti číslo v čase.** Starší zápis může mít jiné číslo než dnešní (`cisla`); stabilní katastr a skica ukážou, zda dům
   na místě stál (stare-adresy). Dnešní dům na parcele s vysokým číslem je často novostavba po katastru (v Horním Vestci
   č.p. 13–17 na st. 31–37, skica má domy jen do st. 28).
4. **Najdi držitele.** Gruntovní kniha (do 1850), pozemková kniha (po 1850), sčítání 1910 a 1921. U matričního zápisu
   „hostinský v čp. 2“ zapiš do `obyvatele`, do `drzitele` až s dokladem (kniha, sčítání) nebo jako `prob` s důvodem.
5. **Zapiš to.** Do `data/stavby.py`, každý údaj s `st` a zdrojem; co nevíš, do `otevrene`.
6. **Zkontroluj a ukaž.** `python3 -I tools/stavby.py kontrola`, pak `npm run data && npm run build` a podívej se na stránku Domy.
7. **Deník.** Každé hledání (i neúspěšné) patří do `data/research_log.md`, jako u matrik.

## Soukromí
- **Žijící lidé** a lidé z posledních ~100 let: jen jméno a role (stejná hranice jako u webu). `kontrola` hlásí `SOUKROMÍ`.
- **Dnešní majitelé a držitelé po roce 1950** na web jen se souhlasem: pole `souhlas="e-mail 3. 11. 2026"`. Bez něj export
  záznam vynechá.
- **Citlivé události** (konfiskace, odsun, kolektivizace, soudní spory, dražby ve 20. století) se mohou týkat rodin, které
  ve vsi stále žijí. Zeptej se uživatele, jestli a jak je zmínit (`reference/soukromi.md`).
- **Výřezy indikačních skic** patří archivu (NA, MZA, ZA Opava): na rodinném webu za heslem jsou v pořádku, na veřejný
  web jen se souhlasem archivu. Originální mapy a císařské otisky ÚAZK smí na web s citací (viz stare-adresy, `zdroje.md`).
