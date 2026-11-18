"""tools/brana.py (Fáze D, Q-D1, Q-D4): strukturní brána po aktualizaci verze skillu v projektu, bez sítě a bez prohlížeče. Spustí kontroly
dat a kontrolu sestavených stránek; výsledek zelená / červená / nepokryto a soubor pracovni/brana.json. Rozhraní: příkazová řádka nad
dočasným projektem z ukázky se sestavenými stránkami (jednoduché HTML) nebo bez nich. Bez sítě."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

CISTA = "<!doctype html><html><body><h1>Rodokmen</h1><p>Jan Novák, narozen 1890.</p></body></html>"


class Brana(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.assertEqual(novy_projekt(self.p, "--ukazka").returncode, 0)

    def tearDown(self):
        self._tmp.cleanup()

    def web(self, html=CISTA, pristup=None):
        d = self.p / "web" / "dist" / ("_p/" + pristup if pristup else "")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html, encoding="utf-8")

    def brana(self, *args):
        return spust(self.p, "brana.py", *args, check=False)

    def marker(self):
        f = self.p / "pracovni" / "brana.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def test_zelena_zapise_znacku_s_verzi(self):
        self.web()
        r = self.brana()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = self.marker()
        self.assertEqual(m["vysledek"], "zelena")
        self.assertEqual(m["verze"], (self.p / ".skill_verze").read_text(encoding="utf-8").strip())
        self.assertIn("otisk_dat", m)
        self.assertIn("cas", m)

    def test_cervena_u_procesniho_textu_a_prepise_starou_zelenou(self):
        self.web()
        self.assertEqual(self.brana().returncode, 0)
        self.web("<html><body><p>Ověřil pomocník, úkol U-0013.</p></body></html>")
        r = self.brana()
        self.assertEqual(r.returncode, 1)
        self.assertIn("index.html", r.stdout + r.stderr)
        self.assertEqual(self.marker()["vysledek"], "cervena")

    def test_site_json_se_pouzije_jen_pro_vse_ne_pro_pristupy(self):
        """Rody a barvy ze site.json (poslední export) platí jen pro verzi „vse“; přístup má vlastní rody (jako test_jednotnost_web)."""
        site = self.p / "web" / "src" / "data" / "site.json"
        site.parent.mkdir(parents=True, exist_ok=True)
        site.write_text(json.dumps({"lines": {"rod-a": {"k": 8, "slug": "rod-a", "name": "Rodové A", "color": "#111111"}}}), encoding="utf-8")
        znacka = '<span class="rod-znak"><span class="dot" style="background: {b}"></span><a href="/rod/{s}/">{n}</a></span>'
        stranka = "<!doctype html><html><body><p>{z}</p></body></html>"
        vse = self.p / "web" / "dist" / "_p" / "vse"
        pristup = self.p / "web" / "dist" / "_p" / "pristup"
        for d in (vse, pristup):
            d.mkdir(parents=True, exist_ok=True)
        (vse / "index.html").write_text(stranka.format(z=znacka.format(b="#111111", s="rod-a", n="Rodové A")), encoding="utf-8")
        (pristup / "index.html").write_text(stranka.format(z=znacka.format(b="#222222", s="rod-b", n="Rodové B")), encoding="utf-8")
        r = self.brana()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        (vse / "index.html").write_text(stranka.format(z=znacka.format(b="#999999", s="rod-a", n="Rodové A")), encoding="utf-8")
        r = self.brana()
        self.assertEqual(r.returncode, 1)
        self.assertIn("barva značky", r.stdout)

    def test_cervena_u_rozbitych_dat(self):
        self.web()
        (self.p / "data" / "denik.jsonl").write_text('{"id": 1, "datum": "nedatum"}\n{rozbitý řádek\n', encoding="utf-8")
        r = self.brana("--json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["vysledek"], "cervena")
        self.assertTrue(any(k["krok"] == "denik" and not k["ok"] for k in d["kroky"]))

    def test_nepokryto_bez_sestaveneho_webu(self):
        r = self.brana()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotEqual((self.marker() or {}).get("vysledek"), "zelena")

    def test_kazdy_pristup_zvlast(self):
        self.web(pristup="a")
        self.web("<html><body>pomocník N3e</body></html>", pristup="b")
        r = self.brana()
        self.assertEqual(r.returncode, 1)
        self.assertIn("_p", r.stdout + r.stderr)
        self.assertIn("b", r.stdout + r.stderr)

    def test_json_ma_kroky(self):
        self.web()
        d = json.loads(self.brana("--json").stdout)
        self.assertEqual(d["vysledek"], "zelena")
        self.assertEqual({k["krok"] for k in d["kroky"]}, {"kontrola", "denik", "otazky", "web"})

    def test_data_nemeni(self):
        self.web()
        pred = {str(f): f.read_bytes() for f in (self.p / "data").rglob("*") if f.is_file()}
        self.brana()
        self.assertEqual(pred, {str(f): f.read_bytes() for f in (self.p / "data").rglob("*") if f.is_file()})


if __name__ == "__main__":
    unittest.main()
