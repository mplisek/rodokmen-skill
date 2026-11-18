"""Šablona dat po přechodu na originál: nový projekt dostane deník denik.jsonl, veřejné otázky verejne_otazky.json, plán
ukoly.md a archivni_dotazy.md originálu, žádné fronty úkolů; prázdné nové úložiště nepřebije dosavadní soubory.
Rozhraní: soubory ve složce data po novy_projekt.py a export webu. Bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402


class SablonaFormy(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name) / "projekt"

    def tearDown(self):
        self._tmp.cleanup()

    def test_novy_projekt_ma_denik_otazky_plan_a_zadne_fronty(self):
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        d = self.p / "data"
        for f in ("denik.jsonl", "verejne_otazky.json", "ukoly.md", "archivni_dotazy.md"):
            self.assertTrue((d / f).exists(), f)
        for f in ("research_log.md", "otazky_pro_rodinu.md", "rezim.json"):
            self.assertFalse((d / f).exists(), f)
        self.assertFalse(list(d.glob("ukoly_*.md")))
        self.assertEqual((d / "denik.jsonl").read_text(encoding="utf-8"), "")
        self.assertEqual(json.loads((d / "verejne_otazky.json").read_text(encoding="utf-8")), {"otazky": []})

    def test_prazdne_nove_uloziste_nezastini_dosavadni_soubory(self):
        # ukázka nemá nové úložiště; prázdné soubory z šablony (nebo ručně založené) nesmějí zrušit deník ani otázky
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)
        d = self.p / "data"
        (d / "denik.jsonl").write_text("", encoding="utf-8")
        (d / "verejne_otazky.json").write_text('{"otazky": []}', encoding="utf-8")
        spust(self.p, "export_web.py")
        gen = self.p / "web" / "src" / "generated"
        self.assertTrue((gen / "denik.md").read_text(encoding="utf-8").strip())
        self.assertTrue((gen / "otazky.md").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
