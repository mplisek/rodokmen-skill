"""znackuj_rody.py a kontrola_webu.py (Fáze B, ADR 0004): holý název rodu v textu stránek se nahradí jednotnou značkou (barevný
kruh a název s odkazem) a kontrola webu hlídá holé názvy, barvu značky, pořadí rodů a procesní text. Rozhraní: příkazy nad
vzorovými stránkami v dočasné složce (vymyšlená data), bez sítě."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

SITE = {"lines": {
    "novakove": {"k": 8, "slug": "novakove", "name": "Novákové", "color": "#EFB45F"},
    "kralove": {"k": 9, "slug": "kralove", "name": "Králové", "color": "#5FA8EF"},
}}


def znacka(slug="novakove", nazev="Novákové", barva="#EFB45F"):
    return (f'<span class="rod-znak"><span class="dot" style="background:{barva}"></span>'
            f'<a href="/rod/{slug}/">{nazev}</a></span>')


class Zaklad(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name) / "dist"
        self.d.mkdir()
        self.site = Path(self._tmp.name) / "site.json"
        self.site.write_text(json.dumps(SITE, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def stranka(self, jmeno, telo):
        cesta = self.d / jmeno
        cesta.parent.mkdir(parents=True, exist_ok=True)
        cesta.write_text(f"<!doctype html><html><head><title>Web</title></head><body><main>{telo}</main></body></html>",
                         encoding="utf-8")
        return cesta

    def nastroj(self, skript, *args):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / skript), str(self.d), "--site", str(self.site), *args],
                              capture_output=True, text=True, encoding="utf-8")

    def znackuj(self):
        return self.nastroj("znackuj_rody.py")

    def kontrola(self):
        return self.nastroj("kontrola_webu.py")


class Znackovani(Zaklad):
    def test_holy_nazev_se_nahradi_znackou(self):
        c = self.stranka("index.html", "<p>Rod Novákové žil v Holicích.</p>")
        self.assertEqual(self.znackuj().returncode, 0)
        self.assertIn(f"<p>Rod {znacka()} žil v Holicích.</p>", c.read_text(encoding="utf-8"))

    def test_vic_rodu_a_delsi_nazev_ma_prednost(self):
        site = {"lines": {**SITE["lines"], "novak": {"k": 10, "slug": "novak", "name": "Novák", "color": "#111111"}}}
        self.site.write_text(json.dumps(site, ensure_ascii=False), encoding="utf-8")
        c = self.stranka("a.html", "<p>Novákové, Králové a Novák.</p>")
        self.znackuj()
        t = c.read_text(encoding="utf-8")
        self.assertIn(znacka("novakove", "Novákové"), t)
        self.assertIn(znacka("kralove", "Králové", "#5FA8EF"), t)
        self.assertIn(znacka("novak", "Novák", "#111111"), t)

    def test_neni_nahrazeno_v_odkazu_znacce_atributu_a_skriptu(self):
        telo = (f'<a href="/x/">Novákové</a><h1>Novákové</h1>{znacka()}<img alt="Novákové" title="Novákové">'
                "<script>var x = 'Novákové';</script><style>.Novákové{}</style><textarea>Novákové</textarea>"
                "<select><option>Novákové</option></select><button>Novákové</button>")
        c = self.stranka("b.html", telo)
        pred = c.read_text(encoding="utf-8")
        self.znackuj()
        self.assertEqual(c.read_text(encoding="utf-8"), pred)

    def test_hranice_slov_a_skloneny_tvar_se_nenahradi(self):
        c = self.stranka("c.html", "<p>Novákovědi, Novákových a ZNovákové.</p>")
        pred = c.read_text(encoding="utf-8")
        self.znackuj()
        self.assertEqual(c.read_text(encoding="utf-8"), pred)

    def test_kruh_sablony_pred_nazvem_se_nezdvoji(self):
        """Podnět z bádání 16. 11. 2026: stránky jmen, domů a mapy mají před názvem rodu vlastní kruh rodu a značka přidala druhý."""
        telo = ('<span class="chip" data-astro-cid-x><span class="dot" style="background:#EFB45F" data-astro-cid-x></span>Novákové</span>'
                '<span><span class="dot" style="background:#5FA8EF"></span>Králové 4</span>'
                '<span><span class="dot" style="background:#111111"></span>Novákové</span>')   # jiná barva = jiný význam, zůstane
        c = self.stranka("e.html", telo)
        self.znackuj()
        t = c.read_text(encoding="utf-8")
        self.assertEqual(t.count('style="background:#EFB45F"'), 2, t)                    # jeden kruh na každý ze dvou výskytů
        self.assertIn(f'<span class="chip" data-astro-cid-x>{znacka()}</span>', t)
        self.assertIn(f'<span>{znacka("kralove", "Králové", "#5FA8EF")} 4</span>', t)
        self.assertIn(f'<span class="dot" style="background:#111111"></span>{znacka()}', t)
        self.znackuj()
        self.assertEqual(c.read_text(encoding="utf-8"), t)                                # opakování nic nemění

    def test_opakovani_nic_nemeni(self):
        c = self.stranka("d.html", "<p>Novákové</p><ul><li>Králové</li></ul>")
        self.znackuj()
        prvni = c.read_text(encoding="utf-8")
        r = self.znackuj()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(c.read_text(encoding="utf-8"), prvni)

    def test_projde_podslozky_a_jen_html(self):
        a = self.stranka("osoba/jan/index.html", "<p>Králové</p>")
        txt = self.d / "poznamka.txt"
        txt.write_text("Králové", encoding="utf-8")
        self.znackuj()
        self.assertIn("rod-znak", a.read_text(encoding="utf-8"))
        self.assertEqual(txt.read_text(encoding="utf-8"), "Králové")

    def test_text_s_entitami_a_zalomenim_zustane_celistvy(self):
        c = self.stranka("e.html", "<p>A&nbsp;Novákové &amp; Králové,\nnebo ne.</p>")
        self.znackuj()
        t = c.read_text(encoding="utf-8")
        self.assertIn("A&nbsp;" + znacka(), t)
        self.assertIn("&amp; " + znacka("kralove", "Králové", "#5FA8EF") + ",\nnebo ne.", t)


class KontejnerRodu(Zaklad):
    """Rozhodnutí uživatele 16. 11. 2026: kontejner vázaný na rod má barvu rodu (jako /rody/), obecný je neutrální; na stránce
    Co hledáme jeden kontejner na rod v otázkách pro rodinu a v otevřených otázkách."""
    def box(self, rod="novakove", barva="#EFB45F", obsah="x"):
        styl = f' style="--c:{barva}"' if barva else ""
        return f'<section class="card rod-box" data-rod="{rod}"{styl}>{obsah}</section>'

    def test_spravny_kontejner_projde(self):
        self.stranka("a.html", self.box() + self.box("kralove", "#5FA8EF") + self.box("", None)
                     + '<section class="card rod-box" data-rod="obecne" data-astro-cid-x><div class="rod-box-hlava">Obecné</div></section>')   # komponenta RodBox
        r = self.kontrola()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_chyby_kontejneru(self):
        for telo, stopa in ((self.box(barva=None), "bez barvy"), (self.box(barva="#000000"), "barva kontejneru"),
                            (self.box("cizi"), "neznámého rodu"), (self.box("", "#EFB45F"), "obecný kontejner"),
                            ('<div class="card rod-box">x</div>', "data-rod")):
            with self.subTest(stopa=stopa):
                self.stranka("b.html", telo)
                r = self.kontrola()
                self.assertNotEqual(r.returncode, 0, telo)
                self.assertIn(stopa, r.stdout)

    def test_hledame_kontejner_na_otazku(self):
        """Uživatel 20. 11. 2026: co otázka, to kontejner – víc kontejnerů téhož rodu v kterékoli části je v pořádku."""
        dvakrat = self.box() + self.box()
        self.stranka("hledame/index.html", "".join(f'<section data-hledame="{c}">{dvakrat}</section>'
                                                   for c in ("rodina", "prameny", "otevrene")))
        self.assertEqual(self.kontrola().returncode, 0)


class NepotvrzeneOtazky(Zaklad):
    def test_nepotvrzeny_text_na_strance_je_chyba(self):
        data = Path(self._tmp.name) / "data"
        data.mkdir()
        (data / "verejne_otazky.json").write_text(json.dumps({"otazky": [
            {"id": 1, "druh": "rodina", "otazka": "Kde se narodil prapradědeček Josef?"},
            {"id": 2, "druh": "rodina", "otazka": "Je doma oddací list babičky?", "potvrzeno": {"datum": "2026-11-16", "kdo": "u"}},
        ]}, ensure_ascii=False), encoding="utf-8")
        self.stranka("hledame/index.html", "<ul><li>Je doma oddací list babičky?</li></ul>")
        r = self.nastroj("kontrola_webu.py", "--data", str(data), "--bez-vazeb")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.stranka("hledame/index.html", "<ul><li>Je doma oddací list babičky?</li><li>Kde se narodil  prapradědeček Josef?</li></ul>")
        r = self.nastroj("kontrola_webu.py", "--data", str(data), "--bez-vazeb")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nepotvrzená", r.stdout)


class KontrolaWebu(Zaklad):
    def test_cista_stranka_projde(self):
        self.stranka("index.html", f"<p>Rod {znacka()} žil v Holicích.</p>")
        r = self.kontrola()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_holy_nazev_je_chyba_a_po_znackovani_projde(self):
        self.stranka("index.html", "<p>Rod Novákové žil v Holicích.</p>")
        r = self.kontrola()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Novákové", r.stdout + r.stderr)
        self.assertIn("index.html", r.stdout + r.stderr)
        self.znackuj()
        self.assertEqual(self.kontrola().returncode, 0)

    def test_spatna_barva_znacky(self):
        self.stranka("index.html", znacka("novakove", "Novákové", "#000000"))
        r = self.kontrola()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("barva", (r.stdout + r.stderr).lower())

    def test_poradi_rodu_v_nadpisech(self):
        spatne = f"<h2>{znacka('kralove', 'Králové', '#5FA8EF')}</h2><p>a</p><h2>{znacka()}</h2>"
        dobre = f"<h2>{znacka()}</h2><p>a</p><h2>{znacka('kralove', 'Králové', '#5FA8EF')}</h2>"
        self.stranka("hledame.html", spatne)
        r = self.kontrola()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("pořadí", (r.stdout + r.stderr).lower())
        self.stranka("hledame.html", dobre)
        self.assertEqual(self.kontrola().returncode, 0)

    def test_procesni_text_na_strance(self):
        for telo, stopa in (("<p>Úkol U-0013 čeká.</p>", "U-0013"), ("<p>Čte pomocník.</p>", "pomocník"),
                            ("<p>viz pracovni/aron/x.jpg</p>", "pracovni/"), ("<p>čtyři oči</p>", "čtyři oči"),
                            ("<p>Sonnet přečetl.</p>", "sonnet")):
            with self.subTest(telo=telo):
                self.stranka("p.html", telo)
                r = self.kontrola()
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(stopa.lower(), (r.stdout + r.stderr).lower())

    def test_procesni_vzory_ve_skriptu_a_stylu_nevadi(self):
        self.stranka("p.html", "<script>const x = 'pomocník U-0013 pracovni/';</script><style>/* sonnet */</style><p>čisto</p>")
        self.assertEqual(self.kontrola().returncode, 0)

    def test_bez_dat_rodu_se_kontroluje_jen_procesni_text(self):
        self.stranka("p.html", f"<p>{znacka('cizi', 'Cizí', '#123456')} Novákové.</p>")
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontrola_webu.py"), str(self.d), "--site",
                            str(self.d / "neexistuje.json")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.stranka("p.html", "<p>Čte pomocník.</p>")
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(TOOLS / "kontrola_webu.py"), str(self.d), "--site",
                            str(self.d / "neexistuje.json")], capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(r.returncode, 0)

    def test_skloneny_tvar_je_jen_upozorneni(self):
        self.stranka("p.html", f"<p>{znacka()} a Novákových.</p>")
        r = self.kontrola()
        self.assertEqual(r.returncode, 0)
        self.assertIn("Novákových", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
