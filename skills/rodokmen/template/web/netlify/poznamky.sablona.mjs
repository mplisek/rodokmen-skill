// Poznámky ke stránkám webu – funkce na Netlify (/api/poznamky). Soubor functions/poznamky.mjs z této šablony vyrábí
// tools/export_web.py – ručně neupravovat. Ukládá do Netlify Blobs (úložiště „poznamky“, jedna položka = jedna poznámka).
// Kdo smí číst a psát: přihlášený přístup s „poznamky“: true (v cookie otisk odpovědi nebo klíč z osobního odkazu,
// stejně jako brána).
// Přístup vidí poznámky ze svého přístupu a poznámky jiných větví ke stránkám, které sám má (společní předci),
// kromě soukromých; přístup „vse“ všechny (vidiPoznamku v src/lib/poznamky.mjs). Psát jde jen ke stránce, kterou přístup
// má. Měnit (vyřízeno, soukromá, smazat) jen správce v projektu: npm run poznamky (scripts/poznamky.mjs).
import { getStore } from '@netlify/blobs';
import { zkontroluj, vidiPoznamku, normStranka } from '../../src/lib/poznamky.mjs';

const PRISTUPY = {{PRISTUPY}};   // otisk odpovědi → { id, poznamky }
const KLICE = {{KLICE}};         // otisk klíče z osobního odkazu (tools/pozvanky.py) → { id, poznamky }
const STRANKY = Object.fromEntries(Object.entries({{STRANKY}}).map(([id, s]) => [id, new Set(s)]));   // id → stránky verze (build.mjs)

async function pristupZCookie(cookie) {
  if (!cookie) return undefined;
  if (Object.hasOwn(PRISTUPY, cookie)) return PRISTUPY[cookie];
  if (Object.keys(KLICE).length === 0) return undefined;
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(cookie));
  const h = Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
  return Object.hasOwn(KLICE, h) ? KLICE[h] : undefined;
}

// teplá instance funkce si poznámky pamatuje 5 minut (každá stránka je načítá – bez toho stovky čtení úložiště)
const CACHE = new Map();
async function nactiBlob(store, jmeno, key) {
  const c = CACHE.get(`${jmeno}:${key}`);
  if (c && Date.now() - c.t < 300000) return c.v;
  const v = await store.get(key, { type: 'json' });
  CACHE.set(`${jmeno}:${key}`, { t: Date.now(), v });
  return v;
}

const odpoved = (data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' },
});

export default async (req, context) => {
  const pristup = await pristupZCookie(context.cookies.get('rodokmen'));
  if (!pristup || !pristup.poznamky) return odpoved({ chyba: 'Poznámky nejsou pro tento přístup zapnuté.' }, 403);
  // náhled (adresa s „--“, např. test--web.netlify.app) má vlastní úložiště – zkušební poznámky se nepletou s ostrým webem
  const nahled = new URL(req.url).hostname.includes('--');
  const jmenoStore = nahled ? 'poznamky-test' : 'poznamky';
  const store = getStore({ name: jmenoStore, consistency: 'strong' });

  if (req.method === 'GET') {
    const stranka = new URL(req.url).searchParams.get('stranka');
    const mojeStranky = STRANKY[pristup.id];
    const { blobs } = await store.list({ prefix: pristup.id === 'vse' || mojeStranky ? '' : `${pristup.id}/` });
    const vse = (await Promise.all(blobs.map((b) => nactiBlob(store, jmenoStore, b.key))))
      .filter((p) => p && !p.smazano && (!stranka || p.stranka === stranka) && vidiPoznamku(pristup.id, p, mojeStranky))
      .sort((a, b) => (a.cas < b.cas ? 1 : -1))
      .map(({ cas, stranka: s, kdo, text, stav, pristup: p }) => ({ cas, stranka: s, kdo, text, stav, ...(pristup.id === 'vse' ? { pristup: p } : {}) }));
    return odpoved(vse);
  }

  if (req.method === 'POST') {
    let data;
    try {
      data = await req.json();
    } catch {
      return odpoved({ chyba: 'Neplatná data.' }, 400);
    }
    const v = zkontroluj(data);
    if (v.chyba) return odpoved({ chyba: v.chyba }, 400);
    // web s přístupy: psát jen ke stránce své verze (chybí-li seznam přístupu, nikam – sestav web znovu: npm run build)
    if (pristup.id !== 'vse' && Object.keys(STRANKY).length && !STRANKY[pristup.id]?.has(normStranka(v.stranka))) {
      return odpoved({ chyba: 'Tuto stránku váš přístup nemá.' }, 403);
    }
    const cas = new Date().toISOString();
    const id = `${pristup.id}/${cas.replace(/[:.]/g, '-')}-${crypto.randomUUID().slice(0, 8)}`;
    const sdilet = data.soukroma !== true;   // „jen pro naši větev“ nezaškrtnuto → uvidí i jiné větve se stejnou stránkou
    const poznamka = { id, cas, stranka: v.stranka, kdo: v.kdo, text: v.text, pristup: pristup.id, stav: 'nova', sdilet,
                       ...(sdilet ? {} : { soukroma: true }) };
    await store.setJSON(id, poznamka);
    return odpoved({ cas, stranka: v.stranka, kdo: v.kdo, text: v.text, stav: 'nova' }, 201);
  }

  return odpoved({ chyba: 'Nepodporovaná metoda.' }, 405);
};

export const config = { path: '/api/poznamky' };
