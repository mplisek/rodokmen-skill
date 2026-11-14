"""reference/nocni_rezim.md: rozhodovací postup směrování úkolů, struktura úkolu k rozhodnutí a nejisté čtení (analyza/navrh-router-uloh.md, S-002, S-003).
Test hlídá, že pravidla v dokumentaci jsou a že odpovídají nástroji (povinná pole úkolu k rozhodnutí)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402

REF = Path(__file__).resolve().parents[1] / "reference" / "nocni_rezim.md"


class NocniRezimPravidla(unittest.TestCase):
    def setUp(self):
        self.t = REF.read_text(encoding="utf-8")

    def test_rozhodovaci_postup_ma_vsechny_vetve(self):
        for s in ("už v datech", "čtením online zdrojů", "k bádání", "dotaz", "pro rodinu", "k rozhodnutí"):
            self.assertIn(s, self.t, s)

    def test_rodina_jen_3_4_generace_a_zajimavosti(self):
        self.assertIn("nejvýš 3–4 generace", self.t)
        self.assertIn("zajímavosti", self.t)
        self.assertIn("`fam`", self.t)                       # rodina je důkaz nižšího stupně, nepřebije matriku

    def test_vecne_otazky_nejsou_rozhodnuti(self):
        self.assertIn("nepatří", self.t.lower())
        self.assertIn("věcné otázky", self.t)
        self.assertIn("přečíst znovu", self.t)

    def test_pole_ukolu_k_rozhodnuti_odpovidaji_nastroji(self):
        for pole in fronta.POVINNA_ROZHODNUTI:
            self.assertIn(pole, self.t, pole)

    def test_nejiste_cteni_nejde_primo_do_rozhodnuti(self):
        i = self.t.index("## Nejisté čtení")
        odstavec = self.t[i:i + 1200]
        self.assertIn("druhé čtení naslepo", odstavec)
        self.assertNotIn("potvrdit, zamítnout, nebo přečíst znovu", odstavec)


if __name__ == "__main__":
    unittest.main()
