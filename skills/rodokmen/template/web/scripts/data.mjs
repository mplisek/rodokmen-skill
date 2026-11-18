// `npm run data`: spustí ../tools/export_web.py (data → web). Argumenty se předají dál (např. -- --nasazeni).
import { python } from "./python.mjs";

// Astro 7 a lockfile potřebují Node ≥ 22.19 (reference/instalace.md) – říct to hned a srozumitelně, ne až chybou při `astro build`.
const [maj, min] = process.versions.node.split(".").map(Number);
if (maj < 22 || (maj === 22 && min < 19)) {
  console.error(`CHYBA: web potřebuje Node 22.19 nebo novější, tady je ${process.versions.node}. Nainstaluj aktuální ` +
    "Node LTS (macOS: brew install node, Windows: winget install OpenJS.NodeJS.LTS, pak restart Claude Code) a spusť znovu.");
  process.exit(1);
}

const run = python("export_web.py", process.argv.slice(2));
process.exit(run.status ?? 1);
