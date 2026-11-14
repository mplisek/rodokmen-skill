"""Stránka Předci (template/web/src/pages/predci.astro): sloupec Rod používá jednotnou značku <Rod> (jeden kruh, ne vlastní kruh + název,
který znackuj_rody.py ještě jednou obalí značkou), a dlouhý název rodu se nezalamuje přes sloupec Stav (buňka se smí zalomit, sloupec je dost široký)."""
import re
import unittest
from pathlib import Path

PREDCI = Path(__file__).resolve().parents[1] / "template" / "web" / "src" / "pages" / "predci.astro"


class PredciRod(unittest.TestCase):
    def setUp(self):
        self.src = PREDCI.read_text(encoding="utf-8")

    def test_rod_je_jednotna_znacka_a_ne_vlastni_kruh(self):
        self.assertIn("<Rod ", self.src)
        self.assertRegex(self.src, r"import Rod from '\.\./components/Rod\.astro'")
        self.assertNotIn('class="dot"', self.src)

    def test_bunka_rodu_se_nezalamuje_do_sloupce_stav(self):
        radek = next(r for r in self.src.splitlines() if "<Rod " in r)
        self.assertNotIn("nowrap", radek)

    def test_sloupec_rodu_je_dost_siroky_na_dlouhy_nazev(self):
        m = re.search(r"col\.c-rod\s*\{\s*width:\s*([\d.]+)rem", self.src)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(float(m.group(1)), 11)


if __name__ == "__main__":
    unittest.main()
