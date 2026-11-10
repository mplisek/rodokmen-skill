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
| `npm run data` | převede data do webu (vždy po změně dat; `scripts/data.mjs` si sám najde funkční Python 3) |
| `npm run build` | sestaví web do `dist/` (s přístupy zvlášť verzi pro každý přístup, viz níže) |
| `npm run nahled` | data + build + náhled na http://localhost:4321 (Ctrl+C ukončí); `-- --pristup <id>` = verze pro jeden přístup |
| `npm run dev` | vývojový režim při úpravách vzhledu |
| `npm run nasadit-cloudflare` | data + build + nahrání na Cloudflare (výchozí) + kontrola |
| `npm run nasadit` | data + build + nahrání na Netlify + kontrola |
| `npm run overit` | kontrola nasazeného webu bez přihlášení (rodinná otázka × ochrana týmu Netlify / stránka Cloudflare) |

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
 "kontakt": {"jmeno": "Petrovi", "kdo": "Petr", "email": "petr@example.cz"},
 "prihlaseni": {"uvod": "Tenhle web je jen pro rodinu.", "adresa": "https://novakovi.netlify.app",
                "otazka": "Jak se jmenoval pes u babičky v Holicích?", "odpoved": "Alík"},
 "uvod": {"nadpis": "Lákavý nadpis", "odstavce": ["2–3 věty, které chytí"], "foto": "klic_obrazku_ve_vyrezech", "foto_popis": "…"},
 "pribeh": {"menu": "Příběh Nováků", "rod": 8, "tlacitko": "Přečíst příběh Nováků"},
 "pribehy": [],
 "zajimavosti_na_uvodu": [{"nadpis": "Nejstarší předek", "text": "Kovář Jan, asi 1825."}]
}
```
- `kontakt.jmeno` je ve 3. pádě („Napište Petrovi na …“), `kontakt.kdo` v 1. pádě („odkaz posílá Petr“; bez něj
  „správce rodokmenu“).
- **Přihlášení** má dvě cesty, platí obě najednou. Stačí nastavit jednu z nich.
  - **Rodinná otázka:** otázka, na kterou zná odpověď jen rodina (ne snadno dohledatelná na sociálních sítích).
    Odpověď se porovnává bez diakritiky a velkých písmen. Na serveru i v cookie prohlížeče je jen její otisk (SHA-256),
    samotná odpověď se nikam neukládá. Krátkou nebo běžnou odpověď (jméno, obec) ale jde z otisku uhádnout zkoušením,
    proto ať ji uživatel nepoužívá jako heslo jinde. Odpověď je jedna pro všechny a jednomu člověku ji vzít nejde.
  - **Osobní odkazy** (`tools/pozvanky.py`): každý příbuzný dostane vlastní odkaz `https://<web>/?k=<klíč>`. Klíč je
    náhodný (128 bitů), uhádnout ho nejde. Odkaz jde jednomu člověku zrušit nebo vyměnit, ostatním odkazy fungují dál.
    Po otevření odkazu si web zapamatuje prohlížeč na rok. Funguje jen na Netlify (viz Vlastní server).
    ```
    python3 -I tools/pozvanky.py pridej "Teta Jana"        # nový odkaz, vypíše se jen jednou – hned ho předej uživateli
    python3 -I tools/pozvanky.py seznam                    # kdo má odkaz (bez odkazů samotných)
    python3 -I tools/pozvanky.py prejmenuj p1 "Jana Nováková"
    python3 -I tools/pozvanky.py nova p1                   # ztracený odkaz: nový, starý přestane platit
    python3 -I tools/pozvanky.py zrus p1
    ```
    Adresa odkazu se bere z `prihlaseni.adresa` (adresa webu, např. `https://<název>.netlify.app`). V
    `data/pozvanky.json` je u odkazu jen jméno, datum a otisk klíče (SHA-256), proto může jít do gitu. Zrušený
    odkaz tam zůstane bez otisku, aby jeho číslo nedostal nikdo jiný. Klíč samotný
    nástroj nikam neukládá: kdo odkaz ztratí, dostane nový (`nova`). Každá změna platí až po `npm run nasadit`, potom
    zrušený odkaz přestane fungovat i v prohlížečích, kde už byl otevřený.
    Když se zruší poslední odkaz a otázka není nastavená, web zůstane zamčený a nepustí nikoho (export upozorní).
    Přihlašovací stránka bez otázky jen vysvětlí, že se vstupuje odkazem, a podle `kontakt` poradí, jak získat nový.
    S otázkou ukáže formulář jako dřív a k němu větu, že osobní odkaz stačí otevřít.
  Bez otázky i bez odkazu nasazení (`npm run nasadit-cloudflare`, `nasadit`, `deploy-caprover`) skončí chybou; otevřený web jen výslovně
  přes `"otevreny": true` v `prihlaseni` (jen `true`, ne `"true"` ani `"ano"`; otevře web i s nastavenou otázkou).
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
  U domů, které mají záznam v `data/stavby.py` (`tools/stavby.py`, `reference/stavby.md`), je v seznamu pod mapou
  název a typ stavby, popis a rozbalovací **Dějiny domu** (čísla popisná v čase, události, držitelé, obyvatelé,
  „Co zatím nevíme“); nejistý údaj je označený („pravděpodobně“). Žijící a držitelé po roce 1950 bez souhlasu se
  na web nedostanou. Stavba, jejíž dům není v `domy.geojson`, se nezobrazí – export na to upozorní.

