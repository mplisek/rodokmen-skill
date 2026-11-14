"""tools/pracovni_prehled.py: soupis toho, co už leží ve složce pracovni/ (stažené snímky ARONu po svazcích, výřezy a ostatní soubory),
s vazbou na data/svazky.json a deník (které řádky se svazku týkají). Researcher ho volá před každým novým stažením. Jen čte, nic nemění,
bez sítě. Rozhraní: příkazová řádka nad dočasným projektem."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

APU = "03066862"


class PracovniPrehled(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)
        sv = self.p / "pracovni" / "aron" / f"{APU}_365"
        sv.mkdir(parents=True)
        for n in (236, 248, 257, 258):
            (sv / f"CZ_215000010_00190_UCWE2WEJ_{n:05d}_sign-365.jpg").write_bytes(b"\xff\xd8\xff" + b"0" * 100)
        (self.p / "pracovni" / "kh53").mkdir()
        (self.p / "pracovni" / "kh53" / "e1.jpg").write_bytes(b"\xff\xd8\xff" + b"0" * 50)
        (self.p / "pracovni" / "poznamka.md").write_text("x", encoding="utf-8")
        (self.p / "data" / "svazky.json").write_text(json.dumps({APU: {
            "archiv": "SOA Zámrsk", "portal": "ARON", "svazek": "Sbírka matrik, sign.: 365 (poř.č. 1), Libice nad Doubravou, 1800-1850",
            "snimku": 300, "url": "https://aron.example/apu/x"}}), encoding="utf-8")
        radky = [
            {"id": 7, "datum": "2026-10-30", "zdroj": {"typ": "archiv", "text": "ARON Libice sign. 365, sn. 236–258"},
             "rozsah": "sn. 236–258", "hledano": "křty Plíšků", "vysledek": "nalezeno", "nalez": "x"},
            {"id": 8, "datum": "2026-10-30", "zdroj": {"typ": "archiv", "text": "ARON Chloumek sign. 3650"},
             "rozsah": "r", "hledano": "jiné", "vysledek": "nenalezeno"},
        ]
        (self.p / "data" / "denik.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in radky) + "\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def prehled(self, *args):
        return spust(self.p, "pracovni_prehled.py", *args)

    def test_svazek_aronu_ma_pocet_rozsah_a_radky_denika(self):
        d = json.loads(self.prehled("--json").stdout)
        sv = [s for s in d["svazky"] if s["apu"] == APU]
        self.assertEqual(len(sv), 1)
        s = sv[0]
        self.assertEqual((s["snimku_stazeno"], s["snimku_celkem"]), (4, 300))
        self.assertEqual((s["od"], s["do"]), (236, 258))
        self.assertEqual(s["signatura"], "365")
        self.assertEqual(s["denik"], [7])           # 3650 není 365

    def test_ostatni_slozky_bez_adresy_jsou_zvlast(self):
        d = json.loads(self.prehled("--json").stdout)
        self.assertEqual([o["slozka"] for o in d["ostatni"]], ["kh53"])
        self.assertEqual(d["ostatni"][0]["souboru"], 1)

    def test_text_obsahuje_svazek_a_chybejici_snimky(self):
        t = self.prehled().stdout
        self.assertIn("365", t)
        self.assertIn("Libice", t)
        self.assertIn("4/300", t)

    def test_hledej_najde_svazek_a_radky_a_necha_ostatni(self):
        t = self.prehled("--hledej", "Libice 365").stdout
        self.assertIn(APU, t)
        self.assertIn("7", t)
        self.assertNotIn("kh53", t)

    def test_hledej_najde_i_jen_radek_denika_bez_svazku(self):
        r = self.prehled("--hledej", "Chloumek")
        self.assertEqual(r.returncode, 0)
        self.assertIn("8", r.stdout)

    def test_hledej_bez_shody_vrati_kod_1(self):
        r = spust(self.p, "pracovni_prehled.py", "--hledej", "Neexistuje", check=False)
        self.assertEqual(r.returncode, 1)

    def test_nic_nemeni(self):
        pred = sorted(str(f.relative_to(self.p)) for f in (self.p / "pracovni").rglob("*"))
        self.prehled()
        self.prehled("--json")
        po = sorted(str(f.relative_to(self.p)) for f in (self.p / "pracovni").rglob("*"))
        self.assertEqual(pred, po)

    def test_prazdna_pracovni_neni_chyba(self):
        import shutil
        shutil.rmtree(self.p / "pracovni")
        d = json.loads(self.prehled("--json").stdout)
        self.assertEqual((d["svazky"], d["ostatni"]), ([], []))


if __name__ == "__main__":
    unittest.main()
