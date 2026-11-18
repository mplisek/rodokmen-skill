"""tools/dodrzovani.py: kontrola dodržování metodiky ze záznamů sezení (zjednoduseni-badani.md, 10.7) – místo hlídačů,
které obcházení bránily, se obcházení ukáže po sezení. Vymyšlené záznamy v dočasné složce (RODOKMEN_PREPISY), bez sítě."""
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

UUID = "0a1b2c3d-1111-2222-3333-444455556666"


def tah(cas, nastroj, vstup):
    return {"type": "assistant", "timestamp": cas, "message": {"id": cas, "model": "claude-test", "usage": {"input_tokens": 1},
            "content": [{"type": "tool_use", "name": nastroj, "input": vstup}]}}


class Dodrzovani(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        t = Path(self._tmp.name)
        self.p, self.prepisy = t / "projekt", t / "prepisy"
        (self.p / "tools").mkdir(parents=True)
        self.prepisy.mkdir()
        for f in ("dodrzovani.py", "spotreba.py"):
            shutil.copy(TOOLS / f, self.p / "tools" / f)

    def tearDown(self):
        self._tmp.cleanup()

    def sezeni(self, tahy, pomocnik=None):
        (self.prepisy / "s1.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in tahy) + "\n", encoding="utf-8")
        if pomocnik:
            d = self.prepisy / "s1" / "subagents"
            d.mkdir(parents=True)
            (d / "agent-a1.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in pomocnik) + "\n", encoding="utf-8")
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "dodrzovani.py"), "--json"], cwd=self.p,
                           capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, RODOKMEN_PREPISY=str(self.prepisy)))
        return r.returncode, json.loads(r.stdout)[0]

    def test_postup_podle_metodiky_je_bez_poruseni(self):
        kod, v = self.sezeni([
            tah("2026-11-18T10:00:00", "Bash", {"command": f"python -I tools/aron_img.py {UUID} 40 0 pracovni/s.jpg"}),
            tah("2026-11-18T10:05:00", "Bash", {"command": "python -I tools/nalez.py zapis pracovni/nalez.json"}),
            tah("2026-11-18T10:06:00", "Edit", {"file_path": "data/udaje_od_rodiny.md"}),
            tah("2026-11-18T10:07:00", "Bash", {"command": "python -I tools/slusne.py curl https://aron.example.cz/x"}),
            tah("2026-11-18T10:08:00", "Bash", {"command": "curl http://localhost:4321/"}),
            tah("2026-11-18T10:09:00", "Bash", {"command": "python -I tools/brana.py"}),
            tah("2026-11-18T10:10:00", "Bash", {"command": "npm run nasadit-cloudflare"})])
        self.assertEqual((kod, v["porušení"], v["upozornění"]), (0, [], []))

    def test_obchazeni_se_ukaze(self):
        kod, v = self.sezeni([
            tah("2026-11-18T11:00:00", "Edit", {"file_path": "C:/projekt/data/zaznamy.json"}),
            tah("2026-11-18T11:01:00", "Bash", {"command": "sed -i 's/a/b/' data/osoby.py"}),
            tah("2026-11-18T11:02:00", "Bash", {"command": "curl -s https://www.mza.cz/actapublica/x"}),
            tah("2026-11-18T11:03:00", "Bash", {"command": "npm run nasadit"})])
        self.assertEqual(kod, 1)
        self.assertEqual(sorted(n["druh"] for n in v["porušení"]), ["nasazeni_brana", "sit_mimo_brzdu", "zapis_dat", "zapis_dat"])

    def test_text_v_heredocu_a_web_mimo_archivy_nejsou_poruseni(self):
        """Falešné poplachy ze skutečných záznamů: obsah heredocu není příkaz, curl na web, který není archiv, brzdu neobchází."""
        kod, v = self.sezeni([
            tah("2026-11-18T13:00:00", "Bash", {"command": "cat > pracovni/audit.py <<'E'\nimport json\n"
                                                         "d = json.load(open('data/zaznamy.json'))\nE"}),
            tah("2026-11-18T13:01:00", "Bash", {"command": "cat >> data/poznamky_pro_skill.md <<'E'\nnpm run nasadit selhal\nE"}),
            tah("2026-11-18T13:02:00", "Bash", {"command": "curl -s https://downloads.example.org/latest"})])
        self.assertEqual((kod, v["porušení"]), (0, []))

    def test_pomocnik_nesmi_do_dat_a_stazeni_bez_deniku_je_upozorneni(self):
        kod, v = self.sezeni(
            [tah("2026-11-18T12:00:00", "Bash", {"command": f"python -I tools/aron_img.py {UUID} 41 0 pracovni/t.jpg"})],
            pomocnik=[tah("2026-11-18T12:01:00", "Bash", {"command": "python -I tools/zapis.py zaznamy k pracovni/x.json"}),
                      tah("2026-11-18T12:02:00", "Write", {"file_path": "data/poznamky_pro_skill.md"})])
        self.assertEqual(kod, 1)
        self.assertEqual([n["druh"] for n in v["porušení"]], ["pomocnik_data", "pomocnik_data"])
        self.assertEqual([n["druh"] for n in v["upozornění"]], ["denik"])


if __name__ == "__main__":
    unittest.main()
