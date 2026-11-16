"""Zapojení brány (Fáze D, Q-D4): novy_projekt.py při změně verze skillu v projektu zneplatní starý výsledek brány a hlídač
(hlidac_site.py) nepustí nasazení (testovací ani ostré), dokud pracovni/brana.json není zelený pro aktuální verzi projektu. Ostatní
příkazy a projekty bez verze nevadí. Rozhraní: vstup a výstup hooku, soubory projektu. Bez sítě."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt  # noqa: E402

NASAZENI = ["npm run nasadit", "npm run nasadit-cloudflare", "cd web && npm run nasadit", "npx netlify deploy --alias test",
            "npx -y netlify-cli deploy --prod", "npx -y wrangler@4 deploy", "node scripts/nasadit.mjs", "npm run deploy-caprover"]
JINE = ["npm run build", "npm run data", "git status", "npx netlify status", "git commit -m \"po npm run nasadit\"",
        "python3 -I tools/brana.py", "npm run nahled"]


class Zapojeni(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)
        self.verze = (self.p / ".skill_verze").read_text(encoding="utf-8").strip()
        self.znacka = self.p / "pracovni" / "brana.json"
        self.znacka.parent.mkdir(exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def zapis(self, vysledek="zelena", verze=None):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", "-c",
                            "import sys, json; sys.path.insert(0, 'tools'); import brana; print(json.dumps(brana.otisky()))"],
                           cwd=self.p, capture_output=True, text=True, encoding="utf-8")
        self.znacka.write_text(json.dumps({"vysledek": vysledek, "verze": verze or self.verze, **json.loads(r.stdout), "cas": "2026-01-01"}),
                               encoding="utf-8")

    def hlidac(self, prikaz, cwd=None, nastroj="Bash"):
        vstup = json.dumps({"tool_name": nastroj, "tool_input": {"command": prikaz}, "cwd": str(cwd or self.p)})
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "hlidac_site.py")], input=vstup,
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return "allow", ""
        o = json.loads(r.stdout)["hookSpecificOutput"]
        return o["permissionDecision"], o["permissionDecisionReason"]

    # ---- hlídač nasazení
    def test_bez_znacky_nasazeni_zamitne_a_poradi_branu(self):
        for p in NASAZENI:
            rozhodnuti, duvod = self.hlidac(p)
            self.assertEqual(rozhodnuti, "deny", p)
            self.assertIn("brana.py", duvod)

    def test_cervena_a_nepokryto_zamitne(self):
        for v in ("cervena", "nepokryto"):
            self.zapis(v)
            self.assertEqual(self.hlidac("npm run nasadit")[0], "deny", v)

    def test_zelena_stare_verze_zamitne(self):
        self.zapis("zelena", verze="0.0.1")
        self.assertEqual(self.hlidac("npm run nasadit")[0], "deny")

    def test_zelena_aktualni_verze_pusti(self):
        self.zapis()
        for p in NASAZENI:
            self.assertEqual(self.hlidac(p)[0], "allow", p)

    def test_zmena_po_zelene_brane_nasazeni_zamitne(self):
        """E5, scénář 12: zelená brána platí jen pro stav, který zkontrolovala – data, šablony i sestavený web."""
        dist = self.p / "web" / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<html><body>a</body></html>", encoding="utf-8")
        sablona = self.p / "web" / "src" / "pages" / "index.astro"
        for nazev, soubor, co in (("data", self.p / "data" / "pribeh.md", "data"), ("šablona", sablona, "web/src"),
                                  ("dist", dist / "index.html", "web/dist")):
            self.zapis()
            self.assertEqual(self.hlidac("npm run nasadit")[0], "allow", nazev)
            puvodni = soubor.read_bytes() if soubor.exists() else b""
            soubor.write_bytes(puvodni + b" <!-- zmena -->")
            rozhodnuti, duvod = self.hlidac("npm run nasadit")
            self.assertEqual(rozhodnuti, "deny", nazev)
            self.assertIn(co, duvod)
            self.assertIn("brana.py", duvod)

    def test_znacka_ze_starsi_brany_bez_otisku_nestaci(self):
        self.znacka.write_text(json.dumps({"vysledek": "zelena", "verze": self.verze, "otisk_dat": "x", "cas": "2026-01-01"}), encoding="utf-8")
        self.assertEqual(self.hlidac("npm run nasadit")[0], "deny")

    def test_ostatni_prikazy_se_pousti_i_bez_znacky(self):
        for p in JINE:
            self.assertEqual(self.hlidac(p)[0], "allow", p)

    def test_powershell_se_hlida_stejne(self):
        self.assertEqual(self.hlidac("npm run nasadit", nastroj="PowerShell")[0], "deny")

    def test_mimo_projekt_a_bez_verze_se_nehlida(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.hlidac("npm run nasadit", cwd=t)[0], "allow")
        (self.p / ".skill_verze").unlink()
        self.assertEqual(self.hlidac("npm run nasadit")[0], "allow")

    def test_poskozena_znacka_zamitne(self):
        self.znacka.write_text("není json", encoding="utf-8")
        self.assertEqual(self.hlidac("npm run nasadit")[0], "deny")

    # ---- novy_projekt.py
    def test_zmena_verze_smaze_znacku(self):
        self.zapis()
        (self.p / ".skill_verze").write_text("0.0.1\n", encoding="utf-8")
        r = novy_projekt(self.p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.znacka.exists())
        self.assertIn("brana.py", r.stdout)
        self.assertEqual((self.p / ".skill_verze").read_text(encoding="utf-8").strip(), self.verze)

    def test_stejna_verze_znacku_nechava(self):
        self.zapis()
        r = novy_projekt(self.p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.znacka.exists())


if __name__ == "__main__":
    unittest.main()
