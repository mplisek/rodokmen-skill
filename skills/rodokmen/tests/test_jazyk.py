"""scripts/jazyk.py (Fáze E, Q-E3): anglická vrstva (pravidla pro agenty, tenký skill) je anglicky. Rozhraní: příkaz jazyk.py nad
vzorovými soubory. České výrazy v uvozovkách, v kódu a v odkazech na zdroj nevadí. Bez sítě."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKRIPT = REPO / "scripts" / "jazyk.py"


class Jazyk(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def jazyk(self, *soubory):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), *map(str, soubory)], capture_output=True, text=True,
                              encoding="utf-8")

    def soubor(self, jmeno, text):
        p = self.t / jmeno
        p.write_text(text, encoding="utf-8")
        return p

    def test_anglicky_text_projde(self):
        p = self.soubor("a.md", "# Rules\n\nMerge two people only on two independent signs. Read the register column by column.\n" * 5)
        r = self.jazyk(p)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_cesky_text_neprojde_a_hlasi_soubor(self):
        p = self.soubor("b.md", "# Pravidla\n\nSpoj dvě osoby stejného jména jen podle dvou nezávislých znaků. Čti rejstřík po sloupcích.\n" * 5)
        r = self.jazyk(p)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("b.md", r.stdout + r.stderr)

    def test_ceske_vyrazy_v_uvozovkach_kodu_a_zdroji_nevadi(self):
        p = self.soubor("c.md", (
            "## R-X-001\n"
            "when: a book is organised \"po vsích\" (by village)\n"
            "do: map every section before writing \"nenalezeno\" for the whole book\n"
            "why: a wedding was \"nenalezen\" in two parishes and was in the village book\n"
            "source: reference/matriky.md#Knihy řazené po vsích (časté 1784–1900, všechny archivy)\n\n"
            "```text\nKřest Josefa Nováka * 1852 Dolní Lhota čp. 12, kmotři Václav Kříž a Anežka Šťastná\n```\n"
            "Use `data/vyřešené.md` and the field „výsledek“ as is.\n") * 2)
        r = self.jazyk(p)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_slozka_projde_vsechny_md_a_jiny_typ_ignoruje(self):
        self.soubor("ok.md", "Plain English only here. " * 20)
        self.soubor("zly.md", "Tohle je česky psaný text s diakritikou, který tam nepatří. " * 5)
        (self.t / "data.json").write_text('{"x": "Čeština žluťoučký kůň"}', encoding="utf-8")
        r = self.jazyk(self.t)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("zly.md", r.stdout + r.stderr)
        self.assertNotIn("ok.md", r.stdout + r.stderr)
        self.assertNotIn("data.json", r.stdout + r.stderr)

    def test_prah_jde_zmenit(self):
        p = self.soubor("d.md", "Mostly English text with the word Šťastná and Kříž twice in the file. " * 3)
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), "--prah", "0.2", str(p)], capture_output=True, text=True,
                           encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
