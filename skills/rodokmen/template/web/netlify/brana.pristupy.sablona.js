// Přihlašovací brána pro Netlify (Edge Function) – web s více přístupy (data/web.json → pristupy).
// Soubor edge-functions/brana.js z této šablony vyrábí tools/export_web.py – ručně neupravovat.
// Každý přístup má vlastní verzi webu v /_p/<přístup>/. Přístup se pozná podle cookie „rodokmen“: buď otisk odpovědi
// (SHA-256, uloží ho přihlašovací stránka), nebo klíč z osobního odkazu /?k=<klíč> (tools/pozvanky.py), jehož otisk
// je v KLICE. Odpovědi ani klíče tu nejsou, jen otisky. Brána pošle jen verzi toho přístupu; cizí verze nejdou otevřít
// ani přímou adresou. Zrušený odkaz přestane platit po dalším nasazení, i ve starých cookie.
const PRISTUPY = {{PRISTUPY}};   // otisk odpovědi → přístup
const KLICE = {{KLICE}};         // otisk klíče z osobního odkazu → přístup
const ROBOTS = 'noindex, nofollow';
// Neplatnou cookie smazat: zrušený klíč je v cookie HttpOnly a tu by odpověď na otázku z přihlašovací stránky nepřepsala.
const SMAZAT = 'rodokmen=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax';

async function otisk(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
}

async function pristupKlice(klic) {
  if (!klic || Object.keys(KLICE).length === 0) return undefined;
  return KLICE[await otisk(klic)];
}

async function pristupCookie(cookie) {
  if (!cookie) return undefined;
  return (Object.hasOwn(PRISTUPY, cookie) ? PRISTUPY[cookie] : undefined) || pristupKlice(cookie);
}

function bezKlice(url) {
  const cil = new URL(url);
  cil.searchParams.delete('k');
  if (cil.pathname === '/prihlaseni.html') return '/';   // přihlášený člověk patří na úvod, ne na přihlašovací stránku
  // úvodní lomítka sloučit: z adresy „https://web//cizi.web/?k=…“ by jinak „//cizi.web/“ přesměrovalo na cizí web
  return cil.pathname.replace(/^[\/\\]+/, '/') + cil.search;
}

const prihlaseni = async (url, cookie) => {
  // přihlašovací stránka pozná neplatný odkaz podle parametru k v adrese
  const login = await fetch(new URL('/prihlaseni.html', url));
  const headers = { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'referrer-policy': 'no-referrer', 'x-robots-tag': ROBOTS };
  if (cookie) headers['set-cookie'] = SMAZAT;
  return new Response(await login.text(), { status: 401, headers });
};

export default async (request, context) => {
  const url = new URL(request.url);
  const cookie = context.cookies.get('rodokmen');
  const pristup = await pristupCookie(cookie);

  if (url.searchParams.has('k')) {
    const klic = url.searchParams.get('k');
    const headers = { location: bezKlice(url), 'cache-control': 'no-store', 'referrer-policy': 'no-referrer', 'x-robots-tag': ROBOTS };
    if (await pristupKlice(klic)) {
      headers['set-cookie'] = `rodokmen=${klic}; Max-Age=31536000; Path=/; HttpOnly; Secure; SameSite=Lax`;
      return new Response(null, { status: 302, headers });
    }
    if (pristup) return new Response(null, { status: 302, headers });   // starý odkaz, ale člověk už má platnou cookie
    return prihlaseni(url, cookie);
  }
  if (url.pathname === '/prihlaseni.html') {   // přihlašovací stránka je dostupná vždy
    const res = await context.next();
    if (cookie && !pristup) res.headers.append('set-cookie', SMAZAT);
    return res;
  }
  if (!pristup) return prihlaseni(url, cookie);
  if (url.pathname.startsWith('/api/')) return context.next();   // funkce (poznámky) si přístup ověří samy
  const vlastni = `/_p/${pristup}/`;
  if (url.pathname.startsWith('/_p/')) {
    // přepsaný požadavek této brány (nebo přímá adresa vlastní verze) projde; cizí verze ne
    if (!url.pathname.startsWith(vlastni)) return new Response('Nenalezeno', { status: 404 });
    const res = await context.next();
    res.headers.set('X-Robots-Tag', ROBOTS);
    res.headers.set('Cache-Control', 'private, no-cache');
    return res;
  }
  return new URL(vlastni + url.pathname.replace(/^\/+/, '') + url.search, url);   // přepis (rewrite), adresa v prohlížeči zůstane
};

export const config = { path: '/*' };
