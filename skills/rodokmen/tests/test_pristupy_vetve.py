"""Přístupy s kořenem a větvemi: přímá a rozšířená linie, vlastní větev, práva, stránky, brána (bez sítě).

Testy vycházejí ze zadání (datový kontrakt `web.json` -> `pristupy` a `site.json` -> `pristup`, `people[].linie`,
`people[].vlastni`, `stranky`), ne z implementace. Ukázkový projekt se doplní o vymyšlené větve (DOPLNEK)
a pro každý přístup se jednou spustí `export_web.py --pristup <id>`.
"""
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

# Doplněné osoby (jména jsou záměrně jedinečná, hledá se podle nich). Petr = P[1], jeho otec P[2], matka P[3],
# otec otce P[4] (František Novák), jeho otec P[8] (Jan Novák).
DOPLNEK = '''
# sourozenec kořene, jeho partnerka, její rodina a dítě sourozence s potomkem
RODINA["sourozenec-petra"] = dict(n="Sourozenec Petra", y="* 1983", sex="M", otec=2, matka=3, st="fam")
RODINA["partnerka-sourozence"] = dict(n="Partnerka Sourozence", y="* 1984", sex="F", otec="otec-partnerky",
                                      matka="matka-partnerky", st="fam")
RODINA["otec-partnerky"] = dict(n="Otec Partnerky", y="* 1955", sex="M", otec="otec-otce-partnerky", st="fam")
RODINA["matka-partnerky"] = dict(n="Matka Partnerky", y="* 1957", sex="F", st="fam")
RODINA["otec-otce-partnerky"] = dict(n="Otec Otce Partnerky", y="1920–1990", sex="M", st="fam")
RODINA["sourozenec-partnerky"] = dict(n="Sourozenec Partnerky", y="* 1986", sex="M", otec="otec-partnerky",
                                      matka="matka-partnerky", st="fam")
RODINA["synovec-petra"] = dict(n="Synovec Petra", y="* 2006", sex="M", otec="sourozenec-petra",
                               matka="partnerka-sourozence", st="fam")
RODINA["potomek-synovce"] = dict(n="Potomek Synovce", y="* 2025", sex="M", otec="synovec-petra", st="fam")
# strýc (sourozenec předka P[4]), jeho partnerka, syn a vnuk
RODINA["stryc-alois"] = dict(n="Strýc Alois", y="1915–1990", sex="M", otec=8, matka=9, st="fam")
RODINA["manzelka-stryce"] = dict(n="Manželka Strýce", y="1918–2000", sex="F", st="fam")
RODINA["bratranec-petra"] = dict(n="Bratranec Petra", y="* 1950", sex="M", otec="stryc-alois",
                                 matka="manzelka-stryce", st="fam")
RODINA["dite-bratrance"] = dict(n="Dítě Bratrance", y="* 1980", sex="F", otec="bratranec-petra", st="fam")
# dítě kořene, partner dítěte a partnerka kořene
RODINA["partnerka-petra"] = dict(n="Partnerka Petra", y="* 1982", sex="F", st="fam")
RODINA["dcera-petra"] = dict(n="Dcera Petra", y="* 2005", sex="F", otec=1, matka="partnerka-petra", st="fam")
RODINA["partner-dcery"] = dict(n="Partner Dcery", y="* 2004", sex="M", st="fam")
# osoba bez vazby na rozšířenou linii
RODINA["cizi-osoba"] = dict(n="Cizí Osoba", y="* 1975", sex="M", st="fam")
# dvě větve bez společných předků
RODINA["va-koren"] = dict(n="Kořen Větve A", y="* 1970", sex="M", st="fam")
RODINA["va-partnerka"] = dict(n="Partnerka Větve A", y="* 1972", sex="F", st="fam")
RODINA["va-dite"] = dict(n="Dítě Větve A", y="* 2000", sex="F", otec="va-koren", matka="va-partnerka", st="fam")
RODINA["vb-koren"] = dict(n="Kořen Větve B", y="* 1965", sex="M", st="fam")
RODINA["vb-partnerka"] = dict(n="Partnerka Větve B", y="* 1967", sex="F", st="fam")
RODINA["vb-dite"] = dict(n="Dítě Větve B", y="* 1995", sex="M", otec="vb-koren", matka="vb-partnerka", st="fam")
PARTNERI = [
    dict(a=1, b="partnerka-petra"),
    dict(a="sourozenec-petra", b="partnerka-sourozence"),
    dict(a="dcera-petra", b="partner-dcery"),
    dict(a="stryc-alois", b="manzelka-stryce"),
    dict(a="va-koren", b="va-partnerka"),
    dict(a="vb-koren", b="vb-partnerka"),
]
'''

