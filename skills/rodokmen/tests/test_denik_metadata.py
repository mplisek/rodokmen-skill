"""Metadata čtení v deníku (analyza/navrh-router-uloh.md kap. 6.1, S-006): pole ukol, nastroj, model a snimky; ověření tvaru, výchozí nástroj z .skill_verze,
na web nejdou. Starší záznamy bez nich zůstávají platné."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

ZAKLAD = ["pridej", "--datum", "2026-11-14", "--zdroj-typ", "archiv", "--zdroj", "ARON, vymyšlená kniha, sn. 20–35", "--rozsah", "sn. 20–35",
          "--hledano", "křest Jana Vzorného * 1852", "--vysledek", "nalezeno", "--nalez", "Křest 14. 3. 1852, otec Josef Vzorný."]


class DenikMetadata(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        (self.p / "tools").mkdir()
        (self.p / "data").mkdir()
        for f in ("denik.py", "zaznamy_store.py", "soubory.py"):
            shutil.copy(TOOLS / f, self.p / "tools" / f)
        self.log = self.p / "data" / "denik.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def denik(self, *a):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "denik.py"), *a], cwd=self.p, capture_output=True,
                              text=True, encoding="utf-8")

    def zaznamy(self):
        return [json.loads(r) for r in self.log.read_text(encoding="utf-8").splitlines() if r.strip()]

    def test_metadata_se_ulozi(self):
        r = self.denik(*ZAKLAD, "--ukol", "U-0042", "--nastroj", "0.10.1-fork.1", "--model", "sonnet", "--snimky", "03066862:236-258,a20a05e2:12")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = self.zaznamy()[0]
        self.assertEqual((z["ukol"], z["nastroj"], z["model"]), ("U-0042", "0.10.1-fork.1", "sonnet"))
        self.assertEqual(z["snimky"], [{"svazek": "03066862", "od": 236, "do": 258}, {"svazek": "a20a05e2", "od": 12, "do": 12}])

    def test_spatny_tvar_se_odmitne(self):
        pred = self.log.read_bytes() if self.log.exists() else None
        for a in (["--ukol", "nejaky"], ["--snimky", "bez-dvojtecky"], ["--snimky", "k:20-10"], ["--snimky", "k:0"]):
            r = self.denik(*ZAKLAD, *a)
            self.assertNotEqual(r.returncode, 0, a)
        self.assertEqual(self.log.read_bytes() if self.log.exists() else None, pred)

    def test_vychozi_nastroj_je_z_skill_verze(self):
        (self.p / ".skill_verze").write_text("0.10.1-fork.1\n", encoding="utf-8")
        self.assertEqual(self.denik(*ZAKLAD).returncode, 0)
        self.assertEqual(self.zaznamy()[0]["nastroj"], "0.10.1-fork.1")

    def test_bez_metadat_je_zaznam_platny_a_pole_na_web_nejdou(self):
        self.assertEqual(self.denik(*ZAKLAD).returncode, 0)
        self.assertNotIn("ukol", self.zaznamy()[0])
        self.assertEqual(self.denik(*ZAKLAD, "--ukol", "U-0007", "--model", "tajnymodel", "--nastroj", "tajnaverze").returncode, 0)
        r = self.denik("vykresli", "--do", "data/denik.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        md = (self.p / "data" / "denik.md").read_text(encoding="utf-8")
        for s in ("U-0007", "tajnymodel", "tajnaverze"):
            self.assertNotIn(s, md)
        self.assertEqual(self.denik("over").returncode, 0)


if __name__ == "__main__":
    unittest.main()
