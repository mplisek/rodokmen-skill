"""soubory.py (bezpečný zápis), cache.py (sdílená cache snímků) a zapis.py (změna jedné položky dat)."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import cache  # noqa: E402
import soubory  # noqa: E402


class Soubory(unittest.TestCase):
    def test_zapis_json_format_a_lf(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "data", "svazky.json")
            soubory.zapis_json(p, {"a": {"svazek": "Holice č"}})
            self.assertEqual(Path(p).read_bytes(), '{\n "a": {\n  "svazek": "Holice č"\n }\n}'.encode())

    def test_chyba_nechá_puvodni_soubor(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.json")
            soubory.zapis_json(p, {"a": 1})
            with self.assertRaises(TypeError):
                soubory.zapis_json(p, {"b": object()})
            self.assertEqual(json.loads(Path(p).read_text(encoding="utf-8")), {"a": 1})
            self.assertEqual(os.listdir(d), ["x.json"])   # žádný dočasný soubor


class Cache(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._koren = cache.KOREN
        cache.KOREN = os.path.join(self._tmp.name, "cache")

    def tearDown(self):
        cache.KOREN = self._koren
        self._tmp.cleanup()

    def test_podruhe_z_cache(self):
        volani = []

        def stahni(cil):
            volani.append(cil)
            Path(cil).write_bytes(b"snimek")
        out = os.path.join(self._tmp.name, "pracovni", "a.jpg")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(cache.soubor("aron/x/sn0001-u1.jpg", out, stahni))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(cache.soubor("aron/x/sn0001-u1.jpg", out + "2", stahni))
        self.assertEqual(len(volani), 1)
        self.assertEqual(Path(out + "2").read_bytes(), b"snimek")
        self.assertTrue(volani[0].endswith(".jpg"))   # dočasný soubor má příponu (podle ní ImageMagick volí formát)

    def test_nepovedene_stazeni_do_cache_nepatri(self):
        def spadne(cil):
            Path(cil).write_bytes(b"pul")
            sys.exit("portál neodpovídá")
        with self.assertRaises(SystemExit):
            cache.soubor("trebon/1/sn0001.jpg", None, spadne)
        self.assertEqual(os.listdir(os.path.dirname(cache.cesta("trebon/1/sn0001.jpg"))), [])


class Zapis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        (self.p / "tools").mkdir()
        (self.p / "data").mkdir()
        (self.p / "pracovni").mkdir()
        shutil.copy(TOOLS / "zapis.py", self.p / "tools")
        self.svazky = self.p / "data" / "svazky.json"
        self.svazky.write_text('{\n "a": {\n  "svazek": "A",\n  "snimku": 10\n },\n "b": {\n  "svazek": "B"\n }\n}',
                               encoding="utf-8", newline="\n")

    def tearDown(self):
        self._tmp.cleanup()

    def zapis(self, klic, obj, *volby):
        vstup = self.p / "pracovni" / "vstup.json"
        vstup.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "zapis.py"), "svazky", klic,
                               str(vstup), *volby], cwd=self.p, capture_output=True, text=True, encoding="utf-8")

    def test_nahradi_jen_jednu_polozku(self):
        self.assertEqual(self.zapis("a", {"svazek": "Á nové"}).returncode, 0)
        text = self.svazky.read_text(encoding="utf-8")
        self.assertEqual(json.loads(text), {"a": {"svazek": "Á nové"}, "b": {"svazek": "B"}})
        self.assertIn('\n "b": {\n  "svazek": "B"\n }\n}', text)   # ostatní položky beze změny formátu
        self.assertNotIn(b"\r\n", self.svazky.read_bytes())

    def test_sloucit_a_pridat(self):
        self.assertEqual(self.zapis("a", {"snimku": 12}, "--sloucit").returncode, 0)
        self.assertEqual(self.zapis("c", {"svazek": "C"}).returncode, 0)
        self.assertEqual(json.loads(self.svazky.read_text(encoding="utf-8")),
                         {"a": {"svazek": "A", "snimku": 12}, "b": {"svazek": "B"}, "c": {"svazek": "C"}})

    def test_spatny_vstup_data_nezmeni(self):
        pred = self.svazky.read_bytes()
        r = self.zapis("a", ["není objekt"])
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.svazky.read_bytes(), pred)


if __name__ == "__main__":
    unittest.main()
