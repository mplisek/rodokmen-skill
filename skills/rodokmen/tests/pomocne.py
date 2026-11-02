"""Společné pomůcky testů: založení dočasného projektu ze šablony skillu a spuštění nástroje v něm (bez sítě)."""
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TOOLS = SKILL / "tools"


def spust(projekt, nastroj, *args, check=True):
    """Spustí tools/<nastroj> projektu (kopie ze šablony) a vrátí CompletedProcess s výstupem jako text."""
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run([sys.executable, "-X", "utf8", str(Path(projekt) / "tools" / nastroj), *map(str, args)],
                       cwd=projekt, capture_output=True, text=True, encoding="utf-8", env=env)
    if check and r.returncode:
        raise AssertionError(f"{nastroj} {' '.join(map(str, args))} skončil kódem {r.returncode}:\n{r.stdout}\n{r.stderr}")
    return r


def novy_projekt(cil, *args):
    """tools/novy_projekt.py ze skillu na složku cil (založení nebo aktualizace)."""
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "novy_projekt.py"), str(cil), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)
