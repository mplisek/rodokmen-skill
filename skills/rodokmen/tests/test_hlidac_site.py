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
    # vlastní prohlížeč na portál, kam skript nesmí, jen přes tools/prohlizec.py (ten drží pauzy, stop a jeden archiv na relaci)
    ("PowerShell", 'Start-Process "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" "https://digi.ceskearchivy.cz/"'),
    ("PowerShell", 'Start-Process msedge -ArgumentList "--remote-debugging-port=9222"'),
    ("PowerShell", "Start-Process https://www.mza.cz/actapublica/"),
    ("Bash", "msedge --remote-debugging-port=9222 about:blank"),
    ("Bash", "chrome https://digi.archives.cz/da/"),
]
PUSTIT = [
    ("Bash", "python3 -I tools/slusne.py curl https://www.mza.cz/"),
    ("Bash", "python3 -I tools/mza.py hledat Brno"),
    ("Bash", "curl http://localhost:4321/"),
    ("Bash", "npm run build"),
    ("Bash", "git push origin main"),
    ("PowerShell", "Get-ChildItem"),
    ("Bash", "python tools/prohlizec.py start --port 9222"),
    ("Bash", "python tools/prohlizec.py otevri https://digi.ceskearchivy.cz/ebadatelna --listovani"),
    ("PowerShell", "python tools/prohlizec.py text"),
    ("PowerShell", "Start-Process msedge https://github.com/mplisek/rodokmen-skill"),     # prohlížeč mimo portály ze ZAKAZ nevadí
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