## Zveřejnění na Cloudflare (výchozí, zdarma)
**Ve forku zatím jen pro jednoduchý web s jednou rodinnou otázkou:** přístupy (`pristupy`), osobní odkazy
(`pozvanky.py`) a poznámky ke stránkám umí jen Netlify – export pak bránu pro Cloudflare nevyrobí a
`npm run nasadit-cloudflare` skončí chybou. Nasazování i přenos jsou zdarma bez limitu; brána běží před každým souborem a to se počítá do 100 000 požadavků denně
(stránka webu je asi 20–40 požadavků → tisíce zobrazení denně; po vyčerpání vrací web do půlnoci UTC chybu 429).
1. **Účet:** nemá-li uživatel účet Cloudflare, ať si ho **nejdřív** založí na dash.cloudflare.com (zdarma, stačí e-mail)
   a potvrdí e-mail z pošty – registrace se do dvou minut přihlášení nevejde. Až je v dashboardu přihlášený, pokračuj.
2. **Přihlášení:** spusť sám na pozadí `cd web && npx -y wrangler@4 login` – otevře prohlížeč. Řekni uživateli:
   „Otevře se stránka Cloudflare – klikni na **Allow**, máš na to asi 2 minuty.“ Ověření: `npx -y wrangler@4 whoami`.
   - **„Application authorization failed / Authentication error, please login“:** prohlížeč není u Cloudflare přihlášený
     (typicky hned po registraci, nebo jiné okno/anonymní okno). „Retry authorization“ nepomůže, když login mezitím
     vypršel. Ať se uživatel v tom prohlížeči přihlásí na dash.cloudflare.com, pak spusť `wrangler login` znovu
     (nový odkaz). Odkaz bez otevření prohlížeče: `npx -y wrangler@4 login --browser=false`.
   - „Timed out waiting for authorization code“ = vypršely 2 minuty, spusť login znovu.
3. **Adresa webu:** web poběží na `https://rodokmen.<název>.workers.dev` (`rodokmen` = název webu na účtu, `<název>` =
   subdoména účtu). Vymysli 2–3 názvy podle rodu (malá písmena
   bez diakritiky, pomlčky: `novakovi`, `novakovi-holice`, `rod-novaku`), ověř je
   `cd web && node scripts/nasadit_cloudflare.mjs --volno novakovi novakovi-holice rod-novaku` (ptá se DNS Cloudflare,
   adresu tím „nevyplašíš“) a uživateli nabídni jen volné. Vybraný zapiš do `data/web.json` jako
   `"cloudflare": {"nazev": "novakovi"}`. Název je subdoména celého účtu Cloudflare (založí se při prvním nasazení,
   změnit jde jen v administraci); kdyby byl přece obsazený, nasazení zkusí variantu s číslem a řekne ji.
   **Má-li uživatel účet Cloudflare už dřív**, použije se jeho stávající subdoména a název z `web.json` se nepoužije –
   adresu pak řekne až nasazení. Subdoména je na účtu jen jedna a přes API ji změnit nejde (jen v administraci).
   **Druhý rodokmen na stejném účtu** potřebuje jiný název webu, jinak by první web přepsal: zeptej se na něj (např.
   `rodokmen-dvorakovi`), zapiš `"cloudflare": {"web": "rodokmen-dvorakovi"}` a ukaž celou adresu
   `https://rodokmen-dvorakovi.<subdoména>.workers.dev`. Nasazení to samo hlídá: když web s tím názvem na účtu už je
   a z téhle složky se ještě nenasazoval, skončí s radou (tentýž projekt z jiného počítače: `node scripts/nasadit_cloudflare.mjs --prepsat`).
