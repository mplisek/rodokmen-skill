"""tools/svazky.py: svazek do katalogu data/svazky.json ze souboru v pracovni/, bez sítě. Pro portály, kam skript nesmí (ZAKAZ v slusne.py),
jiná cesta není: čtenář v prohlížeči opíše údaje o svazku, badatel je zapíše tímto nástrojem (podnět z bádání 16. 11. 2026: zadani.py
svazek mimo katalog odmítne). Dočasný projekt, bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

SVAZEK = {"klic": "ebad_99999", "archiv": "SOA Praha – Sbírka matrik", "portal": "eBadatelna", "svazek": "Ukázka 12, N 1784–1850",
          "url": "https://ebadatelna.soapraha.cz/pages/MatrikaPage/matrikaId/99999", "snimku": 120, "popis": "Ukázkov",
          "pokryva": {"role": ["křtěnec", "otec", "matka", "kmotr"]}}


class Svazky(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "p"
        r = novy_projekt(cls.root)
        assert r.returncode == 0, r.stdout + r.stderr
        (cls.root / "pracovni").mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def soubor(self, jmeno, obsah):
        p = self.root / "pracovni" / jmeno
        p.write_text(json.dumps(obsah, ensure_ascii=False), encoding="utf-8")
        return f"pracovni/{jmeno}"

    def katalog(self):
        p = self.root / "data" / "svazky.json"
        return json.loads(p.read_text(encoding="utf-8-sig")) if p.exists() else {}

    def test_pridej_overi_a_zapise_bez_klice_v_zaznamu(self):
        r = spust(self.root, "svazky.py", "pridej", self.soubor("s1.json", SVAZEK), check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = self.katalog()["ebad_99999"]
        self.assertEqual(z["pokryva"]["role"], ["křtěnec", "otec", "matka", "kmotr"])
        self.assertNotIn("klic", z)
        r = spust(self.root, "svazky.py", "pridej", self.soubor("s1b.json", SVAZEK), check=False)   # podruhé bez --doplnit ne
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("už je", r.stdout + r.stderr)

    def test_doplnit_jen_pridava_pole(self):
        zaklad = dict(SVAZEK, klic="ebad_88888", url="https://ebadatelna.soapraha.cz/pages/MatrikaPage/matrikaId/88888")
        zaklad.pop("pokryva")
        self.assertEqual(spust(self.root, "svazky.py", "pridej", self.soubor("s2.json", zaklad), check=False).returncode, 0)
        r = spust(self.root, "svazky.py", "pridej", self.soubor("s2b.json", {"klic": "ebad_88888", "pokryva": {"role": ["ženich", "nevěsta"]}}),
                  "--doplnit", check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = self.katalog()["ebad_88888"]
        self.assertEqual(z["pokryva"]["role"], ["ženich", "nevěsta"])
        self.assertEqual(z["snimku"], 120)                       # ostatní pole zůstala

    def test_chybny_vstup_nic_nezapise(self):
        pred = self.katalog()
        spatne = [
            dict(SVAZEK, klic="Ebad 1"),                                        # klíč jen malá písmena, číslice, podtržítko
            {k: v for k, v in SVAZEK.items() if k != "url"} | {"klic": "ebad_77777"},   # chybí adresa
            dict(SVAZEK, klic="ebad_77777", url="http://jinde.example/x"),       # jen https
            dict(SVAZEK, klic="ebad_77777", snimku=0),
            dict(SVAZEK, klic="ebad_77777", pokryva={"role": ["kmotřenec"]}),   # role mimo kontrakt
            dict(SVAZEK, klic="ebad_77777", poznamka="Jan Novák * 1850"),      # neznámé pole
        ]
        for i, s in enumerate(spatne):
            r = spust(self.root, "svazky.py", "pridej", self.soubor(f"x{i}.json", s), check=False)
            self.assertNotEqual(r.returncode, 0, s)
        self.assertEqual(self.katalog(), pred)
        (self.root / "jinde.json").write_text(json.dumps(dict(SVAZEK, klic="ebad_66666")), encoding="utf-8")
        self.assertNotEqual(spust(self.root, "svazky.py", "pridej", "jinde.json", check=False).returncode, 0)   # vstup jen z pracovni/
        self.assertNotIn("ebad_66666", self.katalog())

    def test_ukaz(self):
        spust(self.root, "svazky.py", "pridej", self.soubor("s4.json", dict(SVAZEK, klic="ebad_55555")), check=False)
        r = spust(self.root, "svazky.py", "ukaz", "ebad_55555", check=False)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Ukázka 12", r.stdout)


if __name__ == "__main__":
    unittest.main()
