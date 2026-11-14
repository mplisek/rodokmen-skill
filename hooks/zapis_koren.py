#!/usr/bin/env python3
"""SessionStart hook pluginu rodokmen: zapíše cestu pluginu do <projekt>/pracovni/.plugin_root.

Bash nástroj proměnnou CLAUDE_PLUGIN_ROOT nemá (jen hooky), takže tools/kontext.py by v projektu nenašel pravidla agentů
(skills/rodokmen-agents/rules/ leží v pluginu, ne v projektu). Soubor je v pracovni/ (nejde na web ani do gitu) a kontext.py ho čte.
Zapisuje jen do projektu rodokmenu (je v něm data/); nikdy neshodí session (výstup prázdný, kód 0).
"""
import os
import sys


def main():
    koren = os.environ.get("CLAUDE_PLUGIN_ROOT")
    projekt = os.environ.get("CLAUDE_PROJECT_DIR")
    if not koren or not projekt or not os.path.isdir(os.path.join(projekt, "data")):
        return
    cil = os.path.join(projekt, "pracovni")
    os.makedirs(cil, exist_ok=True)
    with open(os.path.join(cil, ".plugin_root"), "w", encoding="utf-8", newline="\n") as f:
        f.write(koren + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
