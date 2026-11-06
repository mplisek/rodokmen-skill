"""Osobní odkazy (tools/pozvanky.py, PR #94) s přístupy forku: odkaz patří k přístupu, brána i poznámky ho znají."""
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

PRISTUPY = [{"nazev": "Matčina rodina", "odpoved": "lipa", "koren": [3], "poznamky": True},
            {"nazev": "Marie", "odpoved": "marie-ci", "koren": ["marie-novakova"]}]


class PozvankyPristupy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls._tmp.name) / "ukazka"
        r = novy_projekt(cls.p, "--ukazka")
        assert r.returncode == 0, r.stdout + r.stderr
        cfg_path = cls.p / "data" / "web.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["pristupy"] = PRISTUPY
        cfg["prihlaseni"]["adresa"] = "https://rod.example"
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def pridej(self, *args, check=True):
        return spust(self.p, "pozvanky.py", "pridej", *args, check=check)

    @staticmethod
    def klic(vystup):
        return re.search(r"/\?k=(\S+)", vystup).group(1)

    def mapa(self, soubor, nazev):
        text = (self.p / "web" / "netlify" / soubor).read_text(encoding="utf-8")
        return json.loads(re.search(rf"const {nazev} = (\{{.*?\}});", text, re.S).group(1))

    def test_odkazy_s_pristupem_v_brane_a_poznamkach(self):
        teta = self.klic(self.pridej("Teta Jana", "--pristup", "matcina-rodina").stdout)
        stryc = self.klic(self.pridej("Strýc Karel").stdout)            # bez přístupu = celý web (vse)
        marie = self.klic(self.pridej("Marie", "--pristup", "marie").stdout)
        seznam = spust(self.p, "pozvanky.py", "seznam").stdout
        self.assertIn("(přístup matcina-rodina)", seznam)
        self.assertNotIn(teta, seznam)                                     # klíč se nikam neukládá

        r = spust(self.p, "export_web.py")
        self.assertIn("osobních odkazů 3", r.stdout)
        self.assertIn("POZOR: nginx.conf", r.stdout)
        sha = lambda k: hashlib.sha256(k.encode()).hexdigest()
        klice = self.mapa("edge-functions/brana.js", "KLICE")
        self.assertEqual(klice, {sha(teta): "matcina-rodina", sha(stryc): "vse", sha(marie): "marie"})
        self.assertNotIn(teta, (self.p / "web" / "netlify" / "edge-functions" / "brana.js").read_text(encoding="utf-8"))
        # poznámky: Matčina rodina je má zapnuté, Marie ne; vse je má, protože je má některý přístup
        pozn = self.mapa("functions/poznamky.mjs", "KLICE")
        self.assertEqual(pozn[sha(teta)], {"id": "matcina-rodina", "poznamky": True})
        self.assertEqual(pozn[sha(marie)], {"id": "marie", "poznamky": False})
        # přihlašovací stránka: otázka zůstane (přístupy mají odpovědi) a k ní rada k osobnímu odkazu
        login = (self.p / "web" / "public" / "prihlaseni.html").read_text(encoding="utf-8")
        self.assertIn('id="f"', login)
        self.assertIn("Máte osobní odkaz?", login)

        # přístup, který ve web.json není: pozvanky.py ho odmítne, export taky (ruční úprava pozvanky.json)
        r = self.pridej("Cizí", "--pristup", "neexistuje", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("neexistuje", r.stderr)
        poz = self.p / "data" / "pozvanky.json"
        data = json.loads(poz.read_text(encoding="utf-8"))
        data[0]["pristup"] = "zmizely"
        poz.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        r = spust(self.p, "export_web.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("pozvanky.py pristup p1", r.stdout + r.stderr)
        self.assertIn("vede na přístup marie", spust(self.p, "pozvanky.py", "pristup", "p1", "marie").stdout)
        spust(self.p, "export_web.py")
        self.assertEqual(self.mapa("edge-functions/brana.js", "KLICE")[sha(teta)], "marie")


if __name__ == "__main__":
    unittest.main()
