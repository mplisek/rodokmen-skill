// Po sestavení ověří, že KAŽDÁ stránka v dist/ odkazuje na existující soubor CSS; jinak skončí chybou (kód 1).
// Spouští ho `npm run nahled`, `npm run nasadit` a `deploy-caprover`. Chyba se objevila u projektu za odkazem
// (junction/symlink) a po zastaralé cache: soubor CSS v dist/_astro byl, ale stránky na něj neodkazovaly – web byl bez stylů.
// Oprava: smazat dist, .astro a node_modules/.vite a sestavit znovu (viz reference/web.md).
// Web s více přístupy má každou verzi v dist/_p/<přístup>/ – odkazy „/…“ se ověřují v té verzi, kam stránka patří.
import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
if (!existsSync(dist)) {
  console.error('CHYBA: složka dist/ neexistuje – nejdřív npm run build.');
  process.exit(1);
}
const verze = existsSync(join(dist, '_p'))
  ? readdirSync(join(dist, '_p')).map((id) => join(dist, '_p', id)).filter((d) => statSync(d).isDirectory())
  : [dist];
let pages = 0;
const bad = [];
function walk(d, koren) {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) {
      if (n !== 'pagefind' && n !== '_p') walk(p, koren);
      continue;
    }
    if (!n.endsWith('.html') || n === 'prihlaseni.html') continue;
    pages++;
    const html = readFileSync(p, 'utf8');
    const links = [...html.matchAll(/rel="stylesheet"[^>]*href="([^"]+)"|href="([^"]+\.css)"/g)].map((m) => m[1] || m[2]);
    if (!links.length) { bad.push(`${p} (bez odkazu na CSS)`); continue; }
    for (const l of links) {
      if (/^https?:/.test(l)) continue;
      const f = join(koren, decodeURIComponent(l.replace(/^\//, '').split(/[?#]/)[0]));
      if (!existsSync(f) || statSync(f).size < 100) bad.push(`${p} (chybí soubor ${l})`);
    }
  }
}
for (const v of verze) walk(v, v);
if (!pages) {
  console.error('CHYBA: v dist/ nejsou žádné stránky.');
  process.exit(1);
}
if (bad.length) {
  console.error(`CHYBA: ${bad.length} stránek má styly v nepořádku, např.:\n  ${bad.slice(0, 10).join('\n  ')}\n` +
    'Smaž dist, .astro a node_modules/.vite a sestav web znovu (npm run build).');
  process.exit(1);
}
console.log(`Kontrola stylů OK: ${pages} stránek${verze.length > 1 ? ` v ${verze.length} verzích webu` : ''}, všechny odkazují na existující CSS.`);
