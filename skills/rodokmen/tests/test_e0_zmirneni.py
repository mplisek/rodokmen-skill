"""E0 (analyza/navrh-optimalizace.md, oddíl 9): okamžité zmírnění škod z běhu 14.–15. 11. 2026. Slučování úkolů jen ve stejné frontě a se
shodným cílem (ne podle překryvu osob), deník přijme jen osoby z data/osoby.py, snímek bez zadaného výstupu nejde do aktuální složky,
stav rozpočtu se necommituje, hook pluginu volá nejdřív `python`. Bez sítě, dočasná složka dat."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import SKILL, TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


class Fronta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = fronta.main(list(a))
        self.out = out.getvalue()
        return kod

    def ids(self, f):
        return [u.id for u in fronta.nacti(f)[1]]

    def test_prekryv_osob_neslucuje(self):
        self.run_("pridej", "noc", "--text", "křest osoby 44", "--os", "44,45", "--typ", "krest")
        self.run_("pridej", "noc", "--text", "křest osoby 89", "--os", "44,89", "--typ", "krest")
        self.assertEqual(self.ids("noc"), ["U-0001", "U-0002"])

    def test_jina_fronta_neslucuje_ani_pri_stejnych_osobach(self):
        self.run_("pridej", "dotazy", "--text", "dotaz do archivu", "--os", "44", "--typ", "krest")
        self.run_("pridej", "noc", "--text", "čtení rejstříku", "--os", "44", "--typ", "krest")
        self.assertEqual(self.ids("dotazy"), ["U-0001"])
        self.assertEqual(self.ids("noc"), ["U-0002"])
        self.assertNotIn("čtení rejstříku", fronta.nacti("dotazy")[1][0].text)

    def test_stejny_cil_ve_stejne_fronte_se_doplni(self):
        self.run_("pridej", "noc", "--text", "první", "--os", "44", "--cil", "krest-44")
        self.run_("pridej", "noc", "--text", "druhý", "--os", "45", "--cil", "krest-44")
        self.assertEqual(self.ids("noc"), ["U-0001"])
        self.assertIn("doplněno", self.out)

    def test_stejny_typ_a_stejne_osoby_bez_cile_se_doplni(self):
        self.run_("pridej", "noc", "--text", "první", "--os", "44,45", "--typ", "krest")
        self.run_("pridej", "noc", "--text", "druhý", "--os", "45,44", "--typ", "krest")
        self.assertEqual(self.ids("noc"), ["U-0001"])

    def test_volba_nove_slouceni_zakaze(self):
        self.run_("pridej", "noc", "--text", "první", "--os", "44", "--cil", "krest-44")
        self.run_("pridej", "noc", "--text", "druhý", "--os", "44", "--cil", "krest-44", "--nove")
        self.assertEqual(self.ids("noc"), ["U-0001", "U-0002"])

    def test_casti_rozdeleneho_ukolu_nejsou_duplicity(self):
        self.run_("pridej", "noc", "--text", "velký úkol", "--os", "44,45", "--typ", "krest")
        self.run_("rozdel", "U-0001", "--cast", "noc", "kniha 1", "řádek deníku", "os=44,45", "--cast", "noc", "kniha 2", "řádek deníku", "os=44,45")
        self.assertEqual(len(self.ids("noc")), 2)
        self.run_("kontrola")
        self.assertNotIn("překrývají", self.out)

    def test_smeruj_slucuje_jen_v_cilove_fronte(self):
        self.run_("pridej", "dotazy", "--text", "dotaz", "--os", "44", "--typ", "krest")
        (self.data / "ukoly_vstup.md").write_text("# Vstup\n", encoding="utf-8")
        self.run_("pridej", "vstup", "--text", "čtení", "--os", "44", "--typ", "krest")
        self.run_("smeruj", "U-0002", "--do", "noc", "--dod", "řádek deníku", "--cena", "S")
        self.assertEqual(self.ids("noc"), ["U-0002"])
        self.assertEqual(self.ids("dotazy"), ["U-0001"])


class Denik(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "tools").mkdir()
        for n in ("denik.py", "zaznamy_store.py"):
            (self.root / "tools" / n).write_bytes((TOOLS / n).read_bytes())
        (self.root / "data" / "osoby.py").write_text(
            'P = {1: dict(n="A"), 160: dict(n="B")}\nRODINA = {"anna-vzorna": dict(n="C", sex="F")}\nSAME = {350: 160}\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def pridej(self, osoby):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.root / "tools" / "denik.py"), "pridej", "--datum", "2026-11-15",
                               "--zdroj-typ", "archiv", "--zdroj", "kniha N 1800",
                               "--hledano", "křest osoby", "--vysledek", "nenalezeno", "--rozsah", "snímky 1–5", "--osoby", osoby],
                              capture_output=True, text=True, encoding="utf-8")

    def test_zname_osoby_projdou(self):
        r = self.pridej("160,anna-vzorna,350")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = json.loads((self.root / "data" / "denik.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(z["osoby"], ["160", "anna-vzorna", "350"])

    def test_jmeno_misto_klice_se_odmitne(self):
        r = self.pridej("Josef Vzorný ml. (160)")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("osoby", r.stdout + r.stderr)
        self.assertIn("160", r.stdout + r.stderr)                      # napoví, že klíč je číslo nebo zkratka
        self.assertFalse((self.root / "data" / "denik.jsonl").exists())

    def test_neznama_osoba_se_odmitne(self):
        r = self.pridej("160,999")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("999", r.stdout + r.stderr)

    def test_bez_osoby_py_se_osoby_nekontroluji(self):
        (self.root / "data" / "osoby.py").unlink()
        self.assertEqual(self.pridej("160").returncode, 0)


class Snimek(unittest.TestCase):
    def test_vychozi_vystup_neni_aktualni_slozka(self):
        import aron_img
        with tempfile.TemporaryDirectory() as t:
            stare = os.getcwd()
            os.chdir(t)
            try:
                p = Path(aron_img.vychozi_vystup("fb341fdc-aaaa", 206))
            finally:
                os.chdir(stare)
        self.assertEqual(p.name, "fb341fdc_0206.jpg")
        self.assertEqual(p.parent.name, "snimky")
        self.assertEqual(p.parent.parent.name, "pracovni")
        self.assertTrue(p.is_absolute())


class Ostatni(unittest.TestCase):
    def test_stav_rozpoctu_se_necommituje(self):
        self.assertIn("data/.rozpocet.json", (SKILL / "template" / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_hook_vola_nejdriv_python(self):
        h = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        for udalost in h["hooks"].values():
            for x in udalost:
                for hk in x["hooks"]:
                    c = hk["command"]
                    self.assertLess(c.index("python -I"), c.index("python3 -I"), c)

    def test_browser_reader_ma_vycet_nastroju(self):
        t = (REPO / "agents" / "browser-reader.md").read_text(encoding="utf-8")
        hlava = t.split("---")[1]
        self.assertRegex(hlava, r"(?m)^tools: Read, Glob, Grep, Bash, Write$")
        self.assertNotIn("disallowedTools", hlava)

    def test_orchestrator_drzi_jeden_model(self):
        t = (REPO / "agents" / "orchestrator.md").read_text(encoding="utf-8")
        self.assertRegex(t, r"(?i)one model for the whole session")
        self.assertIn("/model", t)


if __name__ == "__main__":
    unittest.main()
