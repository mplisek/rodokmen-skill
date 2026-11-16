"""tools/podnet.py (analyza/navrh-optimalizace.md, E2/E6): bádací sezení předává metodice jen technický podnět; text s příjmením
z rodokmenu nebo s číslem úkolu se nezapíše (poznámky jdou do veřejného repozitáře skillu). Bez sítě, dočasný projekt."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402


class Podnet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "tools").mkdir()
        shutil.copy(TOOLS / "podnet.py", self.root / "tools" / "podnet.py")
        (self.root / "data" / "osoby.py").write_text('P = {1: dict(n="Josef Vzorný"), 3: dict(n="Anna Příkladová")}\n', encoding="utf-8")
        self.soubor = self.root / "data" / "poznamky_pro_skill.md"
        self.soubor.write_text("# Poznámky\n\n## Nové\n\n(nic nového)\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_(self, *a):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.root / "tools" / "podnet.py"), *a], capture_output=True, text=True,
                              encoding="utf-8")

    def test_technicky_podnet_se_pripise(self):
        r = self.run_("mapa.py zapis odmítl stránku s typem index; čekal jsem nápovědu výčtu", "--dopad", "cena", "--kolikrat", "4")
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.soubor.read_text(encoding="utf-8")
        self.assertNotIn("(nic nového)", t)
        self.assertRegex(t, r"(?m)^- \d{4}-\d\d-\d\d: mapa\.py zapis odmítl.*Dopad: cena\. Výskytů: 4\.$")
        self.run_("druhý podnět o nástroji, který skončil chybou cesty")
        self.assertEqual(self.soubor.read_text(encoding="utf-8").count("\n- "), 2)

    def test_prijmeni_z_rodokmenu_se_odmitne_i_ve_sklonovani(self):
        for text in ("čtenář zaměnil Vzorného za jmenovce v téže farnosti", "rejstřík vede Příkladovou pod jiným písmenem než kniha"):
            r = self.run_(text)
            self.assertNotEqual(r.returncode, 0, text)
            self.assertIn("příjmení z rodokmenu", r.stderr)
        self.assertIn("(nic nového)", self.soubor.read_text(encoding="utf-8"))

    def test_cislo_ukolu_a_prilis_kratky_text(self):
        self.assertNotEqual(self.run_("úkol U-0045 stál moc a nic nenašel v rejstříku").returncode, 0)
        self.assertNotEqual(self.run_("nejde to").returncode, 0)

    def test_bez_souboru_ho_zalozi(self):
        self.soubor.unlink()
        self.assertEqual(self.run_("nástroj při startu nenašel složku pravidel pluginu").returncode, 0)
        self.assertIn("## Nové", self.soubor.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
