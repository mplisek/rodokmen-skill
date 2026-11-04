# Rodinný web – stavba, nastavení, zveřejnění

Web je statický (Astro + vyhledávání Pagefind), data bere z `data/` přes `tools/export_web.py`.
Šablona používá Astro 7.3.8; podle `package-lock.json` vyžaduje Astro Node.js `>=22.12.0` a tranzitivní `undici`
8.11.2 `>=22.19.0`. Používej proto Node.js `>=22.19.0` při čisté instalaci i sestavení webu.
Stránky: úvod (lákadlo, statistiky, zajímavosti, mapa, rody, vějíř), příběh, zajímavosti, rody, stránka rodu,
mapa (OpenStreetMap; název obce v bublině vede na stránku místa s časovou osou lidí a událostí v obci), vějíř přes celou obrazovku s hledáním, časová osa (pruhy životů předků a pod nimi, co spolu
časově nesedí – stejná pravidla jako `kontrola.py`, ověřený údaj skryje `overeno`), seznam předků, zápisy (s výřezem, rámečkem, přepisem
a překladem), stránka osoby, rodiny, „Co hledáme“, výzkumný deník, hledání.

## Příkazy (ve složce `web/`)
| příkaz | co dělá |
|---|---|
| `npm ci` | čistá instalace přesně podle `package-lock.json` |
| `npm run data` | převede data do webu (vždy po změně dat; funkční Python 3 vyhledá `scripts/data.mjs`) |
| `npm run build` | sestaví web do `dist/` (s přístupy zvlášť verzi pro každý přístup, viz níže) |
| `npm run nahled` | data + build + náhled na http://localhost:4321 (Ctrl+C ukončí); `-- --pristup <id>` = verze pro jeden přístup |
| `npm run dev` | vývojový režim při úpravách vzhledu |
| `npm run nasadit` | data + build + nahrání na Netlify |

Náhled spouštěj na pozadí a uživateli pošli odkaz. `nahled` i `nasadit` po sestavení spustí `scripts/over_css.mjs`: ověří,
že každá stránka odkazuje na existující styly. Když selže (web by byl bez stylů – stává se u projektu za odkazem typu
junction a po zastaralé cache), smaž ve `web/` složky `dist`, `.astro` a `node_modules/.vite` a sestav znovu.
`astro.config.mjs` má proto `preserveSymlinks: true`. Netlify CLI za junction končí chybou „build.base … must be inside
the repository root“ – `nasadit` to řeší sám (`scripts/nasadit.mjs`): za odkazem nasazuje z čisté složky
`~/.rodokmen-netlify/<projekt>`, kam zkopíruje jen `dist/`, `netlify/` a `netlify.toml`. Propojení s webem
(`web/.netlify/state.json`) tam zkopíruje; když chybí, vypíše, ve které složce udělat jednou `sites:create` (nebo `link`).

**Web ve vnitřní síti (domácí počítač, bez nasazení na internet):** stačí servírovat hotové `dist/`, např.
`python3 -I -m http.server 4321 --bind 0.0.0.0 --directory dist` (ve `web/`). Aby běžel i po restartu (Linux),
uživatelská služba systemd `~/.config/systemd/user/rodokmen-web.service` s tímto `ExecStart`, `WorkingDirectory=%h/<projekt>/web`,
`Restart=on-failure`, `WantedBy=default.target` → `systemctl --user enable --now rodokmen-web`; bez přihlášení po restartu
ještě jednou `sudo loginctl enable-linger <uživatel>` (pustí uživatel). Po změně dat jen `npm run data && npm run build` –
server obnovu pozná sám. Úvod i patička ukazují „Poslední aktualizace“, ať rodina vidí, že se web obnovuje.
Pozor: takový web nemá přihlášení – je vidět z celé domácí sítě. Vzhled si ověř sám (snímek obrazovky přes prohlížeč, je-li k dispozici).

