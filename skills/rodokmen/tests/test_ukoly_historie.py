"""Historie úkolů a opakované čtení (analyza/navrh-router-uloh.md kap. 6.1, S-006): každá změna úkolu se zapíše do data/ukoly_historie.jsonl
(jen přidávání, hotový úkol po sobě nechá stopu); `fronta.py historie`; `fronta.py znovu` najde v deníku neúspěšná čtení staršího nástroje."""
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


class Zaklad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.stare = fronta.DATA
        fronta.DATA = str(self.data)
        (self.data / "osoby.py").write_text('P = {5: dict(n="A", f=["* 1. 2. 1800 Obec"])}\n', encoding="utf-8")

    def tearDown(self):
        fronta.DATA = self.stare
        self.tmp.cleanup()

    def run_(self, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = fronta.main(list(a))
        self.out = out.getvalue()
        return kod

    def udalosti(self):
        p = self.data / "ukoly_historie.jsonl"
        return [json.loads(r) for r in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def typy(self, id_=None):
        return [u["udalost"] for u in self.udalosti() if id_ is None or u.get("id") == id_]

    def vstup(self):
        (self.data / "ukoly_vstup.md").write_text("# Vstup\n", encoding="utf-8")


class Historie(Zaklad):
    def test_vznik_a_hotovo_zustanou_v_historii(self):
        self.run_("pridej", "noc", "--text", "najít křest\nvíc textu", "--p", "P1")
        self.run_("hotovo", "U-0001", "--denik", "12,13", "--soubory", "pracovni/vysledky/x.json", "--spotreba", "M", "--poznamka", "zapsáno")
        e = self.udalosti()
        self.assertEqual([u["udalost"] for u in e], ["vznik", "hotovo"])
        self.assertEqual((e[0]["id"], e[0]["fronta"], e[0]["text"]), ("U-0001", "noc", "najít křest"))
        self.assertEqual((e[1]["denik"], e[1]["soubory"], e[1]["spotreba"]), ([12, 13], ["pracovni/vysledky/x.json"], "M"))
        self.assertTrue(all("cas" in u for u in e))
        self.assertEqual(fronta.nacti("noc")[1], [])                         # z fronty zmizel, v historii zůstal

    def test_hotovo_podle_cile_zapise_kazdy_smazany(self):
        self.run_("pridej", "noc", "--text", "a", "--os", "1", "--typ", "krest", "--cil", "krest:1")
        self.run_("hotovo", "--cil", "krest:1")
        self.assertEqual(self.typy("U-0001"), ["vznik", "hotovo"])

    def test_router_a_selhani_se_zapisuji(self):
        self.vstup()
        self.run_("pridej", "vstup", "--text", "úkol")
        self.run_("smeruj", "U-0001", "--do", "noc", "--dod", "hotovo", "--cena", "S")
        self.run_("selhani", "U-0001", "--druh", "prechodna", "--portal", "aron", "--kdy", "2026-11-16 23:00")
        self.run_("zaparkuj", "U-0001", "--do", "2999-01-01", "--duvod", "čeká")
        e = {u["udalost"]: u for u in self.udalosti()}
        self.assertEqual((e["smerovani"]["z"], e["smerovani"]["do"], e["smerovani"]["cena"], e["smerovani"]["dod"]), ("vstup", "noc", "S", "hotovo"))
        self.assertEqual((e["selhani"]["druh"], e["selhani"]["portal"], e["selhani"]["pokusu"]), ("prechodna", "aron", 1))
        self.assertEqual((e["parkovani"]["do"], e["parkovani"]["duvod"]), ("2999-01-01", "čeká"))

    def test_deleni_a_presun(self):
        self.vstup()
        self.run_("pridej", "vstup", "--text", "dvě věci")
        self.run_("rozdel", "U-0001", "--cast", "noc", "a", "dod a", "--cast", "dotazy", "b", "dod b")
        self.run_("presun", "U-0002", "badani")
        d = [u for u in self.udalosti() if u["udalost"] == "deleni"][0]
        self.assertEqual((d["id"], [x["id"] for x in d["deti"]]), ("U-0001", ["U-0002", "U-0003"]))
        p = [u for u in self.udalosti() if u["udalost"] == "presun"][0]
        self.assertEqual((p["id"], p["z"], p["do"]), ("U-0002", "noc", "badani"))

    def test_id_se_po_hotovo_nepouzije_znovu(self):
        """Stabilní identita úkolu (kap. 6.1): smazaný úkol zůstává v historii, jeho ID se nesmí přidělit novému."""
        self.run_("pridej", "noc", "--text", "první", "--os", "1", "--typ", "a")
        self.run_("hotovo", "U-0001")
        self.run_("pridej", "noc", "--text", "druhý", "--os", "2", "--typ", "b")
        self.assertEqual([u.id for u in fronta.nacti("noc")[1]], ["U-0002"])

    def test_slouceni_se_zapise_jako_doplneni(self):
        self.run_("pridej", "noc", "--text", "a", "--os", "1", "--typ", "krest")
        self.run_("pridej", "noc", "--text", "b", "--os", "1", "--typ", "krest")
        self.assertEqual(self.typy(), ["vznik", "doplneno"])

    def test_historie_vypise_udalosti_ukolu_i_jeho_deti(self):
        self.vstup()
        self.run_("pridej", "vstup", "--text", "dvě věci")
        self.run_("rozdel", "U-0001", "--cast", "noc", "a", "dod a")
        self.run_("historie", "U-0001")
        self.assertIn("vznik", self.out)
        self.assertIn("deleni", self.out)
        self.assertIn("U-0002", self.out)

    def test_soubor_je_jen_pridavany_json_radky(self):
        self.run_("pridej", "noc", "--text", "a")
        t = (self.data / "ukoly_historie.jsonl").read_text(encoding="utf-8")
        self.assertTrue(t.endswith("\n"))
        for r in t.splitlines():
            json.loads(r)


class Znovu(Zaklad):
    def radky(self, *rr):
        (self.data / "denik.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rr) + "\n", encoding="utf-8")

    @staticmethod
    def r(id_, vys, nastroj=None, **kw):
        z = {"id": id_, "datum": "2026-11-01", "zdroj": {"typ": "archiv", "text": f"ARON kniha {id_}"}, "rozsah": "sn. 1–5", "hledano": f"hledání {id_}",
             "vysledek": vys, "nalez": "x"}
        if nastroj:
            z["nastroj"] = nastroj
        z.update(kw)
        return z

    def test_najde_jen_neuspesna_cteni_starsiho_nastroje(self):
        self.radky(self.r(1, "nečitelné", "0.9.0"), self.r(2, "nenalezeno", "0.10.1-fork.1"), self.r(3, "nalezeno", "0.9.0"),
                   self.r(4, "nečitelné"), self.r(5, "nečitelné", "0.9.0", k_rucni_kontrole=True, puvodni="x"),
                   self.r(6, "nenalezeno", "0.9.0"), self.r(7, "nalezeno", "0.10.1-fork.1", opravuje=6))
        self.run_("znovu", "--vysledek", "nečitelné,nenalezeno", "--starsi-nez", "0.10.0")
        radky = [x for x in self.out.splitlines() if x.startswith("deník")]
        self.assertEqual([x.split(":")[0] for x in radky], ["deník 1", "deník 4"])   # 2 novější, 3 nalezeno, 5 skrytý, 6 nahrazený opravou

    def test_zaloz_vytvori_ukoly_a_je_idempotentni(self):
        self.radky(self.r(1, "nečitelné", "0.9.0", osoby=["7"]), self.r(4, "nečitelné"))
        self.run_("znovu", "--starsi-nez", "0.10.0", "--zaloz")
        uk = fronta.nacti("noc")[1]
        self.assertEqual(len(uk), 2)
        self.assertTrue(any("(deník 1)" in u.text and u.os == ["7"] for u in uk))
        self.assertEqual([e["udalost"] for e in self.udalosti()], ["vznik", "vznik"])
        self.run_("znovu", "--starsi-nez", "0.10.0", "--zaloz")
        self.assertEqual(len(fronta.nacti("noc")[1]), 2)                     # podruhé nic nového

    def test_zaloz_jde_do_vstupu_kdyz_existuje(self):
        self.vstup()
        self.radky(self.r(1, "nečitelné", "0.9.0"))
        self.run_("znovu", "--starsi-nez", "0.10.0", "--zaloz")
        self.assertEqual(len(fronta.nacti("vstup")[1]), 1)
        self.assertEqual(fronta.nacti("noc")[1], [])


if __name__ == "__main__":
    unittest.main()
