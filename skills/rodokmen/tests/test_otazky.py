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
        for f in ("otazky.py", "zaznamy_store.py", "soubory.py", "fronta.py", "zapis.py"):
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

    # ---- propojení s frontou
    def test_z_ukolu_vytvori_koncept_s_odkazem_a_nic_nezmeni_ve_fronte(self):
        fronta = self.p / "data" / "ukoly_na_noc.md"
        text = "# Úkoly na noc\n\n## U-0013 | P2 | os:3 | typ:sňatek | stav:otevřeno\nZjistit u rodiny, kde se Anna vdávala.\n"
        fronta.write_text(text, encoding="utf-8")
        r = self.otazky("z-ukolu", "U-0013", "--druh", "rodina", "--rod", "9")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = self.data()[0]
        self.assertEqual(z["z_ukolu"], "U-0013")
        self.assertNotIn("potvrzeno", z)
        self.assertEqual(fronta.read_text(encoding="utf-8"), text)               # fronta se nemění
        md = self.otazky("vykresli", "--druh", "rodina", "--nazvy-rodu", NAZVY).stdout
        self.assertNotIn("U-0013", md)
        self.assertNotEqual(self.otazky("z-ukolu", "U-9999", "--druh", "rodina").returncode, 0)   # neexistující úkol


if __name__ == "__main__":
    unittest.main()
