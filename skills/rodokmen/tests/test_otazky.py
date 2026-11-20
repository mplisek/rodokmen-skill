"""otazky.py: veřejné otázky (data/verejne_otazky.json) odděleně od vnitřní fronty. Na web jde jen ručně potvrzený záznam;
vznik z úkolu je jediné propojení a zůstane jen odkaz z_ukolu v datech. Rozhraní: příkazy otazky.py a jejich výstup
(Markdown ve tvaru, který čte export webu). Dočasný projekt s vymyšlenými daty, bez sítě."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

NAZVY = json.dumps({"8": "Novákové", "9": "Králové"}, ensure_ascii=False)


class OtazkyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        (self.p / "tools").mkdir()
        (self.p / "data").mkdir()
        for f in ("otazky.py", "zaznamy_store.py", "soubory.py", "zapis.py"):
            if (TOOLS / f).exists():
                shutil.copy(TOOLS / f, self.p / "tools" / f)
        self.soubor = self.p / "data" / "verejne_otazky.json"

    def tearDown(self):
        self._tmp.cleanup()

    def otazky(self, *args):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "otazky.py"), *args],
                              cwd=self.p, capture_output=True, text=True, encoding="utf-8")

    def data(self):
        return json.loads(self.soubor.read_text(encoding="utf-8"))["otazky"]

    def rodina(self, *navic):
        return self.otazky("pridej", "--druh", "rodina", "--rod", "8", "--otazka", "Kde se narodil Jan Novák (* 1850)?",
                           "--proc", "V Holicích jsme jeho křest nenašli.", "--pomuze", "Pomůže rodný nebo oddací list.", *navic)

    def pramen(self, *navic):
        return self.otazky("pridej", "--druh", "pramen", "--rod", "9", "--archiv", "SOA Zámrsk", "--osoba", "Anna Králová",
                           "--co-hledat", "sňatek asi 1895 v Holicích; oddací knihy po 1890 nejsou online.", *navic)

    # ---- zápis
    def test_pridej_je_nepotvrzene_a_nejde_na_web(self):
        self.assertEqual(self.rodina().returncode, 0)
        z = self.data()
        self.assertEqual(len(z), 1)
        self.assertEqual(z[0]["id"], 1)
        self.assertNotIn("potvrzeno", z[0])
        md = self.otazky("vykresli", "--druh", "rodina", "--nazvy-rodu", NAZVY).stdout
        self.assertNotIn("Kde se narodil", md)

    def test_potvrd_pusti_na_web_v_tvaru_pro_export(self):
        self.assertEqual(self.rodina().returncode, 0)
        self.assertEqual(self.otazky("pridej", "--druh", "rodina", "--oddil", "Dokumenty doma", "--otazka",
                                     "Je doma oddací list?", "--proc", "Pomohl by s rodem.").returncode, 0)
        for i in ("1", "2"):
            self.assertEqual(self.otazky("potvrd", i, "--kdo", "správce webu", "--datum", "2026-11-14").returncode, 0)
        md = self.otazky("vykresli", "--druh", "rodina", "--nazvy-rodu", NAZVY).stdout
        self.assertIn("## Dokumenty doma", md)
        self.assertIn("## Novákové", md)
        self.assertIn("- Kde se narodil Jan Novák (* 1850)? V Holicích jsme jeho křest nenašli. Pomůže rodný nebo oddací list. <!-- rody: 8 -->", md)
        self.assertNotIn("správce webu", md)                  # kdo potvrdil je jen v datech
        self.assertNotIn("z_ukolu", md)

    def test_pramen_se_radi_po_archivech(self):
        self.assertEqual(self.pramen().returncode, 0)
        self.assertEqual(self.otazky("potvrd", "1", "--kdo", "správce webu").returncode, 0)
        md = self.otazky("vykresli", "--druh", "pramen", "--nazvy-rodu", NAZVY).stdout
        self.assertIn("## SOA Zámrsk", md)
        self.assertIn("- **Králové – Anna Králová:** sňatek asi 1895 v Holicích; oddací knihy po 1890 nejsou online. <!-- rody: 9 -->", md)

    def test_odmitne_chyby_a_zakazane_vzory_bez_zmeny_souboru(self):
        self.assertEqual(self.rodina().returncode, 0)
        pred = self.soubor.read_bytes()
        for args, stopa in (
            (("--druh", "rodina", "--otazka", "Otázka (U-0013)?", "--proc", "x"), "U-0013"),
            (("--druh", "rodina", "--otazka", "Otázka?", "--proc", "Čte pomocník."), "pomocník"),
            (("--druh", "rodina", "--proc", "chybí otázka"), "otazka"),
            (("--druh", "pramen", "--archiv", "SOA", "--co-hledat", "viz pracovni/x.jpg"), "pracovni/"),
            (("--druh", "pramen", "--co-hledat", "chybí archiv"), "archiv"),
            (("--druh", "jiny", "--otazka", "x", "--proc", "y"), "druh"),
        ):
            with self.subTest(args=args):
                r = self.otazky("pridej", *args)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(stopa.lower(), (r.stdout + r.stderr).lower())
                self.assertEqual(self.soubor.read_bytes(), pred)

    def test_potvrzeni_vyzaduje_cisty_text(self):
        # záznam vzniklý z úkolu může nést vnitřní text; potvrdit ho jde až po úpravě
        self.soubor.write_text(json.dumps({"otazky": [{"id": 1, "druh": "rodina", "otazka": "Zjistit (U-0013).", "proc": "x"}]}),
                               encoding="utf-8")
        r = self.otazky("potvrd", "1", "--kdo", "správce webu")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("potvrzeno", self.data()[0])
        self.assertEqual(self.otazky("uprav", "1", "--otazka", "Zjistit u rodiny.").returncode, 0)
        self.assertEqual(self.otazky("potvrd", "1", "--kdo", "správce webu").returncode, 0)

    def test_uprav_smaz_a_over(self):
        self.assertEqual(self.rodina().returncode, 0)
        self.assertEqual(self.rodina().returncode, 0)
        self.assertEqual([z["id"] for z in self.data()], [1, 2])
        self.assertEqual(self.otazky("smaz", "1").returncode, 0)
        self.assertEqual([z["id"] for z in self.data()], [2])
        self.assertEqual(self.otazky("over").returncode, 0)
        self.soubor.write_text(json.dumps({"otazky": [{"id": 1, "druh": "rodina"}, {"id": 1, "druh": "pramen"}]}), encoding="utf-8")
        self.assertNotEqual(self.otazky("over").returncode, 0)


class CoHledame(OtazkyTest):
    """Rozhodnutí uživatele 16. 11. 2026 (analyza/ukoly_na_skill.md, H2): rod jménem i číslem, převod odrážek otázek pro rodinu a dotazů na
    archivy na nepotvrzené koncepty, potvrzování po rodech, všechny dotazy na archivy včetně čekajících na souhlas s odesláním."""
    RODINA = ("# Otázky pro rodinu\n\nÚvod pro rodinu.\n\n## Dokumenty doma\n- Je doma oddací list prababičky?\n\n"
              "## Novákové\n- Kde se narodil Jan Novák (* 1850)?\n- Kdo byl kmotrem\n  jeho syna?\n\n"
              "## Králové z Lhoty\n- Odkud přišla Anna Králová?\n\n"
              "## U-0040 | P2 | os:3 | typ:rodina | stav:otevřeno\nInterní: zeptat se tety, snímek 45.\n")
    ARCHIVY = ("# Dotazy na archivy\n\n## SOA Zámrsk\n- **Novákové – Jan Novák:** sňatek 1875, kniha není online.\n"
               "- Pozemková kniha obce Lhota.\n\n## Matriční úřad Holice\n- **Králové – Anna Králová:** úmrtí 1950.\n\n"
               "## U-0022 | P1 | os:9 | typ:archiv | stav:otevřeno\nŽádost jen po souhlasu, snímky 12–14.\n")

    def setUp(self):
        super().setUp()
        (self.p / "data" / "osoby.py").write_text('LINES = {8: ("Novákové", "a"), 9: ("Králové z Lhoty", "b")}\n', encoding="utf-8")

    def test_rod_jmenem_i_cislem(self):
        for rod in ("8", "novakove", "Novákové"):
            self.otazky("pridej", "--druh", "rodina", "--rod", rod, "--otazka", f"Otázka {rod}?")
        self.assertEqual([z["rod"] for z in self.data()], [8, 8, 8])                # v datech číslo rodu (přístupy ho přečíslují)
        self.assertEqual(self.otazky("pridej", "--druh", "rodina", "--rod", "kralove-z-lhoty", "--otazka", "X?").returncode, 0)
        self.assertEqual(self.data()[-1]["rod"], 9)
        r = self.otazky("pridej", "--druh", "rodina", "--rod", "neznami", "--otazka", "Y?")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rod", (r.stdout + r.stderr).lower())

    def test_proc_u_otazky_pro_rodinu_neni_povinne(self):
        self.assertEqual(self.otazky("pridej", "--druh", "rodina", "--otazka", "Je doma rodný list?").returncode, 0)
        self.assertEqual(self.otazky("potvrd", "1", "--kdo", "uživatel").returncode, 0)

    def test_ze_souboru_prevede_jen_odrazky_a_je_idempotentni(self):
        (self.p / "data" / "otazky_pro_rodinu.md").write_text(self.RODINA, encoding="utf-8")
        (self.p / "data" / "archivni_dotazy.md").write_text(self.ARCHIVY, encoding="utf-8")
        pred = ((self.p / "data" / "otazky_pro_rodinu.md").read_bytes(), (self.p / "data" / "archivni_dotazy.md").read_bytes())
        for s in ("rodina", "archivy"):
            r = self.otazky("ze-souboru", "--soubor", s)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = self.data()
        rod = [(x["druh"], x.get("rod"), x.get("oddil"), x.get("otazka") or x.get("co_hledat")) for x in z]
        self.assertIn(("rodina", None, "Dokumenty doma", "Je doma oddací list prababičky?"), rod)
        self.assertIn(("rodina", 8, None, "Kdo byl kmotrem jeho syna?"), rod)
        self.assertIn(("rodina", 9, None, "Odkud přišla Anna Králová?"), rod)
        pramen = next(x for x in z if x.get("osoba") == "Jan Novák")
        self.assertEqual((pramen["archiv"], pramen["rod"], pramen["co_hledat"]), ("SOA Zámrsk", 8, "sňatek 1875, kniha není online."))
        self.assertIn(("pramen", None, None, "Pozemková kniha obce Lhota."), rod)
        self.assertFalse(any("U-00" in json.dumps(x, ensure_ascii=False) or "snímk" in json.dumps(x, ensure_ascii=False) for x in z))  # karty úkolů ze starší fronty ne
        self.assertTrue(all("potvrzeno" not in x and x.get("ze_souboru") for x in z))
        pocet = len(z)
        self.otazky("ze-souboru", "--soubor", "rodina")
        self.assertEqual(len(self.data()), pocet)                                   # podruhé nic nového
        self.assertEqual(((self.p / "data" / "otazky_pro_rodinu.md").read_bytes(),
                          (self.p / "data" / "archivni_dotazy.md").read_bytes()), pred)   # zdrojové soubory se nemění

    def test_ze_souboru_stejny_text_v_jinem_archivu_neni_duplicita(self):
        """Poznámka z bádání 18. 11. 2026: sčítací operáty pro dvě obce ve dvou archivech mají stejné „co hledat“."""
        (self.p / "data" / "archivni_dotazy.md").write_text(
            "# Prameny\n\n## SOkA Chrudim\n\n- Sčítací operáty 1869–1921 – na internetu nejsou.\n\n"
            "## SOkA Havlíčkův Brod\n\n- Sčítací operáty 1869–1921 – na internetu nejsou.\n", encoding="utf-8")
        self.assertEqual(self.otazky("ze-souboru", "--soubor", "archivy").returncode, 0)
        self.assertEqual(sorted(x["archiv"] for x in self.data()), ["SOkA Chrudim", "SOkA Havlíčkův Brod"])
        self.otazky("ze-souboru", "--soubor", "archivy")
        self.assertEqual(len(self.data()), 2)                                        # podruhé nic nového

    def test_potvrd_po_rodech_vse_nebo_nic(self):
        self.otazky("pridej", "--druh", "rodina", "--rod", "8", "--otazka", "A?")
        self.otazky("pridej", "--druh", "pramen", "--rod", "novakove", "--archiv", "SOA", "--co-hledat", "B")
        self.otazky("pridej", "--druh", "rodina", "--rod", "9", "--otazka", "C?")
        self.otazky("pridej", "--druh", "rodina", "--oddil", "Obecně", "--otazka", "D?")
        r = self.otazky("potvrd", "--rod", "novakove", "--kdo", "uživatel")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(["potvrzeno" in z for z in self.data()], [True, True, False, False])
        self.assertEqual(self.otazky("potvrd", "--obecne", "--kdo", "uživatel").returncode, 0)
        self.assertEqual(["potvrzeno" in z for z in self.data()], [True, True, False, True])
        d = json.loads(self.soubor.read_text(encoding="utf-8"))                      # koncept s vnitřním textem (např. z úkolu)
        d["otazky"].append({"id": 9, "druh": "rodina", "rod": 9, "otazka": "Špatně (U-0013)?"})
        self.soubor.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        r = self.otazky("potvrd", "--rod", "9", "--kdo", "uživatel")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(["potvrzeno" in z for z in self.data()][2], False)            # ani dobrý záznam rodu 9 se nepotvrdil
        self.assertNotEqual(self.otazky("potvrd", "--rod", "9").returncode, 0)          # bez --kdo ne

    def test_ceka_na_souhlas_jde_na_web_s_priznakem(self):
        self.otazky("pridej", "--druh", "pramen", "--archiv", "SOA", "--co-hledat", "B", "--ceka-na-souhlas", "ano")
        self.assertTrue(self.data()[0]["ceka_na_souhlas"])
        self.otazky("potvrd", "1", "--kdo", "uživatel")
        md = self.otazky("vykresli", "--druh", "pramen").stdout
        self.assertIn("<!-- ceka -->", md)
        self.otazky("uprav", "1", "--ceka-na-souhlas", "ne")
        self.assertNotIn("ceka_na_souhlas", self.data()[0])


if __name__ == "__main__":
    unittest.main()
