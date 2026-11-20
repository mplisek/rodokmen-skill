"""tools/oprava.py: oprava polí existujících zápisů (data/zaznamy.json) a míst (data/mista.json) jedním voláním – s důvodem a dokladem,
všechno nebo nic, kontrola dat po změně (nová chyba = vrácení), historie oprav v data/opravy.jsonl. Požadavek uživatele 16. 11. 2026:
badatel opravuje chybné údaje sám, uživatel data nekopíruje. Dočasný projekt, bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

ZAZNAMY = [
    {"klic": "ukazka_snatek_1801", "svazek": "0a1b2c3d", "snimek": 80, "druh": "S", "datum": "1801", "nazev": "Sňatek Ukázka",
     "shrnuti": "sňatek", "odkaz": "https://example.org/1"},
    {"klic": "ukazka_krest_1784", "svazek": "0a1b2c3d", "snimek": 81, "druh": "N", "datum": "6. 6. 1784", "nazev": "Křest Ukázka",
     "shrnuti": "křest", "odkaz": "https://example.org/2"},
]
MISTA = {"Ukázkov": {"re": "Ukázkov", "dotaz": "Ukázkov, Česko", "lat": 50.6, "lon": 15.3, "osm": "Ukázkov, Semily"}}


class Oprava(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "p"
        r = novy_projekt(self.root)
        assert r.returncode == 0, r.stdout + r.stderr
        (self.root / "pracovni").mkdir(exist_ok=True)
        d = self.root / "data"
        (d / "zaznamy.json").write_text(json.dumps(ZAZNAMY, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (d / "mista.json").write_text(json.dumps(MISTA, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        sv = json.loads((d / "svazky.json").read_text(encoding="utf-8-sig")) if (d / "svazky.json").exists() else {}
        sv["0a1b2c3d"] = {"archiv": "SOA Zámrsk", "portal": "ARON", "svazek": "sign.: 712"}
        (d / "svazky.json").write_text(json.dumps(sv, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def oprav(self, obsah, *volby, jmeno="oprava.json"):
        p = self.root / "pracovni" / jmeno
        p.write_text(json.dumps(obsah, ensure_ascii=False), encoding="utf-8")
        return spust(self.root, "oprava.py", f"pracovni/{jmeno}", *volby, check=False)

    def data(self, soubor):
        return (self.root / "data" / soubor).read_text(encoding="utf-8")

    def zaznam(self, klic):
        return next(z for z in json.loads(self.data("zaznamy.json")) if z["klic"] == klic)

    def historie(self):
        p = self.root / "data" / "opravy.jsonl"
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []

    def test_oprava_druhu_zapise_jen_pole_a_historii(self):
        r = self.oprav({"duvod": "sňatek označený jako soupis", "doklad": "snímek 80: oddací zápis",
                        "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = self.zaznam("ukazka_snatek_1801")
        self.assertEqual(z["druh"], "O")
        self.assertEqual(z["snimek"], 80)                                         # ostatní pole beze změny
        h = self.historie()
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["zmeny"][0]["pole"]["druh"], {"bylo": "S", "je": "O"})
        self.assertEqual((h[0]["duvod"], h[0]["doklad"]), ("sňatek označený jako soupis", "snímek 80: oddací zápis"))
        self.assertIn("uložit: git add", r.stdout)
        self.assertIn("data/opravy.jsonl", r.stdout)

    def test_overeno_u_zapisu_po_kontrolnim_cteni(self):
        r = self.oprav({"duvod": "kontrolní čtení po polích, shoda", "doklad": "cteni.py porovnej",
                        "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"overeno": "kontrolni-cteni"}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.zaznam("ukazka_snatek_1801")["overeno"], "kontrolni-cteni")
        r = self.oprav({"duvod": "x", "doklad": "y",
                        "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"overeno": True}}]})
        self.assertNotEqual(r.returncode, 0)

    def test_misto_souradnice(self):
        r = self.oprav({"duvod": "obec u stejnojmenné obce jinde", "doklad": "titulní štítek knihy narozených",
                        "zmeny": [{"soubor": "mista", "klic": "Ukázkov", "pole": {"lat": 49.69, "lon": 15.81, "dotaz": "Ukázkov, okres Havlíčkův Brod"}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = json.loads(self.data("mista.json"))["Ukázkov"]
        self.assertEqual((m["lat"], m["lon"], m["re"]), (49.69, 15.81, "Ukázkov"))

    def test_chybny_vstup_nic_nezmeni(self):
        pred = (self.data("zaznamy.json"), self.data("mista.json"))
        zmena = {"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}
        spatne = [
            {"doklad": "x", "zmeny": [zmena]},                                                          # chybí důvod
            {"duvod": "x", "zmeny": [zmena]},                                                           # chybí doklad
            {"duvod": "x", "doklad": "y", "zmeny": []},
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, klic="neexistuje")]},                  # nový zápis tudy ne
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"druh": "X"})]},
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"klic": "jiny"})]},              # klíč se nemění
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"ucastnici": []})]},             # na to je ucastnici.py
            {"duvod": "x", "doklad": "y", "zmeny": [dict(zmena, pole={"svazek": "ffffffff"})]},        # svazek mimo katalog
            {"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "mista", "klic": "Ukázkov", "pole": {"lat": 120}}]},
            {"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "osoby", "klic": "1", "pole": {"n": "x"}}]},
            {"duvod": "x", "doklad": "y", "zmeny": [zmena, {"soubor": "mista", "klic": "Nikde", "pole": {"lat": 1}}]},   # vše nebo nic
        ]
        for i, s in enumerate(spatne):
            r = self.oprav(s, jmeno=f"x{i}.json")
            self.assertNotEqual(r.returncode, 0, s)
        self.assertEqual((self.data("zaznamy.json"), self.data("mista.json")), pred)
        self.assertEqual(self.historie(), [])

    def test_nova_chyba_kontroly_vrati_vse(self):
        """Oprava, po které kontrola dat hlásí novou chybu (tady neplatný výraz místa), se vrátí celá, i zápis, který byl v pořádku."""
        pred = (self.data("zaznamy.json"), self.data("mista.json"))
        r = self.oprav({"duvod": "x", "doklad": "y", "zmeny": [
            {"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}},
            {"soubor": "mista", "klic": "Ukázkov", "pole": {"re": "Ukázkov("}}]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vráceno", r.stdout)
        self.assertEqual((self.data("zaznamy.json"), self.data("mista.json")), pred)
        self.assertEqual(self.historie(), [])

    def test_nanecisto_a_beze_zmeny(self):
        pred = self.data("zaznamy.json")
        o = {"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}]}
        r = self.oprav(o, "--nanecisto")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("S → O", r.stdout)
        self.assertEqual(self.data("zaznamy.json"), pred)
        r = self.oprav({"duvod": "x", "doklad": "y", "zmeny": [{"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "S"}}]})
        self.assertEqual(r.returncode, 0)
        self.assertIn("nic ke změně", r.stdout)
        self.assertEqual(self.historie(), [])

    def test_historie_oprav_je_chranena_pred_rucnim_zapisem(self):
        import subprocess
        data = {"tool_name": "Edit", "tool_input": {"file_path": str(self.root / "data" / "opravy.jsonl")}, "cwd": str(self.root)}
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.root / "tools" / "hlidac_zapisu.py")], input=json.dumps(data),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertIn("oprava.py", r.stdout)                                     # zamítnuto s nápovědou, kterým nástrojem

    def test_vzor_projde_kontrolou_tvaru(self):
        """Podnět z bádání 16. 11. 2026: tvar vstupu šel zjistit jen z odmítnutí; `oprava.py vzor` ho vypíše."""
        r = spust(self.root, "oprava.py", "vzor", check=False)
        self.assertEqual(r.returncode, 0)
        v = json.loads(r.stdout)
        self.assertEqual(set(v), {"duvod", "doklad", "zmeny"})
        self.assertEqual(set(v["zmeny"][0]), {"soubor", "klic", "pole"})

    def test_vstup_jen_z_pracovni(self):
        (self.root / "o.json").write_text(json.dumps({"duvod": "x", "doklad": "y", "zmeny": [
            {"soubor": "zaznamy", "klic": "ukazka_snatek_1801", "pole": {"druh": "O"}}]}), encoding="utf-8")
        self.assertNotEqual(spust(self.root, "oprava.py", "o.json", check=False).returncode, 0)
        self.assertEqual(self.zaznam("ukazka_snatek_1801")["druh"], "S")


OSOBY = '''# Osoby (ukázka)
P = {
 1: dict(n="Petr Ukázka", y="* 1950", st="fam", f=["* 1950 Holice"]),
 8: dict(n="Josef Vzorný", y="1812–1870", st="doc", f=["* 17. 3. 1812 Lhota", "kovář"]),  # poznámka u řádku
 9: dict(n="Anna Vzorná", y="* 1815", st="doc", f=[]),
}
LINES = {8: ("Vzorní", "rod")}
RODINA = {
}
ISSUES = [
 dict(k=8, otazka="Kdo byli rodiče Josefa?", stav="otevřené", text="Křest nenalezen."),
]
'''


class OsobyUpravy(unittest.TestCase):
    """tools/osoby_upravy.py: nahradí jen text jedné položky (i za řádkem s českými znaky – pozice v ast jsou v bajtech UTF-8)."""
    def test_nahrada_a_pridani_jen_dotcene_polozky(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
        import ast
        import osoby_upravy as ou
        text = 'P = {\n 8: dict(n="Šťastný Žluťoučký", f=["kůň"]),  # ěščř\n 9: dict(n="Anna")\n}\nISSUES = []\n'
        t2 = ou.uloz_osobu(text, "P", 9, {"n": "Anna Řeháková", "f": ["* 1815"]})
        self.assertIn(' 8: dict(n="Šťastný Žluťoučký", f=["kůň"]),  # ěščř\n', t2)
        self.assertEqual(ast.literal_eval(ast.parse(t2).body[0].value.values[1].keywords[0].value), "Anna Řeháková")
        t3 = ou.uloz_osobu(t2, "P", 10, {"n": "Nový"})
        self.assertEqual(ou.nacti_osobu(t3, "P", 10), {"n": "Nový"})
        t4 = ou.uloz_otazku(t3, None, {"k": 9, "otazka": "Kdy?", "stav": "otevřené"})
        self.assertEqual(ou.otazky(t4)[0][0]["otazka"], "Kdy?")
        compile(t4, "osoby.py", "exec")


class OpravaOsobDokumentuMist(Oprava):
    """Požadavek uživatele 16. 11. 2026: badatel sám doplní a opraví osoby (fakta, nová osoba, bydliště), rodinné dokumenty, místa
    a otevřené otázky – se stejnými zárukami jako oprava zápisu (důvod, doklad, vše nebo nic, kontrola dat, historie)."""
    def setUp(self):
        super().setUp()
        (self.root / "data" / "osoby.py").write_text(OSOBY, encoding="utf-8")
        (self.root / "data" / "dokumenty.json").write_text("[]\n", encoding="utf-8")

    def osoby(self):
        import runpy
        return runpy.run_path(str(self.root / "data" / "osoby.py"))

    def test_osoba_fakta_a_bydliste_zbytek_souboru_beze_zmeny(self):
        r = self.oprav({"duvod": "rodinné schéma", "doklad": "dokumenty/schema_novakovi.jpg", "zmeny": [
            {"soubor": "osoby", "klic": 8, "fakta_pridej": ["bydliště Lhota čp. 5 (1840–1870, podle rodinného schématu)"],
             "fakta_nahrad": [["kovář", "kovář a hostinský"]]}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        p = self.osoby()["P"]
        self.assertEqual(p[8]["f"], ["* 17. 3. 1812 Lhota", "kovář a hostinský", "bydliště Lhota čp. 5 (1840–1870, podle rodinného schématu)"])
        text = self.data("osoby.py")
        self.assertIn(' 1: dict(n="Petr Ukázka", y="* 1950", st="fam", f=["* 1950 Holice"]),', text)   # ostatní řádky doslova
        self.assertIn("# Osoby (ukázka)", text)
        self.assertEqual(self.historie()[-1]["zmeny"][0]["soubor"], "osoby")

    def test_nova_osoba_v_rodine(self):
        r = self.oprav({"duvod": "dcera podle schématu", "doklad": "schéma", "zmeny": [
            {"soubor": "osoby", "skupina": "RODINA", "klic": "marie-vzorna-1840", "nove": True,
             "pole": {"n": "Marie Vzorná", "y": "* 1840", "sex": "F", "otec": 8, "matka": 9, "st": "fam", "f": ["* 1840 Lhota"]}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.osoby()["RODINA"]["marie-vzorna-1840"]["otec"], 8)

    def test_otazka_nova_a_vyresena(self):
        r = self.oprav({"duvod": "rozpor s rodinným listem", "doklad": "úmrtní list 1906", "zmeny": [
            {"soubor": "issues", "nove": True, "pole": {"k": 9, "otazka": "Kdy zemřela Anna?", "stav": "otevřené", "text": "List 1906 × rodina 1907."}},
            {"soubor": "issues", "klic": "Kdo byli rodiče Josefa?", "pole": {"stav": "vyřešeno"}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        iss = self.osoby()["ISSUES"]
        self.assertEqual([(i["otazka"], i["stav"]) for i in iss], [("Kdo byli rodiče Josefa?", "vyřešeno"), ("Kdy zemřela Anna?", "otevřené")])

    def test_dokument_a_nove_misto(self):
        r = self.oprav({"duvod": "rodinný dokument", "doklad": "sken od rodiny 15. 11.", "zmeny": [
            {"soubor": "dokumenty", "klic": "schema_vzorni", "nove": True,
             "pole": {"popis": "Schéma potomků Josefa a Anny", "osoby": [8, 9, 1], "druh": "schema", "rc": [], "autor": "rodina", "datum": "1960"}},
            {"soubor": "mista", "klic": "Lhota", "nove": True,
             "pole": {"re": "Lhot", "dotaz": "Lhota, okres Chrudim", "lat": 49.9, "lon": 15.8}}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = json.loads(self.data("dokumenty.json"))
        self.assertEqual(d[0]["img"], "schema_vzorni")
        self.assertIn("Lhota", json.loads(self.data("mista.json")))

    def test_chyby_osob_a_dokumentu_nic_nezmeni(self):
        pred = (self.data("osoby.py"), self.data("dokumenty.json"))
        spatne = [
            {"soubor": "osoby", "klic": 8, "pole": {"st": "jiste"}},
            {"soubor": "osoby", "klic": 8, "pole": {"souhlas": {"kdo": "x"}}},                       # souhlas dává uživatel
            {"soubor": "osoby", "skupina": "RODINA", "klic": "x-1900", "nove": True, "pole": {"n": "X", "otec": 777}},
            {"soubor": "osoby", "klic": 8, "fakta_nahrad": [["neexistující fakt", "nový"]]},
            {"soubor": "osoby", "klic": 99, "pole": {"n": "Nikdo"}},                                 # existující osoba, ne nová
            {"soubor": "dokumenty", "klic": "d1", "nove": True, "pole": {"popis": "x", "osoby": [8], "zacerneno": [8]}},
            {"soubor": "dokumenty", "klic": "d2", "nove": True, "pole": {"popis": "x", "osoby": [8], "soukrome": False}},
            {"soubor": "dokumenty", "klic": "d3", "nove": True, "pole": {"popis": "x", "osoby": [404]}},
            {"soubor": "issues", "nove": True, "pole": {"k": 8, "otazka": "Q?", "stav": "nevim"}},
        ]
        for i, z in enumerate(spatne):
            r = self.oprav({"duvod": "x", "doklad": "y", "zmeny": [z]}, jmeno=f"o{i}.json")
            self.assertNotEqual(r.returncode, 0, z)
        self.assertEqual((self.data("osoby.py"), self.data("dokumenty.json")), pred)


if __name__ == "__main__":
    unittest.main()
