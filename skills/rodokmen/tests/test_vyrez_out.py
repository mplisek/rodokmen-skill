"""vyrez.py --out SLOŽKA: výřez jen do zadané složky (agent smí zapisovat jen do pracovni/vysledky/), bez zápisu do veřejných složek
zdroje/ a vyrezy/ a bez pamatování oblasti. Bez --out se chování nemění. Dočasný projekt, bez sítě; potřebuje ImageMagick."""
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


@unittest.skipUnless(MAGICK, "chybí ImageMagick")
class VyrezOut(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)
        self.src = self.p / "pracovni" / "snimek.jpg"
        self.src.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([MAGICK, "-size", "400x300", "xc:white", str(self.src)], check=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_out_zapise_jen_do_zadane_slozky(self):
        spust(self.p, "vyrez.py", self.src, "klic_x", "0.1,0.1,0.9,0.5", "--out", "pracovni/vysledky/orezy")
        self.assertTrue((self.p / "pracovni" / "vysledky" / "orezy" / "klic_x.jpg").is_file())
        self.assertFalse((self.p / "zdroje" / "klic_x.jpg").exists())
        self.assertFalse((self.p / "vyrezy" / "klic_x.jpg").exists())
        self.assertFalse((self.p / "pracovni" / "vyrezy_oblasti.json").exists())

    def test_out_vyrez_ma_plne_rozliseni_oblasti(self):
        spust(self.p, "vyrez.py", self.src, "klic_x", "0.0,0.0,0.5,0.5", "--out", "pracovni/vysledky/orezy")
        r = subprocess.run([MAGICK, str(self.p / "pracovni" / "vysledky" / "orezy" / "klic_x.jpg"), "-format", "%w %h", "info:"],
                           capture_output=True, text=True, check=True)
        self.assertEqual(r.stdout.split(), ["200", "150"])

    def test_bez_out_se_nic_nemeni(self):
        spust(self.p, "vyrez.py", self.src, "klic_y", "0.1,0.1,0.9,0.5")
        self.assertTrue((self.p / "zdroje" / "klic_y.jpg").is_file())
        self.assertTrue((self.p / "vyrezy" / "klic_y.jpg").is_file())
        self.assertTrue((self.p / "pracovni" / "vyrezy_oblasti.json").is_file())


if __name__ == "__main__":
    unittest.main()
