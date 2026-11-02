// Poznámky ke stránkám webu – funkce na Netlify (/api/poznamky). Soubor functions/poznamky.mjs z této šablony vyrábí
// tools/export_web.py – ručně neupravovat. Ukládá do Netlify Blobs (úložiště „poznamky“, jedna položka = jedna poznámka).
// Kdo smí číst a psát: přihlášený přístup s „poznamky“: true (otisk odpovědi z cookie, stejně jako brána).
// Každý přístup vidí jen poznámky ze svého přístupu, přístup „vse“ všechny. Měnit (vyřízeno, smazat) jen správce
// v projektu: npm run poznamky (scripts/poznamky.mjs).
import { getStore } from '@netlify/blobs';
import { zkontroluj } from '../../src/lib/poznamky.mjs';

const PRISTUPY = {{PRISTUPY}};   // otisk odpovědi → { id, poznamky }

const odpoved = (data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' },
});

export default async (req, context) => {
  const pristup = PRISTUPY[context.cookies.get('rodokmen') || ''];
  if (!pristup || !pristup.poznamky) return odpoved({ chyba: 'Poznámky nejsou pro tento přístup zapnuté.' }, 403);
  const store = getStore({ name: 'poznamky', consistency: 'strong' });

  if (req.method === 'GET') {
    const stranka = new URL(req.url).searchParams.get('stranka');
    const { blobs } = await store.list({ prefix: pristup.id === 'vse' ? '' : `${pristup.id}/` });
    const vse = (await Promise.all(blobs.map((b) => store.get(b.key, { type: 'json' }))))
      .filter((p) => p && !p.smazano && (!stranka || p.stranka === stranka))
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
    const cas = new Date().toISOString();
    const id = `${pristup.id}/${cas.replace(/[:.]/g, '-')}-${crypto.randomUUID().slice(0, 8)}`;
    const poznamka = { id, cas, stranka: v.stranka, kdo: v.kdo, text: v.text, pristup: pristup.id, stav: 'nova' };
    await store.setJSON(id, poznamka);
    return odpoved({ cas, stranka: v.stranka, kdo: v.kdo, text: v.text, stav: 'nova' }, 201);
  }

  return odpoved({ chyba: 'Nepodporovaná metoda.' }, 405);
};

export const config = { path: '/api/poznamky' };
