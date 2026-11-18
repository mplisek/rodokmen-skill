"""zapis.zapis: náhrada, která by ztratila pole, se bez --prepsat odmítne; s prepsat=True / sloucit=True projde (bez sítě)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import zapis  # noqa: E402


class ZapisPrepsat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "data"))
        self.stary_root = zapis.ROOT
        zapis.ROOT = self.tmp.name
        self.cesta = os.path.join(self.tmp.name, "data", "svazky.json")
        json.dump({"a": {"svazek": "S", "obce": ["x", "y"]}}, open(self.cesta, "w", encoding="utf-8"))

    def tearDown(self):
        zapis.ROOT = self.stary_root
        self.tmp.cleanup()

    def nacti(self):
        return json.load(open(self.cesta, encoding="utf-8"))["a"]

    def test_ztrata_pole_se_odmitne(self):
        with self.assertRaises(SystemExit):
            zapis.zapis("svazky", "a", {"svazek": "T"})
        self.assertEqual(self.nacti()["obce"], ["x", "y"])

    def test_prepsat_nahradi_celou_polozku(self):
        zapis.zapis("svazky", "a", {"svazek": "T"}, prepsat=True)
        self.assertEqual(self.nacti(), {"svazek": "T"})

    def test_sloucit_zachova_pole(self):
        zapis.zapis("svazky", "a", {"svazek": "T"}, sloucit=True)
        self.assertEqual(self.nacti(), {"svazek": "T", "obce": ["x", "y"]})


if __name__ == "__main__":
    unittest.main()
