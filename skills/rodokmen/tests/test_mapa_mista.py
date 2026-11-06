"""Přiřazení osob k místům na mapě (export_web.text_pro_misto): poznámky v závorkách, okres a původ partnera se nepočítají."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
from export_web import text_pro_misto  # noqa: E402


def najde(obec, fakt):
    return bool(re.search(obec, text_pro_misto(fakt)))


class TextProMisto(unittest.TestCase):
    def test_poznamky_a_okres_se_nepocitaji(self):
        self.assertFalse(najde("Brod", "* 19. 3. 1926 Horní Vestec (okr. Havlíčkův Brod)"))
        self.assertFalse(najde("Kutn", "dcera Václava Vojty z Rozkoše čp. 5, okres Kutná Hora"))
        self.assertFalse(najde("Libic", "* 1. 5. 1825 Bezděkov čp. 35 (kniha narozených Libice 727, str. 76)"))
        self.assertTrue(najde("Bezd", "* 1. 5. 1825 Bezděkov čp. 35 (kniha narozených Libice 727, str. 76)"))

    def test_snatek_misto_ano_puvod_partnera_ne(self):
        self.assertTrue(najde("Libic", "× 25. 6. 1918 Libice nad Doubravou Marie Culková"))
        self.assertFalse(najde("Chlum", "× 12. 11. 1889 Marie Tesařová z Chlumu (rodina)"))
        self.assertTrue(najde("Polom", "× 8. 5. 1864 Polom Anna Růžičková"))
        self.assertFalse(najde("Stru", "rodiče podle schématu: Karel Plíšek × Cecílie Stehnová ze Stružince"))
        self.assertTrue(najde("Stru", "ze Stružince"))


class RodyOsoby(unittest.TestCase):
    def test_rody(self):
        from export_web import rody_osoby
        R = {"dite": dict(otec=8, matka=9), "partner": dict(partner=["dite"]), "nikdo": dict()}
        self.assertEqual(rody_osoby(10, R), {10})
        self.assertEqual(rody_osoby(21, R), {10})
        self.assertEqual(rody_osoby(4, R), {8, 9})
        self.assertEqual(rody_osoby(1, R), set(range(8, 16)))
        self.assertEqual(rody_osoby("dite", R), {8, 9})
        self.assertEqual(rody_osoby("partner", R), {8, 9})
        self.assertEqual(rody_osoby("nikdo", R), set())


if __name__ == "__main__":
    unittest.main()
