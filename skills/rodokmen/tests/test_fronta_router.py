"""Router úkolů (analyza/navrh-router-uloh.md, S-001, S-004): vstupní fronta, směrování s definicí hotového (DOD), dělení, parkování a pravidla opakování
po selhání portálu (nejdřív za dvě noci, pak víkend, pak pracovní doba, pak jedno rozhodnutí za portál). Bez sítě, dočasná složka dat."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402

ROZHODNUTI = ["--otazka", "Jet automaticky?", "--moznosti", "A) automaticky; B) ručně", "--vychozi", "ručně"]


class Zaklad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)
        (self.data / "osoby.py").write_text('P = {5: dict(n="A", f=["* 1. 2. 1800 Obec"]), 6: dict(n="B", f=["× asi 1820"])}\n', encoding="utf-8")

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = fronta.main(list(a))
        self.out = out.getvalue()
        return kod

    def soubor(self, nazev):
        p = self.data / nazev
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def ukoly(self, f):
        return fronta.nacti(f)[1]

    def zapni_vstup(self):
        (self.data / "ukoly_vstup.md").write_text("# Vstup\n", encoding="utf-8")


class Vstup(Zaklad):
    def test_s_vstupem_se_primo_do_cilove_fronty_nezaklada(self):
        self.zapni_vstup()
        with self.assertRaises(SystemExit) as cm:
            self.run_("pridej", "noc", "--text", "x")
        self.assertIn("vstup", str(cm.exception))
        self.assertEqual(self.ukoly("noc"), [])
        self.run_("pridej", "vstup", "--text", "nový úkol")
        self.assertEqual(len(self.ukoly("vstup")), 1)

    def test_bez_vstupu_stare_chovani(self):
        self.run_("pridej", "noc", "--text", "x")
        self.assertEqual(len(self.ukoly("noc")), 1)


class Smeruj(Zaklad):
    def setUp(self):
        super().setUp()
        self.zapni_vstup()
        self.run_("pridej", "vstup", "--text", "najít křest", "--os", "7", "--typ", "krest", "--p", "P1")

    def test_smeruj_presune_s_dod_a_cenou(self):
        self.run_("smeruj", "U-0001", "--do", "noc", "--dod", "křest zapsán v datech", "--cena", "M")
        self.assertEqual(self.ukoly("vstup"), [])
        u = self.ukoly("noc")[0]
        self.assertIn("Definice hotového: křest zapsán v datech", u.text)
        self.assertEqual(u.cena, "M")
        self.assertEqual(u.p, "P1")

    def test_bez_dod_se_odmitne(self):
        pred = self.soubor("ukoly_vstup.md")
        with self.assertRaises(SystemExit) as cm:
            self.run_("smeruj", "U-0001", "--do", "noc")
        self.assertIn("definic", str(cm.exception).lower())
        self.assertEqual(self.soubor("ukoly_vstup.md"), pred)

    def test_neznama_fronta_a_cena(self):
        for a in (["--do", "nekam", "--dod", "x"], ["--do", "noc", "--dod", "x", "--cena", "XXL"]):
            with self.assertRaises(SystemExit):
                self.run_("smeruj", "U-0001", *a)
        self.assertEqual(len(self.ukoly("vstup")), 1)

    def test_do_rozhodnuti_jen_se_strukturou(self):
        with self.assertRaises(SystemExit):
            self.run_("smeruj", "U-0001", "--do", "rozhodnuti", "--dod", "rozhodnuto")
        self.assertEqual(len(self.ukoly("vstup")), 1)
        self.run_("uprav", "U-0001", "--text", "Otázka: Q?\nMožnosti: A; B\nVýchozí postup: A")
        self.run_("smeruj", "U-0001", "--do", "rozhodnuti", "--dod", "rozhodnuto")
        self.assertEqual(len(self.ukoly("rozhodnuti")), 1)

    def test_cil_uz_v_datech_se_nesmeruje(self):
        self.run_("pridej", "vstup", "--text", "křest osoby 5", "--cil", "krest:5", "--os", "5")
        kod = self.run_("smeruj", "U-0002", "--do", "noc", "--dod", "zapsáno")
        self.assertEqual(kod, 1)
        self.assertIn("hotovo", self.out)
        self.assertEqual(self.ukoly("noc"), [])
        self.assertEqual(len(self.ukoly("vstup")), 2)

    def test_duplicita_se_slouci_do_existujiciho(self):
        self.run_("pridej", "vstup", "--text", "jiné", "--os", "9", "--typ", "krest")
        self.run_("smeruj", "U-0001", "--do", "noc", "--dod", "hotovo")
        self.run_("uprav", "U-0002", "--os", "7")                       # po úpravě je to tentýž úkol jako v cílové frontě (typ i osoby)
        self.run_("smeruj", "U-0002", "--do", "noc", "--dod", "hotovo")
        self.assertEqual(len(self.ukoly("noc")), 1)
        self.assertEqual(self.ukoly("badani"), [])
        self.assertEqual(self.ukoly("vstup"), [])
        self.assertIn("doplněno", self.out)


class Rozdel(Zaklad):
    def setUp(self):
        super().setUp()
        self.zapni_vstup()
        self.run_("pridej", "vstup", "--text", "rodina X: křest a úmrtí", "--os", "7", "--p", "P2")

    def test_rozdel_na_vice_front_s_dod(self):
        self.run_("rozdel", "U-0001", "--cast", "noc", "křest online", "křest zapsán", "--cast", "dotazy", "úmrtí není online", "dotaz odeslán")
        self.assertEqual(self.ukoly("vstup"), [])
        n, d = self.ukoly("noc")[0], self.ukoly("dotazy")[0]
        self.assertEqual((n.rodic, d.rodic), ("U-0001", "U-0001"))
        self.assertIn("Definice hotového: křest zapsán", n.text)
        self.assertIn("Definice hotového: dotaz odeslán", d.text)
        self.assertNotEqual(n.id, d.id)
        self.assertEqual((n.os, d.os, n.p), (["7"], ["7"], "P2"))

    def test_cast_bez_dod_nebo_s_neznamou_frontou_nic_nezmeni(self):
        pred = self.soubor("ukoly_vstup.md")
        for a in (["--cast", "noc", "text", ""], ["--cast", "nekam", "text", "dod"]):
            with self.assertRaises(SystemExit):
                self.run_("rozdel", "U-0001", *a)
        self.assertEqual(self.soubor("ukoly_vstup.md"), pred)
        self.assertEqual(self.ukoly("noc"), [])


class Zaparkuj(Zaklad):
    def test_zaparkovany_ceka_do_data(self):
        self.run_("pridej", "noc", "--text", "zápis se zpřístupní později")
        self.run_("zaparkuj", "U-0001", "--do", "2999-01-01", "--duvod", "zpřístupnění 2999")
        u = self.ukoly("noc")[0]
        self.assertEqual((u.stav, u.do), ("čeká", "2999-01-01"))
        self.assertIn("zpřístupnění 2999", u.text)
        self.assertEqual(fronta.frontier(fronta.vse()), [])
        self.run_("zaparkuj", "U-0001", "--do", "2000-01-01")
        self.assertEqual([x.id for x in fronta.frontier(fronta.vse())], ["U-0001"])


class Selhani(Zaklad):
    def setUp(self):
        super().setUp()
        self.run_("pridej", "noc", "--text", "čtení z portálu", "--os", "7", "--typ", "krest")

    def selhani(self, kdy, druh="prechodna", portal="aron", id_="U-0001"):
        return self.run_("selhani", id_, "--druh", druh, "--portal", portal, "--kdy", kdy)

    def test_prechodna_chyba_projde_rezimy_noc_vikend_pracovni(self):
        self.selhani("2026-11-16 23:00")                    # pondělí v noci, 1. pokus
        u = self.ukoly("noc")[0]
        self.assertEqual((u.stav, u.kdy, u.do, u.pokusu), ("čeká", "noc", "2026-11-18", 1))   # nejdřív za dvě noci
        self.selhani("2026-11-18 23:00")
        u = self.ukoly("noc")[0]
        self.assertEqual((u.kdy, u.do, u.pokusu), ("vikend", "2026-11-21", 2))                # sobota
        self.selhani("2026-11-21 23:00")
        u = self.ukoly("noc")[0]
        self.assertEqual((u.kdy, u.do, u.pokusu), ("pracovni", "2026-11-23", 3))              # pondělí přes den

    def test_po_vycerpani_rezimu_jedno_rozhodnuti_za_portal(self):
        for kdy in ("2026-11-16 23:00", "2026-11-18 23:00", "2026-11-21 23:00", "2026-11-23 12:00"):
            self.selhani(kdy)
        r = self.ukoly("rozhodnuti")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].cil, "portal:aron")
        self.assertEqual(fronta.chyby_rozhodnuti(r[0].text), [])
        self.assertIn("U-0001", r[0].text)
        self.assertIn(r[0].id, self.ukoly("noc")[0].zavisi)               # odblokuje se po rozhodnutí
        self.assertEqual([x.id for x in fronta.frontier(fronta.vse())], [r[0].id])

    def test_zakaz_nikdy_neopakuje_a_hned_vznikne_rozhodnuti(self):
        self.selhani("2026-11-16 23:00", druh="zakaz")
        u = self.ukoly("noc")[0]
        self.assertEqual((u.kdy, u.pokusu), ("", 0))
        r = self.ukoly("rozhodnuti")
        self.assertEqual(len(r), 1)
        self.assertIn(r[0].id, u.zavisi)

    def test_dalsi_ukol_stejneho_portalu_se_pripoji_k_tomu_samemu_rozhodnuti(self):
        self.run_("pridej", "noc", "--text", "jiné čtení", "--os", "8", "--typ", "umrti")
        self.selhani("2026-11-16 23:00", druh="zakaz")
        self.selhani("2026-11-16 23:05", druh="zakaz", id_="U-0002")
        r = self.ukoly("rozhodnuti")
        self.assertEqual(len(r), 1)
        self.assertIn("U-0001", r[0].text)
        self.assertIn("U-0002", r[0].text)

    def test_vlastni_pocet_pokusu_z_rezim_json(self):
        (self.data / "rezim.json").write_text(json.dumps({"opakovani": [{"rezim": "noc", "odstup_dnu": 3}]}), encoding="utf-8")
        self.selhani("2026-11-16 23:00")
        self.assertEqual(self.ukoly("noc")[0].do, "2026-11-19")
        self.selhani("2026-11-19 23:00")
        self.assertEqual(len(self.ukoly("rozhodnuti")), 1)


class DalsiPodleRezimu(Zaklad):
    def dalsi(self, kdy):
        try:
            self.out = ""
            self.run_("dalsi", "noc", "--kdy", kdy)
        except SystemExit:
            return None
        prvni = self.out.split("|")[0].strip()
        return prvni if prvni.startswith("U-") else None

    def test_ukol_s_kdy_bezi_jen_v_tom_rezimu(self):
        self.run_("pridej", "noc", "--text", "o víkendu", "--os", "1", "--typ", "a")
        self.run_("pridej", "noc", "--text", "přes den", "--os", "2", "--typ", "b")
        u1, u2 = self.ukoly("noc")
        u1.kdy, u2.kdy = "vikend", "pracovni"
        fronta.uloz("noc", "", [u1, u2])
        self.assertEqual(self.dalsi("2026-11-16 12:00"), "U-0002")        # pracovní doba: jen úkol s kdy:pracovni
        self.assertIsNone(self.dalsi("2026-11-16 23:00"))                  # noc: ani jeden
        self.assertEqual(self.dalsi("2026-11-21 12:00"), "U-0001")         # sobota: víkendový

    def test_ukol_bez_kdy_se_v_pracovni_dobe_nepousti(self):
        self.run_("pridej", "noc", "--text", "obyčejný")
        self.assertIsNone(self.dalsi("2026-11-16 12:00"))


if __name__ == "__main__":
    unittest.main()
