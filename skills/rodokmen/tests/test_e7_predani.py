"""E7 (podnět z bádání 16. 11. 2026): data/STAV.md je předání rozpracované práce do nové bádací session. Oddíl Rozpracováno vede
tools/stav.py predani ze souboru v pracovni/ (celý, nebo vůbec), úkoly jen odkazem na frontu, podklady jen verzované; pravidla od uživatele
mají vlastní oddíl (stav.py pravidlo); stav.py na začátku sezení obojí vypíše; kontrola a vyrad slouží migraci staršího STAV.md;
ruční úpravy STAV.md badatelem hlídač zamítne. Průchod v dočasném projektu s kopií nástrojů, bez sítě."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import SKILL, TOOLS  # noqa: E402

REPO = SKILL.parents[1]
HOOK = REPO / "hooks" / "hlidac_orchestratora.py"

STARY_STAV = """# Stav rodokmenu a pravidla práce

## Pro koho

- Výchozí osoba: Josef Vzorný

## Kde co je

| Soubor | Obsah |
|---|---|

## Pravidla

1. Pravidlo ze skillu.

## Rozpracováno (aktualizovat průběžně)

- ručně psaná poznámka, podklad v `pracovni/stare.md`

## Fronta úkolů (aktualizováno 2026-10-31)

