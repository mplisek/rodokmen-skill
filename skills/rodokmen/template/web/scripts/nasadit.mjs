// `npm run nasadit` (poslední krok): nahraje sestavený web (dist/) na Netlify.
// Projekt za odkazem (junction/symlink, např. C:\onedrive → C:\home\OneDrive…) Netlify CLI plete: porovná dva zápisy
// téže cesty a skončí chybou „build.base … must be inside the repository root directory“. V tom případě se nasazuje
// z čisté složky mimo projekt (~/.rodokmen-netlify/<projekt>), kam se zkopíruje jen dist/, netlify/ a netlify.toml.
// Propojení s webem na Netlify (.netlify/state.json) se drží ve web/.netlify a do čisté složky se jen kopíruje.
import { cpSync, rmSync, mkdirSync, existsSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";

const NETLIFY = ["-y", "netlify-cli@latest"];
const web = resolve(fileURLToPath(new URL("../", import.meta.url)));
const skutecna = realpathSync.native(web);
const stejne = (a, b) => (process.platform === "win32" ? a.toLowerCase() === b.toLowerCase() : a === b);
const zaOdkazem = !stejne(web, skutecna) || !stejne(process.cwd(), realpathSync.native(process.cwd()));

function netlify(args, cwd) {
  return spawnSync("npx", [...NETLIFY, ...args], { cwd, stdio: "inherit", shell: true }).status ?? 1;
}

if (!zaOdkazem) process.exit(netlify(["deploy", "--prod", "--dir=dist"], web));

const projekt = basename(dirname(skutecna)).replace(/[^\w.-]+/g, "_");
const cil = join(homedir(), ".rodokmen-netlify", `${projekt}-${createHash("sha1").update(skutecna.toLowerCase()).digest("hex").slice(0, 8)}`);
const stav = join(".netlify", "state.json");
mkdirSync(join(cil, ".netlify"), { recursive: true });
for (const n of ["dist", "netlify"]) rmSync(join(cil, n), { recursive: true, force: true });
cpSync(join(web, "dist"), join(cil, "dist"), { recursive: true });
if (existsSync(join(web, "netlify"))) cpSync(join(web, "netlify"), join(cil, "netlify"), { recursive: true });
cpSync(join(web, "netlify.toml"), join(cil, "netlify.toml"));
const stary = join(homedir(), ".rodokmen-netlify", stav);   // dřívější ruční řešení: jedna složka pro všechno
if (existsSync(join(web, stav))) cpSync(join(web, stav), join(cil, stav));
else if (!existsSync(join(cil, stav)) && existsSync(stary)) cpSync(stary, join(cil, stav));
console.log("Projekt leží za odkazem (junction/symlink) – nasazuji z čisté složky", cil);
if (!existsSync(join(cil, stav))) {
  console.log("Složka ještě není propojená s webem na Netlify. V příkazovém řádku udělej jednou:\n" +
    `  cd "${cil}"\n  npx -y netlify-cli@latest sites:create   (nebo: npx -y netlify-cli@latest link)\n` +
    "a pak znovu npm run nasadit (propojení se uloží i do web/.netlify).");
  process.exit(1);
}
const kod = netlify(["deploy", "--prod", "--dir=dist"], cil);
if (kod === 0) {
  mkdirSync(join(web, ".netlify"), { recursive: true });
  cpSync(join(cil, stav), join(web, stav));   // propojení zůstane u projektu (i po smazání čisté složky)
}
process.exit(kod);
