"""E5 (analyza/navrh-optimalizace.md, oddíl 7; scénář 10): vztah A–B a účast v zápisu musí být na sestaveném webu vidět z obou stran.
Očekávání je ručně psané v datech testu (osoby.py, zaznamy.json), ne spočítané exportem; kontrola čte hotové HTML. Každý chybějící směr
se vyvolá odebráním odkazu z jedné stránky (test tedy chybu opravdu chytí). Bez sítě a bez Node.js: stránky jsou psané ručně."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

OSOBY = '''
P = {1: dict(n="Petr Vzor"), 2: dict(n="Josef Vzor", r=["krest_petr"]), 3: dict(n="Eva Příkladová")}
RODINA = {"anna-vzorova": dict(n="Anna Vzorová", sex="F", otec=2, matka=3), "karel-kmotr": dict(n="Karel Kmotr", sex="M")}
PARTNERI = [dict(a=2, b="karel-kmotr-zena", rok=1900)]
'''
ZAZNAMY = [{"klic": "krest_petr", "druh": "N", "datum": "1. 1. 1900", "nazev": "Křest", "shrnuti": "x",
            "ucastnici": [{"osoba": "1", "role": "křtěnec"}, {"osoba": "karel-kmotr", "role": "kmotr"}]}]
# kdo na koho odkazuje: ručně psaná matice očekávaného webu
OSOBA = {"petr": ["josef", "eva"], "josef": ["petr", "eva", "anna"], "eva": ["petr", "josef", "anna"], "anna": ["josef", "eva"], "karel": []}
ZAPISY_OSOB = {"petr": ["krest_petr"], "josef": ["krest_petr"], "karel": ["krest_petr"]}
LIDE = [dict(tree="k1", slug="petr", name="Petr Vzor", parents=["josef", "eva"], kids=[], partners=[], records=["krest_petr"]),
        dict(tree="k2", slug="josef", name="Josef Vzor", parents=[], kids=[{"slug": "petr"}, {"slug": "anna"}], partners=[{"slug": "eva"}],
             records=["krest_petr"]),
        dict(tree="k3", slug="eva", name="Eva Příkladová", parents=[], kids=[{"slug": "petr"}, {"slug": "anna"}], partners=[{"slug": "josef"}], records=[]),
        dict(tree="o:anna-vzorova", slug="anna", name="Anna Vzorová", parents=["josef", "eva"], kids=[], partners=[], records=[]),
        dict(tree="o:karel-kmotr", slug="karel", name="Karel Kmotr", parents=[], kids=[], partners=[], records=["krest_petr"])]


class VazbyWebu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "data" / "osoby.py").write_text(OSOBY, encoding="utf-8")
        (self.root / "data" / "zaznamy.json").write_text(json.dumps(ZAZNAMY, ensure_ascii=False), encoding="utf-8")
        self.site = self.root / "site.json"
        self.site.write_text(json.dumps({"people": LIDE, "lines": {}}, ensure_ascii=False), encoding="utf-8")
        self.dist = self.root / "dist"
        for slug, odkazy in OSOBA.items():
            self.stranka(f"osoba/{slug}", [f"/osoba/{o}/" for o in odkazy] + [f"/zdroj/{z}/" for z in ZAPISY_OSOB.get(slug, [])])
        self.stranka("zdroj/krest_petr", ["/osoba/petr/", "/osoba/josef/", "/osoba/karel/"])

    def tearDown(self):
        self.tmp.cleanup()

    def stranka(self, cesta, odkazy):
        p = self.dist / cesta / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("<html><body>" + "".join(f'<a href="{o}">x</a>' for o in odkazy) + "</body></html>", encoding="utf-8")

    def kontrola(self):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontrola_webu.py"), str(self.dist), "--site", str(self.site),
                            "--data", str(self.root / "data")], capture_output=True, text=True, encoding="utf-8")
        return r.returncode, r.stdout + r.stderr

    def test_uplny_web_projde_a_rekne_kolik_overil(self):
        kod, out = self.kontrola()
        self.assertEqual(kod, 0, out)
        self.assertRegex(out, r"\d+ vztahů a účastí v zápisech ověřeno z obou stran")

    def test_chybejici_dite_u_rodice(self):
        self.stranka("osoba/josef", ["/osoba/eva/", "/osoba/anna/", "/zdroj/krest_petr/"])      # Josef neuvádí syna Petra
        kod, out = self.kontrola()
        self.assertEqual(kod, 1)
        self.assertIn("osoba/josef: chybí dítě Petr Vzor", out)

    def test_chybejici_rodic_u_ditete(self):
        self.stranka("osoba/anna", ["/osoba/josef/"])                                            # Anna neuvádí matku
        kod, out = self.kontrola()
        self.assertEqual(kod, 1)
        self.assertIn("osoba/anna: chybí rodič Eva Příkladová", out)

    def test_chybejici_partner(self):
        self.stranka("osoba/eva", ["/osoba/petr/", "/osoba/anna/"])                              # Eva neuvádí manžela
        kod, out = self.kontrola()
        self.assertEqual(kod, 1)
        self.assertIn("osoba/eva: chybí partner Josef Vzor", out)

    def test_kmotr_bez_zapisu_a_zapis_bez_kmotra(self):
        """Scénář A–B: vazba je v datech jen jako účast v zápisu (pole ucastnici); musí být u kmotra i u zápisu."""
        self.stranka("osoba/karel", [])
        kod, out = self.kontrola()
        self.assertEqual(kod, 1)
        self.assertIn("osoba/karel: chybí zápis krest_petr", out)
        self.stranka("osoba/karel", ["/zdroj/krest_petr/"])
        self.stranka("zdroj/krest_petr", ["/osoba/petr/", "/osoba/josef/"])
        kod, out = self.kontrola()
        self.assertEqual(kod, 1)
        self.assertIn("zdroj/krest_petr: chybí osoba Karel Kmotr", out)

    def test_vztah_ktery_export_neuvadi_je_jen_upozorneni(self):
        """Skrytá osoba: export vztah neuvádí z žádné strany → nejde o chybu šablony, jen upozornění."""
        lide = json.loads(json.dumps(LIDE))
        lide[0]["parents"] = ["josef"]
        for p in lide:
            if p["slug"] == "eva":
                p["kids"] = [{"slug": "anna"}]
        self.site.write_text(json.dumps({"people": lide, "lines": {}}, ensure_ascii=False), encoding="utf-8")
        self.stranka("osoba/petr", ["/osoba/josef/", "/zdroj/krest_petr/"])
        self.stranka("osoba/eva", ["/osoba/josef/", "/osoba/anna/"])
        kod, out = self.kontrola()
        self.assertEqual(kod, 0, out)
        self.assertIn("upozornění: vztah rodič–dítě Eva Příkladová → Petr Vzor", out)

    def test_bez_vazeb_kontrolu_vynecha(self):
        self.stranka("osoba/eva", [])
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontrola_webu.py"), str(self.dist), "--site", str(self.site),
                            "--data", str(self.root / "data"), "--bez-vazeb"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
