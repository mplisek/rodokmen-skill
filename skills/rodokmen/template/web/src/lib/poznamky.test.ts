import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cistyText, zkontroluj, datum, normStranka, vidiPoznamku, KDO_MAX, TEXT_MAX } from './poznamky.mjs';

test('poznámky napříč větvemi: jen ke stránkám, které přístup má; soukromé jen autorova větev a správce', () => {
  const stranky = new Set(['/', '/osoba/jan-novak-1890/']);
  const cizi = { pristup: 'matka', stranka: '/osoba/jan-novak-1890' };
  assert.equal(normStranka('/osoba/x/index.html?y=1'), '/osoba/x/');
  assert.ok(vidiPoznamku('otec', cizi, stranky));                                         // společný předek
  assert.ok(!vidiPoznamku('otec', { ...cizi, stranka: '/osoba/cizi/' }, stranky));          // stránka jiné větve
  assert.ok(!vidiPoznamku('otec', { ...cizi, soukroma: true }, stranky));                   // soukromá
  assert.ok(vidiPoznamku('matka', { ...cizi, soukroma: true }, stranky));                   // autorova větev
  assert.ok(vidiPoznamku('vse', { ...cizi, soukroma: true }, null));                        // správce
  assert.ok(!vidiPoznamku('otec', cizi, null));                                             // bez seznamu jen vlastní
  assert.ok(vidiPoznamku('otec', { pristup: 'otec', stranka: '/stara/' }, stranky));        // vlastní vždy
});

const ok = { kdo: 'Jana', text: 'Babička se jmenovala Marie.', stranka: '/osoba/jan-novak-1890/' };

test('platná poznámka projde a vyčistí se', () => {
  assert.deepEqual(zkontroluj({ ...ok, kdo: '  Jana \n Nová ', text: '\r\n Řádek 1\r\nŘádek 2 \u0007' }),
    { kdo: 'Jana Nová', text: 'Řádek 1\nŘádek 2', stranka: ok.stranka });
});

test('kdo je volitelné, nejvýš 100 znaků', () => {
  assert.equal(zkontroluj({ ...ok, kdo: '' }).kdo, '');
  assert.equal(zkontroluj({ ...ok, kdo: 'č'.repeat(KDO_MAX) }).kdo.length, KDO_MAX);
  assert.ok(zkontroluj({ ...ok, kdo: 'a'.repeat(KDO_MAX + 1) }).chyba);
});

test('poznámka je povinná, 1–5000 znaků', () => {
  assert.ok(zkontroluj({ ...ok, text: '   \n ' }).chyba);
  assert.equal(zkontroluj({ ...ok, text: 'x' }).text, 'x');
  assert.ok(!zkontroluj({ ...ok, text: 'ř'.repeat(TEXT_MAX) }).chyba);
  assert.ok(zkontroluj({ ...ok, text: 'a'.repeat(TEXT_MAX + 1) }).chyba);
});

test('HTML zůstane obyčejným textem, stránka jen místní adresa', () => {
  assert.equal(zkontroluj({ ...ok, text: '<b>tučně</b>' }).text, '<b>tučně</b>');   // zobrazuje se jako text, ne HTML
  for (const stranka of ['https://cizi.web/', '//cizi.web/', 'osoba/x/', '/a"onclick="x', undefined]) {
    assert.ok(zkontroluj({ ...ok, stranka }).chyba, String(stranka));
  }
});

test('čistý text a datum', () => {
  assert.equal(cistyText('a‮b'), 'ab');   // obrácení směru textu
  assert.match(datum('2026-11-03T13:05:00Z'), /^3\. 11\. 2026 \d{1,2}:05$/);
  assert.equal(datum('nesmysl'), '');
});
