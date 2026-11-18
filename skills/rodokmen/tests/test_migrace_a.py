"""scripts/migrace_a.py: jednorázová migrace front na plán ukoly.md, archivni_dotazy.md a soubor k ručnímu zpracování.
Smyšlený projekt, bez sítě; nanečisto data nemění, čísla úkolů do plánu nejdou, fronty se nemažou."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKRIPT = REPO / "scripts" / "migrace_a.py"

NOC = """# Úkoly na noc

## U-0001 | P2 | os:8 | typ:krest | stav:otevřeno | cena:S
Najít křest osoby 8, Lhota 1810–1814, svazek 0a1b2c3d.
Definice hotového: křest zapsán a ověřen

## U-0002 | P2 | os:8 | typ:krest | stav:otevřeno
Křest osoby 8 ještě v Hoře.

## U-0003 | P3 | os:9 | typ:snatek | stav:čeká | kdy:2026-12-01
Sňatek 9 ve farnosti nevěsty.
"""
DOTAZY = """# Dotazy

## U-0004 | P1 | os:16 | typ:archiv | stav:otevřeno
Pozemková kniha obce Lhota, SOA Zámrsk.
"""
RODINA = """# Na rodinu

## U-0005 | P2 | os:3 | typ:dotaz | stav:otevřeno
Je doma oddací list prababičky?
"""


class Migrace(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        d = self.p / "data"
        d.mkdir()
        (d / "ukoly_na_noc.md").write_text(NOC, encoding="utf-8")
        (d / "ukoly_dotazy_na_archivy.md").write_text(DOTAZY, encoding="utf-8")
        (d / "ukoly_na_rodinu.md").write_text(RODINA, encoding="utf-8")
        (d / "osoby.py").write_text('P = {8: {}, 9: {}}\nISSUES = [dict(k=9, otazka="Kde se vdávala?", stav="otevřené")]\n',
                                    encoding="utf-8")
        (d / "ukoly.md").write_text("# Plán bádání\n\n## Křty\n\n## Sňatky\n\n## Úmrtí\n\n## Jiné\n", encoding="utf-8")
        (d / "archivni_dotazy.md").write_text("# Prameny mimo online matriky\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def spust(self, *a):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), str(self.p), *a], capture_output=True, text=True,
                              encoding="utf-8")

    def data(self):
        return {f.name: f.read_bytes() for f in (self.p / "data").iterdir()}

    def test_nanecisto_jen_prehled_s_upozornenimi(self):
        pred = self.data()
        r = self.spust()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.data(), pred)
        p = (self.p / "pracovni" / "migrace_a_prehled.md").read_text(encoding="utf-8")
        self.assertIn("možná duplicita s U-0001", p)
        self.assertIn("osoba má otevřenou otázku v ISSUES", p)
        self.assertIn("čekalo (kdy: 2026-12-01)", p)

    def test_zapsat_rozdeli_ukoly_dotazy_a_rucni(self):
        r = self.spust("--zapsat")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        plan = (self.p / "data" / "ukoly.md").read_text(encoding="utf-8")
        krty = plan.split("## Křty", 1)[1].split("## Sňatky", 1)[0]
        self.assertIn("- 8 – Najít křest osoby 8, Lhota 1810–1814, svazek 0a1b2c3d.", krty)
        self.assertIn("- 9 – Sňatek 9 ve farnosti nevěsty.", plan.split("## Sňatky", 1)[1])
        self.assertNotIn("U-00", plan)                                                  # čísla úkolů do plánu ne
        self.assertNotIn("Definice hotového", plan)
        self.assertIn("Pozemková kniha obce Lhota", (self.p / "data" / "archivni_dotazy.md").read_text(encoding="utf-8"))
        self.assertIn("oddací list", (self.p / "pracovni" / "migrace_a_rucne.md").read_text(encoding="utf-8"))
        self.assertTrue((self.p / "data" / "ukoly_na_noc.md").exists())                 # fronty se nemažou
        self.assertIn("git rm data/ukoly_na_noc.md", r.stdout)
        self.spust("--zapsat")                                                          # podruhé nic nezdvojí v plánu
        self.assertEqual((self.p / "data" / "ukoly.md").read_text(encoding="utf-8").count("Najít křest osoby 8"), 1)


if __name__ == "__main__":
    unittest.main()
