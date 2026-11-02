// `npm run build`: sestaví web do dist/ (Astro + vyhledávání Pagefind).
// S více přístupy (data/web.json → pristupy) sestaví zvlášť verzi pro každý přístup do dist/_p/<přístup>/ –
// každá obsahuje jen větve svého přístupu; brána (Netlify / nginx) podle přihlášení pošle jen tu jeho.
//
// `npm run nahled` (= node scripts/build.mjs --nahled): data + jedna verze webu + náhled na http://localhost:4321.
// Náhled verze pro jeden přístup: `npm run nahled -- --pristup <přístup>` (id přístupu vypíše npm run data).
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { python } from "./python.mjs";

const web = fileURLToPath(new URL("../", import.meta.url));
const args = process.argv.slice(2);
const nahled = args.includes("--nahled");
const pristupArg = args.includes("--pristup") ? args[args.indexOf("--pristup") + 1] : null;

function npx(...a) {   // astro, pagefind z node_modules projektu
  const r = spawnSync("npx", ["--no-install", ...a], { cwd: web, stdio: "inherit", shell: process.platform === "win32" });
  if (r.status !== 0) process.exit(r.status ?? 1);
}
function exportuj(...a) {
  const r = python("export_web.py", a);
  if (r.status !== 0) process.exit(r.status ?? 1);
}
function sestav(outDir) {
  npx("astro", "build", "--outDir", outDir);
  npx("pagefind", "--site", outDir);
}

const cfgPath = join(web, "..", "data", "web.json");
const cfg = existsSync(cfgPath) ? JSON.parse(readFileSync(cfgPath, "utf8")) : {};
const vicePristupu = Array.isArray(cfg.pristupy) && cfg.pristupy.length > 0;

if (nahled) {
  if (pristupArg) exportuj("--pristup", pristupArg);
  else exportuj();
  rmSync(join(web, "dist"), { recursive: true, force: true });
  sestav("dist");
  const kontrola = spawnSync(process.execPath, [join(web, "scripts", "over_css.mjs")], { cwd: web, stdio: "inherit" });
  if (kontrola.status !== 0) process.exit(kontrola.status ?? 1);
  if (pristupArg) exportuj();   // zpět data celého rodokmenu (npm run dev)
  npx("astro", "preview");
} else if (!vicePristupu) {
  sestav("dist");
} else {
  const r = python("export_web.py", ["--seznam-pristupu"], { vystup: true });
  if (r.status !== 0) process.exit(r.status ?? 1);
  const ids = JSON.parse(r.stdout.trim().split("\n").pop());
  rmSync(join(web, "dist"), { recursive: true, force: true });
  for (const id of ids) {
    console.log(`\n=== Přístup ${id} ===`);
    exportuj("--pristup", id);
    sestav(join("dist", "_p", id));
  }
  cpSync(join(web, "dist", "_p", ids[0], "prihlaseni.html"), join(web, "dist", "prihlaseni.html"));
  exportuj();   // web/src zpět na data celého rodokmenu (npm run dev, náhled)
  console.log(`\nSestaveno ${ids.length} verzí webu (dist/_p/): ${ids.join(", ")}`);
}
