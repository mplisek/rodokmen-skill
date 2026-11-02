// Poznámky (revize, připomínky, nápady) ke stránkám webu – společná kontrola pro formulář na webu
// i pro funkci na serveru (netlify/poznamky.sablona.mjs). Jen čistý text: žádné formátování, žádné HTML.
export const KDO_MAX = 100;
export const TEXT_MAX = 5000;

/** Čistý text: konce řádků LF, bez řídicích znaků (kromě nového řádku a tabulátoru), bez okrajových mezer. */
export function cistyText(s) {
  return String(s ?? '')
    .replace(/\r\n?/g, '\n')
    .replace(/[\u0000-\u0008\u000b-\u001f\u007f​-‏‪-‮⁦-⁩]/g, '')
    .trim();
}

/** Zkontroluje vstup formuláře. Vrací {chyba} nebo {kdo, text, stranka} (vyčištěné). */
export function zkontroluj({ kdo, text, stranka } = {}) {
  const k = cistyText(kdo).replace(/\s+/g, ' ');
  const t = cistyText(text);
  const s = String(stranka ?? '');
  if ([...k].length > KDO_MAX) return { chyba: `Pole „Kdo“ může mít nejvýš ${KDO_MAX} znaků.` };
  if (!t) return { chyba: 'Napište poznámku.' };
  if ([...t].length > TEXT_MAX) return { chyba: `Poznámka může mít nejvýš ${TEXT_MAX} znaků.` };
  if (!/^\/[^\s<>"'`]{0,300}$/.test(s) || s.startsWith('//')) return { chyba: 'Neplatná stránka.' };
  return { kdo: k, text: t, stranka: s };
}

/** Datum a čas po česku: „3. 11. 2026 14:05“. */
export function datum(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getDate()}. ${d.getMonth() + 1}. ${d.getFullYear()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
}
