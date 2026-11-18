"""tools/nalez.py: zápis nálezu jedním příkazem (podle sarsonj/rodokmen-skill#187, napojeno na denik.jsonl a účastníky zápisu).
Dočasný projekt s ukázkou, snímek vyrobený ImageMagickem, bez sítě (jiný archiv než ARON: obraz, svazek, odkaz)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt, spust  # noqa: E402

sys.path.insert(0, str(TOOLS))
import obraz  # noqa: E402

MAGICK = obraz.najdi_magick()
KLIC = "holice_krest_test_vzorny_1891"


@unittest.skipUnless(MAGICK, "chybí ImageMagick")
class Nalez(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)
        (self.p / "pracovni").mkdir(exist_ok=True)
        subprocess.run([MAGICK, "-size", "800x600", "xc:white", str(self.p / "pracovni" / "snimek.jpg")], check=True)
        (self.p / "data" / "denik.jsonl").write_text("", encoding="utf-8")
        self.vstup = {
            "klic": KLIC, "obraz": "pracovni/snimek.jpg", "svazek": "ukazka01", "odkaz": "https://example.org/snimek/12",
            "snimek": 12, "vyrez": [0, 0.2, 1, 0.5], "ramecek": [[0, 0.1, 1, 0.6]], "ramecek_pozn": "zápis č. 3",
            "zaznam": {"druh": "N", "datum": "3. 5. 1891", "nazev": "Křest (1891)", "shrnuti": "křest dítěte",
                       "ucastnici": [{"osoba": "8", "role": "otec"}, {"osoba": "marie-novakova", "role": "kmotr"}]},
            "prepis": {"orig": "Joannes …", "cs": "Jan …"},
            "osoby": [8],
            "denik": {"datum": "2026-11-18", "zdroj_typ": "archiv", "zdroj": "ARON, N Holice 1880–1900", "rozsah": "sn. 10–14",
                      "hledano": "křest dítěte Jana Nováka", "vysledek": "nalezeno", "nalez": "sn. 12, zápis č. 3", "osoby": ["8"]}}

    def tearDown(self):
        self._tmp.cleanup()

    def nalez(self, prikaz, vstup=None, *volby):
        p = self.p / "pracovni" / "nalez.json"
        p.write_text(json.dumps(vstup or self.vstup, ensure_ascii=False), encoding="utf-8")
        return spust(self.p, "nalez.py", prikaz, "pracovni/nalez.json", *volby, check=False)

    def data(self):
        return {f: (self.p / "data" / f).read_bytes() for f in ("zaznamy.json", "prepisy.json", "osoby.py", "denik.jsonl")}

    def test_nahled_udela_vyrez_a_data_nemeni(self):
        pred = self.data()
        r = self.nalez("nahled")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.p / "vyrezy" / f"{KLIC}.jpg").exists())
        self.assertTrue((self.p / "pracovni" / f"ramecek_{KLIC}.jpg").exists())
        self.assertEqual(self.data(), pred)

    def test_zapis_zapise_zapis_ucastniky_prepis_odkaz_a_denik(self):
        r = self.nalez("zapis")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = next(x for x in json.loads((self.p / "data" / "zaznamy.json").read_text(encoding="utf-8")) if x["klic"] == KLIC)
        self.assertEqual((z["svazek"], z["snimek"], z["druh"]), ("ukazka01", 12, "N"))
        self.assertEqual([u["role"] for u in z["ucastnici"]], ["otec", "kmotr"])          # i osoba z RODINA
        self.assertEqual(json.loads((self.p / "data" / "prepisy.json").read_text(encoding="utf-8"))[KLIC]["cs"], "Jan …")
        self.assertIn(KLIC, (self.p / "data" / "osoby.py").read_text(encoding="utf-8"))   # odkaz r u osoby 8
        radky = [json.loads(x) for x in (self.p / "data" / "denik.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        self.assertEqual((len(radky), radky[0]["vysledek"], radky[0]["osoby"]), (1, "nalezeno", ["8"]))
        self.assertEqual(spust(self.p, "kontrola.py", check=False).returncode, 0)

    def test_chybny_denik_zastavi_vse_predem(self):
        v = json.loads(json.dumps(self.vstup))
        v["denik"]["vysledek"] = "asi"
        pred = self.data()
        r = self.nalez("zapis", v)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ODMÍTNUTO", r.stdout)
        self.assertEqual(self.data(), pred)
        self.assertFalse((self.p / "vyrezy" / f"{KLIC}.jpg").exists())                    # nic se nestáhlo ani nevyřezalo

    def test_zapis_bez_osoby_a_neznamy_ucastnik_se_odmitnou(self):
        pred = self.data()
        v = json.loads(json.dumps(self.vstup))
        v["osoby"], v["zaznam"]["ucastnici"] = [], []
        self.assertIn("nepatří žádné osobě", self.nalez("zapis", v).stdout)
        v["zaznam"]["ucastnici"] = [{"osoba": "nikdo-takovy", "role": "otec"}]
        self.assertEqual(self.nalez("zapis", v).returncode, 1)
        self.assertEqual(self.data(), pred)

    def test_existujici_zapis_jen_s_prepsat(self):
        self.assertEqual(self.nalez("zapis").returncode, 0)
        v = json.loads(json.dumps(self.vstup))
        v.pop("denik")
        r = self.nalez("zapis", v)
        self.assertEqual(r.returncode, 1)
        self.assertIn("--prepsat", r.stdout)
        v["prepis"]["cs"] = "Jan, opraveno"
        self.assertEqual(self.nalez("zapis", v, "--prepsat").returncode, 0)
        self.assertEqual(json.loads((self.p / "data" / "prepisy.json").read_text(encoding="utf-8"))[KLIC]["cs"], "Jan, opraveno")

    def test_neznama_osoba_v_odkazech_se_odmitne_predem(self):
        pred = self.data()
        v = json.loads(json.dumps(self.vstup))
        v["osoby"] = [8, 999999]
        r = self.nalez("zapis", v)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ODMÍTNUTO", r.stdout)
        self.assertEqual(self.data(), pred)

    def test_selhani_uprostred_zapisu_vrati_data(self):
        """Selže-li krok až po zapsání zápisu a přepisu (tady odkaz u osoby), zápis, přepis i deník se vrátí – všechno, nebo nic."""
        pred = self.data()
        (self.p / "pracovni" / "nalez.json").write_text(json.dumps(self.vstup, ensure_ascii=False), encoding="utf-8")
        kod = ("import sys; sys.path.insert(0, 'tools'); import nalez\n"
               "puvodni = nalez.nastroj\n"
               "def nastroj(*a, **k):\n"
               "    if a[:2] == ('zapis.py', 'odkaz'):\n"
               "        raise nalez.Odmitnuto('simulované selhání odkazu')\n"
               "    return puvodni(*a, **k)\n"
               "nalez.nastroj = nastroj\n"
               "sys.exit(nalez.main(['zapis', 'pracovni/nalez.json']))\n")
        r = subprocess.run([sys.executable, "-X", "utf8", "-c", kod], cwd=self.p, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ZAPSÁNO NIC", r.stdout)
        self.assertEqual(self.data(), pred)


if __name__ == "__main__":
    unittest.main()
