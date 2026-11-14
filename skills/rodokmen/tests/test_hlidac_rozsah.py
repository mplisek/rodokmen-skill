"""Rozsah hlídače sítě: střeží archivy, nebrání testování vlastní práce (localhost, vlastní nasazení Netlify a Cloudflare,
vlastní domény z data/web.json). Rozhraní: vstup a výstup hooku (příkaz -> povolit / zamítnout) a settings.json,
který vytvoří novy_projekt.py. Bez sítě."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt  # noqa: E402


def hlidac(prikaz, cwd, nastroj="Bash"):
    vstup = json.dumps({"tool_name": nastroj, "tool_input": {"command": prikaz}, "cwd": str(cwd)})
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "hlidac_site.py")], input=vstup,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else "allow"


class VlastniNasazeni(unittest.TestCase):
    """Testy a kontroly nasazeného webu jsou volné (test i produkce, Netlify i Cloudflare)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cwd = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pusti_localhost_a_vlastni_nasazeni(self):
        for prikaz in (
            "curl -s http://localhost:4321/hledame/",
            "curl -sI http://127.0.0.1:4321/denik/",
            "curl -s https://test--mujweb.netlify.app/",
            "curl -s https://mujweb.netlify.app/prihlaseni.html",
            "curl -s https://rodokmen.nazev.workers.dev/",
            "curl -s https://mujweb.pages.dev/",
            "wget -q https://mujweb.pages.dev/index.html",
            "python3 -c \"import urllib.request; urllib.request.urlopen('https://mujweb.pages.dev/')\"",
        ):
            with self.subTest(prikaz=prikaz):
                self.assertEqual(hlidac(prikaz, self.cwd), "allow")

    def test_vlastni_domena_jen_z_web_json(self):
        prikaz = "curl -s https://rodina.example.org/"
        self.assertEqual(hlidac(prikaz, self.cwd), "deny")   # bez web.json cizí doména neprojde
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            (Path(d) / "data" / "web.json").write_text(json.dumps({"domeny": ["rodina.example.org"]}), encoding="utf-8")
            self.assertEqual(hlidac(prikaz, d), "allow")
            self.assertEqual(hlidac("curl -s https://sub.rodina.example.org/", d), "allow")
            self.assertEqual(hlidac("curl -s https://jina.example.org/", d), "deny")   # jen uvedená doména

    def test_archiv_zustava_hlidany(self):
        for prikaz in (
            "curl -s https://aron.vychodoceskearchivy.cz/x",
            "curl -s https://digi.archives.cz/da/",
            "curl -s 'https://aron.vychodoceskearchivy.cz/?u=https://mujweb.pages.dev/'",   # volný host jen jako parametr
            "curl -s https://notpages.dev/",                                               # shoda jen po hranici domény
        ):
            with self.subTest(prikaz=prikaz):
                self.assertEqual(hlidac(prikaz, self.cwd), "deny")


class NastaveniProjektu(unittest.TestCase):
    """novy_projekt.py nezapisuje plošný zákaz curl/wget; ochrana archivů je hook, který se nikdy nevypne sám."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name) / "projekt"
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)

    def tearDown(self):
        self._tmp.cleanup()

    def nastaveni(self):
        return json.loads((self.p / ".claude" / "settings.json").read_text(encoding="utf-8"))

    def zapsat(self, data):
        (self.p / ".claude" / "settings.json").write_text(json.dumps(data), encoding="utf-8")

    def test_novy_projekt_bez_plosneho_zakazu_a_s_hlidacem(self):
        s = self.nastaveni()
        self.assertNotIn("Bash(curl:*)", json.dumps(s))
        self.assertNotIn("Bash(wget:*)", json.dumps(s))
        self.assertIn("hlidac_site.py", json.dumps(s["hooks"]))   # ochrana archivů zůstala, jen úzká

    def test_aktualizace_stareho_projektu_vyjme_zakaz_a_zapne_hlidac(self):
        # starý tvar: plošný zákaz, bez hooku, plus vlastní pravidlo uživatele
        self.zapsat({"permissions": {"deny": ["Bash(curl:*)", "Bash(wget:*)", "Bash(rm:*)"]}})
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        s = self.nastaveni()
        self.assertEqual(s["permissions"]["deny"], ["Bash(rm:*)"])      # naše pravidla pryč, cizí zůstalo
        self.assertIn("hlidac_site.py", json.dumps(s["hooks"]))         # ochrana se aktualizací nezmenšila

    def test_vypnuty_hlidac_zustane_vypnuty(self):
        self.assertEqual(novy_projekt(self.p, "--bez-hlidace").returncode, 0)
        s = self.nastaveni()
        self.assertNotIn("hooks", s)
        self.assertNotIn("Bash(curl:*)", json.dumps(s))
        self.assertEqual(novy_projekt(self.p).returncode, 0)             # další aktualizace ho sama nezapne
        self.assertNotIn("hooks", self.nastaveni())

    def test_cizi_pravidla_a_klice_zustanou(self):
        s = self.nastaveni()
        s["enabledPlugins"] = {"rodokmen@rodokmen-skill": True}
        s.setdefault("permissions", {}).setdefault("deny", []).append("Bash(rm:*)")
        self.zapsat(s)
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        s = self.nastaveni()
        self.assertEqual(s["enabledPlugins"], {"rodokmen@rodokmen-skill": True})
        self.assertEqual(s["permissions"]["deny"], ["Bash(rm:*)"])


if __name__ == "__main__":
    unittest.main()
