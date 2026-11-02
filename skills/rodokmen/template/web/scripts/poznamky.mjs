// `npm run poznamky`: poznámky z webu na Netlify (tlačítko „Připomínka“) do projektu – data/poznamky.json.
// Čte je Claude při další práci (nové nabídne zapracovat) i ty. Používá Netlify CLI, kterým se web nasazuje
// (stejné přihlášení), a stahuje jen poznámky, které v souboru ještě nejsou.
//
//   npm run poznamky                         stáhne nové poznámky a vypíše ty, které ještě nejsou vyřízené
//   npm run poznamky -- --vyrizeno <id>      označí poznámku jako vyřízenou (na webu „vyřízeno“, zůstane v přehledu)
//   npm run poznamky -- --smazat <id>        smaže poznámku (nevhodná, omyl) – z webu i z úložiště
//   … --slozka <cesta>                       složka propojená s webem na Netlify, když to není web/
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const web = fileURLToPath(new URL("../", import.meta.url));
const soubor = join(web, "..", "data", "poznamky.json");
const args = process.argv.slice(2);
const volba = (n) => (args.includes(n) ? args[args.indexOf(n) + 1] : null);
const slozka = resolve(volba("--slozka") || web);
const STORE = "poznamky";

function netlify(...a) {
  const r = spawnSync("npx", ["-y", "netlify-cli@latest", ...a], {
    cwd: slozka, encoding: "utf8", shell: process.platform === "win32", maxBuffer: 64 * 1024 * 1024,
  });
  if (r.status !== 0) {
    console.error((r.stderr || r.stdout || "").trim());
    console.error(`\nNetlify CLI skončil chybou. Je složka ${slozka} propojená s webem (npx netlify-cli link) a jsi přihlášený (npx netlify-cli login)?`);
    process.exit(1);
  }
  return r.stdout;
}

const nacti = () => (existsSync(soubor) ? JSON.parse(readFileSync(soubor, "utf8")) : []);
const uloz = (seznam) => writeFileSync(soubor, JSON.stringify(seznam.sort((a, b) => (a.cas < b.cas ? -1 : 1)), null, 1) + "\n", "utf8");

function zapis(poznamka) {   // blobs:set s obsahem ze souboru (JSON s uvozovkami a diakritikou na příkazové řádce neprojde)
  const d = mkdtempSync(join(tmpdir(), "poznamky-"));
  try {
    writeFileSync(join(d, "p.json"), JSON.stringify(poznamka), "utf8");
    netlify("blobs:set", STORE, poznamka.id, "--input", join(d, "p.json"), "--force");
  } finally {
    rmSync(d, { recursive: true, force: true });
  }
}

const seznam = nacti();
const vyrizeno = volba("--vyrizeno");
const smazat = volba("--smazat");

if (vyrizeno || smazat) {
  const id = vyrizeno || smazat;
  const p = seznam.find((x) => x.id === id);
  if (!p) {
    console.error(`Poznámka ${id} v data/poznamky.json není – nejdřív npm run poznamky.`);
    process.exit(1);
  }
  if (vyrizeno) {
    p.stav = "vyrizena";
    zapis(p);
    uloz(seznam);
    console.log(`Vyřízeno: ${id}`);
  } else {
    netlify("blobs:delete", STORE, id, "--force");
    uloz(seznam.filter((x) => x.id !== id));
    console.log(`Smazáno: ${id}`);
  }
  process.exit(0);
}

const vypis = JSON.parse(netlify("blobs:list", STORE, "--json") || "[]");
const klice = (Array.isArray(vypis) ? vypis : vypis.blobs || []).map((b) => (typeof b === "string" ? b : b.key)).filter(Boolean);
const mam = new Set(seznam.map((p) => p.id));
let nove = 0;
for (const klic of klice) {
  if (mam.has(klic)) continue;
  const p = JSON.parse(netlify("blobs:get", STORE, klic));
  seznam.push({ ...p, id: klic });
  nove++;
}
const smazane = seznam.filter((p) => !klice.includes(p.id));   // smazané jinde (správce na jiném počítači)
uloz(seznam.filter((p) => klice.includes(p.id)));
const otevrene = nacti().filter((p) => p.stav !== "vyrizena");
console.log(`Poznámky z webu: ${klice.length} celkem, ${nove} nových${smazane.length ? `, ${smazane.length} smazaných jinde` : ""} → data/poznamky.json`);
for (const p of otevrene) {
  console.log(`\n[${p.id}] ${p.cas.slice(0, 16).replace("T", " ")} · ${p.stranka} · ${p.kdo || "bez podpisu"}${p.pristup && p.pristup !== "vse" ? ` · přístup ${p.pristup}` : ""}\n${p.text}`);
}
if (!otevrene.length) console.log("Žádné nevyřízené poznámky.");
