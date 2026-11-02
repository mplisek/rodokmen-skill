// `npm run data`: spustí ../tools/export_web.py (data → web). Argumenty se předají dál (např. -- --nasazeni).
import { python } from "./python.mjs";

const run = python("export_web.py", process.argv.slice(2));
process.exit(run.status ?? 1);
