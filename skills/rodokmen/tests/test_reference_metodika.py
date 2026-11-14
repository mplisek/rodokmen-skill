"""Poznatky z bádání, které patří do metodiky skillu (reference/*.md), ne do poznámek pro správce: křest hledat v celém roce,
rejstříky sňatků v AHMP jen u některých farností, názvy obcí z hlavičky archivu bez domýšlení diakritiky."""
import unittest
from pathlib import Path

REF = Path(__file__).resolve().parents[1] / "reference"


class ReferenceMetodika(unittest.TestCase):
    def setUp(self):
        self.matriky = (REF / "matriky.md").read_text(encoding="utf-8")
        self.portaly = (REF / "portaly.md").read_text(encoding="utf-8")

    def test_krest_se_hleda_v_celem_roce(self):
        self.assertIn("Křest hledej v celém roce", self.matriky)

    def test_nazvy_obci_z_hlavicky_bez_domyslene_diakritiky(self):
        self.assertIn("přebírej z hlavičky nebo seznamu archivu", self.matriky)

    def test_ahmp_rejstriky_snatku_jen_u_nekterych_farnosti(self):
        self.assertIn("ejstřík sňatků na konci knihy mají jen některé farnosti", self.portaly)


if __name__ == "__main__":
    unittest.main()
