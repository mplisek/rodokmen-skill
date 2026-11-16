"""tools/rejstrik.py (sarsonj/rodokmen-skill#203) upravený pro fork: deník z data/denik.jsonl, jisté vazby z osob u řádku deníku
a z účastníků zápisu místo odhadu podle jména, platnost rejstříku podle otisku obsahu (ne času souboru), dotaz sql jen pro čtení,
prošlé snímky svazku i z mapy knihy. Rejstřík je odvozený a jen pro čtení; zdrojem pravdy jsou soubory. Dočasný projekt, bez sítě."""
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

OSOBY = '''P = {
 1: dict(n="Petr Ukázka", y="* 1950", st="doc"),
 8: dict(n="Josef Vzorný", y="* 1812", st="doc", r=["lhota_krest_josef_1812"]),
 9: dict(n="Anna Vzorná", y="* 1815", st="doc"),
 16: dict(n="Josef Vzorný", y="* 1780", st="doc"),
}
LINES = {8: ("Vzorní", "rod")}
'''
ZAZNAMY = [{"klic": "lhota_krest_josef_1812", "svazek": "0a1b2c3d", "snimek": 40, "druh": "N", "datum": "17. 3. 1812",
            "nazev": "Křest Josefa", "shrnuti": "křest", "odkaz": "https://example.org/1"},
           {"klic": "lhota_snatek_josef_anna_1835", "svazek": "0a1b2c3d", "snimek": 77, "druh": "O", "datum": "1835",
            "nazev": "Sňatek", "shrnuti": "sňatek", "odkaz": "https://example.org/2",
            "ucastnici": [{"osoba": "8", "role": "ženich"}, {"osoba": "9", "role": "nevěsta"}]}]
DENIK = [
    {"id": 1, "datum": "2026-11-01", "zdroj": {"typ": "archiv", "text": "ARON 0a1b2c3d, Lhota narození"}, "rozsah": "sn. 38–45",
     "hledano": "křest Josefa Vzorného", "vysledek": "nalezeno", "nalez": "sn. 40, kovářův syn", "osoby": ["8"],
     "snimky": [{"svazek": "0a1b2c3d", "od": 38, "do": 45}], "citace": "Josephus filius fabri"},   # tvar tools/denik.py
    {"id": 2, "datum": "2026-11-02", "zdroj": "ARON 0a1b2c3d", "rozsah": "sn. 70–80", "hledano": "sňatek, Josef Vzorný ženich",
     "vysledek": "nenalezeno", "nalez": "", "osoby": ["16"]},
    {"id": 3, "datum": "2026-11-03", "zdroj": "kronika", "rozsah": "s. 5", "hledano": "zmínka Josef Vzorný kovář 1812",
     "vysledek": "nalezeno", "nalez": "kovář"},
    {"id": 4, "datum": "2026-11-04", "zdroj": "ARON 0a1b2c3d", "rozsah": "sn. 70–80", "hledano": "sňatek 1835",
     "vysledek": "nalezeno", "nalez": "sn. 77", "osoby": ["8", "9"], "opravuje": 2},
]


class RejstrikFork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "p"
        assert novy_projekt(cls.root).returncode == 0
        d = cls.root / "data"
        (d / "osoby.py").write_text(OSOBY, encoding="utf-8")
        (d / "zaznamy.json").write_text(json.dumps(ZAZNAMY, ensure_ascii=False), encoding="utf-8")
        (d / "denik.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in DENIK), encoding="utf-8")
        sv = json.loads((d / "svazky.json").read_text(encoding="utf-8-sig")) if (d / "svazky.json").exists() else {}
        sv["0a1b2c3d"] = {"archiv": "SOA Zámrsk", "portal": "ARON", "svazek": "Lhota 12, N 1800–1825"}
        (d / "svazky.json").write_text(json.dumps(sv, ensure_ascii=False), encoding="utf-8")
        cls.mapy = Path(cls.tmp.name) / "mapy"
        (cls.mapy / "aron").mkdir(parents=True)
        (cls.mapy / "aron" / "0a1b2c3d.jsonl").write_text(
            json.dumps({"cas": "2026-11-01T10:00:00", "udalost": "strana", "sn": 41, "typ": "kniha", "od": "1812-03", "do": "1812-05"}) + "\n",
            encoding="utf-8")
        os.environ["RODOKMEN_MAPY"] = str(cls.mapy)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("RODOKMEN_MAPY", None)
        cls.tmp.cleanup()

    def r(self, *a):
        p = spust(self.root, "rejstrik.py", *a, check=False)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def test_denik_z_jsonl_a_jiste_vazby(self):
        out = self.r("osoba", "8")
        self.assertIn("lhota_snatek_josef_anna_1835", out)                     # účastník zápisu = jistá vazba na zápis
        self.assertRegex(out, r"Deník \(osoba zapsaná u řádku[^)]*\): ř\. 1, 4")
        self.assertNotRegex(out, r"ř\.[^\n]*\b2\b[^\n]*ověř")                    # řádek 2 má osobu 16: jmenovec 8 se neodhaduje
        self.assertIn("3", out)                                                   # řádek bez osob: odhad podle jména zůstává (vodítko)
        out16 = self.r("osoba", "16")
        self.assertRegex(out16, r"osoba zapsaná u řádku[^)]*\): ř\. 2")
        self.assertIn("nahrazeno", self.r("denik", "2"))                          # opravený řádek je označený
        d1 = self.r("denik", "1", "--cele")
        self.assertIn("ARON 0a1b2c3d, Lhota narození", d1)                        # zdroj jako objekt → jeho text
        self.assertIn("0a1b2c3d 38–45", d1)                                       # snímky po svazcích
        self.assertIn("Josephus »filius« fabri", self.r("hledej", "filius"))     # citace v fulltextu (»« = zvýraznění)

    def test_svazek_ukaze_mapu_knihy(self):
        out = self.r("svazek", "0a1b2c3d")
        self.assertIn("Mapa knihy", out)
        self.assertIn("41", out)
        self.assertIn("ř. 1", out)

    def test_platnost_podle_obsahu_ne_casu(self):
        self.r("osoba", "8")
        db = self.root / "pracovni" / "rejstrik.sqlite"
        d = self.root / "data" / "osoby.py"
        stary_cas = os.path.getmtime(db) - 100
        d.write_text(OSOBY.replace("Petr Ukázka", "Pavel Ukázka"), encoding="utf-8")
        os.utime(d, (stary_cas, stary_cas))                                       # obsah nový, čas starší než rejstřík
        self.assertIn("Pavel Ukázka", self.r("osoba", "1"))
        d.write_text(OSOBY, encoding="utf-8")

    def test_sql_jen_cteni(self):
        self.assertIn("4", self.r("sql", "SELECT count(*) FROM denik"))
        p = spust(self.root, "rejstrik.py", "sql", "DELETE FROM denik", check=False)
        self.assertNotEqual(p.returncode, 0)
        c = sqlite3.connect(self.root / "pracovni" / "rejstrik.sqlite")
        self.assertEqual(c.execute("SELECT count(*) FROM denik").fetchone()[0], 4)
        c.close()


if __name__ == "__main__":
    unittest.main()
