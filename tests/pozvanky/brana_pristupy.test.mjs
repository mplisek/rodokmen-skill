// Test brány pro web s více přístupy (fork) ze šablony skills/rodokmen/template/web/netlify/brana.pristupy.sablona.js:
// odpověď přístupu i klíč z osobního odkazu pošlou jen verzi webu toho přístupu (/_p/<id>/).
// Z kořene repozitáře: node --test tests/pozvanky/brana_pristupy.test.mjs   (Node 20+, nic nestahuje)
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const sha = (t) => createHash("sha256").update(t).digest("hex");
const sablona = readFileSync(new URL("../../skills/rodokmen/template/web/netlify/brana.pristupy.sablona.js", import.meta.url), "utf8");
const VSE = sha("rodokmen:kovar"), MATKA = sha("rodokmen:lipa");

async function nacti(pristupy, klice) {
  const zdroj = sablona.replace("{{PRISTUPY}}", JSON.stringify(pristupy))
    .replace("{{KLICE}}", JSON.stringify(Object.fromEntries(Object.entries(klice).map(([k, v]) => [sha(k), v]))));
  assert.ok(!zdroj.includes("{{"), "šablona má nevyplněnou značku");
  return import("data:text/javascript," + encodeURIComponent(zdroj));
}

const BRANA = await nacti({ [VSE]: "vse", [MATKA]: "matcina-rodina" }, { abc: "vse", def: "matcina-rodina" });
const BEZ_ODKAZU = await nacti({ [VSE]: "vse", [MATKA]: "matcina-rodina" }, {});

const LOGIN = "<html>prihlaseni</html>";
globalThis.fetch = async (url) => {
  assert.equal(new URL(url).pathname, "/prihlaseni.html");
  return new Response(LOGIN);
};
const SMAZAT = "rodokmen=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax";

async function pozadavek(brana, cesta, cookie) {
  let dal = false;
  const context = {
    cookies: { get: (n) => (n === "rodokmen" ? cookie : undefined) },
    next: async () => { dal = true; return new Response("web"); },
  };
  const res = await brana.default(new Request("https://rod.netlify.app" + cesta), context);
  return { res, dal };
}

const prepis = (r) => (r.res instanceof URL ? r.res.pathname + r.res.search : null);

async function odmitne(cesta, cookie, brana = BRANA) {
  const { res, dal } = await pozadavek(brana, cesta, cookie);
  assert.equal(res.status, 401);
  assert.equal(dal, false);
  assert.equal(await res.text(), LOGIN);
  assert.equal(res.headers.get("set-cookie"), cookie ? SMAZAT : null);
  assert.equal(res.headers.get("cache-control"), "no-store");
}

test("odpověď přístupu: přepis na jeho verzi webu", async () => {
  assert.equal(prepis(await pozadavek(BRANA, "/osoba/jan/?x=1", MATKA)), "/_p/matcina-rodina/osoba/jan/?x=1");
  assert.equal(prepis(await pozadavek(BRANA, "/", VSE)), "/_p/vse/");
});

test("klíč z osobního odkazu v cookie: přepis na verzi jeho přístupu", async () => {
  assert.equal(prepis(await pozadavek(BRANA, "/osoba/jan/", "def")), "/_p/matcina-rodina/osoba/jan/");
  assert.equal(prepis(await pozadavek(BRANA, "/", "abc")), "/_p/vse/");
});

test("platný klíč v adrese: cookie a přesměrování bez klíče", async () => {
  const { res, dal } = await pozadavek(BRANA, "/osoba/jan/?k=def&x=1");
  assert.equal(res.status, 302);
  assert.equal(dal, false);
  assert.equal(res.headers.get("location"), "/osoba/jan/?x=1");
  assert.equal(res.headers.get("set-cookie"), "rodokmen=def; Max-Age=31536000; Path=/; HttpOnly; Secure; SameSite=Lax");
  assert.equal(res.headers.get("referrer-policy"), "no-referrer");
});

test("neplatný klíč bez cookie: přihlašovací stránka 401", async () => {
  for (const cesta of ["/?k=spatne", "/?k=", "/?k=" + MATKA]) await odmitne(cesta);
  await odmitne("/?k=abc", undefined, BEZ_ODKAZU);
});

test("neplatný klíč s platnou cookie: klíč z adresy zmizí, cookie zůstane", async () => {
  const { res } = await pozadavek(BRANA, "/osoba/jan/?k=stary", MATKA);
  assert.equal(res.status, 302);
  assert.equal(res.headers.get("location"), "/osoba/jan/");
  assert.equal(res.headers.get("set-cookie"), null);
});

test("zrušený klíč, otisk místo klíče a cizí cookie: 401 a smazání cookie", async () => {
  await odmitne("/", "def", BEZ_ODKAZU);
  await odmitne("/", sha("def"));
  await odmitne("/", "jiny");
  await odmitne("/", "__proto__");
  await odmitne("/img/a.jpg");
});

test("cizí verze webu nejde otevřít ani klíčem", async () => {
  const { res, dal } = await pozadavek(BRANA, "/_p/vse/osoba/jan/", "def");
  assert.equal(res.status, 404);
  assert.equal(dal, false);
  const vlastni = await pozadavek(BRANA, "/_p/matcina-rodina/osoba/jan/", "def");
  assert.equal(vlastni.dal, true);
  assert.equal(vlastni.res.headers.get("x-robots-tag"), "noindex, nofollow");
});

test("funkce /api/ projde s platnou cookie (přístup si ověří sama), bez ní ne", async () => {
  assert.equal((await pozadavek(BRANA, "/api/poznamky", "def")).dal, true);
  await odmitne("/api/poznamky");
});

test("přihlašovací stránka projde vždy, neplatnou cookie smaže", async () => {
  let r = await pozadavek(BRANA, "/prihlaseni.html", "zruseny");
  assert.equal(r.dal, true);
  assert.equal(r.res.headers.get("set-cookie"), SMAZAT);
  for (const cookie of [VSE, "def", undefined]) {
    r = await pozadavek(BRANA, "/prihlaseni.html", cookie);
    assert.equal(r.dal, true);
    assert.equal(r.res.headers.get("set-cookie"), null);
  }
});

for (const cesta of ["//cizi.web/?k=def", "/\\cizi.web/?k=def", "///cizi.web/?k=stary"]) {
  test(`přesměrování zůstane na webu: ${cesta}`, async () => {
    const { res } = await pozadavek(BRANA, cesta, MATKA);
    assert.equal(res.status, 302);
    const loc = res.headers.get("location");
    assert.ok(loc.startsWith("/") && !/^\/[\/\\]/.test(loc), loc);
  });
}