- opsaný úkol
"""


class Predani(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projekt"
        (self.root / "data").mkdir(parents=True)
        (self.root / "pracovni").mkdir()
        shutil.copytree(TOOLS, self.root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "data" / "STAV.md").write_text(STARY_STAV, encoding="utf-8", newline="\n")
        self.env = dict(os.environ, PYTHONIOENCODING="utf-8", RODOKMEN_MAPY=str(Path(self.tmp.name) / "mapy"),
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.py("fronta.py", "pridej", "noc", "--text", "Křest osoby 88", "--typ", "krest")

    def tearDown(self):
        self.tmp.cleanup()

    def py(self, nastroj, *args):
        return subprocess.run([sys.executable, "-X", "utf8", str(self.root / "tools" / nastroj), *args], cwd=self.root, capture_output=True,
                              text=True, encoding="utf-8", env=self.env)

    def stav(self):
        return (self.root / "data" / "STAV.md").read_text(encoding="utf-8")

    def soubor(self, jmeno, polozky):
        (self.root / "pracovni" / jmeno).write_text(json.dumps({"schema": "predani/1", "polozky": polozky}, ensure_ascii=False),
                                                    encoding="utf-8")
        return f"pracovni/{jmeno}"

    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True, encoding="utf-8", env=self.env)

    # --- předání ---

    def test_predani_prepise_jen_rozpracovano_a_stav_ho_vypise(self):
        p = self.soubor("predani.json", [{"co": "Křest osoby 88 v knize 712", "posledni_krok": "přečteny snímky 40–45",
                                          "dal": "dočíst snímky 46–52", "ukoly": ["U-0001"]}])
        r = self.py("stav.py", "predani", p, "--bez-commitu")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.stav()
        self.assertIn("Křest osoby 88 v knize 712", s)
        self.assertIn("dočíst snímky 46–52", s)
        self.assertIn("U-0001", s)
        self.assertNotIn("ručně psaná poznámka", s)                 # starý obsah oddílu je nahrazen celý
        self.assertIn("- Výchozí osoba: Josef Vzorný", s)           # ostatní oddíly beze změny
        self.assertIn("## Fronta úkolů", s)                          # oddíly navíc odstraní až vyrad, ne předání
        self.assertEqual(s.count("## Rozpracováno"), 1)
        out = self.py("stav.py").stdout
        self.assertIn("předání", out)
        self.assertIn("dočíst snímky 46–52", out)

    def test_predani_odmitne_neexistujici_ukol_a_nic_nezmeni(self):
        pred = self.stav()
        p = self.soubor("predani.json", [{"co": "něco", "dal": "pokračovat", "ukoly": ["U-0999"]}])
        r = self.py("stav.py", "predani", p, "--bez-commitu")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("U-0999", r.stdout + r.stderr)
        self.assertEqual(self.stav(), pred)

    def test_predani_odmitne_chybejici_pole_a_dlouhy_text(self):
        pred = self.stav()
        for pol in ({"co": "", "dal": "x"}, {"co": "x"}, {"co": "x" * 700, "dal": "y"}, {"co": "x", "dal": "y", "ukoly": ["0001"]},
                    {"co": "## Nový oddíl", "dal": "y"}):
            r = self.py("stav.py", "predani", self.soubor("p.json", [pol]), "--bez-commitu")
            self.assertEqual(r.returncode, 1, (pol, r.stdout))
            self.assertEqual(self.stav(), pred, pol)
        (self.root / "pracovni" / "spatne.json").write_text(json.dumps({"schema": "jine/1", "polozky": []}), encoding="utf-8")
        self.assertEqual(self.py("stav.py", "predani", "pracovni/spatne.json", "--bez-commitu").returncode, 1)

    def test_podklad_z_pracovni_se_presune_do_data_predani(self):
        (self.root / "pracovni" / "podklad.md").write_text("rozbor knihy\n", encoding="utf-8")
        p = self.soubor("predani.json", [{"co": "rozbor knihy", "dal": "pokračovat", "podklady": ["pracovni/podklad.md"]}])
        r = self.py("stav.py", "predani", p, "--bez-commitu")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.root / "data" / "predani" / "podklad.md").exists())
        self.assertFalse((self.root / "pracovni" / "podklad.md").exists())
        self.assertIn("data/predani/podklad.md", self.stav())
        self.assertNotIn("pracovni/podklad.md", self.stav())

    def test_chybejici_podklad_zastavi_vse_vcetne_presunu(self):
        (self.root / "pracovni" / "a.md").write_text("a\n", encoding="utf-8")
        pred = self.stav()
        p = self.soubor("predani.json", [{"co": "x", "dal": "y", "podklady": ["pracovni/a.md", "data/neni.md"]}])
        r = self.py("stav.py", "predani", p, "--bez-commitu")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.stav(), pred)
        self.assertTrue((self.root / "pracovni" / "a.md").exists())          # nic se nepřesunulo
        self.assertFalse((self.root / "data" / "predani").exists())
        for spatna in ("../mimo.md", "/etc/passwd", "C:/x.md"):
            r = self.py("stav.py", "predani", self.soubor("p.json", [{"co": "x", "dal": "y", "podklady": [spatna]}]), "--bez-commitu")
            self.assertEqual(r.returncode, 1, spatna)

    def test_nanecisto_nic_nezmeni(self):
        (self.root / "pracovni" / "a.md").write_text("a\n", encoding="utf-8")
        pred = self.stav()
        p = self.soubor("predani.json", [{"co": "x", "dal": "y", "podklady": ["pracovni/a.md"]}])
        r = self.py("stav.py", "predani", p, "--nanecisto")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.stav(), pred)
        self.assertTrue((self.root / "pracovni" / "a.md").exists())

    def test_prazdne_predani(self):
        r = self.py("stav.py", "predani", self.soubor("p.json", []), "--bez-commitu")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nic rozpracovaného", self.stav())

    def test_predani_commitne_stav_a_podklady(self):
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "zaklad")
        (self.root / "pracovni" / "podklad.md").write_text("rozbor\n", encoding="utf-8")
        p = self.soubor("predani.json", [{"co": "rozbor", "dal": "pokračovat", "podklady": ["pracovni/podklad.md"]}])
        r = self.py("stav.py", "predani", p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.git("status", "--porcelain", "data").stdout.strip(), "")
        zmeny = self.git("show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertEqual(sorted(zmeny), ["data/STAV.md", "data/predani/podklad.md"])

    # --- pravidla od uživatele ---

    def test_pravidlo_od_uzivatele_ma_vlastni_oddil_a_stav_ho_vypise(self):
        r = self.py("stav.py", "pravidlo", "Rodinné dokumenty zapisovat celé, i u žijících", "--bez-commitu")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.stav()
        self.assertIn("## Pravidla od uživatele", s)
        self.assertLess(s.index("## Pravidla od uživatele"), s.index("## Rozpracováno"))
        self.assertIn("Rodinné dokumenty zapisovat celé", s)
        self.py("stav.py", "pravidlo", "Druhé pravidlo", "--bez-commitu")
        self.assertEqual(self.stav().count("## Pravidla od uživatele"), 1)
        out = self.py("stav.py").stdout
        self.assertIn("Rodinné dokumenty zapisovat celé", out)
        self.assertIn("Druhé pravidlo", out)
        self.assertEqual(self.py("stav.py", "pravidlo", "  ", "--bez-commitu").returncode, 1)

    # --- migrace staršího STAV.md ---

    def test_kontrola_najde_rucni_oddil_oddil_navic_a_pracovni(self):
        r = self.py("stav.py", "kontrola")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Fronta úkolů", r.stdout)
        self.assertIn("pracovni/stare.md", r.stdout)
        self.assertIn("ručně", r.stdout)
        out = self.py("stav.py").stdout                              # začátek sezení na nesoulad upozorní
        self.assertIn("stav.py kontrola", out)

    def test_vyrad_odstrani_jen_oddil_navic(self):
        r = self.py("stav.py", "vyrad", "Fronta úkolů", "--bez-commitu")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("opsaný úkol", r.stdout)                       # vypíše, co odstranil
        self.assertNotIn("## Fronta úkolů", self.stav())
        for chraneny in ("Pro koho", "Pravidla", "Rozpracováno", "Kde co je"):
            self.assertEqual(self.py("stav.py", "vyrad", chraneny, "--bez-commitu").returncode, 1, chraneny)
        self.assertEqual(self.py("stav.py", "vyrad", "Neexistuje", "--bez-commitu").returncode, 1)
        p = self.soubor("p.json", [{"co": "x", "dal": "y"}])
        self.py("stav.py", "predani", p, "--bez-commitu")
        self.assertEqual(self.py("stav.py", "kontrola").returncode, 0, self.py("stav.py", "kontrola").stdout)

    # --- úklid pracovních souborů (podnět z bádání 17. 11. 2026: smazání v pracovni/ hlídač zamítl, rm badatel nemá) ---

    def test_uklid_smaze_jen_soubory_v_pracovni(self):
        for f in ("oprava_probe.json", "b.txt"):
            (self.root / "pracovni" / f).write_text("x", encoding="utf-8")
        r = self.py("stav.py", "uklid", "pracovni/oprava_probe.json", "pracovni/b.txt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.root / "pracovni" / "oprava_probe.json").exists())
        self.assertFalse((self.root / "pracovni" / "b.txt").exists())

    def test_uklid_odmitne_mimo_pracovni_slozky_a_rozpracovane(self):
        (self.root / "pracovni" / "ok.txt").write_text("x", encoding="utf-8")
        (self.root / "pracovni" / "slozka").mkdir()
        (self.root / "pracovni" / "zadani").mkdir()
        (self.root / "pracovni" / "zadani" / "U-0001.json").write_text("{}", encoding="utf-8")   # úkol U-0001 je ve frontě
        (self.root / "pracovni" / "zapis_U-0001.rozpracovano").write_text("x", encoding="utf-8")
        for spatne in ("data/STAV.md", "pracovni/../data/STAV.md", "pracovni/slozka", "pracovni/neni.txt", "pracovni/zadani/U-0001.json",
                       "pracovni/zapis_U-0001.rozpracovano", "pracovni/.plugin_root", "/etc/passwd"):
            r = self.py("stav.py", "uklid", "pracovni/ok.txt", spatne)
            self.assertEqual(r.returncode, 1, spatne + r.stdout)
            self.assertTrue((self.root / "pracovni" / "ok.txt").exists(), spatne)       # všechno, nebo nic
        self.assertTrue((self.root / "data" / "STAV.md").exists())
        self.assertEqual(self.py("stav.py", "uklid").returncode, 2)

    def test_sablona_projektu_projde_kontrolou(self):
        shutil.copy(SKILL / "template" / "data" / "STAV.md", self.root / "data" / "STAV.md")
        r = self.py("stav.py", "kontrola")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("## Pravidla od uživatele", self.stav())


def hook(data):
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(HOOK)], input=json.dumps(data), capture_output=True, text=True, encoding="utf-8")
    return "deny" if r.stdout.strip() else "allow"


class HlidacPredani(unittest.TestCase):
    def test_badatel_stav_md_jen_nastrojem(self):
        with tempfile.TemporaryDirectory() as t:
            for nastroj in ("Edit", "Write"):
                self.assertEqual(hook({"tool_name": nastroj, "tool_input": {"file_path": "data/STAV.md"}, "agent_type": "rodokmen:badatel",
                                       "cwd": t}), "deny", nastroj)
        for p, ocekavam in (("python -I tools/stav.py", "allow"), ("python -I tools/stav.py --json", "allow"),
                            ("python -I tools/stav.py kontrola", "allow"),
                            ("python -I tools/stav.py predani pracovni/predani.json", "allow"),
                            ("python -I tools/stav.py predani pracovni/predani.json --nanecisto", "allow"),
                            ('python -I tools/stav.py pravidlo "Dokumenty zapisovat celé"', "allow"),
                            ('python -I tools/stav.py vyrad "Fronta úkolů"', "allow"),
                            ("python -I tools/stav.py uklid pracovni/oprava_probe.json pracovni/b.txt", "allow"),
                            ("python -I tools/stav.py uklid data/osoby.py", "deny"),
                            ("python -I tools/stav.py uklid pracovni/../data/osoby.py", "deny"),
                            ("python -I tools/stav.py uklid", "deny"),
                            ("python -I tools/stav.py predani data/x.json", "deny"),
                            ("python -I tools/stav.py predani pracovni/../data/x.json", "deny"),
                            ("python -I tools/stav.py smaz", "deny")):
            self.assertEqual(hook({"tool_name": "Bash", "tool_input": {"command": p}, "agent_type": "rodokmen:badatel"}), ocekavam, p)


if __name__ == "__main__":
    unittest.main()
