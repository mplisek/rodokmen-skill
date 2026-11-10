"""Osobní odkazy (tools/pozvanky.py, PR #94) s přístupy forku: odkaz patří k přístupu, brána i poznámky ho znají."""
import hashlib
import json
import re
import subprocess
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

        # odkazy přístupů jsou ve web.json u přístupu (jen otisk), odkaz na celý web v data/pozvanky.json
        cfg = json.loads((self.p / "data" / "web.json").read_text(encoding="utf-8"))
        u_pristupu = {p["nazev"]: [o["jmeno"] for o in p.get("odkazy", [])] for p in cfg["pristupy"]}
        self.assertEqual(u_pristupu, {"Matčina rodina": ["Teta Jana"], "Marie": ["Marie"]})
        self.assertNotIn(teta, (self.p / "data" / "web.json").read_text(encoding="utf-8"))
        poz = self.p / "data" / "pozvanky.json"
        self.assertEqual([z["jmeno"] for z in json.loads(poz.read_text(encoding="utf-8"))], ["Strýc Karel"])

        # přístup, který ve web.json není: pozvanky.py ho odmítne, export taky (ruční úprava pozvanky.json)
        r = self.pridej("Cizí", "--pristup", "neexistuje", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("neexistuje", r.stderr)
        data = json.loads(poz.read_text(encoding="utf-8"))
        data[0]["pristup"] = "zmizely"
        poz.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        r = spust(self.p, "export_web.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("pozvanky.py pristup p2", r.stdout + r.stderr)
        self.assertIn("vede na přístup marie", spust(self.p, "pozvanky.py", "pristup", "p2", "marie").stdout)
        self.assertIn("vede na přístup marie", spust(self.p, "pozvanky.py", "pristup", "p1", "marie").stdout)
        spust(self.p, "export_web.py")
        self.assertEqual(self.mapa("edge-functions/brana.js", "KLICE")[sha(teta)], "marie")
        self.assertEqual(self.mapa("edge-functions/brana.js", "KLICE")[sha(stryc)], "marie")
        # zpět na celý web (vse – správce má odpověď): odkaz se vrátí do data/pozvanky.json
        self.assertIn("vede na celý web", spust(self.p, "pozvanky.py", "pristup", "p1", "vse").stdout)
        self.assertIn("Teta Jana", poz.read_text(encoding="utf-8"))
        spust(self.p, "export_web.py")
        self.assertEqual(self.mapa("edge-functions/brana.js", "KLICE")[sha(teta)], "vse")


class CloudflareBezPristupu(unittest.TestCase):
    """Brána pro Cloudflare umí jen jednu rodinnou otázku: s přístupy nebo osobními odkazy se nevyrobí."""

    def projekt(self, tmp, web_json_upravy, odkaz=False):
        p = Path(tmp) / "ukazka"
        self.assertEqual(novy_projekt(p, "--ukazka").returncode, 0)
        cfg_path = p / "data" / "web.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg.update(web_json_upravy)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        if odkaz:
            spust(p, "pozvanky.py", "pridej", "Teta")
        return p

    def test_s_otazkou_bez_odkazu_se_brana_vyrobi(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.projekt(tmp, {"prihlaseni": {"otazka": "Pes?", "odpoved": "rex"}})
            spust(p, "export_web.py")
            worker = (p / "web" / "cloudflare" / "worker.js").read_text(encoding="utf-8")
            self.assertIn("OTEVRENY = false", worker)
            self.assertTrue((p / "web" / "wrangler.jsonc").exists())

    def test_jen_odkazy_bez_otazky_nesmi_otevrit_web(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.projekt(tmp, {"prihlaseni": {"otazka": "", "odpoved": ""}, "cloudflare": {"nazev": "novakovi"}}, odkaz=True)
            r = spust(p, "export_web.py")
            self.assertFalse((p / "web" / "cloudflare" / "worker.js").exists())      # ne worker s OTEVRENY = true
            self.assertFalse((p / "web" / "wrangler.jsonc").exists())
            self.assertIn("Cloudflare", r.stdout)
            self.assertIn("osobní odkazy", r.stdout)
            self.assertTrue((p / "web" / "netlify" / "edge-functions" / "brana.js").exists())   # Netlify brána je
            # nasazení na Cloudflare skončí srozumitelnou chybou (node je ve forku povinný pro web)
            r = subprocess.run(["node", "scripts/nasadit_cloudflare.mjs"], cwd=p / "web", capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("neumí osobní odkazy", r.stderr)

    def test_pristupy_brana_pro_cloudflare_neni(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.projekt(tmp, {"prihlaseni": {"otazka": "Pes?", "odpoved": "rex"}, "pristupy": PRISTUPY})
            spust(p, "export_web.py", "--pristup", "marie")
            spust(p, "export_web.py")
            self.assertFalse((p / "web" / "cloudflare" / "worker.js").exists())
            r = subprocess.run(["node", "scripts/nasadit_cloudflare.mjs"], cwd=p / "web", capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("neumí přístupy", r.stderr)


if __name__ == "__main__":
    unittest.main()
