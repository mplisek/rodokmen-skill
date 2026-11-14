#!/usr/bin/env python3
"""Hlídač orchestrátora (hook PreToolUse pluginu, Fáze C, Q6, Q-C4): agent `orchestrator` smí v Bashi jen výpis z fronta.py
(seznam, frontier, kontrola, rezim, dalsi) a kontext.py. Jiné příkazy zamítne a řekne, co smí. Ostatních agentů, hlavního vlákna
bez agenta ani jiných nástrojů se netýká. Při jakékoli vlastní chybě příkaz pustí (stejně jako ostatní hlídače). Sám nic nemění.
"""
import json
import re
import sys

POVOLENE = re.compile(
    r"^(?:python3?|py)(?:\s+-\S+(?:\s+\S+)?)*\s+(?:\./)?(?:tools/)?(?:fronta\.py\s+(?:seznam|frontier|kontrola|rezim|dalsi)(?:\s+[\w.:/=-]+)*"
    r"|kontext\.py(?:\s+[\w.,:/=-]+)*)\s*$")
NEBEZPECNE = re.compile(r"[;&|<>`$()\n]")


def je_orchestrator(typ):
    return isinstance(typ, str) and typ.split(":")[-1] == "orchestrator"


def main():
    try:
        data = json.load(sys.stdin)
        if not je_orchestrator(data.get("agent_type")) or data.get("tool_name") not in ("Bash", "PowerShell", "Monitor"):
            return 0
        prikaz = str((data.get("tool_input") or {}).get("command", "")).strip()
    except Exception:
        return 0
    if POVOLENE.match(prikaz) and not NEBEZPECNE.search(prikaz):
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": ("Orchestrator guard: the orchestrator may run only read-only listings of `tools/fronta.py` "
                                     "(seznam, frontier, kontrola, rezim, dalsi) and `tools/kontext.py --osoba N --tema …`, "
                                     "one command without pipes, redirects or chaining. Delegate everything else to a specialist agent.")}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
