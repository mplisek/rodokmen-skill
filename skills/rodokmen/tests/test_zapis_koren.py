"""hooks/zapis_koren.py (SessionStart hook pluginu) zapíše cestu pluginu do pracovni/.plugin_root projektu, protože Bash nástroj
proměnnou CLAUDE_PLUGIN_ROOT nemá a kontext.py by jinak nenašel pravidla agentů; kontext.py ji tam najde. Bez sítě."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "zapis_koren.py"


def spust_hook(projekt, koren):
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR")}
    env.update(CLAUDE_PLUGIN_ROOT=str(koren), CLAUDE_PROJECT_DIR=str(projekt), PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(HOOK)], input="{}", capture_output=True, text=True, env=env,
                          encoding="utf-8")


class ZapisKoren(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = Path(self._tmp.name)
        self.projekt = self.t / "projekt"
        (self.projekt / "data").mkdir(parents=True)
        (self.projekt / "tools").mkdir()
        self.koren = self.t / "plugin"
        (self.koren / "skills" / "rodokmen-agents" / "rules").mkdir(parents=True)
        (self.koren / "skills" / "rodokmen-agents" / "rules" / "identity.md").write_text("# A\n\n## R-ID-001\nwhen: x\ndo: y\nwhy: z\nsource: fork\n",
                                                                                         encoding="utf-8")
        (self.projekt / "data" / "osoby.py").write_text("P = {1: {'n': 'Jan', 'y': '1890', 'st': 'doc', 'f': []}}\nISSUES = []\n", encoding="utf-8")
        (self.projekt / "data" / "zaznamy.json").write_text("[]", encoding="utf-8")
        shutil.copy(TOOLS / "kontext.py", self.projekt / "tools" / "kontext.py")

    def tearDown(self):
        self._tmp.cleanup()

    def test_hook_zapise_koren_pluginu(self):
        r = spust_hook(self.projekt, self.koren)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.projekt / "pracovni" / ".plugin_root").read_text(encoding="utf-8").strip(), str(self.koren))

    def test_hook_nezapisuje_mimo_projekt_rodokmenu(self):
        shutil.rmtree(self.projekt / "data")
        r = spust_hook(self.projekt, self.koren)
        self.assertEqual(r.returncode, 0)
        self.assertFalse((self.projekt / "pracovni").exists())

    def test_hook_nikdy_neshodi_session(self):
        r = spust_hook(self.t / "neexistuje", self.koren)
        self.assertEqual(r.returncode, 0)

    def test_kontext_najde_pravidla_podle_zapsaneho_korene(self):
        spust_hook(self.projekt, self.koren)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", "tools/kontext.py", "--osoba", "1", "--tema", "identity"],
                           cwd=self.projekt, capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("R-ID-001", r.stdout)

    def test_hooks_json_zapojuje_hook(self):
        d = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        prikazy = [h["command"] for v in d["hooks"].get("SessionStart", []) for h in v["hooks"]]
        self.assertTrue(any("zapis_koren.py" in p for p in prikazy), prikazy)


if __name__ == "__main__":
    unittest.main()
