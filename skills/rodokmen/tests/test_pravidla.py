"""scripts/pravidla.py (Fáze E, ADR 0005): pravidla pro agenty mají pevná pole a odkaz na zdrojový oddíl zrcadla; otisk oddílu zachytí
změnu originálu. Rozhraní: příkazy overit, potvrdit, pokryti nad dočasným zrcadlem a pravidly (vymyšlený obsah), bez sítě."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKRIPT = REPO / "scripts" / "pravidla.py"

ZRCADLO = """# Návod

## Ztotožnění osob

Spoj dvě osoby stejného jména jen podle dvou nezávislých znaků.

### Podrobnosti

Číslo domu, oba rodiče.

## Jiný oddíl

Nesouvisející text.
"""

PRAVIDLO = """# Identity

## R-ID-001
when: two people of the same name appear in one parish
do: merge them only on two independent signs
why: two men of the same name were merged into one
source: reference/navod.md#Ztotožnění osob
"""


class Pravidla(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        t = Path(self._tmp.name)
        self.zrcadlo = t / "zrcadlo"
        self.rules = t / "rules"
        (self.zrcadlo / "reference").mkdir(parents=True)
        self.rules.mkdir()
        (self.zrcadlo / "reference" / "navod.md").write_text(ZRCADLO, encoding="utf-8")
        (self.rules / "identity.md").write_text(PRAVIDLO, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def pravidla(self, *args):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(SKRIPT), *args, "--rules", str(self.rules),
                               "--zrcadlo", str(self.zrcadlo)], capture_output=True, text=True, encoding="utf-8")

    def navod(self, text):
        (self.zrcadlo / "reference" / "navod.md").write_text(text, encoding="utf-8", newline="")

    def potvrd(self):
        r = self.pravidla("potvrdit", "R-ID-001")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # ---- základní tok
    def test_nepotvrzene_pravidlo_neprojde_potvrzene_ano(self):
        r = self.pravidla("overit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("R-ID-001", r.stdout + r.stderr)
        self.potvrd()
        r = self.pravidla("overit")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("zdroje.json", "".join(p.name for p in self.rules.iterdir()) + "zdroje.json")
        z = json.loads((self.rules / "zdroje.json").read_text(encoding="utf-8"))
        self.assertEqual(z["R-ID-001"]["source"], "reference/navod.md#Ztotožnění osob")
        self.assertTrue(z["R-ID-001"]["checked"])

    def test_zmena_oddilu_pravidlo_zastara(self):
        self.potvrd()
        self.navod(ZRCADLO.replace("dvou nezávislých znaků", "tří nezávislých znaků"))
        r = self.pravidla("overit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("zastaral", (r.stdout + r.stderr).lower())
        self.assertIn("R-ID-001", r.stdout + r.stderr)
        self.potvrd()                                                              # po revizi znovu platí
        self.assertEqual(self.pravidla("overit").returncode, 0)

    def test_zmena_pododdilu_je_zmena_oddilu_ale_jiny_oddil_ne(self):
        self.potvrd()
        self.navod(ZRCADLO.replace("Nesouvisející text.", "Úplně jiný text."))
        self.assertEqual(self.pravidla("overit").returncode, 0)                    # jiný oddíl pravidlo nezajímá
        self.navod(ZRCADLO.replace("Číslo domu, oba rodiče.", "Číslo domu."))
        self.assertNotEqual(self.pravidla("overit").returncode, 0)                 # podnadpis patří k oddílu

    def test_mezery_a_konce_radku_otisk_nemeni(self):
        self.potvrd()
        self.navod(ZRCADLO.replace("\n", "\r\n").replace("Spoj dvě osoby", "Spoj   dvě   osoby"))
        self.assertEqual(self.pravidla("overit").returncode, 0)

    def test_zmizely_oddil(self):
        self.potvrd()
        self.navod(ZRCADLO.replace("## Ztotožnění osob", "## Přejmenovaný oddíl"))
        r = self.pravidla("overit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("zmizel", (r.stdout + r.stderr).lower())

    def test_zmena_pole_source_vyzaduje_novou_revizi(self):
        self.potvrd()
        (self.rules / "identity.md").write_text(PRAVIDLO.replace("#Ztotožnění osob", "#Jiný oddíl"), encoding="utf-8")
        self.assertNotEqual(self.pravidla("overit").returncode, 0)
        self.potvrd()
        self.assertEqual(self.pravidla("overit").returncode, 0)

    # ---- tvar pravidel
    def test_chybejici_pole_duplicita_a_neexistujici_zdroj(self):
        self.potvrd()
        (self.rules / "identity.md").write_text(PRAVIDLO.replace("why: two men of the same name were merged into one\n", ""), encoding="utf-8")
        r = self.pravidla("overit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("why", r.stdout + r.stderr)
        (self.rules / "identity.md").write_text(PRAVIDLO + "\n" + PRAVIDLO.split("\n", 2)[2], encoding="utf-8")   # druhé R-ID-001
        r = self.pravidla("overit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("duplic", (r.stdout + r.stderr).lower())
        (self.rules / "identity.md").write_text(PRAVIDLO.replace("reference/navod.md", "reference/neni.md"), encoding="utf-8")
        self.assertNotEqual(self.pravidla("overit").returncode, 0)

    def test_neplatne_id(self):
        (self.rules / "identity.md").write_text(PRAVIDLO.replace("R-ID-001", "pravidlo-1"), encoding="utf-8")
        r = self.pravidla("overit")
        self.assertNotEqual(r.returncode, 0)

    def test_vlastni_pravidlo_fork_nema_otisk(self):
        (self.rules / "vlastni.md").write_text("## R-OWN-001\nwhen: always\ndo: write English rules\nwhy: agents read them\nsource: fork\n",
                                               encoding="utf-8")
        self.potvrd()
        self.assertEqual(self.pravidla("overit").returncode, 0)
        z = json.loads((self.rules / "zdroje.json").read_text(encoding="utf-8"))
        self.assertNotIn("R-OWN-001", z)

    def test_zdroj_mimo_markdown_je_otisk_celeho_souboru(self):
        (self.zrcadlo / "tools").mkdir()
        (self.zrcadlo / "tools" / "brzda.py").write_text("ZAKAZ = {}\n", encoding="utf-8")
        (self.rules / "archivy.md").write_text("## R-ARCH-001\nwhen: any archive request\ndo: go through the throttle\nwhy: archives block\n"
                                               "source: tools/brzda.py\n", encoding="utf-8")
        self.potvrd()
        self.assertEqual(self.pravidla("potvrdit", "R-ARCH-001").returncode, 0)
        self.assertEqual(self.pravidla("overit").returncode, 0)
        (self.zrcadlo / "tools" / "brzda.py").write_text("ZAKAZ = {'a': 1}\n", encoding="utf-8")
        self.assertNotEqual(self.pravidla("overit").returncode, 0)

    def test_potvrdit_neznameho_pravidla_selze(self):
        r = self.pravidla("potvrdit", "R-NEEXISTUJE-001")
        self.assertNotEqual(r.returncode, 0)

    def test_potvrdit_vse(self):
        self.assertEqual(self.pravidla("potvrdit", "--vse").returncode, 0)
        self.assertEqual(self.pravidla("overit").returncode, 0)

    # ---- pokrytí
    def test_pokryti_vypise_oddily_bez_pravidla(self):
        self.potvrd()
        r = self.pravidla("pokryti")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Jiný oddíl", r.stdout)
        self.assertNotIn("Ztotožnění osob", r.stdout)


if __name__ == "__main__":
    unittest.main()
