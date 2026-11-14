"""scripts/sync_report.py (Fáze C, Q-C2, 4.4): zpráva o tom, co je nového v originále – nové commity, verze, dotčené soubory, překryv s forkem
a pravidla s dotčeným zdrojovým oddílem. Jen čte lokální git; nic nesloučí ani nezapíše. Rozhraní: příkazová řádka nad dočasnými repozitáři
(originál a fork) s vymyšleným obsahem. Bez sítě."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKRIPT = REPO / "scripts" / "sync_report.py"
ENV = dict(os.environ, GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.org", GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.org")

ZRCADLO = "# Návod\n\n## Ztotožnění osob\n\nSpoj jen podle dvou znaků.\n\n## Jiné\n\nText.\n"
PRAVIDLO = ("# Identity\n\n## R-ID-001\nwhen: dva stejného jména\ndo: spojit jen na dva znaky\nwhy: chyba\n"
            "source: reference/navod.md#Ztotožnění osob\n")


def git(cwd, *a):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=ENV)
    assert r.returncode == 0, r.stderr
    return r.stdout


class SyncReport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "skills/rodokmen/reference").mkdir(parents=True)
        (self.repo / "skills/rodokmen-agents/rules").mkdir(parents=True)
        (self.repo / "skills/rodokmen/VERZE").write_text("0.10.1\n", encoding="utf-8")
        (self.repo / "skills/rodokmen/reference/navod.md").write_text(ZRCADLO, encoding="utf-8")
        (self.repo / "skills/rodokmen/reference/jiny.md").write_text("jiný\n", encoding="utf-8")
        (self.repo / "skills/rodokmen/reference/nase.md").write_text("naše\n", encoding="utf-8")
        (self.repo / "skills/rodokmen-agents/rules/identity.md").write_text(PRAVIDLO, encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "základ")
        zdroje = self.spust("--rules-potvrdit")  # připraví otisky pro pravidlo (viz skript pravidla.py)
        self.assertIsNotNone(zdroje)
        # „upstream“: větev od základu, kterou pak posuneme
        git(self.repo, "branch", "upstream-zaklad")
        git(self.repo, "update-ref", "refs/remotes/upstream/main", "HEAD")

    def tearDown(self):
        self._tmp.cleanup()

    def spust(self, *args):
        if args == ("--rules-potvrdit",):
            r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(REPO / "scripts" / "pravidla.py"), "potvrdit", "--vse",
                                "--rules", str(self.repo / "skills/rodokmen-agents/rules"), "--zrcadlo", str(self.repo / "skills/rodokmen")],
                               capture_output=True, text=True, encoding="utf-8")
            assert r.returncode == 0, r.stdout + r.stderr
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-q", "-m", "otisky")
            git(self.repo, "update-ref", "refs/remotes/upstream/main", "HEAD")
            return r
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), "--repo", str(self.repo), *args], capture_output=True,
                              text=True, encoding="utf-8")

    def posun_upstream(self, soubory, zprava="změna originálu", verze=None):
        """Vytvoří commit nad upstream/main bez změny pracovní větve a posune refs/remotes/upstream/main."""
        git(self.repo, "checkout", "-q", "--detach", "refs/remotes/upstream/main")
        for cesta, obsah in soubory.items():
            (self.repo / cesta).write_text(obsah, encoding="utf-8")
        if verze:
            (self.repo / "skills/rodokmen/VERZE").write_text(verze + "\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", zprava)
        nove = git(self.repo, "rev-parse", "HEAD").strip()
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "update-ref", "refs/remotes/upstream/main", nove)

    def test_bez_novinek(self):
        r = self.spust("--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["commity"], [])
        self.assertEqual(d["dotcena_pravidla"], [])

    def test_nove_commity_verze_a_soubory(self):
        self.posun_upstream({"skills/rodokmen/reference/jiny.md": "jiný 2\n"}, "Oprava jiného", verze="0.10.2")
        d = json.loads(self.spust("--json").stdout)
        self.assertEqual([c["predmet"] for c in d["commity"]], ["Oprava jiného"])
        self.assertEqual(d["verze_originalu"], "0.10.2")
        self.assertEqual(d["verze_forku"], "0.10.1")
        self.assertIn("skills/rodokmen/reference/jiny.md", d["soubory"])

    def test_prekryv_s_forkem(self):
        self.posun_upstream({"skills/rodokmen/reference/nase.md": "naše upstream\n", "skills/rodokmen/reference/jiny.md": "jiný 2\n"})
        (self.repo / "skills/rodokmen/reference/nase.md").write_text("naše fork\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "změna ve forku")
        d = json.loads(self.spust("--json").stdout)
        self.assertEqual(d["prekryv"], ["skills/rodokmen/reference/nase.md"])

    def test_dotcene_pravidlo_se_ohlasi(self):
        self.posun_upstream({"skills/rodokmen/reference/navod.md": ZRCADLO.replace("dvou znaků", "tří znaků")})
        d = json.loads(self.spust("--json").stdout)
        self.assertEqual(d["dotcena_pravidla"], ["R-ID-001"])

    def test_nedotcene_pravidlo_se_neohlasi(self):
        self.posun_upstream({"skills/rodokmen/reference/navod.md": ZRCADLO.replace("Text.", "Jiný text.")})
        self.assertEqual(json.loads(self.spust("--json").stdout)["dotcena_pravidla"], [])

    def test_citelny_vystup(self):
        self.posun_upstream({"skills/rodokmen/reference/jiny.md": "jiný 2\n"}, "Oprava jiného", verze="0.10.2")
        r = self.spust()
        self.assertEqual(r.returncode, 0, r.stderr)
        for t in ("0.10.2", "Oprava jiného", "reference/jiny.md"):
            self.assertIn(t, r.stdout)

    def test_nic_nezapisuje_a_nesluci(self):
        self.posun_upstream({"skills/rodokmen/reference/jiny.md": "jiný 2\n"})
        hlava, stav = git(self.repo, "rev-parse", "HEAD"), git(self.repo, "status", "--porcelain")
        refs = git(self.repo, "for-each-ref")
        self.spust()
        self.spust("--json")
        self.assertEqual((hlava, stav, refs), (git(self.repo, "rev-parse", "HEAD"), git(self.repo, "status", "--porcelain"),
                                               git(self.repo, "for-each-ref")))

    def test_chybi_upstream_je_srozumitelna_chyba(self):
        git(self.repo, "update-ref", "-d", "refs/remotes/upstream/main")
        r = self.spust()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("upstream", r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
