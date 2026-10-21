#!/usr/bin/env python3
"""Založí nový projekt rodokmenu ze šablony skillu.

Použití: python3 <skill>/tools/novy_projekt.py <cílová složka> [--ukazka]
  --ukazka   nakopíruje i vymyšlená ukázková data (rodina Novákových), aby šel web hned vyzkoušet

Vytvoří: data/ (prázdné kostry nebo ukázka), web/ (Astro web), tools/ (kopie nástrojů),
vyrezy/, zdroje/, dokumenty/, pracovni/, CLAUDE.md a .gitignore. Existující soubory nepřepisuje.
"""
import os, shutil, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def copy(src, out):
    if os.path.islink(out):   # nepsat přes symlink mimo projekt
        os.remove(out)
    shutil.copy2(src, out)


def copy_tree(src, dst):
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "dist", ".astro", "__pycache__")]
        rel = os.path.relpath(base, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for f in files:
            out = os.path.join(dst, rel, f)
            if not os.path.lexists(out):
                copy(os.path.join(base, f), out)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dst = os.path.abspath(os.path.expanduser(sys.argv[1]))
    demo = "--ukazka" in sys.argv
    os.makedirs(dst, exist_ok=True)
    copy_tree(os.path.join(SKILL, "template", "ukazka" if demo else "data"), os.path.join(dst, "data"))
    if demo:
        for sub in ("vyrezy", "zdroje"):
            src = os.path.join(SKILL, "template", "ukazka_" + sub)
            if os.path.isdir(src):
                copy_tree(src, os.path.join(dst, sub))
    copy_tree(os.path.join(SKILL, "template", "web"), os.path.join(dst, "web"))
    tools = os.path.join(dst, "tools")
    os.makedirs(tools, exist_ok=True)
    for f in os.listdir(os.path.join(SKILL, "tools")):
        if f.endswith((".py", ".sh")) and f != "novy_projekt.py":
            copy(os.path.join(SKILL, "tools", f), os.path.join(tools, f))   # nástroje vždy aktualizovat
    for d in ("vyrezy", "zdroje", "dokumenty", "pracovni"):
        os.makedirs(os.path.join(dst, d), exist_ok=True)
    for name in ("CLAUDE.md", ".gitignore", "poznamky_pro_skill.md"):
        out = os.path.join(dst, name)
        if not os.path.lexists(out):
            copy(os.path.join(SKILL, "template", name), out)
    print("Projekt připraven:", dst)


if __name__ == "__main__":
    main()
