"""hlidac_site.py: hook zamítne síťové příkazy mimo brzdu a pustí nástroje, brzdu a místní příkazy."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

ZAMITNOUT = [
    ("Bash", "curl -s https://www.mza.cz/actapublica/"),
    ("Bash", "wget https://aron.vychodoceskearchivy.cz/x"),
    ("Bash", "cd tools && curl https://digi.archives.cz/da/"),
    ("Bash", 'python3 -c "import urllib.request; urllib.request.urlopen(1)"'),
    ("PowerShell", "Invoke-WebRequest https://digi.archives.cz/"),
]
PUSTIT = [
    ("Bash", "python3 -I tools/slusne.py curl https://www.mza.cz/"),
    ("Bash", "python3 -I tools/mza.py hledat Brno"),
    ("Bash", "curl http://localhost:4321/"),
    ("Bash", "npm run build"),
    ("Bash", "git push origin main"),
    ("PowerShell", "Get-ChildItem"),
]


def hlidac(nastroj, prikaz):
    vstup = json.dumps({"tool_name": nastroj, "tool_input": {"command": prikaz}, "cwd": str(TOOLS.parent)})
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "hlidac_site.py")], input=vstup,
                       capture_output=True, text=True, encoding="utf-8")
    return r


class HlidacSite(unittest.TestCase):
    def test_zamitne(self):
        for nastroj, prikaz in ZAMITNOUT:
            with self.subTest(prikaz=prikaz):
                r = hlidac(nastroj, prikaz)
                self.assertEqual(r.returncode, 0)
                vystup = json.loads(r.stdout)["hookSpecificOutput"]
                self.assertEqual(vystup["permissionDecision"], "deny")
                self.assertIn("slusne.py", vystup["permissionDecisionReason"])   # řekne, jak to udělat správně

    def test_pusti(self):
        for nastroj, prikaz in PUSTIT:
            with self.subTest(prikaz=prikaz):
                r = hlidac(nastroj, prikaz)
                self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))

    def test_rozbity_vstup_neblokuje(self):
        r = subprocess.run([sys.executable, "-I", str(TOOLS / "hlidac_site.py")], input="není json",
                           capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))


if __name__ == "__main__":
    unittest.main()
