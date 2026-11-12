"""Fronty úkolů: parser, slučování duplicit, třídění, mazání podle cíle, režim podle času, zámek běhu."""
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402


class Fronty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)
        (self.data / "osoby.py").write_text('P = {5: dict(n="A", f=["* 1. 2. 1800 Obec"]), 6: dict(n="B", f=["× asi 1820"])}\n', encoding="utf-8")

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        return fronta.main(list(a))

    def test_pridej_a_trideni(self):
        self.run_("pridej", "noc", "--text", "druhý", "--p", "P3", "--os", "1", "--typ", "umrti")
        self.run_("pridej", "noc", "--text", "první", "--p", "P1", "--os", "2", "--typ", "krest")
        _, uk = fronta.nacti("noc")
        self.assertEqual([u.p for u in uk], ["P1", "P3"])
        self.assertEqual([u.id for u in uk], ["U-0002", "U-0001"])

    def test_duplicita_se_doplni(self):
        self.run_("pridej", "noc", "--text", "křest Anny", "--p", "P2", "--os", "7", "--typ", "krest", "--cil", "krest:7")
        self.run_("pridej", "badani", "--text", "ověřit na portálu", "--p", "P1", "--os", "7,8", "--typ", "krest")
        self.assertEqual(fronta.nacti("badani")[1], [])
        _, uk = fronta.nacti("noc")
        self.assertEqual(len(uk), 1)
        self.assertEqual((uk[0].p, uk[0].os), ("P1", ["7", "8"]))
        self.assertIn("ověřit na portálu", uk[0].text)

    def test_hotovo_podle_cile_a_presun(self):
        self.run_("pridej", "noc", "--text", "a", "--os", "1", "--typ", "krest", "--cil", "krest:1")
        self.run_("pridej", "noc", "--text", "b", "--os", "2", "--typ", "umrti", "--cil", "umrti:2")
        self.run_("presun", "U-0002", "rodina")
        self.assertEqual([u.id for u in fronta.nacti("rodina")[1]], ["U-0002"])
        self.assertEqual([u.id for u in fronta.nacti("noc")[1]], ["U-0001"])
        self.run_("hotovo", "--cil", "krest:1")
        self.assertEqual(fronta.nacti("noc")[1], [])

    def test_kontrola_cile_v_datech(self):
        self.assertTrue(fronta.cil_splnen("krest:5"))
        self.assertFalse(fronta.cil_splnen("snatek:6"))   # „× asi 1820“ nemá úplné datum

    def test_rezim_podle_casu(self):
        r = dict(fronta.VYCHOZI_REZIM, svatky=["2026-11-17"])
        f = datetime.datetime.fromisoformat
        self.assertEqual(fronta.rezim_v(f("2026-11-12 12:00"), r)[0], "pracovni")
        self.assertEqual(fronta.rezim_v(f("2026-11-12 23:50"), r), ("noc", f("2026-11-13 06:00")))
        self.assertEqual(fronta.rezim_v(f("2026-11-13 23:00"), r), ("vikend", f("2026-11-16 06:00")))
        self.assertEqual(fronta.rezim_v(f("2026-11-16 23:00"), r), ("vikend", f("2026-11-18 06:00")))   # svátek 17. 11.

    def test_zamek_nepusti_druhy_druh_behu(self):
        self.run_("zamek", "start", "badani")
        with self.assertRaises(SystemExit):
            self.run_("zamek", "start", "skill")
        self.run_("zamek", "stop")
        self.run_("zamek", "start", "skill")
        self.assertEqual(json.loads((self.data / ".beh.json").read_text(encoding="utf-8"))["typ"], "skill")


if __name__ == "__main__":
    unittest.main()