## `data/web.json`
```json
{
 "nazev": "Rodokmen Novákových",
 "popis": "Popis pro vyhledávače a sdílení (web je ale noindex).",
 "zapati": "Dohledáno v digitalizovaných matrikách SOA Zámrsk (portál ARON)",
 "kontakt": {"jmeno": "Petrovi", "email": "petr@example.cz"},
 "prihlaseni": {"uvod": "Tenhle web je jen pro rodinu.", "otazka": "Jak se jmenoval pes u babičky v Holicích?", "odpoved": "Alík"},
 "uvod": {"nadpis": "Lákavý nadpis", "odstavce": ["2–3 věty, které chytí"], "foto": "klic_obrazku_ve_vyrezech", "foto_popis": "…"},
 "pribeh": {"menu": "Příběh Nováků", "rod": 8, "tlacitko": "Přečíst příběh Nováků"},
 "pribehy": [],
 "zajimavosti_na_uvodu": [{"nadpis": "Nejstarší předek", "text": "Kovář Jan, asi 1825."}]
}
```
- `kontakt.jmeno` je ve 3. pádě („Napište Petrovi na …“).
- **Přihlášení:** otázka, na kterou zná odpověď jen rodina (ne snadno dohledatelná na sociálních sítích).
  Odpověď se porovnává bez diakritiky a velkých písmen. Na serveru i v cookie prohlížeče je jen její otisk (SHA-256),
  samotná odpověď se nikam neukládá. Krátkou nebo běžnou odpověď (jméno, obec) ale jde z otisku uhádnout zkoušením,
  proto ať ji uživatel nepoužívá jako heslo jinde. Bez odpovědi nasazení (`npm run nasadit`, `deploy-caprover`)
  skončí chybou; otevřený web jen výslovně přes `"otevreny": true` v `prihlaseni`.
  Je to lehká ochrana proti náhodným návštěvníkům, ne bankovní zabezpečení – citlivé věci na web nepatří.
- `uvod.foto` = klíč obrázku ve `vyrezy/` (ulož přes `vyrez.py`).
- `pribeh`: `menu` a `tlacitko` pojmenuj podle hlavního rodu („Příběh Novákových“), `rod` = číslo rodu (8–15).
  Bez vyplněného `uvod` ukáže úvodní stránka aspoň název a `lead` příběhu. Viz `pribehy.md`.
- `pribehy`: volitelný seznam slugů souborů z `data/pribehy/`, který určuje pořadí příběhů v rozcestníku.
  Prázdný seznam použije všechny soubory v abecedním pořadí; vyplněný seznam musí každý slug obsahovat právě jednou.
  Frontmatter (`title`, `lead`, číselné `rod`) a stránka každého příběhu jsou popsány v `reference/pribehy.md`.
- Šablona `web.json` je prázdná – název nastav hned, jak znáš příjmení výchozí osoby (`kontrola.py` hlásí zbytky ukázky).
- `puvodni_jmena`: `true` = jména osob na webu a ve vějíři v původních tvarech ze zápisů (pole `zap` v `osoby.py`,
  „Catharina Nowakin / Kateřina Nováková“). Výchozí je dnešní spisovná podoba; původní tvar je pak jen řádkem na stránce osoby.
- `citlive_schvaleno`: seznam úryvků textu, které uživatel na webu schválil (např. `["oběsil se ve stodole"]`) –
  `kontrola.py` je pak nehlásí jako `CITLIVÉ`. Úryvek musí obsahovat hlášené slovo; když se text změní, hlásí se znovu.

## Stránka Dokumenty
`/dokumenty/` ukáže všechny položky z `data/dokumenty.json` na jedné stránce s odkazy na osoby (u osob jsou i na jejich
stránkách). V menu je, jen když nějaký dokument existuje; text vybízí rodinu poslat další (kontakt z `web.json`).

## Stránky Statistiky a Domy
- **Statistiky** (`/statistiky/`, `tools/statistiky.py`): povolání, věk dožití a při sňatku, měsíce svateb, generační
  odstup, místa narození, křestní jména, víra, zápisy podle druhu a archivu. Počítá se jen z faktů přímých předků –
  čím jednotnější zápis faktů (`* 12. 3. 1873 Obec čp. 5`, `× …`, `† …`, řemeslo samostatně), tím lepší čísla.
