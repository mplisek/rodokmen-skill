"""scripts/pokryti.py (Fáze D, Q-D2, Q-D3, Q-D5): kontrola, že každý nástroj a každá trasa webu má test, že anglická vrstva je anglicky a že
pravidla mají platné otisky. Jen hlásí (text nebo JSON, kód 0 = pokryto, 1 = nepokryto). Rozhraní: příkazová řádka nad dočasným repozitářem
s vymyšleným obsahem a nad skutečným repozitářem (registr tras a výjimek). Bez sítě."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKRIPT = REPO / "scripts" / "pokryti.py"


class PokrytiDocasne(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.r = Path(self._tmp.name)
        s = self.r / "skills" / "rodokmen"
        for d in ("tools", "tests/e2e", "template/web/src/pages/osoba", "template/web/src/pages/pribehy"):
            (s / d).mkdir(parents=True)
        (s / "tools" / "graf.py").write_text("# nástroj\n", encoding="utf-8")
        (s / "tests" / "test_graf.py").write_text("import graf\n", encoding="utf-8")
        (s / "tests" / "test_vykresleni.py").write_text("# trasy\n", encoding="utf-8")
        for p in ("index.astro", "osoba/[slug].astro", "pribehy/index.astro", "pribehy/[slug].astro"):
            (s / "template/web/src/pages" / p).write_text("---\n---\n", encoding="utf-8")
        self.stranky([{"vzor": "/", "test": "test_vykresleni"}, {"vzor": "/osoba/*", "test": "test_vykresleni"},
                      {"vzor": "/pribehy/", "test": "test_vykresleni"}, {"vzor": "/pribehy/*", "test": "test_vykresleni"}])
        self.vyjimky({})

    def tearDown(self):
        self._tmp.cleanup()

    def stranky(self, data):
        (self.r / "skills/rodokmen/tests/e2e/stranky.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def vyjimky(self, data):
        (self.r / "skills/rodokmen/tests/e2e/vyjimky.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def spust(self, *args):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), "--repo", str(self.r), *args], capture_output=True,
                              text=True, encoding="utf-8")

    def zprava(self):
        r = self.spust("--json")
        return r.returncode, json.loads(r.stdout)

    def test_vse_pokryto(self):
        kod, d = self.zprava()
        self.assertEqual((kod, d["nepokryto"]), (0, []))

    def test_nastroj_bez_testu(self):
        (self.r / "skills/rodokmen/tools/novy.py").write_text("# nový\n", encoding="utf-8")
        kod, d = self.zprava()
        self.assertEqual(kod, 1)
        self.assertEqual(d["nastroje"], ["novy.py"])
        self.assertTrue(any("novy.py" in x for x in d["nepokryto"]))

    def test_nastroj_s_vyjimkou_s_duvodem(self):
        (self.r / "skills/rodokmen/tools/novy.py").write_text("# nový\n", encoding="utf-8")
        self.vyjimky({"novy.py": "ruční nástroj portálu, ověřuje ho smoke_test"})
        self.assertEqual(self.zprava()[0], 0)

    def test_vyjimka_bez_duvodu_nestaci(self):
        (self.r / "skills/rodokmen/tools/novy.py").write_text("# nový\n", encoding="utf-8")
        self.vyjimky({"novy.py": ""})
        self.assertEqual(self.zprava()[0], 1)

    def test_vyjimka_neexistujiciho_nastroje_je_chyba(self):
        self.vyjimky({"zmizel.py": "důvod"})
        kod, d = self.zprava()
        self.assertEqual(kod, 1)
        self.assertTrue(any("zmizel.py" in x for x in d["nepokryto"]))

    def test_trasa_bez_zaznamu(self):
        (self.r / "skills/rodokmen/template/web/src/pages/mapa.astro").write_text("---\n---\n", encoding="utf-8")
        kod, d = self.zprava()
        self.assertEqual(kod, 1)
        self.assertEqual(d["stranky"], ["/mapa"])

    def test_zaznam_s_neexistujicim_testem(self):
        self.stranky([{"vzor": "/", "test": "test_vykresleni"}, {"vzor": "/osoba/*", "test": "test_neni"},
                      {"vzor": "/pribehy/", "test": "test_vykresleni"}, {"vzor": "/pribehy/*", "test": "test_vykresleni"}])
        kod, d = self.zprava()
        self.assertEqual(kod, 1)
        self.assertTrue(any("test_neni" in x for x in d["nepokryto"]))

    def test_zaznam_neexistujici_trasy_je_chyba(self):
        self.stranky([{"vzor": "/", "test": "test_vykresleni"}, {"vzor": "/osoba/*", "test": "test_vykresleni"},
                      {"vzor": "/pribehy/", "test": "test_vykresleni"}, {"vzor": "/pribehy/*", "test": "test_vykresleni"},
                      {"vzor": "/zmizela", "test": "test_vykresleni"}])
        kod, d = self.zprava()
        self.assertEqual(kod, 1)
        self.assertTrue(any("/zmizela" in x for x in d["nepokryto"]))

    def test_citelny_vystup_a_nic_nezapisuje(self):
        (self.r / "skills/rodokmen/tools/novy.py").write_text("# nový\n", encoding="utf-8")
        pred = sorted(str(p) for p in self.r.rglob("*"))
        r = self.spust()
        self.assertEqual(r.returncode, 1)
        self.assertIn("novy.py", r.stdout)
        self.assertEqual(pred, sorted(str(p) for p in self.r.rglob("*")))

    def test_bez_vrstvy_agentu_se_jazyk_a_pravidla_preskoci(self):
        _, d = self.zprava()
        self.assertEqual((d["jazyk"], d["pravidla"]), ("preskoceno", "preskoceno"))


class PokrytiSkutecnyRepozitar(unittest.TestCase):
    """Nad skutečným repozitářem: registr tras a výjimek je úplný, takže brána pokrytí prochází."""

    def test_repozitar_je_pokryty(self):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), "--json"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["nepokryto"], [])
        self.assertEqual((d["jazyk"], d["pravidla"]), ("ok", "ok"))

    def test_vyjimky_maji_duvod(self):
        v = json.loads((REPO / "skills/rodokmen/tests/e2e/vyjimky.json").read_text(encoding="utf-8"))
        for nastroj, duvod in v.items():
            self.assertGreaterEqual(len(duvod), 10, nastroj)


if __name__ == "__main__":
    unittest.main()
