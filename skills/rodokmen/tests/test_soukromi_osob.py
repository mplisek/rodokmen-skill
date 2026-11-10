"""Soukromí osob (fáze 2): žijící osoby, souhlas, vlastní větev, ruční označení `soukrome` a `(soukromé) ` (bez sítě).

Testy vycházejí ze zadání, ne z implementace. Ukázkový projekt se doplní o vymyšlené osoby (DOPLNEK) a export
`export_web.py` se spustí pro správce (bez --pristup), pro tři přístupy a pro web bez přístupů.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

ZIJICI = "Žijící – údaje jen základní."
SOUKROME = "Údaje jsou soukromé."
SOUHLAS = 'souhlas={"kdo": "Dcera osobně", "datum": "2026-11-10", "rozsah": ["udaje", "doklady"]}'

# Petr = P[1] (kořen), otec P[2], matka P[3], P[4] František Novák, P[5] Marie Králová.
DOPLNEK = '''
# --- soukromí osob: vymyšlení potomci a sourozenci ---
RODINA["dite-souhlas"] = dict(n="Dítě Souhlas", y="* 2005", sex="F", otec=1, st="fam", f=["* 2005 Brno ZZ-SOUHLAS"], SOUHLAS)
RODINA["dite-bez-souhlasu"] = dict(n="Dítě Bez Souhlasu", y="* 2008", sex="M", otec=1, st="fam", f=["* 2008 Praha ZZ-BEZ"])
RODINA["dite-souhlas-bez-data"] = dict(n="Dítě Bez Data", y="* 2009", sex="M", otec=1, st="fam", f=["* 2009 ZZ-BEZDATA"],
                                       souhlas={"kdo": "Dcera osobně", "rozsah": ["udaje"]})
RODINA["dite-souhlas-bez-kdo"] = dict(n="Dítě Bez Kdo", y="* 2010", sex="M", otec=1, st="fam", f=["* 2010 ZZ-BEZKDO"],
                                      souhlas={"datum": "2026-11-10", "rozsah": ["udaje"]})
RODINA["dite-souhlas-doklady"] = dict(n="Dítě Jen Doklady", y="* 2011", sex="M", otec=1, st="fam", f=["* 2011 ZZ-DOKLADY"],
                                      souhlas={"kdo": "X", "datum": "2026-11-10", "rozsah": ["doklady"]})
RODINA["dite-souhlas-bez-rozsahu"] = dict(n="Dítě Bez Rozsahu", y="* 2012", sex="F", otec=1, st="fam", f=["* 2012 ZZ-ROZSAH"],
                                          souhlas={"kdo": "X", "datum": "2026-11-10"})
RODINA["zijici-poznamka"] = dict(n="Žijící Z Poznámky", y="* 1920", sex="F", otec=1, st="fam", f=["* 1920 ZZ-POZNAMKA"],
                                 note="Žijící sestra, bydlí v domově.")
RODINA["stary-bez-umrti"] = dict(n="Starý Bez Úmrtí", y="* 1900", sex="M", otec=1, st="fam", f=["* 1900 ZZ-STARY"])
RODINA["sourozenec-souhlas"] = dict(n="Sourozenec Souhlas", y="* 1983", sex="M", otec=2, matka=3, st="fam",
                                    f=["* 1983 Pardubice ZZ-SOUROZENEC"], SOUHLAS)
RODINA["dite-sourozence"] = dict(n="Dítě Sourozence", y="* 2006", sex="F", otec="sourozenec-souhlas", st="fam",
                                 f=["* 2006 Pardubice ZZ-DITESOUR"], SOUHLAS)
RODINA["zemrela-soukroma"] = dict(n="Zemřelá Soukromá", y="1999–2020", sex="F", otec=1, st="fam",
                                  f=["* 1999 Brno ZZ-ZEMRELA", "† 2020 Brno", "(soukromé) diagnóza TAJNE-ZEMRELA"], soukrome=True)
RODINA["zemrely-syn"] = dict(n="Zemřelý Syn", y="1990–2015", sex="M", otec=1, st="fam",
                             f=["* 1990 Plzeň ZZ-SYN", "(soukromé) rozvod 1990 TAJNE-SYN"])
RODINA["marie-novakova"]["f"].append("(soukromé) rozvod 1940 TAJNE-SESTRA")
P[4]["soukrome"] = True
P[5]["f"].append("(soukromé) rozvod 1960 TAJNE-P5")
'''.replace("SOUHLAS)", SOUHLAS + ")")

PRISTUPY = [
    {"nazev": "Se soukromim", "koren": [1], "odpoved": "odp1", "prava": {"soukrome": True, "texty": True, "poznamky": True}},
    {"nazev": "Bez prava", "koren": [1], "odpoved": "odp2", "prava": {"soukrome": False, "texty": True, "poznamky": True}},
    {"nazev": "Jina vetev", "koren": ["sourozenec-souhlas"], "odpoved": "odp3",
     "prava": {"soukrome": True, "texty": True, "poznamky": True}},
]
ID = {"se": "se-soukromim", "bez": "bez-prava", "jina": "jina-vetev"}


class SoukromiOsob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls._tmp.name) / "ukazka"
        r = novy_projekt(cls.p, "--ukazka")
        assert r.returncode == 0, r.stdout + r.stderr
        with open(cls.p / "data" / "osoby.py", "a", encoding="utf-8", newline="\n") as f:
            f.write(DOPLNEK)
        cls.web_json = cls.p / "data" / "web.json"
        cfg = json.loads(cls.web_json.read_text(encoding="utf-8"))
        cfg2 = dict(cfg, pristupy=PRISTUPY)
        cfg2["prihlaseni"] = dict(cfg.get("prihlaseni", {}), otazka="Strom?", odpoved="vse-odp", adresa="https://rod.example")
        cls.zapis_cfg(cfg2)
        spust(cls.p, "export_web.py")
        cls.vse = cls.nacti_site()
        cls.site = {}
        for klic, pid in ID.items():
            spust(cls.p, "export_web.py", "--pristup", pid)
            cls.site[klic] = cls.nacti_site()
        # celý web bez přístupů
        cfg3 = {k: v for k, v in cfg2.items() if k != "pristupy"}
        cfg3["prihlaseni"] = {k: v for k, v in cfg2["prihlaseni"].items() if k != "odpoved"}
        cls.zapis_cfg(cfg3)
        cls.bez_pristupu_rc = spust(cls.p, "export_web.py", check=False)
        cls.celek = cls.nacti_site() if cls.bez_pristupu_rc.returncode == 0 else None

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @classmethod
    def zapis_cfg(cls, cfg):
        cls.web_json.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def nacti_site(cls):
        return json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))

    # --- pomůcky ---
    @staticmethod
    def zdroje(site):
        others = site.get("others") or []
        return [list(site["people"].values()), list(others.values()) if isinstance(others, dict) else list(others)]

    def vyskyty(self, site, jmeno):
        """Všechny výskyty osoby (people i others) podle jména."""
        return [p for z in self.zdroje(site) for p in z if p.get("name") == jmeno]

    def osoba(self, site, jmeno):
        v = self.vyskyty(site, jmeno)
        self.assertTrue(v, f"{jmeno} není v site.json")
        return v[0]

    def v_people(self, site, jmeno):
        v = [p for p in site["people"].values() if p["name"] == jmeno]
        self.assertTrue(v, f"{jmeno} chybí v people")
        return v[0]

    def assert_skryta_zijici(self, site, jmeno):
        v = self.vyskyty(site, jmeno)
        self.assertTrue(v, f"{jmeno} není v site.json")
        for p in v:
            self.assertEqual(p["facts"], [], jmeno)
            self.assertEqual(p["records"], [], jmeno)
            self.assertEqual(p["note"], ZIJICI, jmeno)

    def facts(self, site, jmeno):
        return self.osoba(site, jmeno)["facts"]

    @staticmethod
    def text(site):
        return json.dumps(site, ensure_ascii=False)

    def radek(self, site, k):
        """Řádek časové osy předka P[k] (osa obsahuje jen předky podle Kekulého čísel)."""
        radky = [r for r in site["timeline"]["rows"] if r.get("k") == k]
        self.assertTrue(radky, f"P[{k}] není na časové ose")
        return radky[0]

    # --- žijící: správce ---
    def test_spravce_zijici_se_souhlasem_plne_udaje(self):
        self.assertIn("* 2005 Brno ZZ-SOUHLAS", self.facts(self.vse, "Dítě Souhlas"))
        self.assertIn("* 1983 Pardubice ZZ-SOUROZENEC", self.facts(self.vse, "Sourozenec Souhlas"))

    def test_spravce_zijici_bez_souhlasu_skryti(self):
        self.assert_skryta_zijici(self.vse, "Dítě Bez Souhlasu")
        self.assertNotIn("ZZ-BEZ\"", self.text(self.vse))

    def test_neplatny_souhlas_je_jako_zadny(self):
        for jmeno, znacka in (("Dítě Bez Data", "ZZ-BEZDATA"), ("Dítě Bez Kdo", "ZZ-BEZKDO"),
                              ("Dítě Jen Doklady", "ZZ-DOKLADY")):
            self.assert_skryta_zijici(self.vse, jmeno)
            self.assertNotIn(znacka, self.text(self.vse), jmeno)

    def test_souhlas_bez_rozsahu_plati(self):
        self.assertIn("* 2012 ZZ-ROZSAH", self.facts(self.vse, "Dítě Bez Rozsahu"))

    def test_zijici_podle_poznamky_i_kdyz_stara(self):
        self.assert_skryta_zijici(self.vse, "Žijící Z Poznámky")
        self.assertNotIn("ZZ-POZNAMKA", self.text(self.vse))

    def test_stary_bez_umrti_neni_zijici(self):
        self.assertIn("* 1900 ZZ-STARY", self.facts(self.vse, "Starý Bez Úmrtí"))

    def test_zijici_jmeno_a_rok_zustavaji(self):
        p = self.osoba(self.vse, "Dítě Bez Souhlasu")
        self.assertEqual(p["name"], "Dítě Bez Souhlasu")
        self.assertIn("2008", json.dumps(p, ensure_ascii=False))

    # --- časová osa (jen předci; žijící předci P[1] Petr, P[2] Josef, P[3] Eva mají poznámku „Žijící“) ---
    def assert_osa_zijici(self, site, k):
        r = self.radek(site, k)
        self.assertFalse(r.get("death"), r)
        self.assertFalse(r.get("marriage"), r)
        self.assertTrue(r.get("birth"), r)
        self.assertRegex(str(r["birth"].get("text")), r"^\D*\d{4}\D*$", r)  # jen rok, žádné místo
        self.assertNotIn("Holice", json.dumps(r, ensure_ascii=False))
        self.assertNotIn("Chrudim", json.dumps(r, ensure_ascii=False))

    def test_osa_zijici_jen_rok_narozeni_spravce(self):
        for k in (1, 2, 3):
            self.assert_osa_zijici(self.vse, k)

    def test_osa_zijici_jen_rok_narozeni_pristup_s_pravem(self):
        # Petr je kořen (vlastní větev) bez souhlasu, rodiče jsou mimo vlastní větev
        for k in (1, 2, 3):
            self.assert_osa_zijici(self.site["se"], k)

    def test_osa_zemrely_ma_umrti_a_snatek(self):
        r = self.radek(self.vse, 5)
        self.assertTrue(r.get("death"), r)
        self.assertTrue(r.get("marriage"), r)

    # --- přístup s právem soukrome ---
    def test_pristup_s_pravem_vlastni_vetev_se_souhlasem_plne(self):
        s = self.site["se"]
        self.assertTrue(self.v_people(s, "Dítě Souhlas")["vlastni"])
        self.assertIn("* 2005 Brno ZZ-SOUHLAS", self.facts(s, "Dítě Souhlas"))
        self.assertIn("* 2012 ZZ-ROZSAH", self.facts(s, "Dítě Bez Rozsahu"))

    def test_pristup_s_pravem_vlastni_vetev_bez_souhlasu_skryta(self):
        s = self.site["se"]
        self.assert_skryta_zijici(s, "Dítě Bez Souhlasu")
        for znacka in ("ZZ-BEZ\"", "ZZ-BEZDATA", "ZZ-BEZKDO", "ZZ-DOKLADY", "ZZ-POZNAMKA"):
            self.assertNotIn(znacka, self.text(s), znacka)

    def test_pristup_s_pravem_sourozenec_se_souhlasem_jen_jmeno(self):
        s = self.site["se"]
        self.assertFalse(self.v_people(s, "Sourozenec Souhlas")["vlastni"])
        self.assert_skryta_zijici(s, "Sourozenec Souhlas")
        self.assert_skryta_zijici(s, "Dítě Sourozence")
        self.assertNotIn("ZZ-SOUROZENEC", self.text(s))
        self.assertNotIn("ZZ-DITESOUR", self.text(s))

    def test_pristup_bez_prava_se_souhlasem_jen_jmeno(self):
        s = self.site["bez"]
        self.assert_skryta_zijici(s, "Dítě Souhlas")
        self.assert_skryta_zijici(s, "Dítě Bez Rozsahu")
        self.assertNotIn("ZZ-SOUHLAS", self.text(s))
        self.assertNotIn("ZZ-ROZSAH", self.text(s))

    def test_pristup_jine_vetve_koren_je_vlastni_a_plny(self):
        s = self.site["jina"]
        self.assertTrue(self.v_people(s, "Sourozenec Souhlas")["vlastni"])
        self.assertIn("* 1983 Pardubice ZZ-SOUROZENEC", self.facts(s, "Sourozenec Souhlas"))
        self.assertIn("* 2006 Pardubice ZZ-DITESOUR", self.facts(s, "Dítě Sourozence"))

    def test_pristup_jine_vetve_dite_z_cizi_vetve_jen_jmeno(self):
        # Dítě Souhlas je dítě Petra (sourozence kořene) – ve vlastní větvi tohoto přístupu není
        s = self.site["jina"]
        for p in self.vyskyty(s, "Dítě Souhlas"):
            self.assertEqual(p["facts"], [])
            self.assertEqual(p["note"], ZIJICI)
        self.assertNotIn("ZZ-SOUHLAS", self.text(s))

    # --- ruční označení: osoba soukrome=True ---
    def test_soukroma_osoba_pravo_a_vlastni_vetev_vidi_vse(self):
        s = self.site["se"]
        self.assertTrue(self.v_people(s, "Zemřelá Soukromá")["vlastni"])
        f = self.facts(s, "Zemřelá Soukromá")
        self.assertIn("* 1999 Brno ZZ-ZEMRELA", f)
        self.assertIn("diagnóza TAJNE-ZEMRELA", f)
        self.assertNotEqual(self.osoba(s, "Zemřelá Soukromá")["note"], SOUKROME)

    def test_soukroma_osoba_bez_prava_jen_jmeno_a_roky(self):
        s = self.site["bez"]
        p = self.osoba(s, "Zemřelá Soukromá")
        self.assertEqual(p["facts"], [])
        self.assertEqual(p["note"], SOUKROME)
        self.assertIn("1999", json.dumps(p, ensure_ascii=False))
        self.assertNotIn("ZZ-ZEMRELA", self.text(s))
        self.assertNotIn("TAJNE-ZEMRELA", self.text(s))

    def test_soukroma_osoba_mimo_vlastni_vetev_je_skryta_i_s_pravem(self):
        p = self.v_people(self.site["se"], "František Novák")
        self.assertFalse(p["vlastni"])
        self.assertEqual(p["facts"], [])
        self.assertEqual(p["note"], SOUKROME)

    def test_soukroma_osoba_spravce_vidi_vse(self):
        p = self.osoba(self.vse, "František Novák")
        self.assertIn("* 3. 5. 1921 Holice čp. 112", p["facts"])
        self.assertNotEqual(p["note"], SOUKROME)

    # --- ruční označení: údaj (soukromé) ---
    def test_soukromy_udaj_pravo_a_vlastni_vetev_bez_znacky(self):
        f = self.facts(self.site["se"], "Zemřelý Syn")
        self.assertIn("rozvod 1990 TAJNE-SYN", f)
        self.assertFalse([x for x in f if "(soukromé)" in x], f)

    def test_soukromy_udaj_bez_prava_nikde_v_site_json(self):
        s = self.site["bez"]
        self.assertNotIn("TAJNE-SYN", self.text(s))
        self.assertNotIn("(soukromé)", self.text(s))
        self.assertIn("* 1990 Plzeň ZZ-SYN", self.facts(s, "Zemřelý Syn"))  # zbytek údajů zůstává

    def test_soukromy_udaj_mimo_vlastni_vetev_nikde_v_site_json(self):
        s = self.site["se"]
        for znacka in ("TAJNE-P5", "TAJNE-SESTRA", "(soukromé)"):
            self.assertNotIn(znacka, self.text(s), znacka)

    def test_soukromy_udaj_u_predka_a_sourozence_predka_spravce_bez_znacky(self):
        self.assertIn("rozvod 1940 TAJNE-SESTRA", self.facts(self.vse, "Marie Nováková"))
        self.assertIn("rozvod 1960 TAJNE-P5", self.facts(self.vse, "Marie Králová"))
        self.assertNotIn("(soukromé)", self.text(self.vse))

    def test_pristup_jine_vetve_nevidi_cizi_soukrome_udaje(self):
        s = self.site["jina"]
        for znacka in ("TAJNE-SYN", "TAJNE-ZEMRELA", "TAJNE-P5", "TAJNE-SESTRA", "(soukromé)"):
            self.assertNotIn(znacka, self.text(s), znacka)

    # --- celý web bez přístupů ---
    def test_bez_pristupu_zijici_podle_souhlasu(self):
        self.assertEqual(self.bez_pristupu_rc.returncode, 0, self.bez_pristupu_rc.stdout + self.bez_pristupu_rc.stderr)
        c = self.celek
        self.assert_skryta_zijici(c, "Dítě Bez Souhlasu")
        self.assert_skryta_zijici(c, "Dítě Bez Data")
        self.assertIn("* 2005 Brno ZZ-SOUHLAS", self.facts(c, "Dítě Souhlas"))
        self.assertIn("* 1983 Pardubice ZZ-SOUROZENEC", self.facts(c, "Sourozenec Souhlas"))
        self.assertNotIn("ZZ-BEZ\"", self.text(c))


if __name__ == "__main__":
    unittest.main()