# id přístupu = název bez diakritiky malými písmeny s pomlčkami
PRISTUPY = [
    {"nazev": "Petrova rodina", "koren": [1], "odpoved": "odp1"},                            # bez práv
    {"nazev": "Starý zápis", "koren": [1], "odpoved": "odp2", "texty": True, "poznamky": True},  # starší zápis práv
    {"nazev": "Nová práva", "koren": [1], "odpoved": "odp3",
     "prava": {"soukrome": True, "texty": False, "poznamky": True}},
    {"nazev": "Dva kořeny", "koren": [1, "va-koren"], "odpoved": "odp4"},
    {"nazev": "Dva kořeny obráceně", "koren": ["va-koren", 1], "odpoved": "odp5"},
    {"nazev": "Větev A", "koren": ["va-koren"], "odpoved": "odp6"},
    {"nazev": "Větev B", "koren": ["vb-koren"], "odpoved": "odp7"},
]
ID = {"petr": "petrova-rodina", "stary": "stary-zapis", "nova": "nova-prava", "dva": "dva-koreny",
      "dva_obracene": "dva-koreny-obracene", "va": "vetev-a", "vb": "vetev-b"}

STRANKY = {"pribeh", "zajimavosti", "statistiky", "osobnosti", "rody", "mapa", "domy", "vejir", "osa", "strom",
           "predci", "zapisy", "dokumenty", "hledame", "poznamky"}


def sha(klic):
    return hashlib.sha256(klic.encode()).hexdigest()


