// Přihlašovací brána pro Netlify (Edge Function) – web s více přístupy (data/web.json → pristupy).
// Soubor edge-functions/brana.js z této šablony vyrábí tools/export_web.py – ručně neupravovat.
// Každý přístup má vlastní verzi webu v /_p/<přístup>/. Podle otisku odpovědi v cookie (SHA-256, odpověď sama tu
// není) brána pošle jen verzi toho přístupu; cizí verze nejdou otevřít ani přímou adresou.
const PRISTUPY = {{PRISTUPY}};

const prihlaseni = async (url) => {
  const login = await fetch(new URL('/prihlaseni.html', url));
  return new Response(await login.text(), {
    status: 401,
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' },
  });
};

export default async (request, context) => {
  const url = new URL(request.url);
  if (url.pathname === '/prihlaseni.html') return context.next();
  const pristup = PRISTUPY[context.cookies.get('rodokmen') || ''];
  if (!pristup) return prihlaseni(url);
  const vlastni = `/_p/${pristup}/`;
  if (url.pathname.startsWith('/_p/')) {
    // přepsaný požadavek této brány (nebo přímá adresa vlastní verze) projde; cizí verze ne
    if (!url.pathname.startsWith(vlastni)) return new Response('Nenalezeno', { status: 404 });
    const res = await context.next();
    res.headers.set('X-Robots-Tag', 'noindex, nofollow');
    res.headers.set('Cache-Control', 'private, no-cache');
    return res;
  }
  return new URL(vlastni + url.pathname.replace(/^\/+/, '') + url.search, url);   // přepis (rewrite), adresa v prohlížeči zůstane
};

export const config = { path: '/*' };
