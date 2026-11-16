"""E4 (analyza/navrh-optimalizace.md, scénáře 1 a 10): účastníci zápisu se píšou jednou u zápisu a vazba zápis ↔ osoba se odvodí pro
všechny: zápis je na stránce každého účastníka s jeho rolí a na stránce zápisu jsou všichni. Kontrola hlídá tvar, karta osoby zápis zná,
migrační návrh doplní účastníky z dnešních `r`. Ukázkový projekt, bez sítě a bez Node.js."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

KLIC = "ukazka_krest_jan_novak_1890"
UCASTNICI = [{"osoba": "8", "role": "křtěnec"}, {"osoba": "16", "role": "otec"}, {"osoba": "17", "role": "matka"},
             {"osoba": "karel-hruby", "role": "kmotr"}, {"jmeno": "Václav Ukázka", "role": "kmotr"}]


def nastav(projekt, ucastnici):
    p = projekt / "data" / "zaznamy.json"
    z = json.loads(p.read_text(encoding="utf-8"))
    for r in z:
        if r["klic"] == KLIC:
            r["ucastnici"] = ucastnici
    p.write_text(json.dumps(z, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


class Ucastnici(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls._tmp.name)
        assert novy_projekt(cls.p, "--ukazka").returncode == 0
        ns = {}
        exec((cls.p / "data" / "osoby.py").read_text(encoding="utf-8"), ns)
        assert KLIC not in ns["RODINA"]["karel-hruby"].get("r", [])   # kmotr zápis v `r` nemá: vazbu dá jen pole ucastnici
        nastav(cls.p, UCASTNICI)
        spust(cls.p, "export_web.py")
        cls.site = json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        cls.rec = next(r for r in cls.site["records"] if r["key"] == KLIC)
        lide = cls.site["people"]
        cls.lide = {x["slug"]: x for x in (lide.values() if isinstance(lide, dict) else lide)}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def slug(self, k):
        if isinstance(k, int):
            return next(s for s, x in self.lide.items() if x.get("k") == k)
        return next(s for s, x in self.lide.items() if x.get("name") == "Karel Hrubý")

    def test_zapis_je_u_vsech_ucastniku_s_roli(self):
        for k, role in ((8, "křtěnec"), (16, "otec"), (17, "matka"), ("karel-hruby", "kmotr")):
            s = self.slug(k)
            self.assertIn(KLIC, self.lide[s]["records"], k)               # stránka osoby zápis ukáže
            self.assertIn(s, self.rec["people"], k)                       # stránka zápisu osobu ukáže
            self.assertEqual(self.rec["roles"][s], role, k)               # stejná role z obou stran

    def test_ucastnik_mimo_rodokmen_je_na_zapisu_jmenem(self):
        self.assertEqual(self.rec["others"], [{"name": "Václav Ukázka", "role": "kmotr"}])
        self.assertNotIn("ucastnici", self.rec)                           # klíče osob se na web nevyvážejí

    def test_sablony_roli_vykresluji(self):
        web = Path(__file__).resolve().parents[1] / "template" / "web" / "src"
        self.assertIn("r.roles", (web / "components" / "Record.astro").read_text(encoding="utf-8"))
        z = (web / "pages" / "zdroj" / "[key].astro").read_text(encoding="utf-8")
        self.assertIn("r.roles", z)
        self.assertIn("r.others", z)

    def test_kontrola_a_karta_osoby(self):
        self.assertEqual(spust(self.p, "kontrola.py", check=False).returncode, 0)
        r = spust(self.p, "kontext.py", "--osoba", "16", "--tema", "identity", "--rules",
                  str(Path(__file__).resolve().parents[3] / "skills" / "rodokmen-agents" / "rules"), check=False)
        self.assertIn(KLIC, r.stdout + r.stderr)


class Chyby(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)

    def tearDown(self):
        self._tmp.cleanup()

    def test_neznama_osoba_nebo_role_je_chyba_kontroly(self):
        for uc, text in (([{"osoba": "999", "role": "otec"}], "999"), ([{"osoba": "8", "role": "dítě"}], "role"), ([{"role": "kmotr"}], "jmeno")):
            nastav(self.p, uc)
            r = spust(self.p, "kontrola.py", check=False)
            self.assertNotEqual(r.returncode, 0, uc)
            self.assertIn(text, r.stdout + r.stderr)

    def test_kontrola_hlida_denik_tvrzeni(self):
        tv = self.p / "data" / "tvrzeni.jsonl"
        nl = chr(10)
        tv.write_text(json.dumps({"id": "T-0001", "typ": "kmotr", "osoby": ["8", "karel-hruby"], "jistota": "doc"}) + nl, encoding="utf-8")
        self.assertEqual(spust(self.p, "kontrola.py", check=False).returncode, 0)
        tv.write_text(json.dumps({"id": "T-0001", "typ": "kmotr", "osoby": ["8", "999"], "jistota": "doc"}) + nl
                      + json.dumps({"id": "T-0002", "typ": "narozeni", "osoby": ["8"], "jistota": "prob", "nahrazuje": "T-0077"}) + nl, encoding="utf-8")
        r = spust(self.p, "kontrola.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("999", r.stdout + r.stderr)
        self.assertIn("T-0077", r.stdout + r.stderr)

    def test_navrh_migrace_a_zapis_jen_uplnych(self):
        r = spust(self.p, "ucastnici.py", "navrh")
        self.assertIn("k ruční kontrole", r.stdout)
        n = json.loads((self.p / "pracovni" / "ucastnici_navrh.json").read_text(encoding="utf-8"))
        self.assertIn({"osoba": "8", "role": "křtěnec"}, n[KLIC]["ucastnici"])                          # jméno v názvu + druh N
        self.assertIn({"osoba": "16", "role": None}, n[KLIC]["ucastnici"])                              # roli rodiče nástroj nehádá
        SNATEK = "ukazka_snatek_jan_novak_josefa_pokorna_1919"                                          # skloňovaný název a jmenovec
        self.assertTrue(all(x["role"] is None for x in n[SNATEK]["ucastnici"]), n[SNATEK])              # (Josef × Josefa): nehádá se
        UMRTI = "holice_umrti_vaclav_kral_1961"
        self.assertEqual(n[UMRTI]["ucastnici"], [{"osoba": "10", "role": "zemřelý"}])                   # jediná osoba, jméno v názvu
        r = spust(self.p, "ucastnici.py", "zapis", "pracovni/ucastnici_navrh.json")
        self.assertIn("zapsáno", r.stdout)
        z = {x["klic"]: x for x in json.loads((self.p / "data" / "zaznamy.json").read_text(encoding="utf-8"))}
        self.assertEqual(z[UMRTI]["ucastnici"], [{"osoba": "10", "role": "zemřelý"}])
        self.assertNotIn("ucastnici", z[KLIC])                                                          # neúplný návrh se nezapíše
        self.assertNotIn("ucastnici", z[SNATEK])
        self.assertTrue(z[UMRTI]["nazev"])                                                              # ostatní pole zápisu zůstala
        self.assertEqual(spust(self.p, "ucastnici.py", "stav", check=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
