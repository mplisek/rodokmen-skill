"""SKILL.md po přechodu na originál (analyza/zjednoduseni-badani.md, 10.4): základ originálu, nejvýš o desetinu delší,
bez odkazů na zrušenou vrstvu (fronty, kontrakty, agenti), každý zmíněný nástroj existuje, mapa a náhled knihy rozlišené,
deník jen denik.jsonl, ověřování pevnými poli se spory k uživateli."""
import re
import subprocess
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[1]
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")


class SkillMd(unittest.TestCase):
    def test_delka_nejvys_o_desetinu_nad_originalem(self):
        r = subprocess.run(["git", "show", "upstream/main:skills/rodokmen/SKILL.md"], cwd=REPO, capture_output=True, text=True,
                           encoding="utf-8")
        original = len(r.stdout.split()) if r.returncode == 0 and r.stdout.strip() else 3220   # bez remote upstream: 0.10.2
        self.assertLessEqual(len(TEXT.split()), int(original * 1.1), "SKILL.md bobtná – podrobnosti patří do reference/")

    def test_bez_zrusene_vrstvy(self):
        for vzor in (r"fronta\.py", r"ukoly_[a-z_]+\.md", r"stav\.py", r"zadani\.py", r"vysledek\.py", r"zapis_vysledku",
                     r"kontext\.py", r"commit\.py", r"podnet\.py", r"nocni_rezim", r"research_log", r"browser-reader",
                     r"rodokmen-agents", r"\bbadatel\b"):
            self.assertIsNone(re.search(vzor, TEXT), vzor)

    def test_zminene_nastroje_existuji(self):
        for n in sorted(set(re.findall(r"`(?:tools/)?([a-z_]+\.(?:py|sh|js))\b", TEXT))):
            if n == "osoby.py" or n == "stavby.py" and not (SKILL / "tools" / n).exists():
                continue   # datové soubory projektu
            self.assertTrue((SKILL / "tools" / n).exists(), n)

    def test_mapa_a_nahled_knihy_jsou_rozlisene(self):
        self.assertRegex(TEXT, r"`mapa\.py` \| \*\*mapa knihy\*\*")
        self.assertRegex(TEXT, r"`mapa_knihy\.py` \| \*\*náhled knihy\*\*")
        self.assertEqual(TEXT.count("| `graf.py"), 1, "graf.py v tabulce nástrojů jednou")

    def test_overovani_pevnymi_poli_a_spory_k_uzivateli(self):
        for s in ("pevných polí", "spor pro uživatele", "Čeká na rozhodnutí", "overeno: \"uzivatel\"", "nalez.py"):
            self.assertIn(s, TEXT, s)
        z = (SKILL / "reference" / "zapisy.md").read_text(encoding="utf-8")
        self.assertIn("## Pevná pole pro kontrolní čtení", z)
        for druh in ("křest (N)", "sňatek (O)", "úmrtí (Z)"):
            self.assertIn(druh, z)


if __name__ == "__main__":
    unittest.main()
