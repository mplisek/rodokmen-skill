"""tools/prohlizec.py: vlastní prohlížeč pro portály, kam skript nesmí (poznámka browser-reader, 14. 11. 2026). Pravidla jsou v nástroji:
jen portály ze ZAKAZ, jeden archiv na relaci, pauza 5 s (10 s při listování), strop otevření za hodinu, stop při 403/429/CAPTCHA (sdílí brzdu slusne),
snímek jen do pracovni/. Bez sítě a bez prohlížeče: stránka je náhrada, čekání zaznamenává. Hook pouští jen tento nástroj, ne ruční Start-Process."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import prohlizec  # noqa: E402
import slusne  # noqa: E402

TREBON = "digi.ceskearchivy.cz"


class Odpoved:
    def __init__(self, status):
        self.status = status


class Stranka:
    """Náhrada Playwright stránky."""
    def __init__(self, status=200, text="Matriky Třeboň"):
        self.status, self.text, self.volani = status, text, []

    def goto(self, url, **kw):
        self.volani.append(("goto", url))
        return Odpoved(self.status)

    def click(self, sel, **kw):
        self.volani.append(("click", sel))

    def fill(self, sel, txt, **kw):
        self.volani.append(("fill", sel, txt))

    def inner_text(self, sel, **kw):
        return self.text

    def screenshot(self, path, **kw):
        self.volani.append(("screenshot", path))


class Zaklad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stare = (slusne.STAV, list(slusne._slozka_))
        slusne.STAV = str(Path(self.tmp.name) / "brzda")        # stopky brzdy v dočasné složce
        slusne._slozka_.clear()
        self.cekani = []

    def tearDown(self):
        slusne.STAV = self.stare[0]
        slusne._slozka_[:] = self.stare[1]
        self.tmp.cleanup()

    def spi(self, s):
        self.cekani.append(round(s, 1))


class CistaPravidla(unittest.TestCase):
    def test_portal_ze_zakaz(self):
        self.assertTrue(prohlizec.zakazany_portal(prohlizec.host_z_url("https://digi.ceskearchivy.cz/ebadatelna/x")))
        self.assertTrue(prohlizec.zakazany_portal("www.mza.cz"))
        self.assertIsNone(prohlizec.zakazany_portal("aron.vychodoceskearchivy.cz"))

    def test_pauza(self):
        self.assertEqual(prohlizec.pauza(0, 100), 0.0)
        self.assertEqual(prohlizec.pauza(100, 102), 3.0)
        self.assertEqual(prohlizec.pauza(100, 102, listovani=True), 8.0)
        self.assertEqual(prohlizec.pauza(100, 200), 0.0)

    def test_strop_otevreni_za_hodinu(self):
        ted = 10_000
        self.assertTrue(prohlizec.moc_otevreni([ted - 10] * 120, ted))
        self.assertFalse(prohlizec.moc_otevreni([ted - 10] * 119, ted))
        self.assertFalse(prohlizec.moc_otevreni([ted - 4000] * 500, ted))      # starší než hodina se nepočítá

    def test_duvod_stopu(self):
        for s in (403, 429, 503):
            self.assertIn(str(s), prohlizec.duvod_stopu(s, ""))
        self.assertTrue(prohlizec.duvod_stopu(200, "Prosím potvrďte, že nejste robot (CAPTCHA)"))
        self.assertIsNone(prohlizec.duvod_stopu(200, "Matriky Třeboň, kniha 12"))
        self.assertIsNone(prohlizec.duvod_stopu(404, ""))

    def test_snimek_jen_do_pracovni(self):
        self.assertTrue(prohlizec.cesta_snimku("pracovni/x.png", "/tmp/projekt").replace("\\", "/").endswith("/tmp/projekt/pracovni/x.png"))
        for spatne in ("../x.png", "pracovni/x.txt", "x.png", "pracovni/../x.png", "/etc/x.png"):
            with self.assertRaises(ValueError, msg=spatne):
                prohlizec.cesta_snimku(spatne, "/tmp/projekt")


class Akce(Zaklad):
    def otevri(self, st, url="https://digi.ceskearchivy.cz/x", stranka=None, ted=1000.0, **args):
        s = stranka or Stranka()
        host = prohlizec.host_z_url(url)
        out = prohlizec.akce("otevri", dict(url=url, **args), s, st, host, ted, spi=self.spi)
        return s, out

    def test_otevri_zapise_relaci_a_pauza_se_dodrzi(self):
        st = {}
        self.otevri(st)
        self.assertEqual((st["host"], st["posledni"], len(st["otevreni"])), (TREBON, 1000.0, 1))
        self.assertEqual(self.cekani, [])
        self.otevri(st, ted=1001.0)                                         # druhá akce za 1 s: čeká 4 s
        self.assertEqual(self.cekani, [4.0])
        self.otevri(st, ted=1100.0, listovani=True)
        self.assertEqual(self.cekani, [4.0])                                # po 100 s už nečeká

    def test_listovani_ceka_10_s(self):
        st = {}
        self.otevri(st)
        self.otevri(st, ted=1002.0, listovani=True)
        self.assertEqual(self.cekani, [8.0])

    def test_jen_portaly_ze_zakaz_a_jeden_archiv(self):
        with self.assertRaises(prohlizec.Stop) as cm:
            self.otevri({}, url="https://aron.vychodoceskearchivy.cz/x")
        self.assertEqual(cm.exception.kod, 2)
        st = {}
        self.otevri(st)
        with self.assertRaises(prohlizec.Stop) as cm:
            self.otevri(st, url="https://www.mza.cz/actapublica/")
        self.assertIn("stop", str(cm.exception))

    def test_403_zastavi_archiv_i_pro_dalsi_akce(self):
        st = {}
        with self.assertRaises(prohlizec.Stop) as cm:
            self.otevri(st, stranka=Stranka(status=403))
        self.assertEqual(cm.exception.kod, 4)
        self.assertIsNotNone(prohlizec.web_zastaven(TREBON))                 # zapsáno do brzdy (slusne)
        with self.assertRaises(prohlizec.Stop) as cm:
            self.otevri(st, ted=5000.0)
        self.assertEqual(cm.exception.kod, 4)

    def test_captcha_v_textu_zastavi(self):
        with self.assertRaises(prohlizec.Stop) as cm:
            self.otevri({}, stranka=Stranka(text="Are you a robot? CAPTCHA"))
        self.assertEqual(cm.exception.kod, 4)

    def test_prihlaseni_vrati_ukol_cloveku_bez_stopu(self):
        with self.assertRaises(prohlizec.Stop) as cm:
            self.otevri({}, stranka=Stranka(text="Přihlaste se prosím"))
        self.assertEqual(cm.exception.kod, 5)
        self.assertIsNone(prohlizec.web_zastaven(TREBON))

    def test_strop_otevreni_za_hodinu_zastavi_smycku(self):
        st = {"host": TREBON, "posledni": 0, "otevreni": [999.0] * 120}
        with self.assertRaises(prohlizec.Stop) as cm:
            self.otevri(st)
        self.assertIn("strop", str(cm.exception))

    def test_text_je_bez_pauzy_a_nemeni_relaci(self):
        st = {"host": TREBON, "posledni": 1000.0}
        out = prohlizec.akce("text", {}, Stranka(text="obsah"), st, TREBON, 1000.5, spi=self.spi)
        self.assertEqual((out, self.cekani, st["posledni"]), ("obsah", [], 1000.0))

    def test_klik_pis_snimek(self):
        st = {"host": TREBON, "posledni": 0}
        s = Stranka()
        prohlizec.akce("klik", {"selektor": "#hledat"}, s, st, TREBON, 100.0, spi=self.spi)
        prohlizec.akce("pis", {"selektor": "#q", "text": "Vzorová"}, s, st, TREBON, 200.0, spi=self.spi)
        prohlizec.akce("snimek", {"soubor": "pracovni/vysledky/s.png"}, s, st, TREBON, 300.0, spi=self.spi)
        self.assertEqual([v[0] for v in s.volani], ["click", "fill", "screenshot"])
        with self.assertRaises(ValueError):
            prohlizec.akce("snimek", {"soubor": "../ven.png"}, s, st, TREBON, 400.0, spi=self.spi)


class Rozhrani(unittest.TestCase):
    def test_stav_vypise_prostredi_bez_site(self):
        r = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "prohlizec.py"), "stav"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        for k in ("playwright", "edge", "relace", "napoveda"):
            self.assertIn(k, d)

    def test_akce_bez_relace_se_odmitne(self):
        r = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "prohlizec.py"), "otevri", "https://digi.ceskearchivy.cz/"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 2)
        self.assertIn("start", r.stderr)


class Dokumentace(unittest.TestCase):
    """Prohlížeč spouští nástroj sám: uživatel nic nespouští ani nenastavuje; postup je v portaly.md a v instalaci."""
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[3]

    def cti(self, rel):
        return (self.repo / rel).read_text(encoding="utf-8")

    def test_portaly_a_instalace(self):
        self.assertIn("tools/prohlizec.py", self.cti("skills/rodokmen/reference/portaly.md"))
        i = self.cti("skills/rodokmen/reference/instalace.md")
        self.assertIn("python -m pip install --user playwright", i)
        self.assertIn("prohlizec.py stav", i)


if __name__ == "__main__":
    unittest.main()