- **Domy** (`/domy/`, `tools/domy_export.py`): mapa domů předků z výstupu samostatného skillu **stare-adresy**
  (https://github.com/barasoukup/stare-adresy, viz `data.md` → `domy/`). Skill rodokmen ho neobsahuje – bez
  `data/domy/domy.geojson` se stránka v menu neukáže a web funguje dál. Instalace (uživatel, jednou):
  `/plugin marketplace add barasoukup/stare-adresy` a `/plugin install stare-adresy@stare-adresy` (potřebuje ImageMagick
  a prohlížeč, který Claude ovládá). V projektu pak stačí „Projdi adresy v mém rodokmenu a udělej mapu domů předků“ –
  adresy „Obec čp. N“ čte z `data/osoby.py`, výstup patří do `data/domy/`, potom `npm run data && npm run build`.
  Adresy, které na mapě chybí, vypíše export do `data/domy/chybi.txt` (podklad pro další kolo).
  Podklad ČÚZK (mapa / letecký snímek), domy shluknuté podle obcí, barva podle rodu, v okénku lidé, kteří v domě
  žili (přímí předci první, boční příbuzní s odkazem na kartičku u předka), výřez skici a jedna věta o jistotě polohy.
  Na stránkách osob a zápisů jsou odkazy na domy. Výřezy skic na veřejném webu jen s citací archivu (podmínky
  v návodu stare-adresy).

## Zveřejnění na Netlify (výchozí, zdarma)
1. Uživatel si založí účet na netlify.com (stačí přihlášení přes Google/GitHub) – udělá sám.
2. Přihlášení CLI (otevře prohlížeč) – dej uživateli: `! cd web && npx -y netlify-cli@latest login`.
   Když `!` nejde (cloudové prostředí): `npx -y netlify-cli@latest login --request "Rodokmen"` vypíše odkaz a číslo
   lístku – uživatel odkaz otevře a schválí, pak `npx -y netlify-cli@latest login --check <lístek>`.
3. Založení webu a propojení složky (interaktivní, jednou) – dej uživateli:
   `! cd web && npx -y netlify-cli@latest sites:create` (zvolí tým a název → adresa `https://<název>.netlify.app`),
   případně `npx netlify-cli link`, pokud web už existuje. Je-li uživatel už přihlášený, jde web založit i bez dotazů
   (můžeš spustit sám): `cd web && npx -y netlify-cli@latest sites:create --name <název> --account-slug <tým>`.
   **Windows:** když `!` běží ve Windows PowerShellu 5.1 (`&&` tam nefunguje a `npx` blokuje Execution Policy), ať uživatel
   otevře PowerShell 7 nebo Příkazový řádek, přejde do složky `web` a spustí `npx -y netlify-cli@latest login` (a `sites:create`).
4. Nasazení: `cd web && npm run nasadit` (můžeš spustit sám; vypíše adresu webu).
5. Ověř: otevři adresu **v anonymním okně** → musí se ukázat rodinná přihlašovací otázka; po správné odpovědi web.
   Ukáže-li se místo ní přihlášení k Netlify (401, „Login Redirect“), zdědil web ochranu týmu („Team protection“).
   Uživatel ji vypne v administraci webu: Project configuration → Access & security → Visitor access. Web pak chrání
   rodinná otázka – proto znovu ověř v anonymním okně, že se ukáže.
   Přihlášení zajišťuje Netlify Edge Function `web/netlify/edge-functions/brana.js` (generuje ji export).
Další aktualizace = jen `npm run nasadit`. Tarif zdarma má měsíční kredity a každé nasazení je spotřebovává –
nenasazuj po každé drobné změně, ale až na požádání uživatele (třeba po skončení kola hledání). Vlastní doménu lze nastavit v administraci Netlify.

**Pozor:** „Netlify Drop“ (přetažení složky v prohlížeči) neumí Edge Functions → web by byl bez přihlášení. Nepoužívat.

## Náhled v Claude desktop
Projekt má `.claude/launch.json` – náhled webu v Claude desktop spustí `npm --prefix web run dev` (port 4321). Data se
předtím musí vyexportovat (`cd web && npm run data`). Když náhled nenaběhne (třeba na Windows, kde je `npm` jako `npm.cmd`),
zkus v `launch.json` `"runtimeExecutable": "node"` a `"runtimeArgs": ["web/node_modules/astro/bin/astro.mjs", "dev", "--root", "web"]`
(Astro 7 má spouštěč `astro.mjs`, ne `astro.js`). Server běží jen na tomto počítači – nepřidávej `--host`.

## Vlastní server (pokročilé)
- Docker: `web/Dockerfile` jen servíruje hotový web – `dist/` a `nginx.conf` (z `nginx.sablona.conf`, s přístupy
  z `nginx.pristupy.sablona.conf`) se sestaví na počítači (`npm run data && npm run build`). Kontejner Python nepotřebuje.
- CapRover: `npm run deploy-caprover` (data, build, kontrola stylů, balíček a nahrání; vyžaduje přihlášený `caprover` CLI).

## Více přístupů – každá větev rodiny vidí jen svou část
Když web čte víc rodin (manželé, rodina sestry), může mít každá vlastní odpověď na přihlašovací otázku a vidět jen
svou část rodokmenu. Ve `web.json`:
```json
"prihlaseni": {"otazka": "Rodinná otázka", "odpoved": "…"},
"pristupy": [
  {"nazev": "Plíškovi", "odpoved": "…", "koren": [1]},
  {"nazev": "Rodina Jany", "odpoved": "…", "koren": ["jana-nova"], "rody": {"8": ["Novákové", "Kováři z Holic"]}},
  {"nazev": "Děti", "odpoved": "…", "koren": [2, 3], "texty": true}
]
```
- `prihlaseni.odpoved` vidí všechno (přístup `vse`; když chybí, celý web vidí jen správce v náhledu). Každý přístup musí
  mít **jinou** odpověď – podle ní web pozná, kdo se přihlásil. Otázka je jedna společná: formuluj ji obecně
  („Jak se jmenuje náš rodinný pes?“ – každá rodina má jinou odpověď) nebo ji vynech a dej rodinám heslo.
- `koren` = výchozí osoby (čísla z `P` nebo zkratky z `RODINA`). První určuje číslování: úvod, vějíř, rody a Předci jsou
  od ní. Další se přidají s předky jako příbuzní (vlastní stránky a vějíře). Přístup bez `koren` vidí všechno.
- Přístup s `koren` vidí předky výchozích osob, jejich potomky (sourozence předků, jejich rodiny až do dneška) a partnery –
  **ne předky partnerů** (rodina manžela sestry). Zápisy, výřezy, dokumenty, mapa, Domy a Statistiky jen z těchto osob.
- Texty o celé rodině (příběh, zajímavosti, deník, „Co hledáme“, hypotézy, úvod) přístup s `koren` nevidí, ledaže
  `"texty": true`. Vlastní úvod a název webu: `"uvod": {…}`, `"nazev_webu": "…"`. Názvy rodů: `"rody"` (jinak z `LINES`
  nebo z příjmení pradědečka / prababičky).
- `npm run build` sestaví **samostatnou verzi webu pro každý přístup** (`dist/_p/<id>/`, id vypíše
  `python3 -I tools/export_web.py --seznam-pristupu`). Brána (Netlify i nginx) podle přihlášení posílá jen tu verzi;
  ostatní větve na serveru pro daný přístup vůbec nejsou a cizí verze nejde otevřít ani přímou adresou. Build trvá
  déle (× počet přístupů). Náhled jednoho přístupu: `npm run nahled -- --pristup <id>`.
- Před zveřejněním projdi s uživatelem náhled **každého** přístupu (`soukromi.md`) – co která rodina uvidí.

## Poznámky ke stránkám (revize, připomínky, nápady) – jen Netlify
`"poznamky": true` ve `web.json` (web bez přístupů) nebo u přístupu v `pristupy` zapne na každé stránce tlačítko
**Připomínka** (vlevo dole – vpravo dole má Netlify na bezplatném tarifu svůj odznak): formulář *Kdo* (nepovinné, do 100 znaků) a *Poznámka* (1–5000 znaků, jen obyčejný text)
a pod ním poznámky k té stránce (datum, kdo, text – bez úprav). Přehled všech je na `/poznamky/` (v menu).
- Ukládá je funkce `/api/poznamky` do **Netlify Blobs** (úložiště zdarma u webu, nic se nenastavuje). Funkci
  (`netlify/functions/poznamky.mjs`) vyrábí `npm run data` z `netlify/poznamky.sablona.mjs` – jen s otisky odpovědí.
- Kdo vidí: přístup jen poznámky ze svého přístupu, přístup `vse` všechny (s názvem přístupu). Píše jen přihlášený.
- **K uživateli se dostanou** přehledem na webu a příkazem `npm run poznamky` (ve `web/`): stáhne nové do
  `data/poznamky.json` a vypíše nevyřízené. `-- --vyrizeno <id>` označí poznámku na webu jako vyřízenou,
  `-- --smazat <id>` ji smaže (nevhodná, omyl). Používá Netlify CLI jako nasazení; web nasazovaný z jiné složky:
  `-- --slozka <cesta>`. Poznámky se zapracovávají jako podněty od rodiny (`st="fam"`), ne jako doklad.
- Na CapRoveru/nginx ani v místním náhledu poznámky nejsou (tlačítko to napíše).

## Úpravy vzhledu
Styly `web/src/styles/global.css` (barvy v `:root`), rozložení `web/src/layouts/Base.astro`, stránky `web/src/pages/`.
Barvy rodů jsou v `tools/export_web.py` (`LINE_COLORS`) a `tools/fan_chart.py` (`BASE`). Upravuj jen na přání uživatele
a po úpravě zkontroluj web na mobilu i počítači.

## Vějíř pro libovolnou osobu
`/vejir/` je vějíř výchozí osoby. Každá další osoba se známým otcem nebo matkou (předek i příbuzný z `RODINA`) má svůj
vějíř předků na `/vejir/<adresa osoby>/` – odkaz je na její stránce a ve vějíři pole „Vějíř pro jinou osobu“.
SVG kreslí `tools/fan_chart.py <soubor.svg> --web <hrefs> --root <číslo předka nebo zkratka z RODINA>` (volá ho
`npm run data`, několik vějířů najednou). Vějíř ukazuje nejvýš 10 generací nad osobou.

## Vějíř na webu – plynulý posun a přibližování
Stránka `/vejir/` je jedno SVG; u velkého vějíře (stovky jmen) by se při posunu a přibližování sekalo. Proto má
hardwarovou akceleraci jako mapové aplikace (`web/src/lib/fanview.ts`, výpočty a testy v `fanmath.ts`): během pohybu
grafická karta posouvá připravený obraz, po zastavení se dokreslí ostrý výřez v rozlišení obrazovky.
- Výchozí `auto`: zapne se jen u velkých vějířů (od `AUTO_MIN_TEXTS` textů), malý vějíř (5–7 generací) jede bez ní.
- Vynutit: `data/web.json` → `"vejir": { "akcelerace": true }` nebo `false`, pak `npm run data && npm run build`.
- Vyzkoušet bez přestavění webu: adresa `/vejir/?akcelerace=1`, `=0` nebo `=auto`.
- Testy výpočtů: ve `web/` `npm test`.

## Vějíř jako plakát
`python3 -I tools/fan_chart.py vystupy/` → SVG a HTML (a PNG, je-li nainstalovaný Google Chrome, na Windows i Microsoft Edge) k tisku.

## Aktualizace staršího projektu
Znovu spusť `python3 -I SKILL_DIR/tools/novy_projekt.py <složka projektu>`. Data (`data/`, výřezy) zůstanou, `tools/` se přepíše
a soubory ve `web/`, které se liší od nové šablony, taky – staré verze uloží do `pracovni/zaloha_web_<datum>/` a vypíše jejich seznam.
Upravoval-li jsi s uživatelem vzhled (styly, stránky), převezmi úpravy ze zálohy (porovnej soubory) a ověř web. Pak ve `web/`
se stejnou verzí Node.js `>=22.19.0` pro instalaci i build spusť `npm ci`, `npm run data` a `npm run build`.
`package-lock.json` zachovej; `npm ci` z něj provede čistou instalaci. Starou šablonu přihlášení `export_web.py` odmítne s výzvou k aktualizaci.
