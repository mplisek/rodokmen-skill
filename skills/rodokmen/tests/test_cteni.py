"""tools/cteni.py: první a kontrolní čtení po pevných polích; shoda po normalizaci = ověřeno, neshoda = spor pro uživatele
v pracovni/sporna_cteni.json (žádné třetí čtení). Analyza/zjednoduseni-badani.md, 3.1 a 3.2. Bez sítě, vymyšlené hodnoty."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402


class Cteni(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        (self.p / "tools").mkdir()
        (self.p / "pracovni").mkdir()
        shutil.copy(TOOLS / "cteni.py", self.p / "tools" / "cteni.py")

    def tearDown(self):
        self._tmp.cleanup()

    def cteni(self, *a):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "cteni.py"), *a], cwd=self.p,
                              capture_output=True, text=True, encoding="utf-8")

    def dvojice(self, prvni, druhe, druh="Z", necitelne=()):
        for n, pole in ((1, prvni), (2, druhe)):
            d = {"klic": "lhota_umrti_test_1856", "druh": druh, "pole": pole}
            if n == 2 and necitelne:
                d["necitelne"] = list(necitelne)
            (self.p / "pracovni" / f"c{n}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return self.cteni("porovnej", "pracovni/c1.json", "pracovni/c2.json")

    def spory(self):
        p = self.p / "pracovni" / "sporna_cteni.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

    def test_shoda_po_normalizaci_je_overeno(self):
        r = self.dvojice({"datum_umrti": "31. Maji 1856", "vek": "80 let", "dum": "č. 12", "jmeno": "Wenceslaus Vzorny"},
                         {"datum_umrti": "31. května 1856", "vek": "80", "dum": "čp. 12", "jmeno": "Venceslaus Vzorny"})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ověřený", r.stdout)
        self.assertIn('"overeno": "kontrolni-cteni"', r.stdout)                         # kam zapsat výsledek (18. 11. 2026)
        self.assertIn("--overeno", r.stdout)
        self.assertEqual(self.spory(), [])

    def test_neshoda_jde_do_davky_sporu_pro_uzivatele(self):
        r = self.dvojice({"dum": "12", "vek": "80"}, {"dum": "2", "vek": "80"})
        self.assertEqual(r.returncode, 1, r.stdout)
        s = self.spory()
        self.assertEqual([(x["pole"], x["moznosti"]) for x in s], [("dum", ["12", "2"])])
        self.assertEqual(s[0]["vyrez"], "vyrezy/lhota_umrti_test_1856.jpg")
        self.dvojice({"dum": "12"}, {"dum": "2"})                                        # podruhé spor nezdvojí
        self.assertEqual(len(self.spory()), 1)

    def test_kratsi_prepis_a_necitelne_pole_jsou_spor(self):
        r = self.dvojice({"jmeno": "Josef Vzorny vejminkar", "pricina": "zimnice"}, {"jmeno": "Josef Vzorny"},
                         necitelne=("pricina",))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(sorted(x["pole"] for x in self.spory()), ["jmeno", "pricina"])

    def test_prazdne_v_obou_a_jen_otaznik_nejsou_spor(self):
        """Poznámka z bádání 18. 11. 2026: údaj, který zápis nevede (obě čtení prázdná), a hodnota lišící se jen „(?)“."""
        r = self.dvojice({"datum_pohrbu": None, "pricina": "", "dum": "12 (?)", "vek": "80"},
                         {"datum_pohrbu": None, "pricina": "–", "dum": "12", "vek": "80"})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("nevede se", r.stdout)
        self.assertIn("shoda, nejisté", r.stdout)
        self.assertEqual(self.spory(), [])
        r = self.dvojice({"datum_pohrbu": None}, {"datum_pohrbu": "2. 6. 1856"})            # jen v jednom čtení = spor
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_cizi_pole_a_jiny_zapis_se_odmitnou(self):
        self.assertEqual(self.dvojice({"krestni_jmeno": "Jan"}, {"krestni_jmeno": "Jan"}).returncode, 2)
        self.assertEqual(self.dvojice({"dite": "Jan"}, {"dite": "Jan"}, druh="X").returncode, 2)
        self.assertEqual(self.spory(), [])

    def test_vzor_ma_pevna_pole_druhu(self):
        d = json.loads(self.cteni("vzor", "N").stdout)
        self.assertIn("kmotri", d["pole"])
        self.assertEqual(self.cteni("vzor", "X").returncode, 2)


if __name__ == "__main__":
    unittest.main()
