"""Agenti pro údržbu skillu po přechodu na originál (metodik, upstream-sync): povinná pole, odkazy na existující skripty
a nástroje, žádné odkazy na zrušenou vrstvu (pravidla pro agenty, fronty, kontrakty)."""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
AGENTI = REPO / "agents"


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    return dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M)) if m else {}


class Agenti(unittest.TestCase):
    def test_jen_agenti_udrzby(self):
        self.assertEqual(sorted(p.stem for p in AGENTI.glob("*.md")), ["metodik", "upstream-sync"])

    def test_povinna_pole_a_existujici_odkazy(self):
        for p in AGENTI.glob("*.md"):
            t = p.read_text(encoding="utf-8")
            fm = frontmatter(t)
            for pole in ("name", "description", "tools", "model"):
                self.assertTrue(fm.get(pole), (p.name, pole))
            self.assertEqual(fm["name"], p.stem)
            self.assertIn("## Done when", t, p.name)
            for cesta in re.findall(r"`((?:scripts|skills/rodokmen/tools|tools)/[a-z_]+\.py)", t):
                kandidati = [REPO / cesta, REPO / "skills" / "rodokmen" / cesta]
                self.assertTrue(any(k.exists() for k in kandidati), (p.name, cesta))
            for vzor in ("rodokmen-agents", "pravidla.py", "fronta.py", "vysledek.py", "zapis_vysledku", "orchestrator"):
                self.assertNotIn(vzor, t, (p.name, vzor))
            for a in re.findall(r"Agent\(([^)]*)\)", fm["tools"]):
                for jmeno in re.split(r"\s*,\s*", a):
                    self.assertTrue((AGENTI / (jmeno.split(":")[-1] + ".md")).exists(), (p.name, jmeno))


if __name__ == "__main__":
    unittest.main()
