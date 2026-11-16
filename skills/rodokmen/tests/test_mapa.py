"""tools/mapa.py (analyza/navrh-router-uloh.md kap. 6.2, S-011): mapa knihy = co které snímky pokrývají (písmena, roky, čísla), aby se stahovalo jen
potřebné. Mapa je jen rada (nikdy neuzavře hledání), jedna na svazek, mimo úklid cache, bez jmen lidí. Bez sítě, dočasná složka map."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import mapa  # noqa: E402


def strana(sn, od, do, typ="rejstřík", **kw):
    return dict(portal="aron", svazek="03066862", snimek=sn, typ=typ, od=od, do=do, kvalita="dobrá", **kw)


class Zaklad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.koren = os.path.join(self.tmp.name, "rodokmen_mapy")
        self.stare = os.environ.get("RODOKMEN_MAPY")
        os.environ["RODOKMEN_MAPY"] = self.koren

    def tearDown(self):
        if self.stare is None:
            os.environ.pop("RODOKMEN_MAPY", None)
        else:
            os.environ["RODOKMEN_MAPY"] = self.stare
        self.tmp.cleanup()

    def zapis(self, *strany, kdo="sonnet"):
        for s in strany:
            mapa.zapis_stranu(s, kdo=kdo, nastroj="0.10.1")


class Klice(unittest.TestCase):
    def test_poradi_pismen_cesky(self):
        pismena = ["A", "B", "C", "Č", "D", "F", "H", "Ch", "I", "K", "Ř", "S", "Š", "Z", "Ž"]
        klice = [mapa.klic_pismeno(p) for p in pismena]
        self.assertEqual(klice, sorted(klice))
        self.assertLess(mapa.klic_pismeno("Hora"), mapa.klic_pismeno("Chalupa"))
        self.assertLess(mapa.klic_pismeno("Novák"), mapa.klic_pismeno("Novotný"))        # druhé písmeno upřesňuje
        self.assertEqual(mapa.klic_pismeno("čermák"), mapa.klic_pismeno("Čermák"))

    def test_cislo_a_rok(self):
        self.assertEqual(mapa.klic_cislo("1856"), 1856.0)
        self.assertEqual(mapa.klic_cislo("1856–1860"), 1856.0)
        self.assertIsNone(mapa.klic_cislo("bez čísla"))


class Zapis(Zaklad):
    def test_zapis_a_posledni_cteni_vyhrava(self):
        self.zapis(strana(43, "A", "C"))
        self.zapis(strana(43, "A", "D"))
        m = mapa.nacti("aron", "03066862")
        self.assertEqual(m[43]["do"], "D")
        radky = Path(self.koren, "aron", "03066862.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(radky), 2)                                      # jen přidávání, historie zůstává

    def test_spatna_strana_se_odmitne(self):
        for spatna in (strana(0, "A", "B"), strana(5, "A", "B", typ="nesmysl"), dict(strana(5, "A", "B"), kvalita="skvělá"),
                       dict(strana(5, "A", "B"), svazek="../x")):
            with self.assertRaises(ValueError, msg=spatna):
                mapa.zapis_stranu(spatna, kdo="x", nastroj="1")

    def test_mapa_je_mimo_slozku_cache(self):
        import cache
        self.assertFalse(os.path.abspath(mapa.koren()).startswith(os.path.abspath(cache.KOREN) + os.sep))

    def test_zapis_z_vysledku_agenta(self):
        v = Path(self.tmp.name, "vysledek.json")
        v.write_text(json.dumps({"model": "sonnet", "stranky": [strana(43, "A", "C"), strana(44, "D", "H")]}), encoding="utf-8")
        self.assertEqual(mapa.main(["zapis", str(v)]), 0)
        self.assertEqual(sorted(mapa.nacti("aron", "03066862")), [43, 44])

    def test_snimek_v_cache_je_jen_identita(self):
        mapa.snimek("aron", "03066862", 7, "cache")
        m = mapa.nacti("aron", "03066862")
        self.assertEqual(m[7].get("typ"), None)
        self.assertEqual(m[7]["zdroj"], "cache")


class Hledej(Zaklad):
    def test_pismeno_uvnitr_znameho_rozsahu(self):
        self.zapis(strana(20, "A", "C"), strana(35, "K", "M"))
        r = mapa.hledej("aron", "03066862", pismeno="B")
        self.assertEqual((r["stav"], r["snimek"]), ("zname", 20))

    def test_pismeno_mezi_dvema_body_se_interpoluje(self):
        self.zapis(strana(20, "A", "C"), strana(35, "K", "M"))
        r = mapa.hledej("aron", "03066862", pismeno="F")
        self.assertEqual(r["stav"], "odhad")
        self.assertTrue(20 < r["snimek"] < 35, r)
        self.assertEqual((r["zdola"], r["shora"]), (20, 35))
        self.assertIn("rada", r["poznamka"].lower())                          # jen rada, ne důkaz

    def test_rok_mezi_dvema_body(self):
        self.zapis(strana(10, "1800", "1810", typ="zápisy"), strana(50, "1850", "1860", typ="zápisy"))
        r = mapa.hledej("aron", "03066862", rok=1830)
        self.assertEqual(r["stav"], "odhad")
        self.assertTrue(25 <= r["snimek"] <= 35, r)

    def test_sousedni_snimky_bez_mezery(self):
        self.zapis(strana(20, "A", "C"), strana(21, "K", "M"))
        r = mapa.hledej("aron", "03066862", pismeno="F")
        self.assertEqual(r["stav"], "mezera")
        self.assertEqual(sorted(r["precti"]), [20, 21])                        # hledání se uzavře až čtením okolí

    def test_jedna_strana_zname_jen_zdola_nebo_shora(self):
        self.zapis(strana(20, "A", "C"))
        r = mapa.hledej("aron", "03066862", pismeno="Z", celkem=100)
        self.assertEqual((r["stav"], r["zdola"]), ("odhad", 20))
        self.assertTrue(20 < r["snimek"] <= 100)

    def test_prazdna_mapa(self):
        r = mapa.hledej("aron", "03066862", pismeno="F", celkem=100)
        self.assertEqual((r["stav"], r["snimek"]), ("nezname", 50))
        r = mapa.hledej("aron", "03066862", pismeno="F")
        self.assertEqual((r["stav"], r["snimek"]), ("nezname", 1))

    def test_cli_kod_1_kdyz_mapa_nic_nevi_a_0_kdyz_je_odhad(self):
        self.zapis(strana(20, "A", "C"), strana(35, "K", "M"))
        env = dict(os.environ, RODOKMEN_MAPY=self.koren)
        ok = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "mapa.py"), "hledej", "aron", "03066862", "--pismeno", "F"],
                            capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["stav"], "odhad")
        nic = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "mapa.py"), "hledej", "aron", "jiny", "--pismeno", "F"],
                             capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(nic.returncode, 1)


class Stav(Zaklad):
    def test_stav_a_naplneni_z_pracovni(self):
        sl = Path(self.tmp.name, "pracovni", "aron", "03066862_365")
        sl.mkdir(parents=True)
        for n in (236, 248):
            (sl / f"CZ_215000010_00190_UCWE2WEJ_{n:05d}_sign-365.jpg").write_bytes(b"x")
        self.assertEqual(mapa.main(["naplnit-z-pracovni", "--slozka", str(sl.parent)]), 0)
        m = mapa.nacti("aron", "03066862")
        self.assertEqual(sorted(m), [236, 248])
        self.assertEqual(m[236]["zdroj"], "pracovni")
        self.zapis(strana(236, "A", "C"))
        self.assertEqual(mapa.nacti("aron", "03066862")[236]["typ"], "rejstřík")     # popis doplní identitu
        s = mapa.stav("aron", "03066862")
        self.assertEqual((s["snimku"], s["popsano"]), (2, 1))


class Dokumentace(unittest.TestCase):
    """Před každým čtením (noc i den): mapa knihy, cache a historie (S-007); čtenář vrací údaje o stránkách, zapíše je orchestrátor přes fixera."""
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[3]

    def cti(self, rel):
        return (self.repo / rel).read_text(encoding="utf-8")

    def test_researcher_a_browser_reader(self):
        r = self.cti("agents/researcher.md")
        for s in ("tools/mapa.py hledej", "stranky", "never conclude", "cache.py najdi", "pracovni_prehled.py"):
            self.assertIn(s, r, s)
        self.assertIn("stranky", self.cti("agents/browser-reader.md"))

    def test_orchestrator_pta_se_mapy_a_stranky_zapisuje_zapis_vysledku(self):
        """E2: stránky z nálezu jdou do mapy jako součást zápisu výsledku, bez dalšího agenta."""
        o = self.cti("agents/orchestrator.md")
        for s in ("tools/mapa.py hledej", "mapa.py zapis", "zapis_vysledku.py", "never closes a search"):
            self.assertIn(s, o, s)

    def test_metodika(self):
        n = self.cti("skills/rodokmen/reference/nocni_rezim.md")
        for s in ("Před každým čtením", "tools/mapa.py", "rodokmen_mapy", "nikdy neuzavře hledání", "Stažených snímků na nalezený záznam"):
            self.assertIn(s, n, s)
        self.assertIn("tools/mapa.py hledej", self.cti("skills/rodokmen/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
