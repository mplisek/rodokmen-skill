"""tools/zadani.py (analyza/navrh-optimalizace.md, E1; scénáře 2 a 5): zadání pro čtenáře jako zkontrolovaný soubor, rozšíření rozsahu jako
schválené pokračování téhož úkolu. Chybné zadání se nezapíše. Bez sítě, dočasný projekt."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import vysledek  # noqa: E402
import zadani  # noqa: E402

NOVY = ["novy", "U-0101", "--otazka", "Najdi křest osoby 88 (rodiče, kmotři).", "--hleda", "křtěnec", "--osoba", "88:křtěnec:* asi 1812, čp. 5",
        "--svazek", "0a1b2c3d", "--snimky", "40-52", "--vratit", "datum,otec,matka,kmotri", "--strop", "12,12",
        "--nezamenit", "josef-vzorny-1809:* 1809, otec mlynář"]


class Zadani(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.stare = vysledek.ROOT
        vysledek.ROOT = str(self.root)
        (self.root / "data").mkdir()
        (self.root / "data" / "osoby.py").write_text('P = {88: dict(n="A")}\nRODINA = {"josef-vzorny-1809": dict(n="B")}\n', encoding="utf-8")
        (self.root / "data" / "svazky.json").write_text(json.dumps({
            "0a1b2c3d": {"svazek": "sign.: 712"}, "0e0e0e0e": {"svazek": "sign.: 759", "pokryva": {"role": ["ženich"]}}}), encoding="utf-8")

    def tearDown(self):
        vysledek.ROOT = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = zadani.main(list(a))
        self.out = out.getvalue()
        return kod

    def soubor(self):
        return json.loads((self.root / "pracovni" / "zadani" / "U-0101.json").read_text(encoding="utf-8"))

    def test_nove_zadani_projde_kontrolou_a_rekne_kam_psat(self):
        self.assertEqual(self.run_(*NOVY), 0)
        d = self.soubor()
        self.assertEqual(vysledek.over_zadani(d), [])
        self.assertEqual((d["osoby"][0]["id"], d["rozsah"]["snimky"], d["strop"]), ("88", [40, 52], {"kroku": 12, "snimku": 12}))
        self.assertEqual(d["nezamenit_s"][0]["id"], "josef-vzorny-1809")
        self.assertIn("pracovni/zadani/U-0101.json", self.out)
        self.assertIn("pracovni/vysledky/U-0101.json", self.out)

    def test_chybne_zadani_se_nezapise(self):
        for zmena in (("--svazek", "712"), ("--osoba", "Josef Vzorný:křtěnec"), ("--hleda", "dítě")):
            a = list(NOVY)
            a[a.index(zmena[0]) + 1] = zmena[1]
            with self.assertRaises(SystemExit) as cm:
                self.run_(*a)
            self.assertIn("ODMÍTNUTO", str(cm.exception))
            self.assertFalse((self.root / "pracovni" / "zadani" / "U-0101.json").exists())

    def test_pramen_ktery_roli_nevede_se_odmitne_pred_spustenim_ctenare(self):
        a = list(NOVY)
        a[a.index("--svazek") + 1] = "0e0e0e0e"
        a[a.index("--hleda") + 1] = "nevěsta"
        with self.assertRaises(SystemExit) as cm:
            self.run_(*a)
        self.assertIn("vede jen: ženich", str(cm.exception))

    def test_existujici_zadani_se_neprepise_bez_volby(self):
        self.run_(*NOVY)
        with self.assertRaises(SystemExit):
            self.run_(*NOVY)
        self.assertEqual(self.run_(*NOVY, "--prepis"), 0)

    def test_rozsireni_je_pokracovani_tehoz_ukolu(self):
        self.run_(*NOVY)
        self.assertEqual(self.run_("rozsir", "U-0101", "--snimky", "53", "--duvod", "řádek pokračuje vpravo", "--vratit", "kmotri"), 0)
        d = self.soubor()
        self.assertEqual(d["rozsireni"], [{"snimky": [53, 53], "duvod": "řádek pokračuje vpravo", "vratit": ["kmotri"]}])
        self.assertEqual(d["rozsah"]["snimky"], [40, 52])                       # původní zadání se nemění
        nalez = dict(vysledek.VZORY["nalez"], prohledano=[{"svazek": "0a1b2c3d", "snimky": [53, 53], "uplne": True}], cast=2)
        self.assertEqual(vysledek.over_nalez(nalez, d), [])                     # čtenář smí číst rozšířený rozsah

    def test_rozsireni_bez_zadani(self):
        with self.assertRaises(SystemExit):
            self.run_("rozsir", "U-0101", "--snimky", "53", "--duvod", "x")


if __name__ == "__main__":
    unittest.main()
