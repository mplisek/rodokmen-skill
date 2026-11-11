"""Statistiky: histogram věku při sňatku, počet předků doložených matrikou v generaci, barva rodu u dožití."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import statistiky  # noqa: E402


class Histogram(unittest.TestCase):
    def test_pasma_pokryji_kazdy_vek_jednou(self):
        vek = list(range(14, 81))
        h = statistiky.histogram(vek)
        self.assertEqual(sum(x["count"] for x in h), len(vek))
        self.assertEqual([x["name"] for x in h][0], "do 17")
        self.assertEqual([x["name"] for x in h][-1], "40 a víc")

    def test_hranice_pasem(self):
        h = {x["name"]: x["count"] for x in statistiky.histogram([17, 18, 19, 20, 29, 30, 39, 40])}
        self.assertEqual((h["do 17"], h["18–19"], h["20–21"], h["28–29"], h["30–34"], h["35–39"], h["40 a víc"]), (1, 2, 1, 1, 1, 1, 1))

    def test_prazdny_vstup_ma_vsechna_pasma(self):
        h = statistiky.histogram([])
        self.assertEqual(len(h), len(statistiky.VEK_PASMA))
        self.assertTrue(all(x["count"] == 0 for x in h))


class Export(unittest.TestCase):
    def test_generace_maji_dolozeno_a_rod_je_v_odkazech(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lide = {
                "a": dict(k=1, slug="a", name="Jan Novák", st="doc", gen=0, sex="M", facts=["* 1. 1. 1900 Obec"], lineSlug="novakove"),
                "b": dict(k=2, slug="b", name="Petr Novák", st="doc", gen=1, sex="M", facts=["* 1. 1. 1870 Obec", "† 1. 1. 1940"], lineSlug="novakove"),
                "c": dict(k=3, slug="c", name="Eva Nováková", st="prob", gen=1, sex="F", facts=["* 1. 1. 1875 Obec"], lineSlug=None),
            }
            site = dict(people=lide, records=[])
            vstup = d / "site.json"
            vystup = d / "statistiky.json"
            vstup.write_text(json.dumps(site, ensure_ascii=False), encoding="utf-8")
            stare = (statistiky.SITE, statistiky.OUT)
            statistiky.SITE, statistiky.OUT = str(vstup), str(vystup)
            try:
                statistiky.main()
            finally:
                statistiky.SITE, statistiky.OUT = stare
            out = json.loads(vystup.read_text(encoding="utf-8"))
        g = {x["gen"]: x for x in out["generace"]}
        self.assertEqual((g[1]["pocet"], g[1]["dolozeno"], g[1]["max"]), (2, 1, 2))
        self.assertEqual(out["doziti"]["list"][0]["rod"], "novakove")
        self.assertIn("snatek_histogram", out)
        self.assertEqual(len(out["snatek_histogram"]["M"]), len(statistiky.VEK_PASMA))


if __name__ == "__main__":
    unittest.main()
