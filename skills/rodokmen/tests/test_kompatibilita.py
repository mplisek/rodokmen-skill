"""Celý skill: syntaxe pro Python 3.9 (minimum podle SKILL.md), návody odkazují jen na existující nástroje,
síťové nástroje mají brzdu, verze je stejná ve VERZE a plugin.json."""
import ast
import json
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[1]
TOOLS = SKILL / "tools"


class Kompatibilita(unittest.TestCase):
    def test_python_39(self):
        for f in sorted(TOOLS.glob("*.py")) + sorted((SKILL / "tests").glob("*.py")):
            with self.subTest(soubor=f.name):
                ast.parse(f.read_text(encoding="utf-8"), str(f), feature_version=(3, 9))

    def test_navody_odkazuji_na_existujici_nastroje(self):
        texty = [SKILL / "SKILL.md", *sorted((SKILL / "reference").glob("*.md"))]
        for md in texty:
            for nazev in sorted(set(re.findall(r"tools/([\w-]+\.(?:py|sh|js))", md.read_text(encoding="utf-8")))):
                with self.subTest(navod=md.name, nastroj=nazev):
                    self.assertTrue((TOOLS / nazev).exists())

    def test_sitove_nastroje_maji_brzdu(self):
        bez = []
        for f in sorted(TOOLS.glob("*.py")):
            t = f.read_text(encoding="utf-8")
            if f.name in ("slusne.py", "smoke_test.py", "hlidac_site.py"):
                continue
            if re.search(r"urllib\.request|http\.client|urlopen", t) and "import slusne" not in t:
                bez.append(f.name)
        self.assertEqual(bez, [], "síťové nástroje bez brzdy tools/slusne.py")

    def test_verze_souhlasi(self):
        verze = (SKILL / "VERZE").read_text(encoding="utf-8").strip()
        plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], verze)
        self.assertIn(f"verze {verze}", (REPO / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
