"""soal_zoomify.get: 403/429/503 zastaví web v brzdě (kód 3), 404 skončí srozumitelnou hláškou bez opakování (bez sítě, SOA Litoměřice; Opava už nástroj nepouští)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

SKRIPT = r'''
import io, sys, urllib.request, urllib.error
sys.path.insert(0, r"%s")
pokusy = []
def falesny(url, timeout=None):
    pokusy.append(url)
    raise urllib.error.HTTPError(url, int(sys.argv[1]), "x", {}, io.BytesIO(b""))
import soal_zoomify as z
urllib.request.urlopen = falesny
try:
    z.get("https://images.soalitomerice.cz/ximage/a.jpg")
except SystemExit as e:
    print("KOD", e.code if isinstance(e.code, int) else "zprava", "POKUSU", len(pokusy))
    if not isinstance(e.code, int):
        print(e.code)
''' % str(TOOLS)


def spust(kod):
    with tempfile.TemporaryDirectory() as stav:
        env = dict(os.environ, SLUSNE_STAV=stav, PYTHONUTF8="1")
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", "-c", SKRIPT, str(kod)], capture_output=True, text=True, encoding="utf-8", env=env)
        s = subprocess.run([sys.executable, "-I", "-X", "utf8", str(Path(TOOLS) / "slusne.py"), "stav"], capture_output=True, text=True,
                           encoding="utf-8", env=env)
        return r.stdout + r.stderr, s.stdout


class SoalZoomify(unittest.TestCase):
    def test_403_zastavi_web_v_brzde(self):
        out, stav = spust(403)
        self.assertIn("KOD 3", out)                           # SystemExit z brzdy (kód 3)
        self.assertIn("ZASTAVENO images.soalitomerice.cz", stav)

    def test_404_srozumitelna_hlaska_bez_opakovani(self):
        out, stav = spust(404)
        self.assertIn("POKUSU 1", out)                       # bez opakování (dřív 3× a traceback)
        self.assertIn("Snímek nenalezen (HTTP 404)", out)
        self.assertIn("z prohlížeče", out)
        self.assertNotIn("Traceback", out)
        self.assertNotIn("ZASTAVENO", stav)                  # 404 není blokace


if __name__ == "__main__":
    unittest.main()
