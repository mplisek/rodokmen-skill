"""Čekání, odesílání ven a typy úkolů (analyza/navrh-router-uloh.md, S-008, S-009, S-010): přehled čekajících odděleně od úkolů k řešení,
`odeslano` jen na pokyn uživatele (dotazy a otázky pro rodinu odesílá člověk), úkoly pro skill se ve frontách nevedou. Bez sítě, dočasná složka dat."""
import contextlib
import datetime
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402


class Zaklad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                kod = fronta.main(list(a))
        except SystemExit as e:
            self.out = out.getvalue() + str(e)
            raise
        self.out = out.getvalue()
        return kod

    def udalosti(self):
        p = self.data / "ukoly_historie.jsonl"
        return [json.loads(r) for r in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


class Cekajici(Zaklad):
    def setUp(self):
        super().setUp()
        self.run_("pridej", "noc", "--text", "aktivní úkol", "--os", "1", "--typ", "a")
        self.run_("pridej", "noc", "--text", "zápis se zpřístupní", "--os", "2", "--typ", "b")
        self.run_("pridej", "dotazy", "--text", "odpověď archivu", "--os", "3", "--typ", "c")
        self.run_("zaparkuj", "U-0002", "--do", "2999-06-01", "--duvod", "zpřístupnění 2999")
        self.run_("zaparkuj", "U-0003", "--do", "2999-01-01", "--duvod", "odpověď archivu")

    def test_cekajici_serazene_podle_data_s_duvodem(self):
        self.run_("cekajici")
        r = [x for x in self.out.splitlines() if x.startswith("2999")]
        self.assertEqual([x.split()[0] for x in r], ["2999-01-01", "2999-06-01"])
        self.assertIn("U-0003", r[0])
        self.assertIn("zpřístupnění 2999", self.out)
        self.assertNotIn("U-0001", self.out)

    def test_seznam_standardne_ceka_jen_v_pocitadle(self):
        self.run_("seznam")
        self.assertIn("U-0001", self.out)
        self.assertNotIn("U-0002", self.out)
        self.assertIn("čeká 2", self.out)
        self.assertIn("fronta.py cekajici", self.out)
        self.run_("seznam", "--vse")
        self.assertIn("U-0002", self.out)

    def test_ukol_kteremu_datum_uplynulo_je_zase_v_seznamu(self):
        self.run_("zaparkuj", "U-0002", "--do", "2000-01-01")
        self.run_("seznam")
        self.assertIn("U-0002", self.out)
        self.run_("cekajici")
        self.assertNotIn("U-0002", self.out)


class Odeslano(Zaklad):
    def setUp(self):
        super().setUp()
        self.run_("pridej", "dotazy", "--text", "dotaz do archivu", "--os", "1", "--typ", "a")
        self.run_("pridej", "rodina", "--text", "otázka pro rodinu", "--os", "2", "--typ", "b")
        self.run_("pridej", "noc", "--text", "noční úkol", "--os", "3", "--typ", "c")

    def test_odeslano_vyzaduje_uzivatele_a_nastavi_cekani(self):
        with self.assertRaises(SystemExit):
            self.run_("odeslano", "U-0001")                              # bez toho, kdo odeslání potvrdil
        self.assertEqual(fronta.nacti("dotazy")[1][0].stav, "otevřeno")
        self.run_("odeslano", "U-0001", "--uzivatel", "správce webu")
        u = fronta.nacti("dotazy")[1][0]
        dnes = datetime.date.today()
        self.assertEqual(u.stav, "čeká")
        self.assertEqual(u.do, (dnes + datetime.timedelta(days=30)).isoformat())
        self.assertIn(f"Odesláno: {dnes.isoformat()}", u.text)
        e = [x for x in self.udalosti() if x["udalost"] == "odeslano"][0]
        self.assertEqual((e["id"], e["potvrdil"]), ("U-0001", "správce webu"))

    def test_vlastni_termin_odpovedi_a_rezim_json(self):
        self.run_("odeslano", "U-0002", "--uzivatel", "správce", "--odpoved-do", "2999-03-01")
        self.assertEqual(fronta.nacti("rodina")[1][0].do, "2999-03-01")
        (self.data / "rezim.json").write_text(json.dumps({"odpoved_dnu": 10}), encoding="utf-8")
        self.run_("pridej", "dotazy", "--text", "další dotaz", "--os", "9", "--typ", "z")
        self.run_("odeslano", "U-0004", "--uzivatel", "správce")
        self.assertEqual(fronta.nacti("dotazy")[1][-1].do, (datetime.date.today() + datetime.timedelta(days=10)).isoformat())

    def test_jen_dotazy_a_rodina(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_("odeslano", "U-0003", "--uzivatel", "správce")
        self.assertIn("dotazy", str(cm.exception))
        self.assertEqual(fronta.nacti("noc")[1][0].stav, "otevřeno")


class TypyUkolu(Zaklad):
    def test_ukoly_pro_skill_se_ve_frontach_nevedou(self):
        for typ in ("skill", "test", "údržba"):
            with self.assertRaises(SystemExit) as cm:
                self.run_("pridej", "noc", "--text", "x", "--typ", typ)
            self.assertIn("poznamky_pro_skill.md", str(cm.exception))
            self.assertIn("ukoly_na_skill.md", str(cm.exception))
        self.assertEqual(fronta.nacti("noc")[1], [])
        self.run_("pridej", "noc", "--text", "x", "--typ", "krest")
        with self.assertRaises(SystemExit):
            self.run_("uprav", "U-0001", "--typ", "skill")

    def test_kontrola_varuje_u_stareho_ukolu_typu_skill(self):
        (self.data / "ukoly_na_noc.md").write_text("# N\n\n## U-0001 | P2 | typ:skill | stav:otevřeno\n\nstará úprava skillu\n", encoding="utf-8")
        self.run_("kontrola")
        self.assertIn("U-0001", self.out)
        self.assertIn("typ skill", self.out)


if __name__ == "__main__":
    unittest.main()
