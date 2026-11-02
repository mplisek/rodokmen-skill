// Spuštění nástroje skillu (../tools/*.py) prvním funkčním Pythonem 3.9+.
// macOS/Linux: python3; Windows: python nebo py -3 („python3“ tam bývá jen nefunkční alias z Microsoft Store).
// -X utf8: s -I se proměnná PYTHONUTF8 ignoruje, na Windows by jinak výstup a soubory byly v cp1250.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const kandidati = process.platform === "win32" ? [["python"], ["py", "-3"], ["python3"]] : [["python3"], ["python"]];
let nalezeny = null;

function najdi() {
  if (nalezeny) return nalezeny;
  for (const k of kandidati) {
    const zkouska = spawnSync(k[0], [...k.slice(1), "-c", "import sys; sys.exit(sys.version_info < (3, 9))"], { stdio: "ignore" });
    if (zkouska.status === 0) return (nalezeny = k);
  }
  console.error("Nenašel jsem Python 3.9+ (python3, python ani py -3). Nainstalujte ho (python.org) a zkuste to znovu.");
  process.exit(1);
}

/** Spustí ../tools/<nastroj> s argumenty; vrátí výsledek spawnSync. vystup=true → stdout jako text (jinak do konzole). */
export function python(nastroj, args = [], { vystup = false } = {}) {
  const [cmd, ...pre] = najdi();
  const skript = fileURLToPath(new URL(`../../tools/${nastroj}`, import.meta.url));
  return spawnSync(cmd, [...pre, "-I", "-X", "utf8", skript, ...args],
    vystup ? { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] } : { stdio: "inherit" });
}
