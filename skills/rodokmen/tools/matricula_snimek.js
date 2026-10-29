#!/usr/bin/env node
/* Uloží JEDEN snímek z Matricula Online tak, jak ho stáhne prohlížeč (Playwright).
 *
 * Použití (z kořene projektu):
 *   node tools/matricula_snimek.js <cesta-knihy> <snímek> <vystup.jpg>
 *   příklad: node tools/matricula_snimek.js oesterreich/wien/01-am-hof/01-01 5 pracovni/wien_krest_5.jpg
 * <cesta-knihy> a číslo snímku zjistíš nástrojem `python3 -I tools/matricula.py` (fary, knihy, snimky).
 *
 * Matricula chrání obrázky tokenem, který počítá JavaScript stránky. Tento skript ho NEnapodobuje: otevře knihu v pravém
 * prohlížeči (Chromium), počká, až si stránka sama načte obrázek, a uloží ho. Stahuj jen snímky, které čteš – žádné hromadné stahování.
 * Potřebuje balíček playwright: `npm install playwright` a `npx playwright install chromium` (jednou, ve složce projektu).
 * Bez Playwrightu otevři knihu v prohlížeči (Claude in Chrome) a snímek ulož ručně; trvalý odkaz je …/<kniha>/?pg=<snímek>.
 */
const fs = require('fs');
const path = require('path');

const [, , kniha, pg, out] = process.argv;
if (!kniha || !pg || !out) { console.error('Použití: node tools/matricula_snimek.js <cesta-knihy> <snímek> <vystup.jpg>'); process.exit(2); }
const castiCesty = kniha.replace(/^\/+|\/+$/g, '').replace(/^en\//, '').split('/');
if (castiCesty.length < 2 || castiCesty.length > 5 || castiCesty.some((c) => !/^[A-Za-z0-9_-][A-Za-z0-9_.-]*$/.test(c) || c === '.' || c === '..')) {
  console.error('Cesta knihy smí obsahovat jen písmena, číslice, pomlčky a lomítka (např. oesterreich/wien/01-am-hof/01-01).'); process.exit(2);
}
if (!/^[1-9][0-9]*$/.test(pg)) { console.error('Snímek musí být kladné číslo.'); process.exit(2); }

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) {
  console.error('Chybí balíček playwright. Nainstaluj ho: npm install playwright && npx playwright install chromium'); process.exit(3);
}

(async () => {
  const cesta = kniha.replace(/^\/+|\/+$/g, '').replace(/^en\//, '');
  const url = `https://data.matricula-online.eu/en/${cesta}/?pg=${pg}`;
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
    const obrazky = [];
    page.on('response', (r) => {
      const ct = r.headers()['content-type'] || '';
      if (ct.startsWith('image/jpeg') && new URL(r.url()).hostname === 'img.data.matricula-online.eu') obrazky.push(r);
    });
    await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(2500);
    // prohlížeč číslo snímku za koncem knihy tiše „přilepí“ na poslední snímek – počet snímků proto ověříme z popisků v stránce
    const html = await page.content();
    const m = /"labels":\s*\[/.exec(html);
    if (m) {
      let i = m.index + m[0].length, hloubka = 1, v_retezci = false, pocet = 0, cteno = false;
      for (; i < html.length && hloubka > 0; i++) {
        const c = html[i];
        if (v_retezci) { if (c === '\\') i++; else if (c === '"') v_retezci = false; continue; }
        if (c === '"') { v_retezci = true; pocet++; cteno = true; } else if (c === '[') hloubka++; else if (c === ']') hloubka--;
      }
      if (cteno && Number(pg) > pocet) { console.error(`Kniha má jen ${pocet} snímků (zadáno ${pg}).`); process.exitCode = 1; return; }
    }
    if (!obrazky.length) { console.error('Stránka žádný snímek nenačetla (špatná cesta nebo číslo snímku? Zkontroluj `matricula.py snimky`).'); process.exitCode = 1; return; }
    let nejlepsi = null;
    for (const r of obrazky) { const buf = await r.body().catch(() => null); if (buf && (!nejlepsi || buf.length > nejlepsi.length)) nejlepsi = buf; }
    if (!nejlepsi || nejlepsi.length < 20000) { console.error('Obrázek se nepodařilo uložit (příliš malý nebo prázdný).'); process.exitCode = 1; return; }
    fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
    fs.writeFileSync(out, nejlepsi);
    console.log(`${out} ${nejlepsi.length} B odkaz: ${url}`);
  } finally { await browser.close(); }
})().catch((e) => { console.error('Chyba:', e.message); process.exit(1); });
