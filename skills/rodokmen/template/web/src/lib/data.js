// Data exported from the research repo by tools/export_web.py (re-run `npm run data` after changes).
import site from '../data/site.json';
import stories from '../generated/pribehy.json';

export const { people, families, lines, stats, issues, hypotheses, docs, config, timeline } = site;
export { stories };
/** Osoby mimo přímou linii (data/osoby.py RODINA) pro stromový graf. */
export const others = site.others ?? [];
// přístup (export_web.py): id, název, výchozí osoby, práva; stránky s daty (menu ukáže jen je)
export const pristup = site.pristup ?? { id: 'vse', koreny: [site.root], prava: { soukrome: true, texty: true, poznamky: !!config.poznamky } };
export const stranky = site.stranky ?? null;
/** Počet rodů slovem pro nadpisy („Osm rodů“). */
export const linesTitle = (n) => (['Žádný rod', 'Jeden rod', 'Dva rody', 'Tři rody', 'Čtyři rody', 'Pět rodů', 'Šest rodů', 'Sedm rodů', 'Osm rodů'][n] ?? `${n} rodů`);
export const root = people[site.root];
export const records = Object.fromEntries(site.records.map((r) => [r.key, r]));
export const recordList = site.records;
export const byK = Object.fromEntries([
  ...Object.values(people).filter((p) => !p.extra).map((p) => [p.k, p]),   // extra = osoba z RODINA (k=0)
  ...Object.entries(site.aliases ?? {}).map(([k, slug]) => [Number(k), people[slug]]),
]);
export const lineByK = Object.fromEntries(Object.values(lines).map((l) => [l.k, l]));
// Místo v grafu předků: { k, p }. U přímé linie rodiče podle Kekulého čísla (2k, 2k+1 – ukáže i předka za mezerou),
// u osoby z RODINA (k = 0) podle odkazů otec/matka z exportu (p.parents); od přímého předka se pak jde zase po číslech.
export const slot = (p) => ({ k: p && !p.extra ? p.k : 0, p: p ?? null });
export function rodiceSlotu({ k, p }) {
  if (k) return [{ k: 2 * k, p: byK[2 * k] ?? null }, { k: 2 * k + 1, p: byK[2 * k + 1] ?? null }];
  return (p?.parents ?? [null, null]).map((s) => slot(s ? people[s] : null));
}
export const hloubka = (sl) => { const [a, b] = rodiceSlotu(sl); return a.p || b.p ? 1 + Math.max(hloubka(a), hloubka(b)) : 0; };
export const znamych = (sl) => { if (!sl.p) return 0; const [a, b] = rodiceSlotu(sl); return 1 + znamych(a) + znamych(b); };

export const href = {
  person: (slug) => `/osoba/${slug}/`,
  family: (id) => `/rodina/${id}/`,
  line: (slug) => `/rod/${slug}/`,
  record: (key) => `/zdroj/${key}/`,
  place: (slug) => `/misto/${slug}/`,
};

/** Sortable number from dates like "12. 5. 1811", "3/1867", "12/1790", "1797". */
export function dateKey(date) {
  const y = (date.match(/\d{4}/) || ['9999'])[0];
  const parts = date.replace(y, '').match(/\d+/g) || [];
  const [d, m] = parts.length >= 2 ? [parts[0], parts[1]] : [0, parts[0] || 0];
  return Number(y) * 10000 + Number(m) * 100 + Number(d);
}

export const genName = (g) =>
  ['výchozí osoba', 'rodiče', 'prarodiče', 'praprarodiče'][g] ?? `${g}. generace (${'pra'.repeat(g - 1)}rodiče)`;

export const statusClass = (st) => ({ doc: 'st-doc', prob: 'st-prob', fam: 'st-fam', mh: 'st-mh' })[st] ?? 'st-unk';
