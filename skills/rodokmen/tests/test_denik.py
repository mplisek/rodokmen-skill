"""denik.py: strukturovaný deník (data/denik.jsonl, jen přidávání) s pevnou formou, kontrolou zakázaných vzorů a generovanou
tabulkou. Rozhraní: příkazy denik.py (argumenty a stdin -> soubor dat a vykreslená tabulka), jak je vidí uživatel.
Dočasný projekt s vymyšlenými daty, bez sítě."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402


class DenikTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        (self.p / "tools").mkdir()
        (self.p / "data").mkdir()
        for f in ("denik.py", "zaznamy_store.py", "soubory.py"):
            shutil.copy(TOOLS / f, self.p / "tools" / f)
        self.log = self.p / "data" / "denik.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def denik(self, *args, stdin=None):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "denik.py"), *args],
                              cwd=self.p, capture_output=True, text=True, encoding="utf-8", input=stdin)

    def zaznamy(self):
        return [json.loads(r) for r in self.log.read_text(encoding="utf-8").splitlines() if r.strip()]

    ZAKLAD = ["pridej", "--datum", "2026-10-30", "--zdroj-typ", "archiv", "--zdroj", "ARON, Dolní Lhota, narození 1850–1860, sign. 1234, sn. 31",
              "--rozsah", "sn. 20–35", "--hledano", "křest Jana Nováka * 1852", "--vysledek", "nalezeno",
              "--nalez", "Křest 14. 3. 1852, otec Josef Novák, čp. 12."]

    def pridej(self, *navic):
        return self.denik(*self.ZAKLAD, *navic)

    # ---- zápis
    def test_pridej_zalozi_soubor_a_cisluje(self):
        self.assertEqual(self.pridej().returncode, 0)
        self.assertEqual(self.pridej("--osoby", "jan_novak").returncode, 0)
        z = self.zaznamy()
        self.assertEqual([x["id"] for x in z], [1, 2])
        self.assertEqual(z[0]["zdroj"], {"typ": "archiv", "text": self.ZAKLAD[self.ZAKLAD.index("--zdroj") + 1]})
        self.assertEqual(z[1]["osoby"], ["jan_novak"])
        self.assertTrue(self.log.read_text(encoding="utf-8").endswith("\n"))

    def odmitne(self, *args, kod=None, fragment=None):
        pred = self.log.read_bytes() if self.log.exists() else None
        r = self.denik(*args)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        po = self.log.read_bytes() if self.log.exists() else None
        self.assertEqual(pred, po, "chybný zápis nesmí nic změnit")
        if fragment:
            self.assertIn(fragment.lower(), (r.stdout + r.stderr).lower())

    def test_odmitne_chybna_pole_a_nic_nezmeni(self):
        self.assertEqual(self.pridej().returncode, 0)
        z = self.ZAKLAD

        def jinak(pole, hodnota):
            a = list(z)
            a[a.index(pole) + 1] = hodnota
            return a

        self.odmitne(*jinak("--datum", "30. 10. 2026"), fragment="datum")
        self.odmitne(*jinak("--datum", "2026-13-45"), fragment="datum")
        self.odmitne(*jinak("--vysledek", "asi"), fragment="vysledek")
        self.odmitne(*jinak("--zdroj-typ", "pomocnik"), fragment="typ")
        self.odmitne(*jinak("--hledano", "x" * 161), fragment="160")
        self.odmitne(*jinak("--nalez", "y" * 401), fragment="400")
        a = jinak("--vysledek", "nenalezeno")
        a.remove("--nalez"), a.remove(z[z.index("--nalez") + 1])
        a.remove("--rozsah"), a.remove("sn. 20–35")
        self.odmitne(*a, fragment="rozsah")             # negativní výsledek bez rozsahu
        self.odmitne(*z, "--opravuje", "99", fragment="opravuje")

    def test_odmitne_zakazane_vzory(self):
        for pole, text, stopa in (
            ("--nalez", "Křest 1852 (U-0013, ověřeno).", "U-0013"),
            ("--poznamka", "Čteno pomocníkem, druhé čtení sonnet.", "pomocník"),
            ("--citace", "viz pracovni/aron/x.jpg", "pracovni/"),
            ("--poznamka", "Ověřeno na snímku, čtyři oči.", "čtyři oči"),
            ("--nalez", "Dříve chybně zapsáno 1853.", "dříve chybně"),
            ("--nalez", "Nalezeno : křest 1852.", "dvojteč"),
            ("--poznamka", "viz A -> B", "->"),
        ):
            with self.subTest(text=text):
                self.odmitne(*self.ZAKLAD, pole, text, fragment=stopa)

    # ---- oprava a vykreslení
    def test_oprava_je_novy_zaznam_a_puvodni_se_nezobrazi(self):
        self.assertEqual(self.pridej().returncode, 0)
        self.assertEqual(self.pridej("--opravuje", "1").returncode, 0)
        z = self.zaznamy()
        self.assertEqual(len(z), 2)
        self.assertEqual(z[1]["opravuje"], 1)
        md = self.denik("vykresli").stdout
        self.assertIn("| 2 |", md)
        self.assertNotIn("| 1 |", md)                   # opravený záznam se na webu nezobrazí, v souboru zůstává

    def test_vykresli_pevna_tabulka(self):
        self.assertEqual(self.pridej("--poznamka", "Dva sourozenci na téže straně.", "--overeno").returncode, 0)
        md = self.denik("vykresli").stdout.splitlines()
        self.assertEqual(md[0], "| # | datum | zdroj | rozsah | hledáno | výsledek | nález | citace | odkaz |")
        self.assertEqual(md[1], "|---|---|---|---|---|---|---|---|---|")
        radek = md[2]
        self.assertTrue(radek.startswith("| 1 | 2026-10-30 | ARON, Dolní Lhota"), radek)
        self.assertIn("nalezeno (ověřeno)", radek)
        self.assertIn("<details>", radek)               # poznámka rozbalitelně pod nálezem, tabulka zůstane jednořádková
        self.assertNotIn("\n", radek)
        self.assertEqual(len(md), 3)

    def test_vykresli_zapise_soubor(self):
        self.assertEqual(self.pridej().returncode, 0)
        r = self.denik("vykresli", "--do", "data/denik.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("| 1 |", (self.p / "data" / "denik.md").read_text(encoding="utf-8"))

    def test_znak_svisle_cary_v_bunce_se_ochrani(self):
        self.assertEqual(self.pridej("--citace", "orig: A | B").returncode, 0)
        radek = self.denik("vykresli").stdout.splitlines()[2]
        self.assertEqual(radek.count("|") - radek.count("\\|"), 10)    # 9 sloupců = 10 oddělovačů

    # ---- kontrola celého souboru
    def test_over_najde_rucne_rozbity_radek(self):
        self.assertEqual(self.pridej().returncode, 0)
        self.assertEqual(self.denik("over").returncode, 0)
        with open(self.log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": 2, "datum": "2026-10-31", "vysledek": "nejspíš"}) + "\n")   # ručně přidaný chybný záznam
        r = self.denik("over")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("2", r.stdout + r.stderr)

    def test_over_najde_duplicitni_id_a_rozbity_json(self):
        self.assertEqual(self.pridej().returncode, 0)
        radky = self.log.read_text(encoding="utf-8")
        self.log.write_text(radky + radky, encoding="utf-8")
        self.assertNotEqual(self.denik("over").returncode, 0)
        self.log.write_text(radky + "{nejde to\n", encoding="utf-8")
        self.assertNotEqual(self.denik("over").returncode, 0)

    def test_puvodni_a_proces_nejsou_kontrolovany_ani_vykreslovany(self):
        # pole puvodni (původní text) a proces (procesní údaje) jsou jen v datech: zakázané vzory v nich nevadí a nevykreslí se
        z = {"id": 1, "datum": "2026-10-30", "zdroj": {"typ": "archiv", "text": "ARON, sn. 1"}, "rozsah": "sn. 1",
             "hledano": "křest", "vysledek": "nenalezeno", "puvodni": "| 1 | … pomocník N3e … |", "proces": ["pomocník N3e"]}
        self.log.write_text(json.dumps(z, ensure_ascii=False) + "\n", encoding="utf-8")
        self.assertEqual(self.denik("over").returncode, 0)
        md = self.denik("vykresli").stdout
        self.assertNotIn("N3e", md)


if __name__ == "__main__":
    unittest.main()
