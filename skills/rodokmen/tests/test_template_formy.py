"""Šablona dat po Fázi A: nový projekt dostane fronty pod jmény ukoly_* a prázdné nové úložiště (denik.jsonl,
verejne_otazky.json), starý projekt se starými názvy front o ně nepřijde a prázdné nové úložiště nepřebije dosavadní soubory.
Rozhraní: soubory ve složce data po novy_projekt.py a export webu. Bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

STARE = ("archivni_dotazy.md", "otazky_pro_rodinu.md", "research_log.md")


class SablonaFormy(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name) / "projekt"

    def tearDown(self):
        self._tmp.cleanup()

    def test_novy_projekt_ma_nove_nazvy_front_a_prazdne_uloziste(self):
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        d = self.p / "data"
        for f in ("ukoly_na_rodinu.md", "ukoly_dotazy_na_archivy.md", "denik.jsonl", "verejne_otazky.json"):
            self.assertTrue((d / f).exists(), f)
        for f in STARE:
            self.assertFalse((d / f).exists(), f)
        self.assertEqual((d / "denik.jsonl").read_text(encoding="utf-8"), "")
        self.assertEqual(json.loads((d / "verejne_otazky.json").read_text(encoding="utf-8")), {"otazky": []})

    def test_stary_projekt_se_starymi_nazvy_nedostane_prazdne_fronty_vedle(self):
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        d = self.p / "data"
        (d / "ukoly_na_rodinu.md").rename(d / "otazky_pro_rodinu.md")                # jako projekt před přejmenováním
        (d / "ukoly_dotazy_na_archivy.md").rename(d / "archivni_dotazy.md")
        (d / "otazky_pro_rodinu.md").write_text("# O\n\n## U-0001 | P2 | stav:otevřeno\nstarý úkol\n", encoding="utf-8")
        self.assertEqual(novy_projekt(self.p).returncode, 0)                          # aktualizace
        self.assertFalse((d / "ukoly_na_rodinu.md").exists())                          # prázdná šablona by starý soubor zastínila
        self.assertFalse((d / "ukoly_dotazy_na_archivy.md").exists())
        self.assertIn("starý úkol", (d / "otazky_pro_rodinu.md").read_text(encoding="utf-8"))

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
