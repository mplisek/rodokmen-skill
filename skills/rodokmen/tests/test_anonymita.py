"""scripts/anonymita.py (Fáze E, Q-E4, ADR 0008): kontrola anonymity před pushem do veřejného repozitáře podle lokálního seznamu zakázaných
řetězců. Prochází přidané řádky a zprávy všech commitů určených k pushi, při shodě skončí chybou s maskovaným nálezem a nikdy nemění historii.
Rozhraní: příkazy anonymita.py v dočasném git repozitáři (vymyšlená data), bez sítě."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKRIPT = REPO / "scripts" / "anonymita.py"
TAJNE = "Tajnýkmen"


class Anonymita(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.r = Path(self._tmp.name) / "repo"
        self.r.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.org")
        self.git("config", "user.name", "Tester")
        self.git("config", "commit.gpgsign", "false")
        (self.r / "README.md").write_text("start\n", encoding="utf-8")
        self.commit("start")
        self.zakladni = self.git("rev-parse", "HEAD").stdout.strip()
        self.seznam = self.r / ".anonymita-seznam"
        self.seznam.write_text(f"# jména z projektu\n{TAJNE}\n!docs/\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.r, capture_output=True, text=True, encoding="utf-8")

    def commit(self, zprava, soubory=()):
        for jmeno, text in soubory:
            p = self.r / jmeno
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.assertEqual(self.git("commit", "-q", "-m", zprava).returncode, 0)

    def anonymita(self, *args, stdin=None):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), *args], cwd=self.r, capture_output=True, text=True,
                              encoding="utf-8", input=stdin)

    def pred_pushem(self):
        return self.anonymita("pred-pushem", "--vuci", self.zakladni, "--seznam", str(self.seznam))

    # ---- hledání
    def test_cisty_repozitar_projde(self):
        self.commit("doc", [("a.md", "Nothing private here.\n")])
        r = self.pred_pushem()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_shoda_v_koncovem_stavu_je_maskovana(self):
        self.commit("add", [("a.md", f"Rodina {TAJNE} žila v Holicích.\n")])
        r = self.pred_pushem()
        self.assertNotEqual(r.returncode, 0)
        vystup = r.stdout + r.stderr
        self.assertIn("a.md", vystup)
        self.assertIn("Taj***", vystup)
        self.assertNotIn(TAJNE, vystup)                                            # nález se do výpisu nepíše celý

    def test_shoda_jen_v_prostrednim_commitu_selze(self):
        self.commit("leak", [("a.md", f"{TAJNE}\n")])
        mezi = self.git("rev-parse", "--short", "HEAD").stdout.strip()
        self.commit("remove", [("a.md", "clean\n")])
        self.commit("more", [("b.md", "also clean\n")])
        r = self.pred_pushem()
        self.assertNotEqual(r.returncode, 0)                                       # koncový stav je čistý, historie ne
        self.assertIn(mezi[:7], r.stdout + r.stderr)

    def test_shoda_ve_zprave_commitu(self):
        self.commit(f"fix for {TAJNE} branch", [("a.md", "x\n")])
        r = self.pred_pushem()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("zpráv", (r.stdout + r.stderr).lower())

    def test_diakritika_velikost_a_kmen(self):
        self.commit("add", [("a.md", "rodina TAJNYKMENOVE a tajnykmenova\n")])
        self.assertNotEqual(self.pred_pushem().returncode, 0)

    def test_vyjmuta_cesta_projde(self):
        self.commit("docs", [("docs/ukazka.md", f"{TAJNE}\n")])
        self.assertEqual(self.pred_pushem().returncode, 0)

    def test_regularni_vyraz_v_seznamu(self):
        self.seznam.write_text("re:cislo osoby \\d{3}\n", encoding="utf-8")
        self.commit("add", [("a.md", "viz číslo osoby 231 v datech\n")])
        self.assertNotEqual(self.pred_pushem().returncode, 0)

    def test_bez_seznamu_jen_varuje(self):
        self.seznam.unlink()
        self.commit("add", [("a.md", f"{TAJNE}\n")])
        r = self.pred_pushem()
        self.assertEqual(r.returncode, 0)
        self.assertIn("seznam", (r.stdout + r.stderr).lower())

    # ---- historie se nikdy nemění
    def test_historie_ani_strom_se_nezmeni(self):
        self.commit("leak", [("a.md", f"{TAJNE}\n")])
        pred = (self.git("rev-parse", "HEAD").stdout, self.git("log", "--format=%H %s").stdout, self.git("status", "--porcelain").stdout,
                (self.r / "a.md").read_bytes())
        self.assertNotEqual(self.pred_pushem().returncode, 0)
        po = (self.git("rev-parse", "HEAD").stdout, self.git("log", "--format=%H %s").stdout, self.git("status", "--porcelain").stdout,
              (self.r / "a.md").read_bytes())
        self.assertEqual(pred, po)

    # ---- hook pre-push
    def test_pre_push_cte_rozsah_ze_stdin(self):
        self.commit("leak", [("a.md", f"{TAJNE}\n")])
        hlava = self.git("rev-parse", "HEAD").stdout.strip()
        radek = f"refs/heads/main {hlava} refs/heads/main {self.zakladni}\n"
        r = self.anonymita("pre-push", "--seznam", str(self.seznam), stdin=radek)
        self.assertNotEqual(r.returncode, 0)
        nulte = "0" * 40
        r = self.anonymita("pre-push", "--seznam", str(self.seznam), "--vuci", self.zakladni,
                           stdin=f"refs/heads/novy {hlava} refs/heads/novy {nulte}\n")      # nová větev: jede se od --vuci
        self.assertNotEqual(r.returncode, 0)
        r = self.anonymita("pre-push", "--seznam", str(self.seznam), stdin=f"refs/heads/main {self.zakladni} refs/heads/main {self.zakladni}\n")
        self.assertEqual(r.returncode, 0)                                           # nic nového k pushnutí

    def test_nainstaluj_nastavi_hooks_path_a_hook_je_v_repozitari(self):
        self.assertTrue((REPO / ".githooks" / "pre-push").exists())
        self.assertTrue((REPO / ".anonymita-seznam.priklad").exists())
        r = self.anonymita("nainstaluj")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.git("config", "--get", "core.hooksPath").stdout.strip(), ".githooks")

    def test_navrhni_z_projektu_nic_nezapise_do_repozitare(self):
        projekt = Path(self._tmp.name) / "projekt"
        (projekt / "data").mkdir(parents=True)
        (projekt / "data" / "osoby.py").write_text(
            'P = {1: dict(n="Jan Tajnýkmen", y="1850"), 2: dict(n="Marie Tajnýkmenová"), 3: dict(n="Josef Novák st.")}\n', encoding="utf-8")
        r = self.anonymita("navrhni-z-projektu", str(projekt))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Tajnýkmen", r.stdout)
        self.assertEqual(self.git("status", "--porcelain").stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
