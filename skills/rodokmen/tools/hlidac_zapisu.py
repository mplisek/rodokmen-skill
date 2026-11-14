#!/usr/bin/env python3
"""Hlídač zápisů do chráněných souborů (hook PreToolUse v .claude/settings.json projektu, ADR 0001, Q2).

Zapisuje ho `novy_projekt.py` spolu s hlídačem sítě (vypíná se stejně: --bez-hlidace). Před úpravou souboru (Edit, Write, MultiEdit,
NotebookEdit) nebo příkazem v Bash či PowerShellu zkontroluje, že se nepíše ručně do souboru, který má jedinou povolenou cestu zápisu:

  data/denik.jsonl             python3 -I tools/denik.py pridej …
  data/verejne_otazky.json     python3 -I tools/otazky.py pridej | uprav | potvrd | smaz
  web/src/generated/, web/src/data/   generuje export_web.py (npm run data)

Takový zápis zamítne a Claudovi napíše, kterým skriptem se to dělá. Nic jiného neblokuje: čtení, kopírování z chráněného souboru,
zápis skriptem, git, localhost, build ani ostatní data. Sám nic nemění. Při jakékoli vlastní chybě příkaz pustí.
"""
import json
import os
import re
import sys

CHRANENE = (
    ("data/denik.jsonl", "python3 -I tools/denik.py pridej … (oprava záznamu: --opravuje <id>)"),
    ("data/verejne_otazky.json", "python3 -I tools/otazky.py pridej | uprav | potvrd | smaz"),
    ("web/src/generated/", "python3 -I tools/export_web.py (npm run data) – soubory se generují z dat"),
    ("web/src/data/", "python3 -I tools/export_web.py (npm run data) – soubory se generují z dat"),
)
EDITACE = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
PRIKAZY = {"Bash", "PowerShell", "Monitor"}
PRED_PRESMEROVANI = re.compile(r">{1,2}\s*[\"']?[^\s\"'|;&<>]*$")
PRED_TEE = re.compile(r"\btee\b(?:\s+-\w+)*\s+[\"']?[^\s\"']*$")
PRED_SED = re.compile(r"\b(?:sed|perl)\b[^|;&]*\s-\w*i\w*\b[^|;&]*$")
PRED_MAZANI = re.compile(r"\b(?:rm|del|erase|rmdir|mv|move|Remove-Item|Move-Item)\b[^|;&]*$", re.I)
PRED_ZAPIS = re.compile(r"\b(?:Set-Content|Add-Content|Clear-Content|Out-File|New-Item|truncate)\b[^|;&]*$", re.I)
PRED_KOPIE = re.compile(r"\b(?:cp|copy|Copy-Item|install|ln)\b[^|;&]*$", re.I)


def koren(cwd):
    d = os.path.abspath(cwd)
    while True:
        if os.path.isdir(os.path.join(d, "data")) and os.path.isdir(os.path.join(d, "tools")):
            return d
        nad = os.path.dirname(d)
        if nad == d:
            return os.path.abspath(cwd)
        d = nad


def vztazna(cesta, cwd):
    """Cesta souboru vůči kořeni projektu s lomítky „/“, nebo None, když leží mimo projekt."""
    kor = koren(cwd)
    absolutni = os.path.normpath(os.path.join(cwd, cesta.replace("\\", "/") if os.name != "nt" else cesta))
    try:
        rel = os.path.relpath(absolutni, kor)
    except ValueError:   # jiný disk
        return None
    rel = rel.replace("\\", "/")
    return None if rel.startswith("..") else rel


def chranena(rel):
    for cesta, napoveda in CHRANENE:
        if rel == cesta or (cesta.endswith("/") and rel.startswith(cesta)):
            return rel, napoveda
    return None


def zapis_v_segmentu(seg, cesta):
    """Zapisuje segment příkazu do chráněné cesty (nebo ji maže, přesouvá)? Čtení a kopie z ní se nepočítají."""
    if re.match(r"\s*git\b", seg):
        return False
    hrana = cesta.rstrip("/")
    for m in re.finditer(re.escape(hrana), seg):
        pred, po = seg[:m.start()], seg[m.end():]
        if (PRED_PRESMEROVANI.search(pred) or PRED_TEE.search(pred) or PRED_SED.search(pred)
                or PRED_MAZANI.search(pred) or PRED_ZAPIS.search(pred)):
            return True
        if PRED_KOPIE.search(pred) and not po.strip().strip("\"'"):   # kopie jen tehdy, když je chráněný soubor cíl
            return True
    if re.search(r"open\(\s*[\"'][^\"']*" + re.escape(hrana) + r"[^\"']*[\"']\s*,\s*[\"'][wax]", seg):
        return True
    return bool(hrana in seg and re.search(r"write_text|write_bytes|writeFile|writeFileSync|appendFile", seg))


def posoudit(tool, vstup, cwd):
    """(chráněný soubor, nápověda) při zákazu, jinak None."""
    if tool in EDITACE:
        cesta = vstup.get("file_path") or vstup.get("notebook_path") or ""
        rel = vztazna(cesta, cwd) if cesta else None
        return chranena(rel) if rel else None
    if tool in PRIKAZY:
        cmd = (vstup.get("command") or "").replace("\\", "/")
        for seg in re.split(r"[;&|\n]+", cmd):
            for cesta, napoveda in CHRANENE:
                if cesta.rstrip("/") in seg and zapis_v_segmentu(seg, cesta):
                    return cesta, napoveda
    return None


def main():
    try:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8-sig")
        data = json.load(sys.stdin)
        nalez = posoudit(data.get("tool_name", ""), data.get("tool_input") or {}, data.get("cwd") or os.getcwd())
    except Exception:   # rozbitý hlídač nic neblokuje
        return 0
    if nalez:
        cesta, napoveda = nalez
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": f"Hlídač zápisů: {cesta} se ručně nepřepisuje (má jedinou cestu zápisu).\n"
                                        f"Použij: {napoveda}\nČtení a kopírování z tohoto souboru je v pořádku."}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
