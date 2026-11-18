"""kramerius.py: hledá jen veřejná díla (dostupnost:public), `--vse` ukáže i neveřejná (PR #168). Bez sítě: místo
urlopen se zachytí adresa dotazu."""
import json
import subprocess
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

SPUSTENI = r'''
import io, json, runpy, sys, urllib.request
sys.argv = ["kramerius.py"] + sys.argv[1:]
def falesny(url, timeout=None):
    print("DOTAZ", url)
    return io.BytesIO(json.dumps({"response": {"numFound": 0, "docs": []}}).encode())
urllib.request.urlopen = falesny
runpy.run_path(r"%s", run_name="__main__")
''' % str(Path(TOOLS) / "kramerius.py")


def dotaz(*args):
    """(dotaz q z adresy, řádků, celá adresa) nebo (None, None, výstup)."""
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", "-c", SPUSTENI, *args], capture_output=True, text=True,
                       encoding="utf-8")
    radek = next((l for l in r.stdout.splitlines() if l.startswith("DOTAZ ")), None)
    if not radek:
        return None, None, r.stdout + r.stderr
    url = radek[6:]
    par = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    return par["q"][0], par["rows"][0], url


class KrameriusVerejna(unittest.TestCase):
    def test_vychozi_jen_verejna_dila(self):
        q, rows, _ = dotaz('text_ocr:"Jan Novák"')
        self.assertEqual(q, '(text_ocr:"Jan Novák") AND fedora.model:page AND dostupnost:public')
        self.assertEqual(rows, "30")

    def test_vse_ukaze_i_neverejna(self):
        q, _, _ = dotaz('text_ocr:"Jan Novák"', "--vse")
        self.assertEqual(q, '(text_ocr:"Jan Novák") AND fedora.model:page')

    def test_pocet_a_vse_v_libovolnem_poradi(self):
        q, rows, _ = dotaz('text_ocr:"Jan Novák"', "50", "--vse")
        self.assertEqual((q, rows), ('(text_ocr:"Jan Novák") AND fedora.model:page', "50"))
        q, rows, _ = dotaz('text_ocr:"Jan Novák"', "--vse", "50")   # přepínač mezi dotazem a počtem
        self.assertEqual((q, rows), ('(text_ocr:"Jan Novák") AND fedora.model:page', "50"))
        q, rows, _ = dotaz('text_ocr:"Jan Novák"', "50")
        self.assertIn("dostupnost:public", q)
        self.assertEqual(rows, "50")

    def test_vse_nesmi_prepsat_dotaz_a_server_zustane(self):
        q, _, url = dotaz("--vse", 'text_ocr:"Novák"', "10", "--server", "https://kramerius5.nkp.cz")
        self.assertEqual(q, '(text_ocr:"Novák") AND fedora.model:page')
        self.assertTrue(url.startswith("https://kramerius5.nkp.cz/search/api/v5.0/search?"))

    def test_napoveda_zminuje_vse(self):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(Path(TOOLS) / "kramerius.py"), "--help"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertIn("--vse", r.stdout + r.stderr)
        self.assertIn("dostupnost:public", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
