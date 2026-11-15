#!/usr/bin/env python3
"""Hlídač agentů (hook PreToolUse pluginu, Fáze C, Q6, Q-C4):
- `orchestrator` smí v Bashi jen výpis z fronta.py (seznam, frontier, kontrola, rezim, dalsi, cekajici, plan, historie, kalibrace), kontext.py, mapa.py hledej|stav (jen čtení) a čtení gitu
  (`git branch --show-current`, `git status --short`, `git log --oneline [-N]`);
- `committer` smí jen `git status|diff|log`, `git branch --show-current`, `git add <konkrétní soubory>` a `git commit -m "…"`
  (bez -a, --amend, --no-verify, --allow-empty; nikdy push, checkout, reset, merge, …).
Jiné příkazy zamítne a řekne, co smí. Ostatních agentů, hlavního vlákna bez agenta ani jiných nástrojů se netýká. Při jakékoli vlastní
chybě příkaz pustí (stejně jako ostatní hlídače). Sám nic nemění.
"""
import json
import re
import shlex
import sys

POVOLENE = re.compile(
    r"^(?:python3?|py)(?:\s+-\S+(?:\s+\S+)?)*\s+(?:\./)?(?:tools/)?(?:fronta\.py\s+(?:seznam|frontier|kontrola|rezim|dalsi|cekajici|plan|historie|kalibrace)(?:\s+[\w.:/=-]+)*"
    r"|kontext\.py(?:\s+[\w.,:/=-]+)*|mapa\.py\s+(?:hledej|stav)(?:\s+[\w.,:/=-]+)*)\s*$")
GIT_CTENI = re.compile(r"^git\s+(?:branch\s+--show-current|status\s+(?:--short|-s|--porcelain)(?:\s+-b)?|log\s+--oneline(?:\s+-\d{1,3})?)\s*$")
NEBEZPECNE = re.compile(r"[;&|<>`$()\n]")
CESTA = re.compile(r"^[\w][\w./@+ěščřžýáíéúůďťňĚŠČŘŽÝÁÍÉÚŮĎŤŇ-]*$")


def jmeno_agenta(typ):
    return typ.split(":")[-1] if isinstance(typ, str) else ""


def orchestrator_smi(prikaz):
    return bool((POVOLENE.match(prikaz) or GIT_CTENI.match(prikaz)) and not NEBEZPECNE.search(prikaz))


def operatory_jen_v_uvozovkach(prikaz):
    """Řetězení, roury, přesměrování a konec řádku smí být jen uvnitř uvozovek (text zprávy); neuzavřená uvozovka = False."""
    q, i = None, 0
    while i < len(prikaz):
        c = prikaz[i]
        if q:
            if c == "\\" and q == '"':
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c in ";&|<>\n\r":
            return False
        i += 1
    return q is None


def committer_smi(prikaz):
    """Jeden git příkaz bez řetězení; add jen konkrétní relativní soubory; commit jen s -m (zpráva smí mít <e-mail>, ;, &, | i víc řádků v uvozovkách)."""
    if re.search(r"[`$]", prikaz) or not operatory_jen_v_uvozovkach(prikaz):   # $(…) a `…` se rozbalí i v uvozovkách
        return False
    try:
        t = shlex.split(prikaz, posix=True)
    except ValueError:
        return False
    if len(t) < 2 or t[0] != "git":
        return False
    sub, arg = t[1], t[2:]
    if sub in ("status", "diff", "log"):
        return all(a.startswith("-") or CESTA.match(a) for a in arg) and not any(a in ("--output", "-o") for a in arg)
    if sub == "branch":
        return arg == ["--show-current"]
    if sub == "add":
        if arg and arg[0] == "--":
            arg = arg[1:]
        return bool(arg) and all(CESTA.match(a) and ".." not in a.split("/") and not a.startswith(("-", "/")) and a != "." for a in arg)
    if sub == "commit":
        if not arg or len(arg) % 2:
            return False
        return all(arg[i] == "-m" and arg[i + 1].strip() for i in range(0, len(arg), 2))
    return False


ORCH_DUVOD = ("Orchestrator guard: the orchestrator may run only read-only listings of `tools/fronta.py` "
              "(seznam, frontier, kontrola, rezim, dalsi, cekajici, plan, historie, kalibrace), `tools/kontext.py --osoba N --tema …`, `tools/mapa.py hledej|stav` and read-only git "
              "(`git branch --show-current`, `git status --short`, `git log --oneline -N`), "
              "one command without pipes, redirects or chaining. Delegate everything else to a specialist agent.")
COMMIT_DUVOD = ("Committer guard: only `git status|diff|log`, `git branch --show-current`, `git add <exact files>` "
                "(no -A, -u, `.`, `..`, absolute paths) and `git commit -m \"…\"` (no -a, --amend, --no-verify, --allow-empty), "
                "one command, no chaining, pipes or redirects outside the quotes of the message, no `$` or backticks. Never push, switch branches, reset or merge.")


def main():
    try:
        data = json.load(sys.stdin)
        agent = jmeno_agenta(data.get("agent_type"))
        if agent not in ("orchestrator", "committer") or data.get("tool_name") not in ("Bash", "PowerShell", "Monitor"):
            return 0
        prikaz = str((data.get("tool_input") or {}).get("command", "")).strip()
    except Exception:
        return 0
    if agent == "orchestrator":
        smi, duvod = orchestrator_smi(prikaz), ORCH_DUVOD
    else:
        smi, duvod = committer_smi(prikaz), COMMIT_DUVOD
    if smi:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": duvod}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
