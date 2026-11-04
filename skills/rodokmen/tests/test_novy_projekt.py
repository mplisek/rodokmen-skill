"""novy_projekt.py: založení, aktualizace staršího projektu (zálohy webu, nástroje, data), nastavení .claude/settings.json."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import SKILL, novy_projekt  # noqa: E402


class NovyProjekt(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.p = self.tmp / "rodokmen"
        r = novy_projekt(self.p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def tearDown(self):
        self._tmp.cleanup()

    def nastaveni(self):
        return json.loads((self.p / ".claude" / "settings.json").read_text(encoding="utf-8"))

    def test_zalozeni(self):
        for f in ("CLAUDE.md", ".gitignore", ".gitattributes", "data/osoby.py", "web/package.json", "tools/slusne.py",
                  "tools/soubory.py", "tools/cache.py", ".claude/launch.json"):
            self.assertTrue((self.p / f).exists(), f)
        self.assertEqual((self.p / ".skill_verze").read_text(encoding="utf-8").strip(),
                         (SKILL / "VERZE").read_text(encoding="utf-8").strip())
        self.assertEqual(self.nastaveni()["permissions"]["deny"], ["Bash(curl:*)", "Bash(wget:*)"])

    def test_help_nezalozi_slozku(self):
        r = novy_projekt("--help")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((Path.cwd() / "--help").exists())

    def test_aktualizace_necha_vlastni_upravy_a_data(self):
        # od 0.8.0 projekt pamatuje šablonu (.skill_sablona/): vlastní úprava při nezměněné šabloně zůstane
        index = self.p / "web" / "src" / "pages" / "index.astro"
        sablona = index.read_text(encoding="utf-8")
        index.write_text(sablona + "\n<!-- moje úprava -->\n", encoding="utf-8")
        osoby = self.p / "data" / "osoby.py"
        osoby.write_text(osoby.read_text(encoding="utf-8") + "\n# moje data\n", encoding="utf-8")
        (self.p / "tools" / "muj_skript.py").write_text("print(1)\n", encoding="utf-8")

        r = novy_projekt(self.p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("moje úprava", index.read_text(encoding="utf-8"))                 # úprava webu zůstala
        self.assertIn("Ponecháno", r.stdout)
        self.assertEqual((self.p / "tools" / "kontrola.py").read_bytes(), (SKILL / "tools" / "kontrola.py").read_bytes())
        self.assertIn("# moje data", osoby.read_text(encoding="utf-8"))                 # data zůstala
        self.assertTrue((self.p / "tools" / "muj_skript.py").exists())                  # cizí soubory nemaže

    def test_nastaveni_zachova_cizi_klice_a_prepina_hlidac(self):
        s = self.nastaveni()
        s["enabledPlugins"] = {"rodokmen@rodokmen-skill": True}
        s["permissions"]["deny"].append("Bash(rm:*)")
        (self.p / ".claude" / "settings.json").write_text(json.dumps(s), encoding="utf-8")

        self.assertEqual(novy_projekt(self.p, "--hlidac").returncode, 0)
        s = self.nastaveni()
        self.assertEqual(s["enabledPlugins"], {"rodokmen@rodokmen-skill": True})
        self.assertEqual(s["permissions"]["deny"], ["Bash(curl:*)", "Bash(wget:*)", "Bash(rm:*)"])   # bez duplicit
        self.assertIn("hlidac_site.py", json.dumps(s["hooks"]))

        self.assertEqual(novy_projekt(self.p).returncode, 0)          # bez přepínače hlídač zůstane
        self.assertIn("hlidac_site.py", json.dumps(self.nastaveni()["hooks"]))
        self.assertEqual(novy_projekt(self.p, "--bez-hlidace").returncode, 0)
        s = self.nastaveni()
        self.assertNotIn("hooks", s)
        self.assertEqual(s["enabledPlugins"], {"rodokmen@rodokmen-skill": True})

    def test_skripty_sh_maji_lf(self):
        for sh in (self.p / "tools").glob("*.sh"):
            self.assertNotIn(b"\r\n", sh.read_bytes(), sh.name)


if __name__ == "__main__":
    unittest.main()
