"""tools/audit_dat.py: kontrola historických dat bez čtení snímků (požadavek uživatele 16. 11. 2026). Jen čte a vypíše rozpory
s návrhem, čím je opravit (oprava.py, druhé čtení, úkol). Dočasný projekt, bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

OSOBY = '''P = {
 8: dict(n="Josef Vzorný", y="* 1812", st="doc", f=["* 17. 3. 1812 Lhota"], r=["lhota_krest_josef_1812", "lhota_krest_dite_1840"]),
 9: dict(n="Anna Vzorná", y="* 1815", st="doc", f=["* 1815 Lhota"]),
 10: dict(n="Jan Vzorný", y="* 1790", st="prob", f=[]),
 11: dict(n="Marie Vzorná", y="* 1792", st="doc", f=["* 1792 Lhota"]),
}
LINES = {8: ("Vzorní", "rod")}
'''
ZAZNAMY = [
    {"klic": "lhota_krest_josef_1812", "svazek": "0a1b2c3d", "snimek": 40, "druh": "N", "datum": "17. 3. 1814", "nazev": "Křest Josefa",
     "ucastnici": [{"osoba": "8", "role": "křtěnec"}]},
    {"klic": "lhota_krest_dite_1840", "svazek": "0a1b2c3d", "snimek": 41, "druh": "N", "datum": "1840", "nazev": "Křest dítěte"},
    {"klic": "lhota_snatek_josef_anna_1835", "svazek": "0a1b2c3d", "snimek": 77, "druh": "S", "datum": "1835", "nazev": "Sňatek Josefa a Anny",
     "ucastnici": [{"osoba": "8", "role": "ženich"}, {"osoba": "9", "role": "nevěsta"}]},
    {"klic": "lhota_umrti_x_1850", "svazek": "ffffffff", "snimek": 3, "druh": "Z", "datum": "1850", "nazev": "Úmrtí"},
]
DENIK = [
    {"id": 1, "datum": "2026-11-01", "zdroj": {"typ": "archiv", "text": "ARON"}, "rozsah": "", "hledano": "křest Jana",
     "vysledek": "nenalezeno", "osoby": ["10"]},
    {"id": 2, "datum": "2026-11-02", "zdroj": {"typ": "archiv", "text": "ARON"}, "rozsah": "sn. 70–80", "hledano": "sňatek",
     "vysledek": "nalezeno", "odkaz": "lhota_snatek_josef_anna_1835", "osoby": ["10"]},
]


class AuditDat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "p"
        assert novy_projekt(cls.root).returncode == 0
        d = cls.root / "data"
        (d / "osoby.py").write_text(OSOBY, encoding="utf-8")
        (d / "zaznamy.json").write_text(json.dumps(ZAZNAMY, ensure_ascii=False), encoding="utf-8")
        (d / "denik.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in DENIK), encoding="utf-8")
        (d / "svazky.json").write_text(json.dumps({"0a1b2c3d": {"portal": "ARON", "svazek": "Lhota 12"}}), encoding="utf-8")
        cls.pred = {f.name: f.read_bytes() for f in d.iterdir() if f.is_file()}
        r = spust(cls.root, "audit_dat.py", "--json", check=False)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.nalezy = json.loads(r.stdout)["nalezy"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def najdi(self, kontrola, co):
        return [n for n in self.nalezy if n["kontrola"] == kontrola and co in json.dumps(n, ensure_ascii=False)]

    def test_druh_zapisu_proti_nazvu(self):
        n = self.najdi("druh", "lhota_snatek_josef_anna_1835")
        self.assertTrue(n)
        self.assertEqual(n[0]["oprava"], "oprava.py")
        self.assertIn('"druh": "O"', json.dumps(n[0], ensure_ascii=False))

    def test_svazek_mimo_katalog(self):
        self.assertTrue(self.najdi("svazek", "lhota_umrti_x_1850"))

    def test_datum_zapisu_proti_faktu_osoby(self):
        self.assertTrue(self.najdi("datum", "lhota_krest_josef_1812"))
        self.assertFalse(self.najdi("datum", "lhota_krest_dite_1840"))   # křest dítěte v r rodiče: role neznámá, nesrovnává se

    def test_osoby_radku_proti_ucastnikum(self):
        self.assertTrue(self.najdi("osoby_deniku", "2"))

    def test_doc_bez_zapisu(self):
        n = self.najdi("doc_bez_zapisu", "11")
        self.assertTrue(n)
        self.assertFalse({"8", "9"} & {x.get("osoba") for x in self.najdi("doc_bez_zapisu", "")})   # 8 cituje zápis, 9 je účastnice

    def test_negativ_bez_rozsahu(self):
        self.assertTrue(self.najdi("negativ_bez_rozsahu", "1"))

    def test_nic_nezapise(self):
        d = self.root / "data"
        self.assertEqual({f.name: f.read_bytes() for f in d.iterdir() if f.is_file()}, self.pred)


if __name__ == "__main__":
    unittest.main()
