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


# Nástroje řídicího agenta: nástroj → podmínka na argumenty. Všechny si vstup kontrolují samy a zapisují jen validovaně (E1, E2):
# fronty přes fronta.py, přijatý výsledek přes zapis_vysledku.py (vstup ze souboru v pracovni/), commit přes commit.py (nikdy push).
FRONTA_ZAPIS = {"pridej", "smeruj", "rozdel", "zaparkuj", "selhani", "hotovo", "uprav", "presun", "odeslano", "znovu"}
NASTROJE_ORCH = {
    "vysledek.py": lambda a: a[:1] and a[0] in {"over", "souhrn", "porovnej", "vzor"},
    "zadani.py": lambda a: a[:1] and a[0] in {"novy", "rozsir", "ukaz"},
    "fronta.py": lambda a: a[:1] and a[0] in FRONTA_ZAPIS,
    "zapis_vysledku.py": lambda a: a[:1] and a[0].replace("\\", "/").startswith("pracovni/") and ".." not in a[0],
    "commit.py": lambda a: bool(a),
    "stav.py": lambda a: True,
    "spotreba.py": lambda a: True,
    "podnet.py": lambda a: bool(a),
}


def orchestrator_nastroj(prikaz):
    """Jeden příkaz `python [-I -X utf8] tools/<nástroj>.py <podpříkaz> …` z NASTROJE_ORCH; řetězení jen uvnitř uvozovek, bez `$` a zpětných apostrofů."""
    if re.search(r"[`$]", prikaz) or not operatory_jen_v_uvozovkach(prikaz):
        return False
    try:
        t = shlex.split(prikaz, posix=True)
    except ValueError:
        return False
    if not t or t[0] not in ("python", "python3", "py"):
        return False
    i = 1
    while i < len(t) and t[i].startswith("-"):
        i += 2 if t[i] == "-X" else 1
    if i >= len(t):
        return False
    m = re.fullmatch(r"(?:\./)?tools/([a-z_]+\.py)", t[i])
    return bool(m and m.group(1) in NASTROJE_ORCH and NASTROJE_ORCH[m.group(1)](t[i + 1:]))


def orchestrator_soubor(cesta, cwd):
    """Řídicí agent smí nástrojem Write psát jen pracovní soubory (rozhodnutí pro zapis_vysledku.py, zadání), nikdy data, nástroje ani web."""
    import os
    if not cesta:
        return False
    plna = os.path.normcase(os.path.abspath(os.path.join(cwd or os.getcwd(), cesta)))
    koren = os.path.normcase(os.path.abspath(os.path.join(cwd or os.getcwd(), "pracovni")))
    return plna.startswith(koren + os.sep)


def orchestrator_smi(prikaz):
    return bool((POVOLENE.match(prikaz) or GIT_CTENI.match(prikaz)) and not NEBEZPECNE.search(prikaz)) or orchestrator_nastroj(prikaz)


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
        elif c in ";&|<>()\n\r":
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
              "`tools/vysledek.py over|souhrn|porovnej|vzor`, `tools/zadani.py novy|rozsir|ukaz`, the queue commands of `tools/fronta.py`, "
              "`tools/zapis_vysledku.py pracovni/…json`, `tools/commit.py`, `tools/stav.py`, `tools/spotreba.py`, `tools/podnet.py` "
              "(text arguments in quotes, no `$` or backticks), "
              "one command without pipes, redirects or chaining. Delegate everything else to a specialist agent.")
SOUBOR_DUVOD = ("Orchestrator guard: you may write only working files under `pracovni/` (a decision for `tools/zapis_vysledku.py`, notes). "
                "Data change only through the validating tools: `tools/zapis_vysledku.py`, `tools/fronta.py`, `tools/zadani.py`.")
COMMIT_DUVOD = ("Committer guard: only `git status|diff|log`, `git branch --show-current`, `git add <exact files>` "
                "(no -A, -u, `.`, `..`, absolute paths) and `git commit -m \"…\"` (no -a, --amend, --no-verify, --allow-empty), "
                "one command, no chaining, pipes or redirects outside the quotes of the message, no `$` or backticks. Never push, switch branches, reset or merge.")


def main():
    try:
        data = json.load(sys.stdin)
        agent = jmeno_agenta(data.get("agent_type"))
        nastroj = data.get("tool_name")
        if agent in ("orchestrator", "badatel") and nastroj in ("Write", "Edit"):
            if orchestrator_soubor(str((data.get("tool_input") or {}).get("file_path", "")), data.get("cwd")):
                return 0
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": SOUBOR_DUVOD}}))
            return 0
        if agent == "badatel":
            agent = "orchestrator"
        if agent not in ("orchestrator", "committer") or nastroj not in ("Bash", "PowerShell", "Monitor"):
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
