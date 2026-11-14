"""Export webu a vynucování formy (ADR 0002, 0003): deník se čte z data/denik.jsonl, veřejné otázky z data/verejne_otazky.json,
fronty (data/ukoly_*.md) se na web nikdy nekopírují a zakázaný vzor v novém úložišti zastaví sestavení. Dokud nové úložiště
neexistuje, platí dosavadní soubory (zpětná kompatibilita). Rozhraní: soubory v web/src/generated a návratový kód export_web.py
nad dočasným projektem z ukázky (vymyšlená data), bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

UNIK = "ZNACKA-UNIKU-4711"


class ExportFormy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls.tmp.name) / "projekt"
        r = novy_projekt(cls.p, "--ukazka")
        assert r.returncode == 0, r.stdout + r.stderr
        spust(cls.p, "export_web.py")
        site = json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        cls.rod_k = sorted(l["k"] for l in site["lines"].values())[0]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        d = self.p / "data"
        self.zaloha = {f: (d / f).read_bytes() if (d / f).exists() else None
                       for f in ("denik.jsonl", "verejne_otazky.json", "ukoly_na_noc.md", "ukoly_na_rodinu.md",
                                 "ukoly_dotazy_na_archivy.md", "archivni_dotazy.md", "otazky_pro_rodinu.md")}

    def tearDown(self):
        d = self.p / "data"
        for f, obsah in self.zaloha.items():
            if obsah is None:
                (d / f).unlink(missing_ok=True)
            else:
                (d / f).write_bytes(obsah)

    def gen(self, jmeno):
        cesta = self.p / "web" / "src" / "generated" / jmeno
        return cesta.read_text(encoding="utf-8") if cesta.exists() else ""

    def export(self, check=True):
        return spust(self.p, "export_web.py", check=check)

    def denik(self, *args):
        return spust(self.p, "denik.py", *args)

    def otazky(self, *args):
        return spust(self.p, "otazky.py", *args)

    # ---- deník
    def test_dosavadni_denik_funguje_a_vyzve_k_migraci(self):
        (self.p / "data" / "denik.jsonl").unlink(missing_ok=True)
        r = self.export()
        self.assertTrue(self.gen("denik.md").strip())
        self.assertIn("denik.py migruj", r.stdout + r.stderr)

    def test_denik_z_jsonl_je_tabulka_z_denik_py(self):
        self.denik("pridej", "--datum", "2026-10-30", "--zdroj-typ", "archiv", "--zdroj", "ARON, Dolní Lhota, sign. 1234",
                   "--rozsah", "sn. 1–5", "--hledano", "křest Jana Nováka", "--vysledek", "nalezeno", "--nalez", "Křest 1852, čp. 12.")
        self.export()
        md = self.gen("denik.md")
        self.assertIn("| # | datum | zdroj | rozsah | hledáno | výsledek | nález | citace | odkaz |", md)
        self.assertIn("Křest 1852, čp. 12.", md)
        self.assertEqual(md.strip(), self.denik("vykresli").stdout.strip())

    def test_zakazany_vzor_v_novem_denikum_zastavi_sestaveni(self):
        self.denik("pridej", "--datum", "2026-10-30", "--zdroj-typ", "archiv", "--zdroj", "ARON", "--rozsah", "sn. 1",
                   "--hledano", "křest", "--vysledek", "nenalezeno")
        with open(self.p / "data" / "denik.jsonl", "a", encoding="utf-8") as f:   # ručně přidaný záznam obchází denik.py
            f.write(json.dumps({"id": 2, "datum": "2026-10-31", "zdroj": {"typ": "archiv", "text": "ARON"}, "rozsah": "sn. 2",
                                "hledano": "křest", "vysledek": "nenalezeno", "poznamka": "Čte pomocník (U-0013)."}) + "\n")
        r = self.export(check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CHYBA", r.stdout + r.stderr)
        self.assertIn("denik.jsonl", r.stdout + r.stderr)

    # ---- fronty a veřejné otázky
    def test_fronty_ukoly_se_na_web_nikdy_nedostanou(self):
        d = self.p / "data"
        text = f"# Fronta\n\n## U-0013 | P2 | os:3 | typ:sňatek | stav:otevřeno\n{UNIK} vnitřní postup.\n"
        for f in ("ukoly_na_noc.md", "ukoly_na_rodinu.md", "ukoly_dotazy_na_archivy.md"):
            (d / f).write_text(text, encoding="utf-8")
        self.otazky("pridej", "--druh", "rodina", "--rod", str(self.rod_k), "--otazka", "Je doma oddací list?", "--proc", "Pomohl by.")
        self.otazky("potvrd", "1", "--kdo", "správce webu")
        self.export()
        for jmeno in ("otazky.md", "dotazy.md", "denik.md", "zajimavosti.md"):
            self.assertNotIn(UNIK, self.gen(jmeno), jmeno)
        self.assertNotIn(UNIK, (self.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        self.assertNotIn("U-0013", self.gen("otazky.md") + self.gen("dotazy.md"))

    def test_otazky_z_json_jen_potvrzene_a_stary_soubor_se_ignoruje(self):
        d = self.p / "data"
        (d / "otazky_pro_rodinu.md").write_text("# Otázky\n\n## Dokumenty doma\n- STARA-OTAZKA-9\n", encoding="utf-8")
        self.otazky("pridej", "--druh", "rodina", "--rod", str(self.rod_k), "--otazka", "Potvrzená otázka k rodu?", "--proc", "Zajímá nás.")
        self.otazky("pridej", "--druh", "rodina", "--rod", str(self.rod_k), "--otazka", "Nepotvrzená otázka?", "--proc", "Zatím ne.")
        self.otazky("potvrd", "1", "--kdo", "správce webu")
        self.export()
        md = self.gen("otazky.md")
        self.assertIn("Potvrzená otázka k rodu?", md)
        self.assertNotIn("Nepotvrzená", md)
        self.assertNotIn("STARA-OTAZKA-9", md)                      # s novým souborem se starý nečte

    def test_prameny_z_json(self):
        self.otazky("pridej", "--druh", "pramen", "--rod", str(self.rod_k), "--archiv", "SOA Zámrsk", "--osoba", "Jan Novák",
                    "--co-hledat", "křest 1872, kniha narozených není naskenovaná.")
        self.otazky("potvrd", "1", "--kdo", "správce webu")
        self.export()
        md = self.gen("dotazy.md")
        self.assertIn("SOA Zámrsk", md)
        self.assertIn("křest 1872, kniha narozených není naskenovaná.", md)

    def test_bez_noveho_souboru_plati_dosavadni_otazky(self):
        (self.p / "data" / "verejne_otazky.json").unlink(missing_ok=True)
        (self.p / "data" / "otazky_pro_rodinu.md").write_text("# Otázky\n\n## Dokumenty doma\n- STARA-OTAZKA-9\n", encoding="utf-8")
        self.export()
        self.assertIn("STARA-OTAZKA-9", self.gen("otazky.md"))      # zpětná kompatibilita do migrace


if __name__ == "__main__":
    unittest.main()