4. **Nasazení:** `cd web && npm run nasadit-cloudflare` (spusť sám). Vypíše adresu a sám spustí kontrolu
   `scripts/overit.mjs`. U nové adresy kontrola počká, až se rozšíří (pár minut); když ji počítač ještě nezná, řekne to
   a skončí bez chyby – pak ověř později `npm run overit`. Do té doby adresu v prohlížeči neotvírej: počítač nebo
   router by si zapamatoval, že neexistuje, a až 30 minut by ji neviděl (jinde, třeba v telefonu na mobilních datech,
   web už jede). Řekni to uživateli, ať se nelekne.
5. Ověř i sám v anonymním okně: rodinná otázka, po správné odpovědi web.
   Bránu (`web/cloudflare/worker.js`) a `web/wrangler.jsonc` vyrábí export – ručně neupravovat. Brána musí běžet
   před každým souborem (`run_worker_first`), jinak by šly stránky a fotky stáhnout bez přihlášení.
Další aktualizace = jen `npm run nasadit-cloudflare`.

**Pasti:**
- „You need to verify your email address to use Workers“ (403) u nového účtu: Cloudflare chce ověřený e-mail – ověření
  v dashboardu (pruh nahoře / My Profile), potvrdit odkaz v poště, nasadit znovu (subdoména už zůstane založená).
- Safari s blokátorem obsahu ukáže místo ověřovací stránky Cloudflare prázdnou stránku 403 – zkus jiný prohlížeč
  (kontrola to pozná).
- Nepoužívej `wrangler pages project create/deploy` ani „Import a repository“ v administraci – založí jiný typ projektu,
  případně sám přepíše `astro.config`/`package.json`. Nasazuj jen přes `npm run nasadit-cloudflare`.
- V cloudovém prostředí (claude.ai), kde se přihlášení přes prohlížeč nevrátí do terminálu, použij Netlify (`login --request`).

## Zveřejnění na Netlify (ve forku nutné pro přístupy, osobní odkazy a poznámky)
Pro uživatele, kteří už web na Netlify mají, a ve forku pro každý web s přístupy, osobními odkazy nebo poznámkami. Bezplatný účet vystačí jen na asi 20 nasazení měsíčně (viz kredity níže).
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
   **Nový web bývá „Private“ (ochrana týmu)** – rodina by místo rodinné otázky viděla přihlášení k Netlify a majitel to
   nepozná (je přihlášený). Řekni to uživateli předem; kontrola po nasazení (krok 4) ji pozná. Vypni ji se souhlasem uživatele:
   `npx -y netlify-cli@latest api updateSite --data '{"site_id":"<siteId z web/.netlify/state.json>","body":{"sso_login":false}}'`
   (v administraci: Project configuration → Access & security → Visitor access → Project visibility → Edit visibility → Public).
4. Nasazení: `cd web && npm run nasadit` (můžeš spustit sám; vypíše adresu webu). Na konci se sama spustí kontrola
   `scripts/overit.mjs` (ručně `npm run overit`): otevře web bez přihlášení a pozná rodinnou otázku, ochranu týmu Netlify
   (vypíše, jak ji vypnout) i web bez brány. Skončí-li chybou, oprav to a spusť `npm run overit` znovu.
5. Ověř i sám: otevři adresu **v anonymním okně** → přihlašovací stránka (s otázkou, nebo bez ní jen s radou
   k osobnímu odkazu), po správné odpovědi web. Jsou-li osobní odkazy, vytvoř si zkušební (`pozvanky.py pridej "Zkouška"`,
   s přístupy i `--pristup <id>`), nasaď, otevři ho v novém anonymním okně (musí se ukázat web – u přístupu jen jeho
   verze – a z adresy zmizet `?k=`), pak ho zruš (`zrus`) a znovu nasaď.
   Přihlášení zajišťuje Netlify Edge Function `web/netlify/edge-functions/brana.js` (generuje ji export).
