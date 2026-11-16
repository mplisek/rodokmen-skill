"""tools/vysledek.py (analyza/navrh-optimalizace.md, E1; scénáře 5, 6, 7, 8): kontrakt zadání, nálezu a ověření. Chybný výsledek se odmítne
dřív, než se zapíše: osoba jménem, signatura místo klíče svazku, typ stránky mimo výčet, čtení mimo rozsah, hledání v prameni, který roli
nevede, „nenalezeno“ bez dočtení. Ověřovatel vrací jen přepis, shodu počítá nástroj. Bez sítě, dočasný projekt."""
import contextlib
import copy
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
import vysledek  # noqa: E402


class Zaklad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.stare = vysledek.ROOT
        vysledek.ROOT = str(self.root)
        (self.root / "data").mkdir()
        (self.root / "pracovni" / "zadani").mkdir(parents=True)
        (self.root / "pracovni" / "vysledky").mkdir()
        (self.root / "data" / "osoby.py").write_text('P = {88: dict(n="Josef Vzorný")}\nRODINA = {"josef-vzorny-1809": dict(n="Josef Vzorný")}\n',
                                                     encoding="utf-8")
        (self.root / "data" / "svazky.json").write_text(json.dumps({
            "0a1b2c3d": {"portal": "ARON", "svazek": "Sbírka matrik, sign.: 712 (poř.č. 1), 1800-1825"},
            "0e0e0e0e": {"portal": "ARON", "svazek": "Sbírka matrik, sign.: 759 (poř.č. 2), 1700-1790", "pokryva": {"role": ["ženich"]}}},
            ensure_ascii=False), encoding="utf-8")
        self.zadani = copy.deepcopy(vysledek.VZORY["zadani"])
        self.nalez = copy.deepcopy(vysledek.VZORY["nalez"])
        self.overeni = copy.deepcopy(vysledek.VZORY["overeni"])

    def tearDown(self):
        vysledek.ROOT = self.stare
        self.tmp.cleanup()

    def uloz(self, rel, d):
        p = self.root / rel
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def run_(self, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = vysledek.main(list(a))
        self.out = out.getvalue()
        return kod


class Vzory(Zaklad):
    def test_vzory_projdou_vlastni_kontrolou(self):
        self.assertEqual(vysledek.over_zadani(self.zadani), [])
        self.assertEqual(vysledek.over_nalez(self.nalez, self.zadani), [])
        self.assertEqual(vysledek.over_overeni(self.overeni), [])

    def test_prikaz_vzor_vypise_priklad_i_vycty(self):
        self.run_("vzor", "nalez")
        self.assertIn('"schema": "nalez/1"', self.out)
        self.assertIn("nedostupné", self.out)


class SpatneIdentifikatory(Zaklad):
    """Scénář 8: každé pole zvlášť."""

    def chyby(self, zmena):
        zmena(self.nalez)
        return "\n".join(vysledek.over_nalez(self.nalez, self.zadani))

    def test_osoba_jmenem(self):
        ch = self.chyby(lambda n: n["kandidati"][0].update(osoba="Josef Vzorný ml. (88)"))
        self.assertIn("kandidati[0].osoba", ch)
        self.assertIn("ne jméno", ch)

    def test_signatura_misto_klice_svazku_napovi_klic(self):
        ch = self.chyby(lambda n: n["cteni"][0]["zdroj"].update(svazek="712"))
        self.assertIn("signatura", ch)
        self.assertIn("0a1b2c3d", ch)

    def test_typ_a_kvalita_stranky_mimo_vycet(self):
        self.assertIn("stranky[0].typ", self.chyby(lambda n: n["stranky"][0].update(typ="index")))
        self.nalez = copy.deepcopy(vysledek.VZORY["nalez"])
        self.assertIn("stranky[0].kvalita", self.chyby(lambda n: n["stranky"][0].update(kvalita="ok")))

    def test_vyrez_do_verejne_slozky(self):
        self.assertIn("vyrez", self.chyby(lambda n: n["cteni"][0].update(vyrez="zdroje/c1.jpg")))

    def test_cteni_mimo_zadany_rozsah(self):
        ch = self.chyby(lambda n: n["prohledano"][0].update(snimky=[44, 60]))
        self.assertIn("mimo zadaný rozsah", ch)
        self.zadani["rozsireni"] = [{"snimky": [53, 60]}]                    # schválené rozšíření ale nestačí na souvislý úsek 44–60
        self.nalez["prohledano"] = [{"svazek": "0a1b2c3d", "snimky": [53, 60], "uplne": True}]
        self.assertEqual(vysledek.over_nalez(self.nalez, self.zadani), [])

    def test_prikaz_over_vrati_kod_1_a_nazvy_poli(self):
        self.nalez["stav"] = "hotovo"
        p = self.uloz("pracovni/vysledky/U-0101.json", self.nalez)
        self.assertEqual(self.run_("over", p), 1)
        self.assertIn("stav:", self.out)
        self.assertIn("nenalezeno", self.out)                                 # výčet dovolených hodnot


class NegativniVysledek(Zaklad):
    """Scénáře 5 a 6."""

    def negativni(self, **kw):
        self.nalez.update(stav="nenalezeno", stav_behu="dočteno", cteni=[], kandidati=[], navrh_dalsiho_kroku=None,
                          prohledano=[{"svazek": "0a1b2c3d", "snimky": [40, 52], "uplne": True}])
        self.nalez.update(kw)
        return "\n".join(vysledek.over_nalez(self.nalez, self.zadani))

    def test_poctivy_negativni_vysledek_projde(self):
        self.assertEqual(self.negativni(), "")

    def test_nenalezeno_po_dosazenem_stropu_se_odmitne(self):
        self.assertIn("rozpočet", self.negativni(stav_behu="strop"))

    def test_nenalezeno_s_nedoctenym_rozsahem_se_odmitne(self):
        self.assertIn("uplne: false", self.negativni(prohledano=[{"svazek": "0a1b2c3d", "snimky": [40, 45], "uplne": False}]))

    def test_nenalezeno_bez_rozsahu_se_odmitne(self):
        self.assertIn("prohledano", self.negativni(prohledano=[]))

    def test_rozpocet_nedostupne_a_necitelne_jsou_platne_stavy_bez_nalezu(self):
        self.assertEqual(self.negativni(stav="rozpočet", stav_behu="strop", prohledano=[{"svazek": "0a1b2c3d", "snimky": [40, 45], "uplne": False}]), "")
        self.assertEqual(self.negativni(stav="nedostupné", stav_behu="překážka", prohledano=[]), "")
        self.assertEqual(self.negativni(stav="nečitelné", stav_behu="překážka", prohledano=[{"svazek": "0a1b2c3d", "snimky": [40, 40], "uplne": False}]), "")

    def test_zadani_hledat_nevestu_v_rejstriku_zenichu_se_odmitne(self):
        self.zadani.update(hleda_roli="nevěsta", pramen={"portal": "aron", "svazek": "0e0e0e0e"})
        ch = "\n".join(vysledek.over_zadani(self.zadani))
        self.assertIn("vede jen: ženich", ch)
        self.zadani["hleda_roli"] = "ženich"
        self.assertEqual(vysledek.over_zadani(self.zadani), [])

    def test_nenalezeno_z_pramene_ktery_roli_nevede_se_odmitne(self):
        self.zadani.update(hleda_roli="nevěsta", pramen={"portal": "aron", "svazek": "0e0e0e0e"})
        ch = self.negativni(prohledano=[{"svazek": "0e0e0e0e", "snimky": [40, 52], "uplne": True}])
        self.assertIn("vede jen: ženich", ch)


class OvereniAPorovnani(Zaklad):
    """Scénář 7."""

    def priprav(self, **druhe):
        self.uloz("pracovni/zadani/U-0101.json", self.zadani)
        self.uloz("pracovni/vysledky/U-0101.json", self.nalez)
        self.overeni["doslova"].update(druhe)
        self.uloz("pracovni/vysledky/U-0101_overeni_c1.json", self.overeni)

    def test_overovatel_nesmi_vracet_shodu_ani_identitu(self):
        self.overeni["shoda"] = True
        self.assertIn("porovnej", "\n".join(vysledek.over_overeni(self.overeni)))

    def test_neshoda_po_polich_a_kod_1(self):
        self.priprav(datum="17. Maii 1812")
        self.assertEqual(self.run_("porovnej", "U-0101", "c1", "--json"), 1)
        v = {r["pole"]: r for r in json.loads(self.out)["pole"]}
        self.assertEqual(v["datum"]["vysledek"], "neshoda")
        self.assertEqual((v["datum"]["prvni"], v["datum"]["druhe"]), ("17. Martii 1812", "17. Maii 1812"))
        self.assertEqual(v["dite"]["vysledek"], "shoda")

    def test_shoda_bez_ohledu_na_velikost_pismen_a_interpunkci(self):
        self.nalez["cteni"][0]["doslova"] = {"datum": "17. Martii 1812", "dite": "Josephus", "otec": "joannes  wzorny,"}
        self.priprav()
        self.assertEqual(self.run_("porovnej", "U-0101", "c1"), 0)
        self.assertIn("shodují", self.out)

    def test_pole_jen_v_jednom_cteni_a_necitelne(self):
        self.overeni["doslova"].pop("otec")
        self.overeni["necitelne"] = ["otec"]
        self.priprav(matka="Anna")
        self.run_("porovnej", "U-0101", "c1", "--json")
        v = {r["pole"]: r["vysledek"] for r in json.loads(self.out)["pole"]}
        self.assertEqual((v["otec"], v["matka"]), ("nečitelné při druhém čtení", "jen druhé čtení"))

    def test_vic_overeni_jednoho_cteni(self):
        """Podnět z bádání 16. 11. 2026: třetí slepé čtení z lepších výřezů (`_overeni_c1_v2.json`) se porovná s prvním čtením taky."""
        self.priprav(datum="17. Maii 1812")                                   # druhé čtení nesouhlasí
        treti = json.loads(json.dumps(self.overeni))
        treti["doslova"] = dict(self.nalez["cteni"][0]["doslova"])            # třetí čtení souhlasí s prvním ve všech polích
        self.uloz("pracovni/vysledky/U-0101_overeni_c1_v2.json", treti)
        # rozhodnutí uživatele 16. 11. 2026: stačí 2 ze 3 (hodnotu prvního čtení potvrdí většina všech čtení, aspoň dvě)
        self.assertEqual(self.run_("porovnej", "U-0101", "c1", "--json"), 0)
        d = json.loads(self.out)
        self.assertEqual([o["soubor"] for o in d["overeni"]], ["U-0101_overeni_c1.json", "U-0101_overeni_c1_v2.json"])
        self.assertEqual([o["shoda"] for o in d["overeni"]], [False, True])
        self.assertEqual(d["vetsina"]["datum"], {"potvrzuje": 2, "cteni": 3, "overeno": True})
        self.run_("porovnej", "U-0101", "c1")
        self.assertIn("c1_v2", self.out)
        self.assertIn("datum: 2 z 3", self.out)
        ctvrte = json.loads(json.dumps(self.overeni))                          # 2 : 2 = bez většiny, neověřeno
        ctvrte["vyrezy"] = ["pracovni/vysledky/U-0101_vyrezy/c1_d.jpg"]           # jiné čtení (vlastní výřez), ne kopie
        self.uloz("pracovni/vysledky/U-0101_overeni_c1_v3.json", ctvrte)
        self.assertEqual(self.run_("porovnej", "U-0101", "c1", "--json"), 1)
        self.assertFalse(json.loads(self.out)["vetsina"]["datum"]["overeno"])
        os.remove(self.root / "pracovni/vysledky/U-0101_overeni_c1_v3.json")
        os.remove(self.root / "pracovni/vysledky/U-0101_overeni_c1.json")       # jen dodatečné ověření stačí, když je jediné
        self.assertEqual(self.run_("porovnej", "U-0101", "c1"), 0)

    def test_kopie_overeni_pod_jinym_nazvem_se_nezapocte_dvakrat(self):
        """Podnět z bádání 16. 11. 2026: tentýž soubor ověření pod dvěma názvy se počítal jako dvě čtení."""
        self.priprav(datum="17. Maii 1812")
        self.uloz("pracovni/vysledky/U-0101_overeni_c1_v2.json", self.overeni)  # kopie, ne nové čtení
        self.assertEqual(self.run_("porovnej", "U-0101", "c1", "--json"), 1)
        d = json.loads(self.out)
        self.assertEqual(d["vetsina"]["datum"]["cteni"], 2)
        self.assertIn("U-0101_overeni_c1_v2.json", d["kopie"])

    def test_datum_s_jinym_zapisem_mesice_je_shoda(self):
        """Podnět z bádání 16. 11. 2026: „1801 Februar 17“ × „1801 Febrr. 17“ byla neshoda; měsíc se porovnává jako měsíc."""
        for prvni, druhe, shoda in (("1801 Februar 17", "1801 Febrr. 17", True), ("17. Martii 1812", "17. Mart. 1812", True),
                                    ("17. Martii 1812", "17. Maii 1812", False), ("3. 9ber 1790", "3. Novembris 1790", True),
                                    ("4. Xbris 1790", "4. Decembr. 1790", True), ("5. července 1850", "5. června 1850", False)):
            r = vysledek.porovnej({"doslova": {"datum": prvni}}, {"doslova": {"datum": druhe}})
            self.assertEqual(r[0]["vysledek"] == "shoda", shoda, (prvni, druhe))
        r = vysledek.porovnej({"doslova": {"otec": "Febr"}}, {"doslova": {"otec": "Februar"}})   # mimo data se měsíce nenormalizují
        self.assertEqual(r[0]["vysledek"], "neshoda")

    def test_dve_overeni_proti_prvnimu_cteni_neovereno(self):
        self.priprav(datum="17. Maii 1812")
        druhe = dict(self.overeni, vyrezy=["pracovni/vysledky/U-0101_vyrezy/c1_b.jpg"])
        self.uloz("pracovni/vysledky/U-0101_overeni_c1_v2.json", druhe)        # obě ověření čtou jinak než první čtení
        self.assertEqual(self.run_("porovnej", "U-0101", "c1", "--json"), 1)
        self.assertEqual(json.loads(self.out)["vetsina"]["datum"], {"potvrzuje": 1, "cteni": 3, "overeno": False})


class Souhrn(Zaklad):
    def test_souhrn_drzi_nejistotu_chybejici_pole_rozsah_a_navrh(self):
        self.uloz("pracovni/vysledky/U-0101.json", self.nalez)
        self.assertEqual(self.run_("souhrn", "U-0101"), 0)
        for s in ("částečně", "CHYBÍ kmotri", "nejisté otec", "snímky 44–46", "NE celé", "sousední strana", "6 kroků", "osoba 88"):
            self.assertIn(s, self.out)
        self.assertNotIn("Josephus", self.out)                                # přepis zůstává v souboru
        self.assertLess(len(self.out), 700)


if __name__ == "__main__":
    unittest.main()
