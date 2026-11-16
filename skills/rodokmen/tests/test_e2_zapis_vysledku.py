"""E2 (analyza/navrh-optimalizace.md; scénáře 1, 6, 9, 13): tools/zapis_vysledku.py zapíše přijatý výsledek celý, nebo vůbec, a podruhé nic
nezdvojí; tools/commit.py commituje jen jeho soubory; tools/stav.py řekne po restartu, co je rozpracováno a co má následovat. Průchod
v dočasném projektu s kopií nástrojů, bez sítě."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import vysledek  # noqa: E402

U = "U-0001"


class Projekt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projekt"
        (self.root / "data").mkdir(parents=True)
        shutil.copytree(TOOLS, self.root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "data" / "osoby.py").write_text('P = {88: dict(n="Josef Vzorný")}\nRODINA = {"josef-vzorny-1809": dict(n="Josef Vzorný")}\n',
                                                     encoding="utf-8")
        (self.root / "data" / "svazky.json").write_text(json.dumps({"0a1b2c3d": {"portal": "ARON", "svazek": "sign.: 712"}}), encoding="utf-8")
        (self.root / "data" / "zaznamy.json").write_text("[]\n", encoding="utf-8")
        self.env = dict(os.environ, RODOKMEN_MAPY=str(Path(self.tmp.name) / "mapy"), PYTHONIOENCODING="utf-8")
        self.py("fronta.py", "pridej", "noc", "--text", "Křest osoby 88", "--os", "88", "--typ", "krest")
        self.py("fronta.py", "uprav", U, "--dod", "křest zapsán a ověřen")
        self.py("zadani.py", "novy", U, "--otazka", "Najdi křest osoby 88.", "--hleda", "křtěnec", "--osoba", "88:křtěnec:* asi 1812",
                "--svazek", "0a1b2c3d", "--snimky", "40-52", "--vratit", "datum,dite,otec")
        self.nalez = copy.deepcopy(vysledek.VZORY["nalez"])
        self.nalez.update(ukol=U, stav="nalezeno", navrh_dalsiho_kroku=None)
        self.nalez["cteni"][0]["chybi"] = []
        self.overeni = copy.deepcopy(vysledek.VZORY["overeni"])
        self.overeni.update(ukol=U)
        self.overeni["doslova"] = dict(self.nalez["cteni"][0]["doslova"])
        self.rozh = copy.deepcopy(vysledek.VZORY["rozhodnuti"])
        self.rozh.update(ukol=U, navazujici=[{"text": "Kdo byl kmotr?", "os": ["88"], "typ": "kmotr"}])
        self.rozh.pop("identita")

    def tearDown(self):
        self.tmp.cleanup()

    def py(self, nastroj, *a):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.root / "tools" / nastroj), *a], capture_output=True, text=True,
                              encoding="utf-8", env=self.env, cwd=self.root)

    def uloz(self, rel, d):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return rel

    def priprav(self, overeni=True):
        self.uloz(f"pracovni/vysledky/{U}.json", self.nalez)
        if overeni:
            self.uloz(f"pracovni/vysledky/{U}_overeni_c1.json", self.overeni)
        return self.uloz(f"pracovni/vysledky/{U}_rozhodnuti.json", self.rozh)

    def zapis(self, *a):
        return self.py("zapis_vysledku.py", self.priprav_cesta, *a)

    def denik(self):
        p = self.root / "data" / "denik.jsonl"
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def stav_dat(self):
        return {p.name: p.read_bytes() for p in sorted((self.root / "data").iterdir()) if p.is_file()}


class Zapis(Projekt):
    def test_jasny_zaznam_se_zapise_cely(self):
        """Scénář 1 (část dat): deník, zápis, přepis, mapa, navazující úkol, uzavření – jedním voláním."""
        r = self.py("zapis_vysledku.py", self.priprav())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = self.denik()
        self.assertEqual(len(d), 1)
        self.assertEqual((d[0]["vysledek"], d[0]["osoby"], d[0]["ukol"], d[0]["overeno"], d[0]["odkaz"]),
                         ("nalezeno", ["88"], U, True, "lhota_krest_josef_vzorny_1812"))
        self.assertEqual(d[0]["snimky"], [{"svazek": "0a1b2c3d", "od": 44, "do": 46}])
        self.assertEqual(json.loads((self.root / "data" / "zaznamy.json").read_text(encoding="utf-8"))[0]["snimek"], 46)
        self.assertIn("lhota_krest_josef_vzorny_1812", json.loads((self.root / "data" / "prepisy.json").read_text(encoding="utf-8")))
        noc = (self.root / "data" / "ukoly_na_noc.md").read_text(encoding="utf-8")
        self.assertNotIn(f"## {U} ", noc)                                   # uzavřeno
        self.assertIn("Kdo byl kmotr?", noc)                                # navazující otázka
        self.assertTrue(list((Path(self.tmp.name) / "mapy").rglob("*.jsonl")))
        h = [json.loads(x) for x in (self.root / "data" / "ukoly_historie.jsonl").read_text(encoding="utf-8").splitlines()]
        z = [e for e in h if e["udalost"] == "zapsano"][0]
        zz = json.loads((self.root / "data" / "zaznamy.json").read_text(encoding="utf-8"))[0]
        self.assertEqual(zz["ucastnici"][0], {"osoba": "88", "role": "křtěnec"})                 # E4: účastníci jsou u zápisu
        tv = [json.loads(x) for x in (self.root / "data" / "tvrzeni.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual((tv[0]["id"], tv[0]["typ"], tv[0]["osoby"], tv[0]["jistota"], tv[0]["denik"], tv[0]["zaznam"]),
                         ("T-0001", "narozeni", ["88"], "doc", d[0]["id"], "lhota_krest_josef_vzorny_1812"))
        self.assertIn("data/tvrzeni.jsonl", z["soubory"])
        self.assertIn("data/denik.jsonl", z["soubory"])
        self.assertIn("data/zaznamy.json", z["soubory"])

    def test_opakovani_nic_nezdvoji(self):
        """Scénář 9."""
        p = self.priprav()
        self.assertEqual(self.py("zapis_vysledku.py", p).returncode, 0)
        pred = self.stav_dat()
        r = self.py("zapis_vysledku.py", p)
        self.assertEqual(r.returncode, 0)
        self.assertIn("už zapsáno", r.stdout)
        self.assertEqual(self.stav_dat(), pred)

    def test_selhani_uprostred_vrati_vsechno(self):
        """Scénář 9: zápis v zaznamy.json už existuje s polem navíc → nástroj zapis odmítne až po řádku deníku; vše se vrátí."""
        (self.root / "data" / "zaznamy.json").write_text(json.dumps(
            [{"klic": "lhota_krest_josef_vzorny_1812", "svazek": "0a1b2c3d", "snimek": 1, "poznamka_navic": "x"}], ensure_ascii=False) + "\n",
            encoding="utf-8")
        p = self.priprav()
        pred = self.stav_dat()
        r = self.py("zapis_vysledku.py", p)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("vráceny", r.stdout)
        self.assertEqual(self.stav_dat(), pred)
        self.assertEqual(self.denik(), [])
        self.assertFalse(list((self.root / "pracovni").glob("zapis_*.rozpracovano")))

    def test_bez_overeni_naslepo_se_overeny_vysledek_nezapise(self):
        r = self.py("zapis_vysledku.py", self.priprav(overeni=False))
        self.assertEqual(r.returncode, 1)
        self.assertIn("ověření naslepo", r.stdout)
        self.assertEqual(self.denik(), [])

    def test_neshoda_cteni_brani_zapisu_doc(self):
        """Scénář 7: rozpor čtení nejde zapsat jako ověřený nález s novým zápisem."""
        self.overeni["doslova"]["datum"] = "17. Maii 1812"
        r = self.py("zapis_vysledku.py", self.priprav())
        self.assertEqual(r.returncode, 1)
        self.assertIn("neshodují", r.stdout)
        self.assertIn("datum", r.stdout)

    def test_tri_nezdary_nejsou_nenalezeno_ani_hotovo(self):
        """Scénář 6: strop, nedostupný portál a nečitelný snímek."""
        self.rozh.pop("zaznam")
        self.rozh.pop("tvrzeni")
        self.rozh["denik"].update(overeno=False)
        for stav, beh, vys in (("rozpočet", "strop", "nenalezeno"), ("nedostupné", "překážka", "nenalezeno"), ("nečitelné", "překážka", "nenalezeno")):
            self.nalez.update(stav=stav, stav_behu=beh, cteni=[], kandidati=[],
                              prohledano=[] if stav == "nedostupné" else [{"svazek": "0a1b2c3d", "snimky": [40, 45], "uplne": False}])
            self.rozh.update(vysledek=vys, dukaz=[])
            r = self.py("zapis_vysledku.py", self.priprav(overeni=False))
            self.assertEqual(r.returncode, 1, stav + r.stdout)
            self.assertEqual(self.denik(), [], stav)
        self.rozh.update(vysledek="částečně", uzavrit=True)                 # po stropu lze zapsat „částečně“, ale ne uzavřít
        self.nalez.update(stav="rozpočet", stav_behu="strop", prohledano=[{"svazek": "0a1b2c3d", "snimky": [40, 45], "uplne": False}])
        r = self.py("zapis_vysledku.py", self.priprav(overeni=False))
        self.assertIn("nelze uzavřít", r.stdout)
        self.rozh.update(uzavrit=False, dod_splneno=False, navazujici=[])
        r = self.py("zapis_vysledku.py", self.priprav(overeni=False))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.denik()[0]["vysledek"], "částečně")
        self.assertIn(f"## {U} ", (self.root / "data" / "ukoly_na_noc.md").read_text(encoding="utf-8"))   # úkol zůstává

    def test_jmenovec_bez_vylouceni_se_odmitne(self):
        """Scénář 3."""
        self.py("zadani.py", "novy", U, "--otazka", "Najdi křest osoby 88.", "--hleda", "křtěnec", "--osoba", "88:křtěnec:* asi 1812",
                "--svazek", "0a1b2c3d", "--snimky", "40-52", "--vratit", "datum", "--nezamenit", "josef-vzorny-1809:otec mlynář", "--prepis")
        r = self.py("zapis_vysledku.py", self.priprav())
        self.assertEqual(r.returncode, 1)
        self.assertIn("jmenovce", r.stdout)
        self.rozh["identita"] = {"osoba": "88", "proc": "čp. 5 a otec chalupník", "vylouceno": ["josef-vzorny-1809"]}
        self.assertEqual(self.py("zapis_vysledku.py", self.priprav()).returncode, 0)

    def test_novy_zapis_bez_ucastniku_a_doc_bez_overeni_se_odmitne(self):
        """E4: zápis bez účastníků by vazbu zápis ↔ osoba zase nechal na ručním `r`; tvrzení doc jen s ověřením."""
        self.rozh["zaznam"].pop("ucastnici")
        r = self.py("zapis_vysledku.py", self.priprav())
        self.assertEqual(r.returncode, 1)
        self.assertIn("ucastnici", r.stdout)
        self.rozh.pop("zaznam")
        self.rozh["denik"]["overeno"] = False
        r = self.py("zapis_vysledku.py", self.priprav(overeni=False))
        self.assertEqual(r.returncode, 1)
        self.assertIn("jistota doc", r.stdout)
        self.rozh["tvrzeni"][0].update(jistota="prob", nahrazuje="T-0099")
        r = self.py("zapis_vysledku.py", self.priprav(overeni=False))
        self.assertIn("T-0099", r.stdout)
        self.rozh["tvrzeni"][0].pop("nahrazuje")
        r = self.py("zapis_vysledku.py", self.priprav(overeni=False))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_nanecisto_nic_nezapise(self):
        r = self.py("zapis_vysledku.py", self.priprav(), "--nanecisto")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("v pořádku", r.stdout)
        self.assertEqual(self.denik(), [])


class StavACommit(Projekt):
    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True, encoding="utf-8")

    def test_stav_po_restartu_rekne_dod_a_dalsi_krok(self):
        """Scénář 13: bez historie rozhovoru."""
        r = self.py("stav.py")
        self.assertIn(U, r.stdout)
        self.assertIn("křest zapsán a ověřen", r.stdout)
        self.assertIn("čtenář ještě nevrátil nález", r.stdout)
        self.nalez.update(stav="částečně", navrh_dalsiho_kroku={"typ": "sousední strana", "snimek": 47, "duvod": "řádek pokračuje"})
        self.nalez["cteni"][0]["chybi"] = ["kmotri"]
        self.uloz(f"pracovni/vysledky/{U}.json", self.nalez)
        r = self.py("stav.py")
        for s in ("nález částečně", "chybí kmotri", "pokračovat v témže úkolu", "sousední strana", "rozsah 40–52"):
            self.assertIn(s, r.stdout, s)
        self.nalez.update(stav="nalezeno", navrh_dalsiho_kroku=None)
        self.uloz(f"pracovni/vysledky/{U}.json", self.nalez)
        self.assertIn("ověřit naslepo", self.py("stav.py").stdout)
        self.assertEqual(self.py("zapis_vysledku.py", self.priprav()).returncode, 0)
        self.assertNotIn(f"{U} (", self.py("stav.py").stdout)               # uzavřený úkol už není rozpracovaný

    def test_commit_jen_soubory_zapisu_na_aktivni_vetvi(self):
        self.git("init", "-q", "-b", "prace")
        self.git("config", "user.email", "test@example.org")
        self.git("config", "user.name", "Test")
        (self.root / ".gitignore").write_text("pracovni/\n__pycache__/\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")
        (self.root / "data" / "cizi.md").write_text("rozdělaná cizí práce\n", encoding="utf-8")
        self.assertEqual(self.py("zapis_vysledku.py", self.priprav()).returncode, 0)
        r = self.py("commit.py", U, "--vetev", "jina")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("větev nepřepínám", r.stdout + r.stderr)
        r = self.py("commit.py", U, "--zprava", f"Hotovo {U}")
        self.assertIn("bez čísel úkolů", r.stdout + r.stderr)
        r = self.py("commit.py", U, "--vetev", "prace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        soubory = self.git("show", "--name-only", "--format=%s", "HEAD").stdout.split()
        self.assertIn("data/denik.jsonl", soubory)
        self.assertNotIn("data/cizi.md", soubory)
        self.assertNotIn(U, self.git("log", "-1", "--format=%B").stdout)
        self.assertIn("cizi.md", self.git("status", "--short").stdout)       # cizí práce zůstala nedotčená
        self.assertEqual(self.py("commit.py", U).returncode, 1)              # podruhé není co commitovat


if __name__ == "__main__":
    unittest.main()
