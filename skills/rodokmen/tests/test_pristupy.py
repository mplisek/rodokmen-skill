"""Přístupy k webu (web.json → pristupy, tools/pohled.py): nastavení, pohled od jiné výchozí osoby, oddělení větví,
brána s otisky odpovědí – a hlavně že se odpovědi ani cizí větve nedostanou do webu."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import SKILL, TOOLS, novy_projekt, spust  # noqa: E402

sys.path.insert(0, str(TOOLS))
import pohled as ph  # noqa: E402


def ukazka():
    ns = {}
    exec((SKILL / "template" / "ukazka" / "osoby.py").read_text(encoding="utf-8"), ns)
    for name, default in (("SIDE", []), ("LINES", {}), ("ISSUES", []), ("HYPOTEZY", []), ("SAME", {}), ("RODINA", {}),
                          ("PARTNERI", [])):
        ns.setdefault(name, default)
    return ns


class Nastaveni(unittest.TestCase):
    def test_bez_pristupu(self):
        self.assertIsNone(ph.nacti_pristupy({"prihlaseni": {"odpoved": "kovář"}}))

    def test_seznam(self):
        p = ph.nacti_pristupy({"prihlaseni": {"odpoved": "kovář"},
                               "pristupy": [{"nazev": "Matčina rodina", "odpoved": "Eva", "koren": [3]},
                                            {"nazev": "Kmotři", "odpoved": "x"}]})
        self.assertEqual([x["id"] for x in p], ["vse", "matcina-rodina", "kmotri"])
        self.assertEqual([x["texty"] for x in p], [True, False, True])   # bez kořene = vidí všechno i texty

    def test_chyby(self):
        for cfg in ({"pristupy": [{"nazev": "A", "odpoved": "Kovář"}, {"nazev": "B", "odpoved": "kovar"}]},   # stejná odpověď
                    {"pristupy": [{"nazev": "A"}]},                                                         # bez odpovědi
                    {"pristupy": [{"nazev": "A", "odpoved": "a"}, {"nazev": "a", "odpoved": "b"}]},           # stejné id
                    {"pristupy": [{"nazev": "A", "odpoved": "a", "koren": 3}]},                             # koren není seznam
                    {"prihlaseni": {"otevreny": True}, "pristupy": [{"nazev": "A", "odpoved": "a"}]}):
            with self.subTest(cfg=cfg), self.assertRaises(SystemExit):
                ph.nacti_pristupy(cfg)

    def test_odkazy_a_prava(self):
        o1, o2 = hashlib.sha256(b"a").hexdigest(), hashlib.sha256(b"b").hexdigest()
        # správce má poznámky, i když je přístup zapíná jen v novém zápisu „prava“
        p = ph.nacti_pristupy({"prihlaseni": {"odpoved": "x"},
                               "pristupy": [{"nazev": "A", "odpoved": "a", "koren": [3], "prava": {"poznamky": True}}]})
        self.assertTrue(p[0]["poznamky"])
        for cfg in ({"pristupy": [{"nazev": "A", "odkazy": [{"id": "p1", "otisk": o1, "zruseno": "2026-01-01"}]}]},   # jen zrušený
                    {"pristupy": [{"nazev": "A", "odkazy": [{"id": "p1", "otisk": o1}]},                          # stejný otisk
                                  {"nazev": "B", "odkazy": [{"id": "p2", "otisk": o1}]}]}):
            with self.subTest(cfg=cfg), self.assertRaises(SystemExit):
                ph.nacti_pristupy(cfg)
        p = ph.nacti_pristupy({"pristupy": [{"nazev": "Włodek", "koren": [3], "odkazy": [{"id": "p1", "otisk": o2}]}]})
        self.assertEqual(p[0]["id"], ph._slug("Włodek"))


class Pohled(unittest.TestCase):
    def setUp(self):
        self.ns = ukazka()

    def jmena(self, nove):
        return {o["n"] for o in list(nove["P"].values()) + list(nove["RODINA"].values())}

    def test_od_matky(self):
        P = self.ns["P"]
        nove, prevod = ph.pohled(self.ns, [3])
        self.assertEqual(nove["P"][1]["n"], P[3]["n"])
        self.assertEqual(nove["P"][2]["n"], P[6]["n"])                 # otec matky = nový č. 2
        self.assertEqual(nove["P"][1]["sex"], "F")
        otcovi = {k for k in P if k >= 8 and bin(k)[3] == "0"}
        self.assertFalse(otcovi & set(prevod))                         # otcova větev od prarodičů otce chybí úplně
        self.assertEqual(prevod[2], "p2")                              # otec jen jako manžel…
        self.assertTrue({4, 5} <= set(prevod))                         # …a jeho rodiče (rodiče partnera, zadání)
        self.assertEqual(nove["RODINA"]["p1"]["otec"], "p2")           # syn: otec manžel, matka výchozí osoba
        self.assertEqual(nove["RODINA"]["p1"]["matka"], 1)
        self.assertEqual(nove["ISSUES"], [])                           # texty o celé rodině skryté
        self.assertTrue(set(nove["_zapisy"]) <= {r for p in list(P.values()) + list(self.ns["RODINA"].values()) for r in p.get("r", [])})

    def test_vychozi_1_nic_nemeni(self):
        nove, _ = ph.pohled(self.ns, [1], texty=True)
        P = self.ns["P"]
        self.assertEqual({k: v["n"] for k, v in nove["P"].items()}, {k: v["n"] for k, v in P.items() if k not in self.ns["SAME"]}
                         | {k: P[k]["n"] for k in self.ns["SAME"] if k in P})
        self.assertEqual(nove["LINES"], self.ns["LINES"])

    def test_od_osoby_z_rodiny_a_vlastni_rody(self):
        nove, _ = ph.pohled(self.ns, ["marie-novakova"], rody={"8": ["Novákové z Holic", "popis"]})
        P = self.ns["P"]
        self.assertEqual(nove["P"][1]["n"], "Marie Nováková")
        self.assertEqual(nove["P"][2]["n"], P[16]["n"])
        self.assertEqual(nove["LINES"][8], ("Novákové z Holic", "popis"))
        _, prevod = ph.pohled(self.ns, ["marie-novakova"])
        self.assertIn(3, prevod)                                       # Eva jako manželka potomka předků ano…
        self.assertTrue({6, 7} <= set(prevod))                          # …její rodiče (rodiče partnera) ano…
        self.assertFalse({k for k in P if k >= 12 and bin(k)[3] == "1"} & set(prevod))  # …další její předci ne

    def test_vice_korenu_sjednoti(self):
        nove, _ = ph.pohled(self.ns, [2, 3])
        P = self.ns["P"]
        jmena = self.jmena(nove)
        self.assertIn(P[4]["n"], jmena)
        self.assertIn(P[6]["n"], jmena)
        self.assertNotIn("otec neuveden", jmena)                       # zástupce není osoba

    def test_neznama_vychozi_osoba(self):
        with self.assertRaises(SystemExit):
            ph.pohled(self.ns, ["neexistuje"])


class ExportPristupu(unittest.TestCase):
    ODPOVEDI = {"vse": "kovář", "matcina-rodina": "Tajná Eva 1955", "marie": "marie-heslo"}

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls._tmp.name) / "p"
        assert novy_projekt(cls.p, "--ukazka").returncode == 0
        cfg_path = cls.p / "data" / "web.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["prihlaseni"].update(odpoved=cls.ODPOVEDI["vse"], otazka="Rodinná otázka")   # ukázková otázka prozrazuje odpověď
        cfg["pristupy"] = [{"nazev": "Matčina rodina", "odpoved": cls.ODPOVEDI["matcina-rodina"], "koren": [3], "poznamky": True},
                           {"nazev": "Marie", "odpoved": cls.ODPOVEDI["marie"], "koren": ["marie-novakova"]}]
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        cls.seznam = json.loads(spust(cls.p, "export_web.py", "--seznam-pristupu").stdout.strip().splitlines()[-1])
        cls.vystup = spust(cls.p, "export_web.py", "--pristup", "matcina-rodina").stdout
        cls.site = json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_seznam_pristupu(self):
        self.assertEqual(self.seznam, ["vse", "matcina-rodina", "marie"])

    def test_web_pristupu(self):
        lide = self.site["people"]
        self.assertEqual(lide[self.site["root"]]["name"], "Eva Dvořáková")
        self.assertNotIn("Václav Novák", {p["name"] for p in lide.values()})
        self.assertNotIn("pristupy", self.site["config"])
        self.assertEqual((self.p / "web" / "src" / "generated" / "zajimavosti.md").read_text(encoding="utf-8"), "")

    def test_odpovedi_nikde_ve_webu(self):
        web = self.p / "web"
        for f in [*(web / "src").rglob("*"), *(web / "public").rglob("*"), web / "nginx.conf",
                  web / "netlify" / "edge-functions" / "brana.js", web / "netlify" / "functions" / "poznamky.mjs"]:
            if f.is_file() and f.suffix in (".json", ".md", ".svg", ".html", ".js", ".conf"):
                t = f.read_text(encoding="utf-8", errors="ignore").lower()
                for o in self.ODPOVEDI.values():
                    self.assertNotIn(o.lower(), t, f"odpověď je v {f}")

    def test_brana_ma_otisky_vsech_pristupu(self):
        brana = (self.p / "web" / "netlify" / "edge-functions" / "brana.js").read_text(encoding="utf-8")
        nginx = (self.p / "web" / "nginx.conf").read_text(encoding="utf-8")
        for pid, odpoved in self.ODPOVEDI.items():
            otisk = hashlib.sha256(("rodokmen:" + ph.norm_odpoved(odpoved)).encode()).hexdigest()
            self.assertIn(f'"{otisk}": "{pid}"', brana)
            self.assertIn(f'"{otisk}" "{pid}";', nginx)
        self.assertIn("location ^~ /_p/", nginx)                       # cizí verze nejdou otevřít přímo

    def test_poznamky_podle_pristupu(self):
        self.assertTrue(self.site["config"]["poznamky"])               # matčina rodina má poznámky zapnuté
        fce = (self.p / "web" / "netlify" / "functions" / "poznamky.mjs").read_text(encoding="utf-8")
        mapa = json.loads(fce.split("const PRISTUPY = ", 1)[1].split(";", 1)[0])
        self.assertEqual({v["id"]: v["poznamky"] for v in mapa.values()},
                         {"vse": True, "matcina-rodina": True, "marie": False})   # správce („vse“) vidí přehled
        spust(self.p, "export_web.py", "--pristup", "marie")
        site = json.loads((self.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        self.assertFalse(site["config"]["poznamky"])


class PrehledPristupu(unittest.TestCase):
    """tools/pristupy.py: kdo co vidí (pomůcka k testům přístupů)."""

    def test_souhrn_a_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ukazka"
            self.assertEqual(novy_projekt(p, "--ukazka").returncode, 0)
            cfg_path = p / "data" / "web.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["prihlaseni"]["odpoved"] = "spravce"
            cfg["pristupy"] = [{"nazev": "Matka", "koren": [3], "odkazy": [{"id": "p1", "jmeno": "X",
                                "otisk": hashlib.sha256(b"k").hexdigest()}], "prava": {"soukrome": True}}]
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
            out = spust(p, "pristupy.py").stdout
            self.assertIn("== matka (Matka) – vstup: odkazy 1; práva: soukrome", out)
            self.assertRegex(out, r"osob: \d+ \(přímá linie \d+, rozšířená \d+, vlastní větev \d+\)")
            self.assertIn("-- Přímá linie:", spust(p, "pristupy.py", "matka").stdout)


if __name__ == "__main__":
    unittest.main()
