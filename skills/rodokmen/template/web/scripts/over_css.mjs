// Po sestavení ověří, že KAŽDÁ stránka v dist/ odkazuje na existující soubor CSS; jinak skončí chybou (kód 1).
// Spouští ho `npm run nahled` a `npm run nasadit`. Chyba se objevila u projektu za odkazem (junction/symlink)
// a po zastaralé cache: soubor CSS v dist/_astro byl, ale stránky na něj neodkazovaly – web byl bez stylů.
// Oprava: smazat dist, .astro a node_modules/.vite a sestavit znovu (viz reference/web.md).
import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
if (!existsSync(dist)) {
  console.error('CHYBA: složka dist/ neexistuje – nejdřív npm run build.');
  process.exit(1);
}
let pages = 0;
const bad = [];
function walk(d) {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) {
      if (n !== 'pagefind') walk(p);
      continue;
    }
    if (!n.endsWith('.html') || n === 'prihlaseni.html') continue;
    pages++;
    const html = readFileSync(p, 'utf8');
    const links = [...html.matchAll(/rel="stylesheet"[^>]*href="([^"]+)"|href="([^"]+\.css)"/g)].map((m) => m[1] || m[2]);
    if (!links.length) { bad.push(`${p} (bez odkazu na CSS)`); continue; }
    for (const l of links) {
      if (/^https?:/.test(l)) continue;
      const f = join(dist, decodeURIComponent(l.replace(/^\//, '').split(/[?#]/)[0]));
      if (!existsSync(f) || statSync(f).size < 100) bad.push(`${p} (chybí soubor ${l})`);
    }
  }
}
walk(dist);
if (bad.length) {
  console.error(`CHYBA: ${bad.length} stránek má styly v nepořádku, např.:\n  ${bad.slice(0, 10).join('\n  ')}\n` +
    'Smaž dist, .astro a node_modules/.vite a sestav web znovu (npm run build).');
  process.exit(1);
}
console.log(`Kontrola stylů OK: ${pages} stránek, všechny odkazují na existující CSS.`);
