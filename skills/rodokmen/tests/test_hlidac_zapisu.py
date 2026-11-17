"""hlidac_zapisu.py (Q2, ADR 0001): hook zablokuje ruční zápis do chráněných souborů (denik.jsonl, verejne_otazky.json, generované
web/src/generated a web/src/data) a řekne, kterým skriptem se to dělá; nic jiného neblokuje (čtení, kopírování z chráněného souboru,
zápis skriptem, localhost, build, git, ostatní data). Rozhraní: vstup a výstup hooku a settings.json z novy_projekt.py. Bez sítě."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt  # noqa: E402


class HookZapisu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls.tmp.name)
        for d in ("data", "tools", "web/src/generated", "web/src/data", "web/src/pages", "pracovni"):
            (cls.p / d).mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def hook(self, nastroj, vstup, cwd=None):
        data = {"tool_name": nastroj, "tool_input": vstup, "cwd": str(cwd or self.p)}
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "hlidac_zapisu.py")], input=json.dumps(data),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return "allow", ""
        o = json.loads(r.stdout)["hookSpecificOutput"]
        return o["permissionDecision"], o["permissionDecisionReason"]

    def zamitne(self, nastroj, vstup, skript, cwd=None):
        rozhodnuti, duvod = self.hook(nastroj, vstup, cwd)
        self.assertEqual(rozhodnuti, "deny", (nastroj, vstup))
        self.assertIn(skript, duvod)

    def pusti(self, nastroj, vstup, cwd=None):
        self.assertEqual(self.hook(nastroj, vstup, cwd)[0], "allow", (nastroj, vstup))

    # ---- úpravy souborů nástroji Edit, Write
    def test_edit_a_write_chranenych_souboru(self):
        for nastroj in ("Edit", "Write", "MultiEdit"):
            self.zamitne(nastroj, {"file_path": "data/denik.jsonl"}, "denik.py")
            self.zamitne(nastroj, {"file_path": str(self.p / "data" / "verejne_otazky.json")}, "otazky.py")
            self.zamitne(nastroj, {"file_path": "web/src/generated/denik.md"}, "export_web.py")
            self.zamitne(nastroj, {"file_path": "web\\src\\data\\site.json"}, "export_web.py")      # zpětná lomítka z Windows
        self.zamitne("Edit", {"file_path": "src/generated/otazky.md"}, "export_web.py", cwd=self.p / "web")   # relativně k cwd

    def test_ostatni_soubory_se_pusti(self):
        for cesta in ("data/osoby.py", "data/zaznamy.json", "data/ukoly_na_noc.md", "web/src/pages/index.astro", "pracovni/x.txt",
                      "data/denik.md", "tools/denik.py", "docs/data/denik.jsonl"):
            self.pusti("Write", {"file_path": cesta})
            self.pusti("Edit", {"file_path": cesta})

    # ---- příkazy v Bashi a PowerShellu
    def test_zapis_pres_prikaz_je_zablokovan(self):
        for prikaz, skript in (
            ("echo '{}' >> data/denik.jsonl", "denik.py"),
            ("cat pracovni/x.json > data/verejne_otazky.json", "otazky.py"),
            ("sed -i 's/a/b/' data/verejne_otazky.json", "otazky.py"),
            ("rm web/src/generated/denik.md", "export_web.py"),
            ("cp pracovni/x data/denik.jsonl", "denik.py"),
            ("mv data/denik.jsonl pracovni/stary.jsonl", "denik.py"),
            ("tee data/denik.jsonl < pracovni/x", "denik.py"),
            ("python3 -c \"open('data/denik.jsonl','a').write('x')\"", "denik.py"),
        ):
            self.zamitne("Bash", {"command": prikaz}, skript)
        self.zamitne("PowerShell", {"command": "Set-Content data/denik.jsonl 'x'"}, "denik.py")
        self.zamitne("PowerShell", {"command": "Remove-Item web\\src\\generated\\denik.md"}, "export_web.py")

    def test_cteni_kopirovani_z_chraneneho_a_skripty_se_pousti(self):
        for prikaz in (
            "cat data/denik.jsonl",
            "grep křest data/verejne_otazky.json",
            "cp data/denik.jsonl pracovni/zaloha.jsonl",
            "head -3 web/src/generated/denik.md",
            "python3 -I tools/denik.py pridej --poznamka \"viz data/denik.jsonl\" --datum 2026-11-14",
            "python3 -I tools/export_web.py",
            "git checkout -- data/denik.jsonl",
            "git rm --cached data/verejne_otazky.json",
            "npm run build",
            "curl -s http://localhost:4321/denik/",
            "echo hotovo > pracovni/x.txt",
        ):
            self.pusti("Bash", {"command": prikaz})
        self.pusti("PowerShell", {"command": "Get-Content data/denik.jsonl"})

    def test_rozbity_vstup_prikaz_pusti(self):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "hlidac_zapisu.py")], input="není json",
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))                     # rozbitý hlídač nic neblokuje


class NastaveniProjektu(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name) / "projekt"

    def tearDown(self):
        self._tmp.cleanup()

    def nastaveni(self):
        return json.loads((self.p / ".claude" / "settings.json").read_text(encoding="utf-8"))

    def hooky(self, s=None):
        return json.dumps((s or self.nastaveni()).get("hooks", {}))

    def test_novy_projekt_ma_oba_hooky(self):
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        h = self.hooky()
        self.assertIn("hlidac_site.py", h)
        self.assertIn("hlidac_zapisu.py", h)
        s = self.nastaveni()
        zapisu = [x for x in s["hooks"]["PreToolUse"] if "hlidac_zapisu.py" in json.dumps(x)][0]
        for nastroj in ("Edit", "Write", "MultiEdit", "Bash", "PowerShell"):
            self.assertIn(nastroj, zapisu["matcher"])

    def test_aktualizace_zapne_hook_zapisu_u_projektu_jen_s_hlidacem_site(self):
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        s = self.nastaveni()
        s["hooks"]["PreToolUse"] = [x for x in s["hooks"]["PreToolUse"] if "hlidac_zapisu.py" not in json.dumps(x)]
        s.setdefault("permissions", {})["deny"] = ["Bash(rm:*)"]                       # vlastní pravidlo uživatele
        (self.p / ".claude" / "settings.json").write_text(json.dumps(s), encoding="utf-8")
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        s = self.nastaveni()
        self.assertIn("hlidac_zapisu.py", self.hooky(s))
        self.assertEqual(s["permissions"]["deny"], ["Bash(rm:*)"])

    def test_bez_hlidace_vypne_oba_a_zustane_vypnuto(self):
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        self.assertEqual(novy_projekt(self.p, "--bez-hlidace").returncode, 0)
        self.assertNotIn("hooks", self.nastaveni())
        self.assertEqual(novy_projekt(self.p).returncode, 0)                            # další aktualizace je nezapne
        self.assertNotIn("hooks", self.nastaveni())

    def test_cizi_hook_zustane(self):
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        s = self.nastaveni()
        s["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [{"type": "command", "command": "echo cizi"}]})
        (self.p / ".claude" / "settings.json").write_text(json.dumps(s), encoding="utf-8")
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        self.assertIn("echo cizi", self.hooky())


if __name__ == "__main__":
    unittest.main()
