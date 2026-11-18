"""Rody začínají dědečkem po mužské linii (děd 4, 6 patří do rodu svého otce 8, 12 a je jeho výchozí osobou),
u babiček (5, 7) rod začíná až u jejich rodičů (10, 11, 14, 15) – babičky samy do žádného rodu nepatří."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402


class RodZacinaDedeckem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls.tmp.name)
        novy_projekt(cls.p, "--ukazka")
        spust(cls.p, "export_web.py")
        cls.site = json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def osoba(self, k):
        return next(p for p in self.site["people"].values() if p["k"] == k)

    def rod(self, k):
        return next(l for l in self.site["lines"].values() if l["k"] == k)

    def test_dedove_patri_do_rodu_otce(self):
        for ded, otec in ((4, 8), (6, 12)):
            o = self.osoba(ded)
            self.assertEqual(o["lineSlug"], self.rod(otec)["slug"], f"děd {ded}")
            self.assertIn(o["slug"], self.rod(otec)["people"])

    def test_rod_zacina_dedeckem(self):
        for ded, otec in ((4, 8), (6, 12)):
            self.assertEqual(self.rod(otec)["root"], self.osoba(ded)["slug"])

    def test_babicky_nemaji_rod(self):
        for k in (5, 7):
            self.assertIsNone(self.osoba(k)["lineSlug"], f"babička {k}")

    def test_rody_prababicek_a_pradedecku_beze_zmeny(self):
        for k in (9, 10, 11, 13, 14, 15):
            self.assertEqual(self.rod(k)["root"], self.osoba(k)["slug"], f"rod {k}")


if __name__ == "__main__":
    unittest.main()
