"""aron_img.py odkazy / opravit-odkazy: staré odkazy na soubor PUBLISHED → TILE téhož snímku (bez sítě, popis svazku v mezipaměti)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

APU, DAO_A, DAO_B = "11111111-1111-1111-1111-111111111111", "aaaaaaaa-0000-0000-0000-000000000000", "bbbbbbbb-0000-0000-0000-000000000000"
PUB5, TILE5, TILE6 = ("c0000000-0000-0000-0000-00000000000" + x for x in "156")
SVAZEK = {"name": "Holice N 1880–1890", "digitalObjects": [
    {"id": DAO_A, "files": [{"id": PUB5, "type": "PUBLISHED", "order": 5}]},
    {"id": DAO_B, "files": [{"id": TILE5, "type": "TILE", "order": 5}, {"id": TILE6, "type": "TILE", "order": 6}]}]}
URL = "https://aron.vychodoceskearchivy.cz/apu/{}/dao/{}/file/{}"
STARY, NOVY, DOBRY = URL.format(APU, DAO_A, PUB5), URL.format(APU, DAO_B, TILE5), URL.format(APU, DAO_B, TILE6)


class OdkazyAron(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name) / "rodokmen"
        self.assertEqual(novy_projekt(self.p).returncode, 0)
        cache = self.p / "pracovni" / ".cache_aron"
        cache.mkdir(parents=True)
        (cache / f"{APU}.json").write_text(json.dumps(SVAZEK), encoding="utf-8")
        self.zaz = self.p / "data" / "zaznamy.json"
        self.zaz.write_text(json.dumps([{"klic": "a", "odkaz": STARY}, {"klic": "b", "odkaz": DOBRY}], indent=1), encoding="utf-8")
        self.md = self.p / "data" / "pribeh.md"
        self.md.write_text(f"Viz [křest]({STARY}).\r\n", encoding="utf-8", newline="")

    def tearDown(self):
        self._tmp.cleanup()

    def test_bez_prepinace_jen_vypise(self):
        r = spust(self.p, "aron_img.py", "odkazy")
        self.assertIn("správně 1, na první snímek 1", r.stdout)
        self.assertIn(STARY, self.zaz.read_text(encoding="utf-8"))

    def test_opravi_i_do_jineho_digitalniho_objektu(self):
        for prikaz in (("odkazy", "--opravit"), ("opravit-odkazy", "--zapsat")):   # i název z originálu
            spust(self.p, "aron_img.py", *prikaz)
        zaz = json.loads(self.zaz.read_text(encoding="utf-8"))
        self.assertEqual([z["odkaz"] for z in zaz], [NOVY, DOBRY])
        self.assertEqual(self.md.read_bytes(), f"Viz [křest]({NOVY}).\r\n".encode())   # konce řádků zůstanou


if __name__ == "__main__":
    unittest.main()
