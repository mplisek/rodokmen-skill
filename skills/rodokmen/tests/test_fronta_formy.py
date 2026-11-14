"""fronta.py: jednotné názvy front ukoly_* (nikdy se nečtou při sestavení webu), zpětná kompatibilita se starými názvy,
příkaz prejmenuj, závislosti mezi úkoly (zavisi) a výběr úkolů, jejichž závislosti jsou hotové (frontier).
Rozhraní: příkazy fronta.py a soubory ve složce data. Dočasná složka, bez sítě."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402


class NazvyFront(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)
        (self.data / "osoby.py").write_text("P = {}\n", encoding="utf-8")

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        return fronta.main(list(a))

    def test_nove_nazvy_front(self):
        self.assertEqual(Path(fronta.cesta("rodina")).name, "ukoly_na_rodinu.md")
        self.assertEqual(Path(fronta.cesta("dotazy")).name, "ukoly_dotazy_na_archivy.md")
        self.run_("pridej", "rodina", "--text", "ptát se rodiny", "--os", "1")
        self.assertTrue((self.data / "ukoly_na_rodinu.md").exists())
        self.assertFalse((self.data / "otazky_pro_rodinu.md").exists())

    def test_stary_nazev_se_dal_cte_a_zapisuje_do_prejmenovani(self):
        (self.data / "archivni_dotazy.md").write_text("# D\n\n## U-0001 | P2 | typ:krest | stav:otevřeno\nstarý úkol\n", encoding="utf-8")
        self.assertEqual([u.id for u in fronta.nacti("dotazy")[1]], ["U-0001"])
        self.run_("pridej", "dotazy", "--text", "druhý", "--os", "2")
        self.assertEqual([u.id for u in fronta.nacti("dotazy")[1]], ["U-0001", "U-0002"])
        self.assertFalse((self.data / "ukoly_dotazy_na_archivy.md").exists())      # nic se nerozdvojilo

    def test_prejmenuj_prevede_stare_nazvy(self):
        (self.data / "archivni_dotazy.md").write_text("# D\n\n## U-0001 | P2 | stav:otevřeno\na\n", encoding="utf-8")
        (self.data / "otazky_pro_rodinu.md").write_text("# O\n\n## U-0002 | P2 | stav:otevřeno\nb\n", encoding="utf-8")
        self.assertEqual(self.run_("prejmenuj"), 0)
        self.assertTrue((self.data / "ukoly_dotazy_na_archivy.md").exists())
        self.assertTrue((self.data / "ukoly_na_rodinu.md").exists())
        self.assertFalse((self.data / "archivni_dotazy.md").exists())
        self.assertEqual([u.id for u in fronta.nacti("rodina")[1]], ["U-0002"])

    def test_prejmenuj_neprepise_existujici_novy_soubor(self):
        (self.data / "archivni_dotazy.md").write_text("# D\n\n## U-0001 | P2 | stav:otevřeno\na\n", encoding="utf-8")
        (self.data / "ukoly_dotazy_na_archivy.md").write_text("# N\n\n## U-0002 | P2 | stav:otevřeno\nb\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_("prejmenuj")
        self.assertTrue((self.data / "archivni_dotazy.md").exists())
        self.assertEqual([u.id for u in fronta.nacti("dotazy")[1]], ["U-0002"])        # nový název má přednost


class Zavislosti(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)
        (self.data / "osoby.py").write_text("P = {}\n", encoding="utf-8")

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        return fronta.main(list(a))

    def nacti(self):
        return {u.id: u for u in fronta.nacti("noc")[1]}

    def test_zavisi_se_zapise_a_precte(self):
        self.run_("pridej", "noc", "--text", "první", "--os", "1", "--typ", "a")
        self.run_("pridej", "noc", "--text", "druhý", "--os", "2", "--typ", "b", "--zavisi", "U-0001")
        text = (self.data / "ukoly_na_noc.md").read_text(encoding="utf-8")
        self.assertIn("zavisi:U-0001", text)
        self.assertEqual(self.nacti()["U-0002"].zavisi, ["U-0001"])
        self.run_("uprav", "U-0002", "--zavisi", "")
        self.assertEqual(self.nacti()["U-0002"].zavisi, [])

    def test_frontier_jen_hotove_zavislosti(self):
        self.run_("pridej", "noc", "--text", "první", "--os", "1", "--typ", "a", "--p", "P3")
        self.run_("pridej", "noc", "--text", "druhý", "--os", "2", "--typ", "b", "--p", "P1", "--zavisi", "U-0001")
        self.assertEqual([u.id for u in fronta.frontier(fronta.vse())], ["U-0001"])
        self.run_("hotovo", "U-0001")
        self.assertEqual([u.id for u in fronta.frontier(fronta.vse())], ["U-0002"])      # závislost je splněná (úkol zmizel)

    def test_dalsi_preskoci_blokovany_ukol_i_s_vyssi_prioritou(self):
        self.run_("pridej", "noc", "--text", "základ", "--os", "1", "--typ", "a", "--p", "P3")
        self.run_("pridej", "noc", "--text", "navazuje", "--os", "2", "--typ", "b", "--p", "P1", "--zavisi", "U-0001")
        import io
        import contextlib
        v = io.StringIO()
        with contextlib.redirect_stdout(v):
            self.assertEqual(self.run_("dalsi", "noc", "--vzdy"), 0)
        self.assertIn("U-0001", v.getvalue())
        self.assertNotIn("U-0002", v.getvalue())

    def test_frontier_prikaz_vypise_pripravene(self):
        import io
        import contextlib
        self.run_("pridej", "noc", "--text", "první", "--os", "1", "--typ", "a")
        self.run_("pridej", "noc", "--text", "druhý", "--os", "2", "--typ", "b", "--zavisi", "U-0001")
        v = io.StringIO()
        with contextlib.redirect_stdout(v):
            self.assertEqual(self.run_("frontier"), 0)
        self.assertIn("U-0001", v.getvalue())
        self.assertNotIn("U-0002", v.getvalue())

    def test_kontrola_hlasi_zavislost_sama_na_sobe_a_cyklus(self):
        self.run_("pridej", "noc", "--text", "a", "--os", "1", "--typ", "a")
        self.run_("pridej", "noc", "--text", "b", "--os", "2", "--typ", "b", "--zavisi", "U-0001")
        self.run_("uprav", "U-0001", "--zavisi", "U-0002")
        self.assertNotEqual(self.run_("kontrola"), 0)


if __name__ == "__main__":
    unittest.main()
