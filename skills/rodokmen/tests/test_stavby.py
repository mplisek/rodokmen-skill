"""stavby.py: kontrola dat staveb, náměty z rodokmenu, export pro web (stránka Domy).

Čisté funkce se zkouší na malých slovnících; integrační část založí ukázkový projekt (novy_projekt.py --ukazka), přidá
data/stavby.py a spustí export_web.py a stavby.py. Síť ani Node.js nepotřebuje.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt, spust  # noqa: E402

sys.path.insert(0, str(TOOLS))
import stavby as sv  # noqa: E402

P = {
    8: dict(n="Jan Novák", y="1890–1944", f=["* 1890 Holice čp. 112", "kovář v Holicích"]),
    16: dict(n="Václav Novák", y="1858–1921", f=["kovář", "hostinský v Holicích čp. 112"]),
    1: dict(n="Žijící Osoba", y="* 1975", note="Žijící – údaje jen základní."),
}
RODINA = {"anna": dict(n="Anna Nováková", y="† 1879")}


def dum(**kw):
    s = dict(nazev="Kovárna", typ="kovarna", popis="Rodinná kovárna.", dum="holice-112", st="doc",
             udalosti=[dict(rok="1838", text="Na skice.", st="doc", zdroj="skica")],
             drzitele=[dict(od="1850", do="1890", n="Václav Novák", os=16, st="doc", r=["z1"])],
             obyvatele=[dict(os=8, role="kovář", st="doc", r=["z1"])])
    s.update(kw)
    return s


def texty(upoz, uroven=None):
    return [t for u, t in upoz if uroven in (None, u)]


class Kontrola(unittest.TestCase):
    def kontrola(self, **kw):
        return sv.zkontroluj({"holice-112": dum(**kw)}, P, RODINA, zaznamy={"z1"}, adresy={"holice-112": {}})

    def test_v_poradku(self):
        self.assertEqual(self.kontrola(), [])

    def test_chybi_pole_a_spatny_typ_a_stav(self):
        u = self.kontrola(nazev="", typ="vila", st="jisté")
        t = texty(u, "CHYBA")
        self.assertTrue(any("chybí pole nazev" in x for x in t))
        self.assertTrue(any("neznámý typ" in x for x in t))
        self.assertTrue(any("stav st musí být" in x for x in t))

    def test_doc_vyzaduje_zdroj_a_lit_vyzaduje_zdroj(self):
        u = self.kontrola(udalosti=[dict(rok="1838", text="a", st="doc"), dict(rok="1700", text="b", st="lit")])
        t = texty(u, "CHYBA")
        self.assertTrue(any("doc vyžaduje" in x for x in t))
        self.assertTrue(any("lit vyžaduje zdroj" in x for x in t))

    def test_prob_bez_poznamky_je_pozor(self):
        u = self.kontrola(udalosti=[dict(rok="1838", text="a", st="prob")])
        self.assertTrue(any("prob bez poznámky" in x for x in texty(u, "POZOR")))

    def test_neexistujici_osoba_a_zapis(self):
        u = self.kontrola(obyvatele=[dict(os=99, role="x", st="doc", r=["nic"])])
        t = texty(u, "CHYBA")
        self.assertTrue(any("osoba 99" in x for x in t))
        self.assertTrue(any("„nic“ není v data/zaznamy.json" in x for x in t))

    def test_osoba_z_rodiny_podle_klice(self):
        self.assertEqual(self.kontrola(obyvatele=[dict(os="anna", role="x", st="fam")]), [])

    def test_chybi_osoba_i_jmeno(self):
        self.assertTrue(any("chybí osoba" in x for x in texty(self.kontrola(obyvatele=[dict(role="x", st="fam")]), "CHYBA")))

    def test_dum_neni_v_adresach(self):
        u = sv.zkontroluj({"a": dum(dum="jinde-1")}, P, RODINA, zaznamy={"z1"}, adresy={"holice-112": {}})
        self.assertTrue(any("není v data/domy/adresy.json" in x for x in texty(u, "POZOR")))

    def test_zijici_jen_jmeno_a_role(self):
        u = self.kontrola(obyvatele=[dict(os=1, role="majitel", st="fam", f=["* 1975 Holice"])])
        self.assertTrue(any("žijící" in x for x in texty(u, "SOUKROMÍ")))
        self.assertEqual(self.kontrola(obyvatele=[dict(os=1, role="majitel", st="fam")]), [])

    def test_drzitel_po_1950_jen_se_souhlasem(self):
        h = dict(od="1990", n="Cizí Majitel", st="fam", note="koupil")
        self.assertTrue(any("souhlasem" in x for x in texty(self.kontrola(drzitele=[h]), "SOUKROMÍ")))
        self.assertEqual(self.kontrola(drzitele=[dict(h, souhlas="e-mail 3. 11. 2026")]), [])


class Pomocne(unittest.TestCase):
    def test_rok(self):
        self.assertEqual(sv.rok("před 1836"), 1836)
        self.assertEqual(sv.rok("asi 1840–1850"), 1840)
        self.assertIsNone(sv.rok(""))
        self.assertIsNone(sv.rok(None))

    def test_kmen_sloucí_skloňované_tvary(self):
        self.assertEqual(sv.kmen("Křemenice"), sv.kmen("Křemenici"))
        self.assertEqual(sv.kmen("Smiřice"), sv.kmen("Smiřic"))
        self.assertNotEqual(sv.kmen("Dolní Vestec"), sv.kmen("Horní Vestec")[:2] + "x")


class Kandidati(unittest.TestCase):
    P2 = {
        1: dict(n="Hostinský Jedna", y="1800–1860", f=["hostinský v Holicích čp. 112"]),
        2: dict(n="Syn Jedna", y="1830–1890", f=["* 1830 Holice čp. 112"]),
        3: dict(n="Osamělý", y="1800–1860", f=["* 1800 Lhota čp. 5"]),
    }

    def test_remeslo_a_vice_lidi_dava_naved(self):
        k = sv.kandidati(self.P2, {}, {}, jmena=["Holice"])
        self.assertEqual([(d["obec"], d["cp"]) for d in k], [("Holice", 112)])
        self.assertIn("hostinec", k[0]["role"])
        self.assertEqual(k[0]["skore"], 5)   # dva lidé + 3 za řemeslo

    def test_vse_ukaze_i_slabe(self):
        self.assertEqual(len(sv.kandidati(self.P2, {}, {}, vse=True)), 2)

    def test_hotove_domy_se_vynechaji_podle_adresy_i_klice(self):
        adresy = {"holice-112": dict(obec="Holice", cp=112)}
        self.assertEqual(sv.kandidati(self.P2, {}, {"x": dict(dum="holice-112")}, adresy), [])
        self.assertEqual(sv.kandidati(self.P2, {}, {"holice-112": dict()}, adresy), [])
        self.assertEqual(sv.kandidati(self.P2, {}, {"holice-112": dict()}), [])   # i bez adresy.json, podle klíče

    def test_zakladni_tvar_obce(self):
        P3 = {1: dict(n="A", f=["hostinský v Křemenici čp. 2"]), 2: dict(n="B", f=["* 1 Křemenici čp. 2"])}
        k = sv.kandidati(P3, {}, {}, jmena=["Křemenice"])
        self.assertEqual(k[0]["obec"], "Křemenice")


class ExportCisteFunkce(unittest.TestCase):
    by_k = {8: dict(slug="jan-novak-1890"), 16: dict(slug="vaclav-novak-1858")}
    by_key = {"anna": dict(slug="anna-novakova-1879")}
    recs = {"z1": dict(title="Křest", date="1890")}

    def exp(self, **kw):
        return sv.sestav_export({"holice-112": dum(**kw)}, P, RODINA, self.by_k, self.by_key, self.recs)

    def test_osoby_se_preloží_na_jména_a_odkazy(self):
        s = self.exp()["holice-112"]
        self.assertEqual(s["typ_text"], "kovárna")
        self.assertEqual((s["drzitele"][0]["name"], s["drzitele"][0]["slug"]), ("Václav Novák", "vaclav-novak-1858"))
        self.assertEqual(s["obyvatele"][0]["zapisy"][0]["title"], "Křest")

    def test_osoba_z_rodiny_a_cizi_jmeno(self):
        s = self.exp(obyvatele=[dict(os="anna", role="x", st="fam"), dict(n="Cizí", role="čeledín", st="fam")])["holice-112"]
        self.assertEqual(s["obyvatele"][0]["slug"], "anna-novakova-1879")
        self.assertEqual((s["obyvatele"][1]["name"], s["obyvatele"][1]["slug"]), ("Cizí", None))

    def test_zijici_bez_podrobnosti(self):
        s = self.exp(obyvatele=[dict(os=1, role="majitel", st="fam", note="tajné", r=["z1"])])["holice-112"]
        self.assertEqual((s["obyvatele"][0]["note"], s["obyvatele"][0]["zapisy"]), ("", []))
        self.assertEqual(s["obyvatele"][0]["role"], "majitel")

    def test_drzitel_po_1950_bez_souhlasu_nejde_na_web(self):
        h = dict(od="1990", n="Cizí Majitel", st="fam")
        self.assertEqual(self.exp(drzitele=[h])["holice-112"]["drzitele"], [])
        self.assertEqual(len(self.exp(drzitele=[dict(h, souhlas="ano")])["holice-112"]["drzitele"]), 1)

    def test_neverejna_stavba_se_vynecha(self):
        self.assertEqual(self.exp(verejne=False), {})

    def test_udalosti_a_drzitele_podle_roku(self):
        s = self.exp(udalosti=[dict(rok="1890", text="b", st="fam"), dict(rok="před 1800", text="a", st="fam")],
                     drzitele=[dict(od="1850", n="B", st="fam"), dict(od="1700", n="A", st="fam")])["holice-112"]
        self.assertEqual([u["text"] for u in s["udalosti"]], ["a", "b"])
        self.assertEqual([h["name"] for h in s["drzitele"]], ["A", "B"])


STAVBY_PY = '''
D = {
    "holice-112": dict(
        nazev="Kovárna Novákových", typ="kovarna", dum="holice-112", st="prob", verejne=True,
        popis="Rodinná kovárna.",
        udalosti=[dict(rok="1890", text="Narození Jana Nováka.", st="doc", r=["ukazka_krest_jan_novak_1890"])],
        drzitele=[dict(od="1884", do="1921", n="Václav Novák", os=16, jak="koupě?", st="prob", note="kovář")],
        obyvatele=[dict(os=8, role="kovář", st="doc", r=["ukazka_krest_jan_novak_1890"])],
        otevrene=["Kdo kovárnu držel před 1884?"],
    ),
}
'''


class Integrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.projekt = Path(cls._tmp.name) / "ukazka"
        r = novy_projekt(cls.projekt, "--ukazka")
        assert r.returncode == 0, r.stdout + r.stderr

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def stavby_json(self):
        return json.loads((self.projekt / "web" / "src" / "data" / "stavby.json").read_text(encoding="utf-8"))["stavby"]

    def test_a_bez_stavby_je_export_prazdny(self):
        out = spust(self.projekt, "export_web.py").stdout
        self.assertEqual(self.stavby_json(), {})
        self.assertNotIn("stavby:", out)
        r = spust(self.projekt, "stavby.py", "kontrola")
        self.assertIn("žádná stavba", r.stdout)

    def test_b_se_stavbou_ji_export_web_propoji_s_osobami(self):
        (self.projekt / "data" / "stavby.py").write_text(STAVBY_PY, encoding="utf-8", newline="\n")
        out = spust(self.projekt, "export_web.py").stdout
        self.assertIn("stavby: 1 staveb", out)
        s = self.stavby_json()["holice-112"]
        site = json.loads((self.projekt / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        slugy = {p["k"]: p["slug"] for p in site["people"].values() if not p.get("extra")}
        self.assertEqual(s["obyvatele"][0]["slug"], slugy[8])
        self.assertEqual(s["drzitele"][0]["slug"], slugy[16])
        self.assertTrue(s["obyvatele"][0]["zapisy"])
        self.assertEqual(spust(self.projekt, "stavby.py", "kontrola").returncode, 0)
        kand = spust(self.projekt, "stavby.py", "kandidati").stdout
        self.assertNotIn("Holice čp. 112", kand)   # už je ve stavby.py

    def test_c_chyba_v_datech_da_nenulovy_kod(self):
        (self.projekt / "data" / "stavby.py").write_text(
            STAVBY_PY.replace('os=8,', 'os=777,'), encoding="utf-8", newline="\n")
        r = spust(self.projekt, "stavby.py", "kontrola", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("777", r.stdout)


if __name__ == "__main__":
    unittest.main()
