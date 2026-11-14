"""Rozpočet na noc (analyza/navrh-router-uloh.md kap. 5, S-005): pásma ceny S až XL, řazení priorita a cena, práh XL (schválení člověkem),
čerpání rozpočtu okna v `dalsi`, plán okna a kalibrace pásem ze skutečné spotřeby v historii. Bez sítě, dočasná složka dat."""
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

NOC1 = "2026-11-16 23:00"      # pondělí v noci
NOC2 = "2026-11-17 23:00"      # další noc = nové okno


class Zaklad(unittest.TestCase):
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
        try:
            with contextlib.redirect_stdout(out):
                kod = fronta.main(list(a))
        except SystemExit as e:
            self.out = out.getvalue() + str(e)
            raise
        self.out = out.getvalue()
        return kod

    def ukol(self, text, cena="", p="P2"):
        self.run_("pridej", "noc", "--text", text, "--p", p, "--os", text, "--typ", "t" + text)
        if cena:
            self.run_("uprav", self.posledni(), "--cena", cena)

    def posledni(self):
        return max(fronta.nacti("noc")[1], key=lambda u: int(u.id[2:])).id

    def rezim(self, **rozpocet):
        (self.data / "rezim.json").write_text(json.dumps({"rozpocet": rozpocet}), encoding="utf-8")

    def dalsi(self, kdy):
        self.out = ""
        try:
            self.run_("dalsi", "noc", "--kdy", kdy)
        except SystemExit:
            return None
        prvni = self.out.split("|")[0].strip()
        return prvni if prvni.startswith("U-") else None


class Razeni(Zaklad):
    def test_radi_podle_priority_pak_ceny_neznama_cena_je_prvni(self):
        self.ukol("a", "L", "P1")
        self.ukol("b", "S", "P1")
        self.ukol("c", "", "P1")
        self.ukol("d", "S", "P2")
        poradi = [(u.p, u.cena) for u in fronta.nacti("noc")[1]]
        self.assertEqual(poradi, [("P1", ""), ("P1", "S"), ("P1", "L"), ("P2", "S")])


class PrahXL(Zaklad):
    def setUp(self):
        super().setUp()
        (self.data / "ukoly_vstup.md").write_text("# Vstup\n", encoding="utf-8")
        self.run_("pridej", "vstup", "--text", "velký úkol")

    def test_xl_do_nocni_fronty_jen_se_schvalenim(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_("smeruj", "U-0001", "--do", "noc", "--dod", "hotovo", "--cena", "XL")
        self.assertIn("rozhodnuti", str(cm.exception))
        self.assertEqual(len(fronta.nacti("vstup")[1]), 1)
        self.run_("smeruj", "U-0001", "--do", "noc", "--dod", "hotovo", "--cena", "XL", "--schvaleno")
        u = fronta.nacti("noc")[1][0]
        self.assertIn("Schváleno:", u.text)
        self.assertEqual(u.cena, "XL")

    def test_xl_do_rozhodnuti_projde(self):
        self.run_("uprav", "U-0001", "--text", "Otázka: Provést?\nMožnosti: A) ano; B) ručně\nVýchozí postup: ručně")
        self.run_("smeruj", "U-0001", "--do", "rozhodnuti", "--dod", "rozhodnuto", "--cena", "XL")
        self.assertEqual(len(fronta.nacti("rozhodnuti")[1]), 1)

    def test_dalsi_nepusti_xl_bez_schvaleni(self):
        (self.data / "ukoly_vstup.md").unlink()
        self.run_("pridej", "noc", "--text", "x", "--os", "x", "--typ", "tx")
        uid = fronta.nacti("noc")[1][0].id
        self.run_("uprav", uid, "--cena", "XL")                         # ručně nastavená cena, bez schválení
        self.assertIsNone(self.dalsi(NOC1))
        self.run_("uprav", uid, "--pridat-text", "Schváleno: uživatel 2026-11-14")
        self.assertEqual(self.dalsi(NOC1), uid)


class Cerpani(Zaklad):
    def setUp(self):
        super().setUp()
        self.rezim(okno={"noc": 4})                                      # výchozí váhy S=1, M=3, L=8, XL=20
        self.ukol("a", "M", "P1")
        self.ukol("b", "M", "P1")
        self.ukol("c", "S", "P1")

    def test_okno_se_vycerpa_a_dalsi_noc_je_nove(self):
        # P1 seřazené: S (c), M (a), M (b); rozpočet 4: S (1) + M (3) = 4, druhé M se už nevejde
        self.assertEqual(self.dalsi(NOC1), "U-0003")
        self.assertEqual(self.dalsi(NOC1), "U-0001")
        self.assertIsNone(self.dalsi(NOC1))
        self.assertIn("rozpočet", self.out)
        self.assertEqual(self.dalsi(NOC2), "U-0002")                     # nové okno, spotřeba od nuly; U-0003 a U-0001 už jsou přidělené

    def test_dalsi_ukol_prideli_a_oznaci_probiha(self):
        self.assertEqual(self.dalsi(NOC1), "U-0003")
        self.assertEqual(fronta.nacti("noc")[1][0].stav, "probíhá")

    def test_vsechny_se_vejdou_ve_vychozim_rozpoctu(self):
        self.rezim()
        self.assertEqual(self.dalsi(NOC1), "U-0003")
        self.assertEqual(self.dalsi(NOC1), "U-0001")
        self.assertEqual(self.dalsi(NOC1), "U-0002")

    def test_plan_ukaze_poradi_a_mimo_rozpocet(self):
        self.run_("plan", "noc", "--kdy", NOC1)
        r = [x for x in self.out.splitlines() if x.startswith("U-")]
        self.assertEqual([x.split()[0] for x in r], ["U-0003", "U-0001", "U-0002"])
        self.assertIn("mimo rozpočet", r[2])
        self.assertNotIn("mimo rozpočet", r[0] + r[1])
        self.assertIn("4/4", self.out)


class Kalibrace(Zaklad):
    def test_porovna_odhad_se_skutecnou_spotrebou(self):
        for i, (odhad, skut) in enumerate([("M", "M"), ("M", "L"), ("M", "L"), ("S", "S")], 1):
            self.run_("pridej", "noc", "--text", f"u{i}", "--os", f"o{i}", "--typ", f"t{i}")
            self.run_("uprav", f"U-000{i}", "--cena", odhad)
            fronta.zapis_udalost("smerovani", f"U-000{i}", z="vstup", do="noc", dod="x", cena=odhad)
            self.run_("hotovo", f"U-000{i}", "--spotreba", skut)
        self.run_("kalibrace")
        self.assertIn("M", self.out)
        self.assertRegex(self.out, r"M\s+3.*L\s*2")                      # odhad M u 3 úkolů, skutečně 2× L
        self.assertIn("podhodnoceno", self.out)


if __name__ == "__main__":
    unittest.main()
