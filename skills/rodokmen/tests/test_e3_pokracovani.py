"""E3 (analyza/navrh-optimalizace.md, scénář 2): neúplný zápis na okraji snímku. Čtenář vrátí část 1 s návrhem, řídicí agent rozšíří rozsah
téhož úkolu, další část se k nálezu připojí a první část zůstane; úkol je jeden a čerpání se sčítá. Výřez pro čtení nesmí být delší než
limit: široký řádek se dělí na díly s překryvem. Bez sítě, dočasný projekt; dělení výřezu potřebuje ImageMagick."""
import contextlib
import copy
import io
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
import vysledek  # noqa: E402
import zadani  # noqa: E402

MAGICK = obraz.najdi_magick()
U = "U-0101"


class Pokracovani(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.stare = vysledek.ROOT
        vysledek.ROOT = str(self.root)
        (self.root / "data").mkdir()
        (self.root / "pracovni" / "vysledky").mkdir(parents=True)
        (self.root / "data" / "osoby.py").write_text('P = {88: dict(n="A")}\n', encoding="utf-8")
        (self.root / "data" / "svazky.json").write_text(json.dumps({"0a1b2c3d": {"svazek": "sign.: 712"}}), encoding="utf-8")
        self.run_(zadani, "novy", U, "--otazka", "Najdi křest osoby 88.", "--hleda", "křtěnec", "--osoba", "88:křtěnec", "--svazek", "0a1b2c3d",
                  "--snimky", "40-46", "--vratit", "datum,otec,kmotri")
        self.cast1 = copy.deepcopy(vysledek.VZORY["nalez"])                 # částečně: chybí kmotři, návrh sousední strana 47
        self.uloz(f"pracovni/vysledky/{U}.json", self.cast1)
        self.cast2 = {"schema": "nalez/1", "ukol": U, "cast": 2, "stav": "nalezeno", "stav_behu": "dočteno",
                      "cteni": [{"id": "c1", "zdroj": {"portal": "aron", "svazek": "0a1b2c3d", "snimek": 47, "radek": 7},
                                 "vyrez": f"pracovni/vysledky/{U}_vyrezy/c1_b.jpg", "doslova": {"kmotri": "Wenceslaus Ukazka"}, "chybi": []}],
                      "kandidati": [], "prohledano": [{"svazek": "0a1b2c3d", "snimky": [47, 47], "uplne": True}],
                      "stranky": [{"portal": "aron", "svazek": "0a1b2c3d", "snimek": 47, "typ": "zápisy", "kvalita": "dobrá"}],
                      "cerpani": {"kroku": 2, "snimku": 1}}

    def tearDown(self):
        vysledek.ROOT = self.stare
        self.tmp.cleanup()

    def uloz(self, rel, d):
        p = self.root / rel
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def run_(self, modul, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = modul.main(list(a))
        self.out = out.getvalue()
        return kod

    def test_dalsi_strana_bez_schvaleni_se_nepripoji(self):
        p = self.uloz(f"pracovni/vysledky/{U}_cast2.json", self.cast2)
        self.assertEqual(self.run_(vysledek, "pripoj", U, p), 1)
        self.assertIn("mimo zadaný rozsah", self.out)
        self.assertEqual(json.loads((self.root / f"pracovni/vysledky/{U}.json").read_text(encoding="utf-8"))["cast"], 1)

    def test_schvalene_pokracovani_doplni_totez_cteni(self):
        self.assertEqual(self.run_(zadani, "rozsir", U, "--snimky", "47", "--duvod", "řádek 7 pokračuje vpravo", "--vratit", "kmotri"), 0)
        for s in ("Continuation", "vysledek.py souhrn", f"{U}_cast2.json", "vysledek.py pripoj"):   # čtenář nezačíná od začátku
            self.assertIn(s, self.out, s)
        p = self.uloz(f"pracovni/vysledky/{U}_cast2.json", self.cast2)
        self.assertEqual(self.run_(vysledek, "pripoj", U, p), 0, self.out)
        n = json.loads((self.root / f"pracovni/vysledky/{U}.json").read_text(encoding="utf-8"))
        self.assertEqual((n["cast"], n["stav"], n["ukol"]), (2, "nalezeno", U))                    # jeden úkol, dvě části
        c = n["cteni"][0]
        self.assertEqual(len(n["cteni"]), 1)
        self.assertEqual(c["doslova"]["datum"], "17. Martii 1812")                                 # první část zůstala
        self.assertEqual(c["doslova"]["kmotri"], "Wenceslaus Ukazka")                              # druhá přibyla
        self.assertEqual(c["chybi"], [])
        self.assertEqual(n["cerpani"], {"kroku": 8, "snimku": 4})                                  # čerpání se sčítá
        self.assertEqual([p["snimky"] for p in n["prohledano"]], [[44, 46], [47, 47]])
        self.assertEqual(vysledek.over_nalez(n, vysledek.nacti(vysledek.cesta_zadani(U))), [])

    def test_cast_mimo_poradi_nebo_pro_jiny_ukol(self):
        self.run_(zadani, "rozsir", U, "--snimky", "47", "--duvod", "pokračuje")
        self.cast2["cast"] = 3
        self.assertEqual(self.run_(vysledek, "pripoj", U, self.uloz(f"pracovni/vysledky/{U}_cast2.json", self.cast2)), 1)
        self.assertIn("další je 2", self.out)
        self.cast2.update(cast=2, ukol="U-0999")
        self.assertEqual(self.run_(vysledek, "pripoj", U, self.uloz(f"pracovni/vysledky/{U}_cast2.json", self.cast2)), 1)


@unittest.skipUnless(MAGICK, "chybí ImageMagick")
class SirokyRadek(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)
        self.src = self.p / "pracovni" / "snimek.jpg"
        self.src.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([MAGICK, "-size", "5600x4400", "xc:white", str(self.src)], check=True)
        self.out = self.p / "pracovni" / "vysledky" / "orezy"

    def tearDown(self):
        self._tmp.cleanup()

    def rozmery(self, f):
        return [int(x) for x in subprocess.run([MAGICK, str(f), "-format", "%w %h", "info:"], capture_output=True, text=True, check=True).stdout.split()]

    def test_prilis_siroky_vyrez_se_odmitne(self):
        r = spust(self.p, "vyrez.py", self.src, "radek", "0.0,0.5,0.5,0.6", "--out", "pracovni/vysledky/orezy", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--dily", r.stdout + r.stderr)
        self.assertFalse((self.out / "radek.jpg").exists())

    def test_dily_s_prekryvem_pokryvaji_cely_radek(self):
        r = spust(self.p, "vyrez.py", self.src, "radek", "0.0,0.5,0.5,0.6", "--out", "pracovni/vysledky/orezy", "--dily")   # 2800 × 440 px
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dily = sorted(self.out.glob("radek_*.jpg"))
        self.assertEqual([d.name for d in dily], ["radek_a.jpg", "radek_b.jpg"])
        for d in dily:
            self.assertEqual(self.rozmery(d), [2000, 440])                 # plné rozlišení, žádné zmenšení
        self.assertIn("x 0.0000–0.3571", r.stdout)                         # první díl: 2000 z 5600 px šířky stránky
        self.assertIn("–0.5000", r.stdout)                                 # poslední končí na konci oblasti
        self.assertFalse((self.out / "radek.jpg").exists())

    def test_prilis_vysoky_vyrez_se_odmitne_i_s_dily(self):
        r = spust(self.p, "vyrez.py", self.src, "blok", "0.0,0.0,0.2,0.6", "--out", "pracovni/vysledky/orezy", "--dily", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("výšku", r.stdout + r.stderr)

    def test_maly_vyrez_projde_beze_zmeny(self):
        r = spust(self.p, "vyrez.py", self.src, "zaznam", "0.1,0.5,0.4,0.6", "--out", "pracovni/vysledky/orezy")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rozmery(self.out / "zaznam.jpg"), [1680, 440])


if __name__ == "__main__":
    unittest.main()
