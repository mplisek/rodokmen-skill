"""cache.py stav ukáže, kolik snímků se stáhlo z archivu na jeden nalezený záznam v deníku (Q-M7: měří, zda mapa knihy šetří archivy);
aron_img.py zapisuje identitu stažených snímků do mapy knihy (Q-M6). Bez sítě."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt  # noqa: E402


def radek(id_, vys, datum):
    return {"id": id_, "datum": datum, "zdroj": {"typ": "archiv", "text": "ARON"}, "rozsah": "sn. 1", "hledano": f"h{id_}", "vysledek": vys,
            "nalez": "x"}


class CacheStav(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name) / "projekt"
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)
        self.stav = Path(self._tmp.name) / "stav"
        self.stav.mkdir()
        self.snimky = Path(self._tmp.name) / "snimky"
        self.snimky.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def spust(self, *a):
        env = dict(os.environ, SLUSNE_STAV=str(self.stav), RODOKMEN_SNIMKY=str(self.snimky), PYTHONUTF8="1")
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "cache.py"), *a], cwd=self.p, capture_output=True,
                              text=True, encoding="utf-8", env=env)

    def denik(self, *rr):
        (self.p / "data" / "denik.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rr) + "\n", encoding="utf-8")

    def test_snimky_na_nalezeny_zaznam(self):
        (self.stav / "aron.vychodoceskearchivy.cz.json").write_text(
            json.dumps({"stazeno": 30, "z_mezipameti": 5, "stazeno_mb": 60, "usetreno_mb": 10, "pocitano_od": "2026-11-01"}), encoding="utf-8")
        self.denik(radek(1, "nalezeno", "2026-11-02"), radek(2, "nalezeno", "2026-11-05"), radek(3, "nalezeno", "2026-11-09"),
                   radek(4, "nalezeno", "2026-10-01"), radek(5, "nenalezeno", "2026-11-03"))
        r = self.spust("stav")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Stažených snímků na nalezený záznam: 10,0", r.stdout)       # 30 snímků / 3 nalezené záznamy od 1. 11.
        self.assertIn("od 2026-11-01", r.stdout)

    def test_bez_nalezu_nebo_bez_statistiky(self):
        r = self.spust("stav")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("na nalezený záznam: ", r.stdout)                          # bez statistiky stažení se nic nepíše
        (self.stav / "aron.vychodoceskearchivy.cz.json").write_text(json.dumps({"stazeno": 4, "pocitano_od": "2026-11-01"}), encoding="utf-8")
        r = self.spust("stav")
        self.assertIn("zatím žádný nalezený záznam", r.stdout)


class AronImgMapa(unittest.TestCase):
    def test_aron_img_zapisuje_identitu_snimku_do_mapy(self):
        zdroj = (TOOLS / "aron_img.py").read_text(encoding="utf-8")
        self.assertIn("mapa.snimek_bezpecne(\"aron\", apu[:8], n, \"cache\")", zdroj)


if __name__ == "__main__":
    unittest.main()
