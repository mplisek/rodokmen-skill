"""Stránka „Co hledáme“: ISSUES s osobou a stavem, otázky pro rodinu podle rodů, kontrola tvaru (kontrola.py)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt, spust  # noqa: E402

sys.path.insert(0, str(TOOLS))
import export_web as ew  # noqa: E402

LINES = {"novakove": dict(k=8, slug="novakove", name="Novákové"), "kralove": dict(k=10, slug="kralove", name="Králové"),
         "hrubi": dict(k=11, slug="hrubi", name="Hrubí")}


class Funkce(unittest.TestCase):
    def test_issue_rows(self):
        r = ew.issue_rows([dict(k=16, otazka="A?", stav="hypotéza", text="t"),
                           ("B?", "Vyřešeno: už víme"), ("C?", "bez stavu"), "D?"],
                          lambda k: f"s{k}", lambda k: "novakove" if k == 16 else None)
        self.assertEqual(r[0], dict(title="A?", text="t", stav="hypotéza", person="s16", rod="novakove"))
        self.assertEqual((r[1]["stav"], r[1]["text"], r[1]["person"]), ("vyřešeno", "už víme", None))
        self.assertEqual((r[2]["stav"], r[2]["text"]), ("otevřené", "bez stavu"))
        self.assertEqual(r[3]["title"], "D?")

    def test_rod_nadpisu_podle_kmene(self):
        self.assertEqual(ew.rod_nadpisu("Novákovi (Holice)", LINES)["k"], 8)
        self.assertEqual(ew.rod_nadpisu("Hrubí", LINES)["k"], 11)
        self.assertIsNone(ew.rod_nadpisu("Dokumenty doma", LINES))

    def test_podle_rodu(self):
        md = "Úvod.\n\n## Hrubí\n- h\n\n## Dokumenty doma\n- d\n\n## Novákové\n- n\n"
        self.assertEqual(ew.podle_rodu(md, LINES), "Úvod.\n\n## Dokumenty doma\n- d\n\n## Novákové\n- n\n## Hrubí\n- h\n\n")


class Ukazka(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls._tmp.name) / "ukazka"
        assert novy_projekt(cls.p, "--ukazka").returncode == 0

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_export_a_kontrola(self):
        self.assertIn("Vše v pořádku", spust(self.p, "kontrola.py").stdout)
        spust(self.p, "export_web.py")
        site = json.loads((self.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        jakub = next(i for i in site["issues"] if i["title"].startswith("Odkud přišel Jakub"))
        self.assertEqual((jakub["rod"], jakub["stav"]), ("novakove", "otevřené"))
        self.assertTrue(site["people"][jakub["person"]]["name"].startswith("Jakub Novák"))
        otazky = (self.p / "web" / "src" / "generated" / "otazky.md").read_text(encoding="utf-8")
        poradi = [otazky.index(h) for h in ("## Dokumenty doma", "## Novákové", "## Hrubí", "## Kučerovi")]
        self.assertEqual(poradi, sorted(poradi))

    def test_kontrola_hlida_tvar(self):
        d = self.p / "data"
        puvodni = {f: (d / f).read_text(encoding="utf-8") for f in ("otazky_pro_rodinu.md", "archivni_dotazy.md", "osoby.py")}
        try:
            (d / "otazky_pro_rodinu.md").write_text(puvodni["otazky_pro_rodinu.md"] + "\n## Sousedé\n- 3. ODPOVĚZENO 6. 11.\n",
                                                    encoding="utf-8")
            (d / "archivni_dotazy.md").write_text("# P\n\n## Jan Novák (zapsáno 2026-10-31)\n- křest\n", encoding="utf-8")
            (d / "osoby.py").write_text(puvodni["osoby.py"] + '\nISSUES.append(("Kdo?", "Libice, kniha 737"))\n'
                                        'ISSUES.append(dict(k=99999, otazka="X?", stav="nevim"))\n', encoding="utf-8")
            out = spust(self.p, "kontrola.py", check=False).stdout
            for hlaska in ("„Sousedé“ není rod", "zodpovězenou položku", "zapsáno", "nevypadá jako archiv",
                           "převeď na dict", "stav „nevim“", "k=99999"):
                self.assertIn(hlaska, out)
        finally:
            for f, t in puvodni.items():
                (d / f).write_text(t, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
