"""tools/oprava.py: oprava polí existujících zápisů (data/zaznamy.json) a míst (data/mista.json) jedním voláním – s důvodem a dokladem,
všechno nebo nic, kontrola dat po změně (nová chyba = vrácení), historie oprav v data/opravy.jsonl. Požadavek uživatele 16. 11. 2026:
badatel opravuje chybné údaje sám, uživatel data nekopíruje. Dočasný projekt, bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

ZAZNAMY = [
    {"klic": "ukazka_snatek_1801", "svazek": "0a1b2c3d", "snimek": 80, "druh": "S", "datum": "1801", "nazev": "Sňatek Ukázka",
     "shrnuti": "sňatek", "odkaz": "https://example.org/1"},
    {"klic": "ukazka_krest_1784", "svazek": "0a1b2c3d", "snimek": 81, "druh": "N", "datum": "6. 6. 1784", "nazev": "Křest Ukázka",
     "shrnuti": "křest", "odkaz": "https://example.org/2"},
]
MISTA = {"Ukázkov": {"re": "Ukázkov", "dotaz": "Ukázkov, Česko", "lat": 50.6, "lon": 15.3, "osm": "Ukázkov, Semily"}}


class Oprava(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "p"
        r = novy_projekt(self.root)
        assert r.returncode == 0, r.stdout + r.stderr
        (self.root / "pracovni").mkdir(exist_ok=True)
        d = self.root / "data"
        (d / "zaznamy.json").write_text(json.dumps(ZAZNAMY, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (d / "mista.json").write_text(json.dumps(MISTA, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        sv = json.loads((d / "svazky.json").read_text(encoding="utf-8-sig")) if (d / "svazky.json").exists() else {}
        sv["0a1b2c3d"] = {"archiv": "SOA Zámrsk", "portal": "ARON", "svazek": "sign.: 712"}
        (d / "svazky.json").write_text(json.dumps(sv, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def oprav(self, obsah, *volby, jmeno="oprava.json"):
        p = self.root / "pracovni" / jmeno
        p.write_text(json.dumps(obsah, ensure_ascii=False), encoding="utf-8")
        return spust(self.root, "oprava.py", f"pracovni/{jmeno}", *volby, check=False)

    def data(self, soubor):
        return (self.root / "data" / soubor).read_text(encoding="utf-8")

    def zaznam(self, klic):
        return next(z for z in json.loads(self.data("zaznamy.json")) if z["klic"] == klic)

    def historie(self):
        p = self.root / "data" / "opravy.jsonl"
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []

    def test_oprava_druhu_zapise_jen_pole_a_historii(self):
        r = self.oprav({"duvod": "sňatek označený jako soupis", "doklad": "snímek 80: oddací zápis",
                        "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = self.zaznam("ukazka_snatek_1801")
        self.assertEqual(z["druh"], "O")
        self.assertEqual(z["snimek"], 80)                                         # ostatní pole beze změny
        h = self.historie()
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["zmeny"][0]["pole"]["druh"], {"bylo": "S", "je": "O"})
        self.assertEqual((h[0]["duvod"], h[0]["doklad"]), ("sňatek označený jako soupis", "snímek 80: oddací zápis"))
        self.assertIn("commit.py --soubory", r.stdout)
        self.assertIn("data/opravy.jsonl", r.stdout)

    def test_misto_souradnice(self):
        r = self.oprav({"duvod": "obec u stejnojmenné obce jinde", "doklad": "titulní štítek knihy narozených",
                        "zmeny": [{"soubor": "mista", "klic": "Ukázkov", "pole": {"lat": 49.69, "lon": 15.81, "dotaz": "Ukázkov, okres Havlíčkův Brod"}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = json.loads(self.data("mista.json"))["Ukázkov"]
        self.assertEqual((m["lat"], m["lon"], m["re"]), (49.69, 15.81, "Ukázkov"))

    def test_chybny_vstup_nic_nezmeni(self):
        pred = (self.data("zaznamy.json"), self.data("mista.json"))
        zmena = {"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}
        spatne = [
            {"doklad": "x", "zmeny": [zmena]},                                                          # chybí důvod
            {"duvod": "x", "zmeny": [zmena]},                                                           # chybí doklad
            {"duvod": "x", "doklad": "y", "zmeny": []},
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, klic="neexistuje")]},                  # nový zápis tudy ne
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"druh": "X"})]},
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"klic": "jiny"})]},              # klíč se nemění
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"ucastnici": []})]},             # na to je ucastnici.py
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"svazek": "ffffffff"})]},        # svazek mimo katalog
            {"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "mista", "klic": "Ukázkov", "pole": {"lat": 120}}]},
            {"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "osoby", "klic": "1", "pole": {"n": "x"}}]},
            {"duvod": "x", "doklad": "y", "zmeny": [zmena, {"soubor": "mista", "klic": "Nikde", "pole": {"lat": 1}}]},   # vše nebo nic
        ]
        for i, s in enumerate(spatne):
            r = self.oprav(s, jmeno=f"x{i}.json")
            self.assertNotEqual(r.returncode, 0, s)
        self.assertEqual((self.data("zaznamy.json"), self.data("mista.json")), pred)
        self.assertEqual(self.historie(), [])

    def test_nova_chyba_kontroly_vrati_vse(self):
        """Oprava, po které kontrola dat hlásí novou chybu (tady neplatný výraz místa), se vrátí celá, i zápis, který byl v pořádku."""
        pred = (self.data("zaznamy.json"), self.data("mista.json"))
        r = self.oprav({"duvod": "x", "doklad": "y", "zmeny": [
            {"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}},
            {"soubor": "mista", "klic": "Ukázkov", "pole": {"re": "Ukázkov("}}]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vráceno", r.stdout)
        self.assertEqual((self.data("zaznamy.json"), self.data("mista.json")), pred)
        self.assertEqual(self.historie(), [])

    def test_nanecisto_a_beze_zmeny(self):
        pred = self.data("zaznamy.json")
        o = {"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}]}
        r = self.oprav(o, "--nanecisto")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("S → O", r.stdout)
        self.assertEqual(self.data("zaznamy.json"), pred)
        r = self.oprav({"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "S"}}]})
        self.assertEqual(r.returncode, 0)
        self.assertIn("nic ke změně", r.stdout)
        self.assertEqual(self.historie(), [])

    def test_historie_oprav_je_chranena_pred_rucnim_zapisem(self):
        import subprocess
        data = {"tool_name": "Edit", "tool_input": {"file_path": str(self.root / "data" / "opravy.jsonl")}, "cwd": str(self.root)}
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.root / "tools" / "hlidac_zapisu.py")], input=json.dumps(data),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertIn("oprava.py", r.stdout)                                     # zamítnuto s nápovědou, kterým nástrojem

    def test_vstup_jen_z_pracovni(self):
        (self.root / "o.json").write_text(json.dumps({"duvod": "x", "doklad": "y", "zmeny": [
            {"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}]}), encoding="utf-8")
        self.assertNotEqual(spust(self.root, "oprava.py", "o.json", check=False).returncode, 0)
        self.assertEqual(self.zaznam("ukazka_snatek_1801")["druh"], "S")


if __name__ == "__main__":
    unittest.main()
