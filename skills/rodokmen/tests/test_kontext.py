"""kontext.py (Fáze C, Q-C3): deterministický kontextový balíček osoby a pravidel vybraných podle témat. Rozhraní: příkazová řádka
(--osoba, --tema, --limit, --rules, --data) nad dočasnou složkou dat a pravidel s vymyšleným obsahem. Bez sítě."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

OSOBY = """P = {
 1: {'n': 'Jan Vymyšlený', 'y': '1890–1944', 'st': 'doc', 'f': ['* 1890 Holice čp. 5'], 'r': ['krest_jan_1890']},
 2: {'n': 'Marie Vymyšlená', 'y': '1895–1972', 'st': 'prob', 'f': ['* 1895 Dolní'], 'note': 'rok podle věku'},
}
ISSUES = [
 dict(k=1, otazka="Odkud přišel Jan?", stav="otevřené", text="Před začátkem matrik."),
 dict(k=1, otazka="Starý dotaz?", stav="vyřešené", text="Vyřešeno."),
 dict(k=2, otazka="Kdo byl otec Marie?", stav="otevřené", text="Není uveden."),
]
"""
ZAZNAMY = '[{"klic": "krest_jan_1890", "svazek": "s1", "snimek": 57, "druh": "N", "datum": "14. 2. 1890", "nazev": "Křest Jana", "shrnuti": "Jan, syn Václava."}]'
PRAVIDLA_A = "# A\n\n## R-ID-001\nwhen: dva stejného jména\ndo: spojit jen na dva znaky\nwhy: chyba\nsource: fork\n"
PRAVIDLA_B = "# B\n\n## R-BOOK-001\nwhen: hledání knihy\ndo: hledat ves\nwhy: farnost nemusí být správná\nsource: fork\n"


class Kontext(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        t = Path(self._tmp.name)
        self.data, self.rules = t / "data", t / "rules"
        self.data.mkdir()
        self.rules.mkdir()
        (self.data / "osoby.py").write_text(OSOBY, encoding="utf-8")
        (self.data / "zaznamy.json").write_text(ZAZNAMY, encoding="utf-8")
        (self.data / "ukoly_dotazy_na_archivy.md").write_text("# D\n\n## U-0001\nTAJNÝ-TEXT-FRONTY\n", encoding="utf-8")
        (self.data / "verejne_otazky.json").write_text('[{"otazka": "TAJNÁ-VEŘEJNÁ-OTÁZKA"}]', encoding="utf-8")
        (self.rules / "identity.md").write_text(PRAVIDLA_A, encoding="utf-8")
        (self.rules / "books.md").write_text(PRAVIDLA_B, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def kontext(self, *args):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontext.py"), "--rules", str(self.rules),
                               "--data", str(self.data), *args], capture_output=True, text=True, encoding="utf-8")

    def test_balicek_obsahuje_osobu_zapisy_otazky_a_vybrana_pravidla(self):
        r = self.kontext("--osoba", "1", "--tema", "identity")
        self.assertEqual(r.returncode, 0, r.stderr)
        for text in ("Jan Vymyšlený", "* 1890 Holice čp. 5", "Křest Jana", "Odkud přišel Jan?", "R-ID-001", "spojit jen na dva znaky"):
            self.assertIn(text, r.stdout)

    def test_jen_otevrene_otazky_jen_teto_osoby(self):
        out = self.kontext("--osoba", "1", "--tema", "identity").stdout
        self.assertNotIn("Starý dotaz?", out)         # vyřešená
        self.assertNotIn("Kdo byl otec Marie?", out)  # jiná osoba
        self.assertNotIn("Marie Vymyšlená", out)

    def test_pravidla_jen_z_vybranych_temat(self):
        out = self.kontext("--osoba", "1", "--tema", "identity").stdout
        self.assertNotIn("R-BOOK-001", out)
        out = self.kontext("--osoba", "1", "--tema", "books,identity").stdout
        self.assertIn("R-BOOK-001", out)
        self.assertIn("R-ID-001", out)

    def test_stejny_vstup_da_stejny_vystup_bez_ohledu_na_poradi_temat(self):
        a = self.kontext("--osoba", "1", "--tema", "books,identity").stdout
        b = self.kontext("--osoba", "1", "--tema", "identity,books").stdout
        self.assertEqual(a, b)
        self.assertEqual(a, self.kontext("--osoba", "1", "--tema", "books,identity").stdout)

    def test_necte_fronty_ani_verejne_otazky(self):
        out = self.kontext("--osoba", "1", "--tema", "identity").stdout
        self.assertNotIn("TAJNÝ-TEXT-FRONTY", out)
        self.assertNotIn("TAJNÁ-VEŘEJNÁ-OTÁZKA", out)

    def test_neznamé_tema_je_chyba_s_vypisem_platnych(self):
        r = self.kontext("--osoba", "1", "--tema", "neexistuje")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("identity", r.stderr + r.stdout)
        self.assertIn("books", r.stderr + r.stdout)

    def test_neznama_osoba_je_chyba(self):
        r = self.kontext("--osoba", "99", "--tema", "identity")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("99", r.stderr + r.stdout)

    def test_limit_se_nikdy_neorezava_mlcky(self):
        r = self.kontext("--osoba", "1", "--tema", "identity", "--limit", "50")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("limit", (r.stderr + r.stdout).lower())
        self.assertEqual(r.stdout.strip(), "")        # žádný ořezaný balíček
        self.assertEqual(self.kontext("--osoba", "1", "--tema", "identity", "--limit", "20000").returncode, 0)

    def test_nic_nezapisuje(self):
        pred = sorted((p.name, p.stat().st_size) for p in self.data.iterdir())
        self.kontext("--osoba", "1", "--tema", "identity")
        self.assertEqual(pred, sorted((p.name, p.stat().st_size) for p in self.data.iterdir()))


if __name__ == "__main__":
    unittest.main()
