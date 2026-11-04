import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from kontrola import kekule, research_log_stats


class KekuleTests(unittest.TestCase):
    P = {1: dict(n="Jan Novák"), 2: dict(n="Václav Novák"), 4: dict(n="Josef Novák"), 5: dict(n="Anna Malá")}

    def test_spravna_cisla_bez_upozorneni(self):
        P = dict(self.P)
        P[4] = dict(n="Josef Novák", note="otec Václava (2), syn Jana (8)")   # 8 v P není – nic
        P[5] = dict(n="Anna Malá", f=["matka Václava (2)", "* 1850 Holice čp. 12 (1850)"])
        self.assertEqual(kekule(P), [])

    def test_spatne_cislo_predka(self):
        P = dict(self.P)
        P[9] = dict(n="Josef Novák", note="otec Václava (2)")   # měl být 4
        P[2] = dict(n="Václav Novák", note="syn Anny Malé (5)")   # 5 je matka osoby 2? ne, 2 má rodiče 4 a 5 – sedí
        w = kekule(P)
        self.assertEqual(len(w), 1)
        self.assertIn("osoba 9", w[0])
        self.assertIn("dítě má mít číslo 4", w[0])

    def test_dite_s_jinym_cislem(self):
        P = dict(self.P)
        P[2] = dict(n="Václav Novák", note="syn Josefa Nováka (40)")
        P[40] = dict(n="Josef Novák")
        self.assertIn("rodiče mají čísla 4 a 5", kekule(P)[0])

    def test_jine_jmeno_nebo_opakovany_predek(self):
        P = dict(self.P)
        P[9] = dict(n="Josef Novák", note="otec Karla (2)")   # jiné jméno – číslo nejspíš něco jiného
        self.assertEqual(kekule(P), [])
        P[9] = dict(n="Josef Novák", note="otec Václava (2)")
        self.assertEqual(kekule(P, {4: 9}), [])   # osoba 9 je v rodokmenu i jako 4


class ResearchLogStatsTests(unittest.TestCase):
    def test_counts_numeric_and_text_identifiers(self):
        contents = "\n".join(
            (
                "| # | datum | zdroj |",
                "|---|---|---|",
                "| 1 | datum | zdroj |",
                "| BA-1 | datum | zdroj |",
                "| KA-1 | datum | zdroj |",
                "| STR-10 | datum | zdroj |",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "research_log.md"
            path.write_text(contents, encoding="utf-8")
            self.assertEqual(research_log_stats(str(path)), (4, []))

    def test_reports_duplicate_identifiers_case_insensitively(self):
        contents = "| BA-1 | a |\n| ba-1 | b |\n| 2 | c |\n| 2 | d |"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "research_log.md"
            path.write_text(contents, encoding="utf-8")
            self.assertEqual(research_log_stats(str(path)), (4, ["2", "BA-1"]))

    def test_missing_log_has_zero_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(research_log_stats(str(Path(tmp) / "missing.md")), (0, []))


if __name__ == "__main__":
    unittest.main()