Další aktualizace = jen `npm run nasadit`. Tarif zdarma má měsíční kredity a každé nasazení je spotřebovává –
nenasazuj po každé drobné změně, ale až na požádání uživatele (třeba po skončení kola hledání). Vlastní doménu lze nastavit v administraci Netlify.
Ostré nasazení (`--prod`) stojí 15 kreditů (zdarma je 300 měsíčně; po vyčerpání Netlify pozastaví **všechny** weby účtu),
provoz rodinného webu jen jednotky (2 kredity za 10 000 požadavků, 20 za GB dat – proto export obrázky pro web zmenšuje
a překóduje, mezipaměť `pracovni/.web_obrazky/`). Na **zkoušení** (testovací web, nová verze skillu) nasazuj náhled bez
`--prod`, ten kredity nestojí ani ostrý web nemění: `npx -y netlify-cli@latest deploy --dir=dist --no-build --alias test` →
adresa `https://test--<web>.netlify.app` (stejný web na Netlify, žádný druhý není potřeba); brána tam běží stejně,
poznámky mají vlastní úložiště. Zapiš to do `CLAUDE.md` projektu.

**Kredity Netlify (bezplatný účet):** 300 kreditů měsíčně, nepřevádějí se. Každé nasazení stojí 15 (nepovedené nic),
1 GB přenosu 20 → asi 20 nasazení měsíčně, nebo méně, když rodina stahuje velké výřezy ze `zdroje/`. Po vyčerpání
Netlify nasazování pozastaví a `npm run nasadit` skončí „Forbidden“ – to jsou vyčerpané kredity, ne chyba webu
(stav kreditů je v administraci Netlify). Proto nasazuj na pokyn uživatele nebo jednou na konci sezení, mezitím jen
náhled. Řekni to uživateli hned při prvním zveřejnění.

**Pozor:** „Netlify Drop“ (přetažení složky v prohlížeči) neumí Edge Functions → web by byl bez přihlášení. Nepoužívat.

## Náhled v Claude desktop
Projekt má `.claude/launch.json` – náhled webu v Claude desktop spustí `npm --prefix web run dev` (port 4321). Data se
předtím musí vyexportovat (`cd web && npm run data`). Když náhled nenaběhne (třeba na Windows, kde je `npm` jako `npm.cmd`),
zkus v `launch.json` `"runtimeExecutable": "node"` a `"runtimeArgs": ["web/node_modules/astro/bin/astro.mjs", "dev", "--root", "web"]`
(Astro 7 má spouštěč `astro.mjs`, ne `astro.js`). Server běží jen na tomto počítači – nepřidávej `--host`.

## Vlastní server (pokročilé)
- Docker: `web/Dockerfile` jen servíruje hotový web – `dist/` a `nginx.conf` (z `nginx.sablona.conf`, s přístupy
  z `nginx.pristupy.sablona.conf`) se sestaví na počítači (`npm run data && npm run build`). Kontejner Python nepotřebuje.
- Přestavba nechává na disku starý image bez tagu (stovky MB). Po `docker build` smaž jen starý image tohoto webu:
  ```
  OLD=$(docker images -q rodokmen-web:latest); docker build -t rodokmen-web .
  docker rm -f rodokmen-web; docker run -d --name rodokmen-web --restart unless-stopped -p 8080:80 rodokmen-web
  [ -n "$OLD" ] && [ "$OLD" != "$(docker images -q rodokmen-web:latest)" ] && docker image rm "$OLD"
  ```
  `docker system/image/builder prune` nepoužívej – platí pro celý server a smaže i věci jiných projektů.
- Web počítá s během v kořeni domény (odkazy, cookie přihlášení i hledání od `/`) – za reverse proxy mu dej
  subdoménu (`rodokmen.server.cz`), ne podadresář (`server.cz/rodokmen/`).