class PristupyVetve(unittest.TestCase):
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
        cfg["pristupy"] = PRISTUPY
        cfg["prihlaseni"]["otazka"] = "Strom před domem?"
        cfg["prihlaseni"]["odpoved"] = "vse-odpoved"
        cfg["prihlaseni"]["adresa"] = "https://rod.example"
        cls.cfg = cfg
        cls.zapis_cfg(cfg)
        # správce vidí všechno (plný export), pak každý přístup zvlášť
        spust(cls.p, "export_web.py")
        cls.vse = cls.nacti_site()
        cls.site = {}
        for klic, pid in ID.items():
            spust(cls.p, "export_web.py", "--pristup", pid)
            cls.site[klic] = cls.nacti_site()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @classmethod
    def zapis_cfg(cls, cfg):
        cls.web_json.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def nacti_site(cls):
        return json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))

    @staticmethod
    def podle_jmena(site):
        return {p["name"]: p for p in site["people"].values()}

    def jmena(self, klic):
        return set(self.podle_jmena(self.site[klic]))

    def osoba(self, klic, jmeno):
        lide = self.podle_jmena(self.site[klic])
        self.assertIn(jmeno, lide, f"{jmeno} chybí v přístupu {klic}")
        return lide[jmeno]

    # --- 1. přímá linie ---
    def test_prima_linie_koren_a_predci(self):
        for jmeno in ("Petr Novák", "Eva Dvořáková", "František Novák", "Marie Králová", "Josefa Pokorná",
                      "Barbora Malá", "Jakub Novák"):
            self.assertEqual(self.osoba("petr", jmeno)["linie"], "prima", jmeno)
        # všichni předci + kořen = přímá linie, nic víc
        prima = [p for p in self.site["petr"]["people"].values() if p["linie"] == "prima"]
        self.assertEqual(len(prima), self.site["petr"]["stats"]["ancestors"] + 1)

    def test_pristup_vychozi_osoba_je_koren(self):
        pr = self.site["petr"]["pristup"]
        self.assertEqual(pr["id"], ID["petr"])
        self.assertEqual(pr["nazev"], "Petrova rodina")
        self.assertEqual([self.site["petr"]["people"][s]["name"] for s in pr["koreny"]], ["Petr Novák"])

    # --- 2. sourozenec kořene a jeho potomci ---
    def test_sourozenec_korene_a_potomek_jsou_rozsirena(self):
        for jmeno in ("Sourozenec Petra", "Synovec Petra", "Potomek Synovce"):
            self.assertEqual(self.osoba("petr", jmeno)["linie"], "rozsirena", jmeno)

    # --- 3. sourozenec předka a jeho potomci ---
    def test_stryc_a_jeho_vetev_jsou_rozsirena(self):
        for jmeno in ("Strýc Alois", "Bratranec Petra", "Dítě Bratrance"):
            self.assertEqual(self.osoba("petr", jmeno)["linie"], "rozsirena", jmeno)

    def test_sestra_predka_z_ukazky_a_jeji_syn_jsou_rozsirena(self):
        # ukázka: Marie Nováková je sestra Jana Nováka (P[8]), Jaroslav Hrubý její syn
        self.assertEqual(self.osoba("petr", "Marie Nováková")["linie"], "rozsirena")
        self.assertEqual(self.osoba("petr", "Jaroslav Hrubý")["linie"], "rozsirena")

    # --- 4. partner a rodiče partnera ---
    def test_partner_sourozence_a_rodice_partnera_jsou_pritomni(self):
        for jmeno in ("Partnerka Sourozence", "Otec Partnerky", "Matka Partnerky"):
            self.assertEqual(self.osoba("petr", jmeno)["linie"], "rozsirena", jmeno)

    def test_sourozenec_a_prarodice_partnera_nejsou_pritomni(self):
        lide = self.jmena("petr")
        self.assertNotIn("Sourozenec Partnerky", lide)
        self.assertNotIn("Otec Otce Partnerky", lide)

    def test_partner_stryce_je_pritomen(self):
        self.assertEqual(self.osoba("petr", "Manželka Strýce")["linie"], "rozsirena")

    # --- 5. osoba bez vazby ---
    def test_osoba_bez_vazby_neni_v_pristupu(self):
        self.assertIn("Cizí Osoba", self.podle_jmena(self.vse))          # správce ji vidí, test není prázdný
        for klic in ID:
            self.assertNotIn("Cizí Osoba", self.jmena(klic), klic)

    def test_osoby_mimo_linii_nejsou_v_people(self):
        # people obsahuje jen prima/rozsirena
        for klic in ID:
            for p in self.site[klic]["people"].values():
                self.assertIn(p["linie"], ("prima", "rozsirena"), (klic, p["name"]))
        self.assertLess(len(self.site["petr"]["people"]), len(self.vse["people"]))

    # --- 6. vlastní větev ---
    def test_vlastni_vetev_koren_dite_a_partner_ditete(self):
        for jmeno in ("Petr Novák", "Dcera Petra", "Partner Dcery", "Partnerka Petra"):
            self.assertTrue(self.osoba("petr", jmeno)["vlastni"], jmeno)

    def test_sourozenec_a_predek_nejsou_vlastni_vetev(self):
        for jmeno in ("Sourozenec Petra", "Synovec Petra", "Eva Dvořáková", "František Novák", "Strýc Alois"):
            self.assertFalse(self.osoba("petr", jmeno)["vlastni"], jmeno)

    # --- 7. víc kořenů ---
    def test_dva_koreny_jsou_sjednoceni(self):
        self.assertEqual(self.jmena("dva"), self.jmena("petr") | self.jmena("va"))
        self.assertEqual(len(self.site["dva"]["pristup"]["koreny"]), 2)

    def test_dva_koreny_statistiky_jen_od_prvniho(self):
        predci_petra = self.site["petr"]["stats"]["ancestors"]
        self.assertGreater(predci_petra, 0)
        self.assertEqual(self.site["dva"]["stats"]["ancestors"], predci_petra)
        # první kořen bez předků -> 0, i když sjednocení předky druhého kořene obsahuje
        self.assertEqual(self.site["dva_obracene"]["stats"]["ancestors"], 0)
        self.assertEqual(self.jmena("dva_obracene"), self.jmena("dva"))

    def test_dva_koreny_vlastni_jsou_oba(self):
        for jmeno in ("Petr Novák", "Kořen Větve A", "Dítě Větve A"):
            self.assertTrue(self.osoba("dva", jmeno)["vlastni"], jmeno)

    # --- 8. odpověď / odkazy ---
    def test_pristup_bez_odpovedi_a_odkazu_je_chyba(self):
        cfg = dict(self.cfg, pristupy=[{"nazev": "Prázdný přístup", "koren": [1]}])
        self.zapis_cfg(cfg)
        try:
            r = spust(self.p, "export_web.py", check=False)
        finally:
            self.zapis_cfg(self.cfg)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        vystup = r.stdout + r.stderr
        self.assertIn("CHYBA", vystup)
        self.assertIn("Prázdný přístup", vystup)

    def test_pristup_jen_s_odkazy_projde_a_otisk_je_v_brane(self):
        otisk = sha("tajny-klic-tety")
        pristup = {"nazev": "Jen odkaz", "koren": [1],
                   "odkazy": [{"id": "p1", "jmeno": "Teta", "otisk": otisk, "vytvoreno": "2026-11-10"}]}
        self.zapis_cfg(dict(self.cfg, pristupy=[pristup]))
        try:
            spust(self.p, "export_web.py")
            spust(self.p, "export_web.py", "--pristup", "jen-odkaz")
            text = (self.p / "web" / "netlify" / "edge-functions" / "brana.js").read_text(encoding="utf-8")
        finally:
            self.zapis_cfg(self.cfg)
        klice = json.loads(re.search(r"const KLICE = (\{.*?\});", text, re.S).group(1))
        self.assertEqual(klice.get(otisk), "jen-odkaz")

    def test_seznam_pristupu(self):
        r = spust(self.p, "export_web.py", "--seznam-pristupu")
        ids = json.loads(r.stdout)
        self.assertTrue(set(ID.values()) <= set(ids), ids)

    # --- 9. práva ---
    def test_bez_prav_jsou_vsechna_false(self):
        self.assertEqual(self.site["petr"]["pristup"]["prava"],
                         {"soukrome": False, "texty": False, "poznamky": False})

    def test_starsi_zapis_prav_plati_jako_prava(self):
        prava = self.site["stary"]["pristup"]["prava"]
        self.assertTrue(prava["texty"])
        self.assertTrue(prava["poznamky"])
        self.assertFalse(prava["soukrome"])

    def test_prava_objekt_a_nevyplnene_je_false(self):
        self.assertEqual(self.site["nova"]["pristup"]["prava"],
                         {"soukrome": True, "texty": False, "poznamky": True})

    # --- 10. stránky ---
    def test_stranky_ukazka_bez_domu(self):
        stranky = self.site["petr"]["stranky"]
        self.assertEqual(set(stranky), STRANKY)
        for hodnota in stranky.values():
            self.assertIsInstance(hodnota, bool)
        self.assertFalse(stranky["domy"])
        self.assertTrue(stranky["predci"])

    # --- 11. izolace větví ---
    def test_dve_vetve_se_navzajem_nevidi(self):
        a = {p["name"] for p in self.site["va"]["people"].values() if p["vlastni"]}
        b = {p["name"] for p in self.site["vb"]["people"].values() if p["vlastni"]}
        self.assertEqual(a, {"Kořen Větve A", "Dítě Větve A", "Partnerka Větve A"})
        self.assertEqual(b, {"Kořen Větve B", "Dítě Větve B", "Partnerka Větve B"})
        self.assertFalse(a & self.jmena("vb"))
        self.assertFalse(b & self.jmena("va"))
        # ani přímá linie Petra o větvích nic neví
        self.assertFalse((a | b) & self.jmena("petr"))


if __name__ == "__main__":
    unittest.main()
