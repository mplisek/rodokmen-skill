"""Fronta úkolů k rozhodnutí (analyza/navrh-router-uloh.md, S-003): úkol musí mít otázku, možnosti a výchozí postup; kontrola varuje u starých
úkolů bez struktury a u úkolů, které vypadají jako práce (ověřit, zkontrolovat, porovnat…), ne jako rozhodnutí. Ostatní fronty se nemění."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402

PLNE = ["--otazka", "Je příjmení Vzor, nebo Wzor?", "--moznosti", "A) Vzor; B) Wzor", "--vychozi", "zapsat Vzor jako prob",
        "--dukazy", "zápis sn. 54", "--zkuseno", "druhé čtení naslepo", "--doporuceni", "A"]


class FronteRozhodnuti(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        return fronta.main(list(a))

    def soubor(self, nazev="ukoly_k_rozhodnuti.md"):
        p = self.data / nazev
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def odmitne(self, *a):
        pred = self.soubor()
        with self.assertRaises(SystemExit) as cm:
            self.run_(*a)
        self.assertEqual(self.soubor(), pred, "odmítnutý úkol nesmí nic změnit")
        return str(cm.exception)

    def test_uplny_ukol_se_zalozi_s_polozkami_v_textu(self):
        self.run_("pridej", "rozhodnuti", "--p", "P2", *PLNE)
        t = self.soubor()
        for s in ("Otázka: Je příjmení Vzor", "Možnosti: A) Vzor; B) Wzor", "Výchozí postup: zapsat Vzor", "Důkazy: zápis sn. 54",
                  "Zkoušeno: druhé čtení naslepo", "Doporučení: A"):
            self.assertIn(s, t)

    def test_text_bez_struktury_se_odmitne(self):
        zprava = self.odmitne("pridej", "rozhodnuti", "--text", "potvrdit, že matkou je druhá žena")
        for s in ("Otázka", "Možnosti", "Výchozí postup"):
            self.assertIn(s, zprava)

    def test_chybi_vychozi_postup(self):
        self.assertIn("Výchozí postup", self.odmitne("pridej", "rozhodnuti", "--otazka", "Q?", "--moznosti", "A; B"))

    def test_jedna_moznost_nestaci(self):
        self.assertIn("Možnosti", self.odmitne("pridej", "rozhodnuti", "--otazka", "Q?", "--moznosti", "jen A", "--vychozi", "x"))

    def test_strukturovany_text_pres_text_projde(self):
        self.run_("pridej", "rozhodnuti", "--text", "Otázka: Jet automaticky?\nMožnosti: A) automaticky; B) ručně\nVýchozí postup: ručně")
        self.assertIn("Otázka: Jet automaticky?", self.soubor())

    def test_ostatni_fronty_se_nemeni(self):
        self.run_("pridej", "noc", "--text", "obyčejný úkol bez struktury")
        self.assertIn("obyčejný úkol", self.soubor("ukoly_na_noc.md"))

    def test_presun_do_rozhodnuti_vyzaduje_strukturu(self):
        self.run_("pridej", "noc", "--text", "volný text úkolu")
        pred = self.soubor("ukoly_na_noc.md")
        with self.assertRaises(SystemExit):
            self.run_("presun", "U-0001", "rozhodnuti")
        self.assertEqual(self.soubor("ukoly_na_noc.md"), pred)
        self.assertEqual(self.soubor(), "")
        self.run_("uprav", "U-0001", "--text", "Otázka: Q?\nMožnosti: A; B\nVýchozí postup: A")
        self.run_("presun", "U-0001", "rozhodnuti")
        self.assertIn("U-0001", self.soubor())

    def kontrola(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = self.run_("kontrola")
        return kod, out.getvalue()

    def test_kontrola_varuje_u_stareho_ukolu_bez_struktury(self):
        (self.data / "ukoly_k_rozhodnuti.md").write_text("# R\n\n## U-0001 | P3 | stav:otevřeno\n\nPotvrdit opravu dat.\n", encoding="utf-8")
        kod, out = self.kontrola()
        self.assertEqual(kod, 0, out)                       # varování, ne chyba: stávající projekty nesmí spadnout
        self.assertIn("U-0001", out)
        self.assertIn("povinná pole", out)

    def test_kontrola_varuje_u_ukolu_ktery_vypada_jako_prace(self):
        self.run_("pridej", "rozhodnuti", "--otazka", "Ověřit, že oprava osoby je správná", "--moznosti", "A) ano; B) ne", "--vychozi", "nechat")
        kod, out = self.kontrola()
        self.assertEqual(kod, 0, out)
        self.assertIn("není rozhodnutí", out)

    def test_dobre_rozhodnuti_nevaruje(self):
        self.run_("pridej", "rozhodnuti", *PLNE)
        kod, out = self.kontrola()
        self.assertNotIn("povinná pole", out)
        self.assertNotIn("není rozhodnutí", out)


if __name__ == "__main__":
    unittest.main()
