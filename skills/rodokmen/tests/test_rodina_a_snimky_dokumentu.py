"""Podnět z bádání 17. 11. 2026: (1) osoby ze skupiny RODINA (klíč je zkratka, ne číslo) nebyly vidět v tools/kontext.py ani
v tools/rejstrik.py osoba, takže text faktů k nahrazení badatel viděl až ve výpisu oprava.py --nanecisto; (2) snímek rodinného dokumentu,
který vyrez.py uloží do zdroje/ a vyrezy/, nešel commitnout tools/commit.py (--soubory jen data/ a mereni/). Dočasný projekt, bez sítě."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt, spust  # noqa: E402

OSOBY = '''P = {
 1: dict(n="Petr Ukázka", y="* 1950", st="doc"),
 8: dict(n="Josef Vzorný", y="* 1812", st="doc"),
}
RODINA = {
 "marie-vzorna": dict(n="Marie Vzorná", y="1840–1910", sex="F", otec=8, st="fam", f=["* 1840 Lhota čp. 3", "provd. Hrubá"],
                      note="Sestra z rodinného dopisu.", r=["lhota_krest_marie_1840"]),
}
ISSUES = [dict(k="marie-vzorna", otazka="Kdy se vdala Marie?", stav="otevřené", text="Dopis rok neuvádí.")]
'''
ZAZNAMY = [{"klic": "lhota_krest_marie_1840", "svazek": "0a1b2c3d", "snimek": 12, "druh": "N", "datum": "1840", "nazev": "Křest Marie",
            "shrnuti": "křest", "odkaz": "https://example.org/1"}]


class RodinaVidetVNastrojich(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "p"
        assert novy_projekt(cls.root).returncode == 0
        (cls.root / "data" / "osoby.py").write_text(OSOBY, encoding="utf-8")
        (cls.root / "data" / "zaznamy.json").write_text(json.dumps(ZAZNAMY, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_kontext_bere_klic_z_rodiny(self):
        rules = Path(self.tmp.name) / "rules"
        rules.mkdir(exist_ok=True)
        (rules / "identity.md").write_text("# A\n\n## R-ID-001\nwhen: x\ndo: y\nwhy: z\nsource: fork\n", encoding="utf-8")
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontext.py"), "--osoba", "marie-vzorna", "--tema", "identity",
                            "--rules", str(rules), "--data", str(self.root / "data")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        for s in ("Marie Vzorná", "* 1840 Lhota čp. 3", "provd. Hrubá", "Sestra z rodinného dopisu.", "lhota_krest_marie_1840",
                  "Kdy se vdala Marie?"):
            self.assertIn(s, r.stdout, s)
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontext.py"), "--osoba", "neni-v-rodine", "--tema", "identity",
                            "--rules", str(rules), "--data", str(self.root / "data")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)

    def test_rejstrik_osoba_ukaze_osobu_z_rodiny(self):
        for dotaz in ("marie-vzorna", "Marie Vzorná"):
            out = spust(self.root, "rejstrik.py", "osoba", dotaz).stdout
            for s in ("Marie Vzorná", "RODINA", "* 1840 Lhota čp. 3", "provd. Hrubá", "lhota_krest_marie_1840"):
                self.assertIn(s, out, (dotaz, s))
        self.assertIn("marie-vzorna", spust(self.root, "rejstrik.py", "hledej", "Hrubá").stdout)


class SnimekDokumentuJdeCommitnout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "p"
        assert novy_projekt(self.root).returncode == 0
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "zaklad")
        (self.root / "data" / "dokumenty.json").write_text(json.dumps([{"img": "dopis_1902", "popis": "dopis", "osoby": [8], "rc": []}]),
                                                           encoding="utf-8")
        for slozka in ("zdroje", "vyrezy"):
            (self.root / slozka).mkdir(exist_ok=True)
            for jmeno in ("dopis_1902.jpg", "cizi.jpg"):
                (self.root / slozka / jmeno).write_bytes(b"\xff\xd8jpg")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True, encoding="utf-8", env=self.env)

    def commit(self, soubory):
        return subprocess.run([sys.executable, "-X", "utf8", str(self.root / "tools" / "commit.py"), "--soubory", soubory, "--zprava",
                               "Rodinný dopis z roku 1902 zapsán"], cwd=self.root, capture_output=True, text=True, encoding="utf-8", env=self.env)

    def test_snimek_dokumentu_z_dokumenty_json(self):
        r = self.commit("data/dokumenty.json,zdroje/dopis_1902.jpg,vyrezy/dopis_1902.jpg")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        zmeny = sorted(self.git("show", "--name-only", "--format=", "HEAD").stdout.split())
        self.assertEqual(zmeny, ["data/dokumenty.json", "vyrezy/dopis_1902.jpg", "zdroje/dopis_1902.jpg"])

    def test_obrazek_mimo_dokumenty_odmitne_a_nic_necommitne(self):
        for soubory in ("data/dokumenty.json,vyrezy/cizi.jpg", "zdroje/../data/x.jpg", "vyrezy/dopis_1902.png", "web/x.jpg"):
            r = self.commit(soubory)
            self.assertNotEqual(r.returncode, 0, soubory)
            self.assertEqual(self.git("rev-list", "--count", "HEAD").stdout.strip(), "1", soubory)


if __name__ == "__main__":
    unittest.main()
