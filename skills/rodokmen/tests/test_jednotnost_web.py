"""Jednotnost sestaveného webu (Fáze B, ADR 0004) na skutečném sestavení ukázkového projektu se dvěma přístupy: v textech deníku,
otázek a pramenů je název rodu vždy značka, nikde není procesní text a kontrola webu projde. Rozhraní: sestavený web (dist/) všech
verzí. Pomalý test (npm ci + sestavení)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt, spust  # noqa: E402

NPM = "npm.cmd" if os.name == "nt" else "npm"


def beh(*cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONUTF8="1"))
    assert r.returncode == 0, f"{cmd}: {r.stdout[-800:]}\n{r.stderr[-800:]}"
    return r.stdout


class JednotnostWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls.tmp.name) / "projekt"
        assert novy_projekt(cls.p, "--ukazka").returncode == 0
        cfg = json.loads((cls.p / "data" / "web.json").read_text(encoding="utf-8"))
        cfg["pristupy"] = [{"nazev": "Matčina rodina", "odpoved": "eva-ci", "koren": [3]}]
        (cls.p / "data" / "web.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        spust(cls.p, "export_web.py")
        site = json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        cls.rod = sorted(site["lines"].values(), key=lambda l: l["k"])[0]
        n = cls.rod["name"]
        # texty, ve kterých autor napsal název rodu holý (a nikoli odkazem)
        spust(cls.p, "denik.py", "pridej", "--datum", "2026-11-14", "--zdroj-typ", "archiv", "--zdroj", "ARON, Dolní Lhota, sign. 1",
              "--rozsah", "sn. 1–5", "--hledano", f"křest v rodu {n}", "--vysledek", "nalezeno", "--nalez", f"Rod {n} v Holicích.")
        spust(cls.p, "otazky.py", "pridej", "--druh", "rodina", "--rod", str(cls.rod["k"]), "--otazka",
              f"Je doma oddací list rodu {n}?", "--proc", "Pomohl by.")
        spust(cls.p, "otazky.py", "potvrd", "1", "--kdo", "správce webu")
        web = cls.p / "web"
        beh(NPM, "ci", "--no-audit", "--no-fund", cwd=web)
        beh(NPM, "run", "build", cwd=web)
        cls.dist = web / "dist" / "_p"
        cls.site = web / "src" / "data" / "site.json"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def verze(self):
        return sorted(p for p in self.dist.iterdir() if p.is_dir())

    def test_sestaveny_web_ma_vice_verzi(self):
        self.assertGreaterEqual(len(self.verze()), 2)

    def test_kontrola_webu_projde_na_vsech_verzich(self):
        for v in self.verze():
            site = str(self.site) if v.name == "vse" else str(v / "neexistuje.json")   # názvy rodů přístupu mají jiná data
            r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontrola_webu.py"), str(v), "--site", site,
                                "--data", str(self.p / "data")], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, f"{v.name}:\n{r.stdout[-1500:]}")
            if v.name == "vse":   # E5: vztahy a účasti v zápisech jsou na skutečně sestaveném webu z obou stran
                m = re.search(r"(\d+) vztahů a účastí v zápisech ověřeno z obou stran", r.stdout)
                self.assertTrue(m and int(m.group(1)) > 50, r.stdout[-400:])

    def test_nazev_rodu_v_textech_je_znacka(self):
        n = self.rod["name"]
        for stranka in ("denik", "hledame"):
            html = (self.dist / "vse" / stranka / "index.html").read_text(encoding="utf-8")
            self.assertIn(f'<a href="/rod/{self.rod["slug"]}/">{n}</a>', html, stranka)
            # holý výskyt „v rodu <název>“ nebo „Rod <název>“ už není
            self.assertNotRegex(html, rf"rodu\s+{re.escape(n)}\b(?![^<]*</a>)", stranka)

    def test_znacka_ma_barvu_rodu_a_pagefind_ji_zna(self):
        html = (self.dist / "vse" / "denik" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'style="background:{self.rod["color"]}"', html)
        self.assertTrue((self.dist / "vse" / "pagefind").is_dir())


if __name__ == "__main__":
    unittest.main()