- **Jen přes https** (reverse proxy s Let's Encrypt, DSM, CapRover to umí): přihlašovací stránka počítá otisk odpovědi
  v prohlížeči a ten to přes obyčejné http (mimo localhost) nedovolí – přihlášení by nefungovalo.
- CapRover: `npm run deploy-caprover` (data, build, kontrola stylů, balíček a nahrání; vyžaduje přihlášený `caprover` CLI).
- Přihlášení tu hlídá nginx a ten umí jen rodinnou otázku (i odpovědi přístupů). Osobní odkazy nefungují: s otázkou pustí
  jen přes ni, bez otázky nepustí nikoho. Export to při každém spuštění připomene hláškou POZOR.

## Více přístupů – každá větev rodiny vidí jen svou část
Když web čte víc rodin (manželé, rodina sestry, větve sourozenců), dostane každá vlastní přístup a vidí jen svou část
rodokmenu. Ve `web.json`:
```json
"prihlaseni": {"otazka": "Rodinná otázka", "odpoved": "…"},
"pristupy": [
  {"nazev": "Plíškovi", "odpoved": "…", "koren": [1], "prava": {"soukrome": true, "texty": true, "poznamky": true}},
  {"nazev": "Rodina Jany", "koren": ["jana-nova"], "rody": {"8": ["Novákové", "Kováři z Holic"]},
   "odkazy": [{"id": "p1", "jmeno": "Jana", "otisk": "…", "vytvoreno": "2026-11-10"}]},
  {"nazev": "Děti", "odpoved": "…", "koren": [2, 3]}
]
```
- `prihlaseni.odpoved` je přístup správce (`vse`): vidí všechno a má všechna práva (když chybí, celý web vidí jen
  správce v náhledu).
- **Vstup:** přístup má odpověď (`odpoved`), osobní odkazy (`odkazy`), nebo obojí – bez obojího export skončí chybou.
  Každá odpověď musí být **jiná** (podle ní web pozná, kdo se přihlásil). Odkazy zakládá `tools/pozvanky.py`
  (`pridej "Jméno" --pristup <id>`), ve `web.json` je u nich jen otisk klíče. Starší `data/pozvanky.json` převede
  `pozvanky.py prevest`; odkazy na celý web (bez přístupu) zůstávají v `data/pozvanky.json`.
- **Práva** (`prava`, nevyplněné = `false`): `texty` = texty bez vazby na osobu nebo rod (příběh, zajímavosti,
  deník, „Co hledáme“, hypotézy, úvod), `poznamky` = tlačítko Připomínka a přehled poznámek, `soukrome` = soukromé
  údaje vlastní větve (připravuje se). Starší `"texty": true` / `"poznamky": true` přímo v přístupu platí jako v `prava`.
  Přístup bez `koren` vidí všechno včetně textů.
- **`koren`** = výchozí osoby (čísla z `P` nebo zkratky z `RODINA`); víc osob = sjednocení. První určuje číslování:
  úvod, vějíř, rody, Předci a Statistiky jsou od ní.
- **Kdo je ve verzi webu přístupu:**
  - **přímá linie** – výchozí osoby a jejich předci; jen z nich jsou Statistiky, Rody, Mapa, Časová osa, Strom a Předci;
  - **rozšířená linie** – navíc sourozenci výchozích osob i všech předků s větvemi až k žijícím, u každé osoby partner
    a **rodiče partnera** (sourozenci a další předci partnera ne); ostatní stránky (osoby, zápisy, dokumenty…);
  - **vlastní větev** – výchozí osoby, jejich potomci a partneři (rozsah práva `soukrome`).
  Osoby mimo rozšířenou linii ve verzi webu přístupu vůbec nejsou. Menu ukáže jen stránky, které v přístupu mají data.
- Vlastní úvod a název webu: `"uvod": {…}`, `"nazev_webu": "…"`. Názvy rodů: `"rody"` (jinak z `LINES`
  nebo z příjmení pradědečka / prababičky).
- **Kdo co vidí:** `python3 -I tools/pristupy.py` (souhrn za přístupy), `pristupy.py <id>` (seznam osob) – projdi ho
  před zveřejněním a pak každý přístup na testovacím webu.
- `npm run build` sestaví **samostatnou verzi webu pro každý přístup** (`dist/_p/<id>/`, id vypíše
  `python3 -I tools/export_web.py --seznam-pristupu`). Brána (Netlify i nginx) podle přihlášení posílá jen tu verzi;
  ostatní větve na serveru pro daný přístup vůbec nejsou a cizí verze nejde otevřít ani přímou adresou. Build trvá
  déle (× počet přístupů). Náhled jednoho přístupu: `npm run nahled -- --pristup <id>`.
- Před zveřejněním projdi s uživatelem náhled **každého** přístupu (`soukromi.md`) – co která rodina uvidí.
- **Osobní odkazy s přístupy:** `pozvanky.py pridej "Teta Jana" --pristup <id>` – teta po otevření odkazu vidí jen
  verzi webu pro ten přístup (stejně, jako by odpověděla jeho odpovědí); odkaz se zapíše k přístupu do `web.json`.
  Bez `--pristup` vede odkaz na celý web (přístup `vse`, ten musí existovat – `prihlaseni.odpoved`) a zůstane
  v `data/pozvanky.json`. Změna: `pozvanky.py pristup p1 <id>`. Poznámky fungují i pro příchozí přes odkaz
  (podle práva `poznamky` jejich přístupu).

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
- Náhled bez `--prod` (`test--<web>.netlify.app`) ukládá poznámky do vlastního úložiště `poznamky-test` – zkušební poznámky se na ostrém webu neukážou; stáhne je `npm run poznamky -- --test` (do `pracovni/poznamky_test.json`).

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
Znovu spusť `python3 -I SKILL_DIR/tools/novy_projekt.py <složka projektu>`. Data (`data/`, výřezy) zůstanou. Projekt má
v `.skill_sablona/` kopii šablony `web/` a `tools/`, ze které vznikl (commitovat s projektem), a skript podle ní rozhodne
o každém souboru a vypíše seznam:
- **Přepsáno**: soubor projekt neupravoval, nahradila ho nová verze.
- **Ponecháno**: vlastní úprava, šablona se nezměnila.
- **Sloučeno**: změnila se úprava i šablona, každá jinde; `git merge-file` je spojil. Ověř, že soubor dává smysl.
- **Ke kontrole**: úprava i šablona změnily stejná místa, chybí `git`, soubor přidal projekt i nová šablona, nebo ho
  projekt smazal a šablona změnila. Soubor zůstal, jak byl; nová verze je v `pracovni/zaloha_<datum>/nova_sablona/`
  (u konfliktu sloučení, kdy je `git`, vedle i návrh se značkami `<<<<<<<` jako `.konflikt`). Převezmi změny šablony
  ručně a pak spusť `python3 -I SKILL_DIR/tools/novy_projekt.py <složka projektu> --vyreseno web/src/…` (volbu lze
  opakovat). Jako základ uloží přesně ten návrh, který je v záloze (zapamatovaný v `.skill_sablona/cekajici.json`),
  takže pozdější změny šablony přijdou při další aktualizaci; soubor v projektu nezmění. Bez záznamu uloží aktuální
  verzi šablony a řekne to. Do té doby se soubor hlásí při každé aktualizaci. Do ke kontrole patří i složka na místě
  souboru (nebo naopak) a na Windows a macOS cesty, které se liší jen velikostí písmen; ty skript nezmění.
- **Smazáno v projektu**: soubor projekt smazal a šablona ho nezměnila, zůstane smazaný.
- **Šablona už nemá**: soubor zůstal (skript nic nemaže) a hlásí se při každé aktualizaci. Zkontroluj, jestli ho web
  ještě potřebuje; případně ho smaž ručně a spusť `--vyreseno` s jeho cestou.
- **Přepsáno, původní verze v záloze**: projekt ze starší verze bez `.skill_sablona/`. Upravené soubory nahradila nová
  verze a původní jsou v `pracovni/zaloha_<datum>/puvodni/`; vlastní úpravy z nich převezmi (porovnej soubory).

Odkaz (symlink, junction) ve `web/`, `tools/`, `.skill_sablona/` nebo `pracovni/`, který vede mimo projekt, a odkaz
nebo složku na místě zálohy skript odmítne s hláškou POZOR a soubory za nimi přeskočí (bez zálohy nic nepřepíše).

`web/package-lock.json` (mění ho `npm install`) se neslučuje: změnila-li ho šablona, vezme se nový a starý jde do zálohy.

**Po aktualizaci projdi výpis s uživatelem** (skript řeší jen mechanické případy):
1. **Ke kontrole:** porovnej, co změnila šablona (`.skill_sablona/<soubor>` proti `nova_sablona/<soubor>` v záloze)
   a co projekt (`.skill_sablona/<soubor>` proti souboru v projektu). Uživateli řekni jednou dvěma větami, co je nového
   a co je jeho úprava, navrhni sloučení a po souhlasu ho udělej a spusť `--vyreseno`.
2. **Přepsáno, původní verze v záloze:** porovnej `puvodni/<soubor>` s novou verzí. Jsou-li v ní vlastní úpravy
   (ne jen starší stav šablony), nabídni jejich převzetí do nové verze.
3. **Sloučeno:** prohlédni výsledek (`git diff`), jestli dává smysl.
4. Ve `web/` se stejnou verzí Node.js `>=22.19.0` pro instalaci i build `npm ci`, `npm run data` a `npm run build`, pak `python3 -I tools/kontrola.py`.
Starou šablonu přihlášení `export_web.py` odmítne s výzvou k aktualizaci, stejně jako šablonu bez osobních odkazů,
když už nějaké jsou v `data/pozvanky.json`.
5. Projekt z verze před 0.7.0-fork.1: `python3 -I tools/aron_img.py odkazy` najde odkazy na ARON, které otevírají knihu
   na prvním snímku, `… odkazy --opravit` je opraví.
