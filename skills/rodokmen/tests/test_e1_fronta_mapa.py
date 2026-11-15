"""E1 (analyza/navrh-optimalizace.md): dělení úkolu bez tichého dědění osob, `uprav --dod`, zápis do mapy knihy buď celý, nebo vůbec
a se signaturou převedenou na klíč svazku. Bez sítě, dočasné složky."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402
import mapa  # noqa: E402
import vysledek  # noqa: E402


class Deleni(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stare = fronta.DATA
        fronta.DATA = self.tmp.name
        self.run_("pridej", "noc", "--text", "dvě rodiny", "--os", "44,45,160", "--typ", "krest")

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = fronta.main(list(a))
        self.out = out.getvalue()
        return kod

    def test_cast_bez_osob_se_odmitne_kdyz_ma_rodic_vic_osob(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_("rozdel", "U-0001", "--cast", "noc", "kniha 1", "řádek", "--cast", "noc", "kniha 2", "řádek")
        self.assertIn("os=", str(cm.exception))
        self.assertEqual([u.id for u in fronta.nacti("noc")[1]], ["U-0001"])

    def test_cast_ma_vlastni_osoby_typ_a_cenu(self):
        self.run_("rozdel", "U-0001", "--cast", "noc", "kniha 1", "řádek", "os=160", "cena=S", "--cast", "dotazy", "dotaz", "odesláno", "os=44,45",
                  "typ=umrti")
        n, d = fronta.nacti("noc")[1][0], fronta.nacti("dotazy")[1][0]
        self.assertEqual((n.os, n.cena, n.typ), (["160"], "S", "krest"))
        self.assertEqual((d.os, d.typ, d.rodic), (["44", "45"], "umrti", "U-0001"))

    def test_neznamy_doplnek_casti_se_odmitne(self):
        for navic in ("osoby=1", "cena=Q", "volný text"):
            with self.assertRaises(SystemExit):
                self.run_("rozdel", "U-0001", "--cast", "noc", "a", "b", "os=1", navic)

    def test_uprav_dod_nahradi_definici_hotoveho(self):
        self.run_("uprav", "U-0001", "--dod", "křest zapsán")
        self.run_("uprav", "U-0001", "--dod", "křest zapsán a ověřen")
        t = fronta.nacti("noc")[1][0].text
        self.assertEqual(t.count("Definice hotového:"), 1)
        self.assertIn("křest zapsán a ověřen", t)


class MapaZapis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "data" / "svazky.json").write_text(json.dumps({
            "0a1b2c3d": {"svazek": "Sbírka matrik, sign.: 744 (poř.č. 1)"}, "0a1b2c3e": {"svazek": "Sbírka matrik, sign.: 7440"}}), encoding="utf-8")
        self.stare_root, vysledek.ROOT = vysledek.ROOT, str(self.root)
        self.stare_env = os.environ.get("RODOKMEN_MAPY")
        os.environ["RODOKMEN_MAPY"] = str(self.root / "mapy")

    def tearDown(self):
        vysledek.ROOT = self.stare_root
        if self.stare_env is None:
            os.environ.pop("RODOKMEN_MAPY", None)
        else:
            os.environ["RODOKMEN_MAPY"] = self.stare_env
        self.tmp.cleanup()

    def zapis(self, stranky):
        p = self.root / "v.json"
        p.write_text(json.dumps({"model": "sonnet", "stranky": stranky}, ensure_ascii=False), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            kod = mapa.main(["zapis", str(p)])
        self.err = err.getvalue()
        return kod

    def test_signatura_se_prevede_na_klic_svazku(self):
        self.assertEqual(self.zapis([dict(portal="aron", svazek="744", snimek=5, typ="rejstřík", od="A", do="C")]), 0)
        self.assertIn(5, mapa.nacti("aron", "0a1b2c3d"))
        self.assertEqual(mapa.nacti("aron", "744"), {})

    def test_jedna_spatna_stranka_a_nezapise_se_zadna(self):
        kod = self.zapis([dict(portal="aron", svazek="0a1b2c3d", snimek=5, typ="rejstřík", od="A", do="C"),
                          dict(portal="aron", svazek="0a1b2c3d", snimek=6, typ="index")])
        self.assertEqual(kod, 2)
        self.assertIn("stranky[1]", self.err)
        self.assertEqual(mapa.nacti("aron", "0a1b2c3d"), {})


if __name__ == "__main__":
    unittest.main()
