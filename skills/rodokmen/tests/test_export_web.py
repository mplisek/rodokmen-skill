"""export_web.py: soukromí žijících, příbuzní z RODINA s vlastními stránkami, PARTNERI, vějíře pro libovolnou osobu.

Integrační část založí ukázkový projekt (novy_projekt.py --ukazka), doplní do data/osoby.py pár osob a spustí export.
Síť ani Node.js nepotřebuje; ImageMagick je volitelný (bez něj se výřezy kopírují bez rámečků).
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt, spust  # noqa: E402

sys.path.insert(0, str(TOOLS))
import export_web as ew  # noqa: E402


class CistéFunkce(unittest.TestCase):
    def test_years(self):
        self.assertEqual(ew.years("1892–1970"), "1892–1970")
        self.assertEqual(ew.years("* 1980"), "* 1980")
        self.assertEqual(ew.years("† 1879"), "† 1879")
        self.assertEqual(ew.years("asi 1855 – ?"), "≈1855")
        self.assertEqual(ew.years(""), "")

    def test_zijici(self):
        h = ew.HRANICE_ZIJICI
        self.assertTrue(ew.zijici("* 1980"))
        self.assertTrue(ew.zijici("1850–1920", "Žijící – údaje jen základní."))   # poznámka má přednost
        self.assertTrue(ew.zijici(f"* {h}"))
        self.assertFalse(ew.zijici(f"* {h - 1}"))                              # starší než 100 let
        self.assertFalse(ew.zijici("1930–2001"))                               # úmrtí známé
        self.assertFalse(ew.zijici("* 1950", "", ["† 2001 Praha"]))             # úmrtí ve faktech
        self.assertFalse(ew.zijici("† 1990"))
        self.assertFalse(ew.zijici("? – 1960"))
        self.assertFalse(ew.zijici(""))

    def test_slugify(self):
        self.assertEqual(ew.slugify("Marie Nováková 1892"), "marie-novakova-1892")


DOPLNEK = '''
RODINA["anicka-novakova"] = dict(n="Anička Nováková", y="† 1879", sex="F", otec=16, matka=17, st="doc")
RODINA["jana-nova"] = dict(n="Jana Nová", y="* 1982", sex="F", st="fam", f=["* 1982 Pardubice"])
RODINA["tomas-novak"] = dict(n="Tomáš Novák", y="* 2010", sex="M", otec=1, matka="jana-nova", st="fam",
                             f=["* 2010 Pardubice"], note="Syn výchozí osoby.")
PARTNERI = [
    dict(a=16, b="anna-hruba", rok=1890, misto="Holice", konec="ovdověl 1900"),
    dict(a=1, b="jana-nova", rok=2008, misto="Pardubice"),
]
SIDE += [
    dict(k=8, n="Josef Novák", v="bratr", y="1885–1886", t="Zemřel jako dítě."),
    dict(k=8, n="Karel Novák", v="nevlastní bratr", y="* 1902", t="Z druhého manželství otce."),
    dict(k=16, n="František Novák", v="syn", y="1888", t="Zemřel po narození."),
]
'''


class ExportUkazky(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.projekt = Path(cls._tmp.name) / "ukazka"
        r = novy_projekt(cls.projekt, "--ukazka")
        assert r.returncode == 0, r.stdout + r.stderr
        with open(cls.projekt / "data" / "osoby.py", "a", encoding="utf-8", newline="\n") as f:
            f.write(DOPLNEK)
        cls.vystup = spust(cls.projekt, "export_web.py").stdout
        cls.site = json.loads((cls.projekt / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        cls.lide = cls.site["people"]
        cls.podle_k = {p["k"]: p for p in cls.lide.values() if not p.get("extra")}
        cls.koren = cls.lide[cls.site["root"]]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def slug(self, jmeno):
        hit = [s for s, p in self.lide.items() if p["name"] == jmeno]
        self.assertEqual(len(hit), 1, f"{jmeno}: {hit}")
        return hit[0]

    # --- soukromí ---
    def test_zijici_predci_jen_zakladni_udaje(self):
        for k in (1, 2, 3):   # ukázka: výchozí osoba a rodiče jsou žijící
            p = self.podle_k[k]
            self.assertEqual((p["facts"], p["records"], p["note"]), ([], [], ew.ZIJICI_POZN), p["name"])
        self.assertIn("soukromí:", self.vystup)

    def test_zijici_z_rodiny_a_jejich_snatek_bez_udaju(self):
        tomas = self.lide[self.slug("Tomáš Novák")]
        self.assertEqual((tomas["facts"], tomas["note"]), ([], ew.ZIJICI_POZN))
        jana = self.slug("Jana Nová")
        self.assertIn(dict(slug=jana, text=""), self.koren["partners"])   # bez roku a místa sňatku

    def test_zijici_na_casove_ose_jen_rok_narozeni(self):
        osa = {r["slug"]: r for r in self.site["timeline"]["rows"]}
        for sl, p in self.lide.items():
            if "Žijící" in (p.get("note") or "") and sl in osa:
                r = osa[sl]
                self.assertIsNone(r["marriage"], sl)
                self.assertIsNone(r["death"], sl)
                self.assertRegex(r["birth"]["text"] if r["birth"] else "1900", r"^\d{0,4}$", sl)
        skryti = {sl for sl, p in self.lide.items() if "Žijící" in (p.get("note") or "")}
        for v in self.site["timeline"]["warnings"]:
            self.assertFalse(set(v["people"]) & skryti)

    def test_zijici_nejsou_na_mape(self):
        skryti = {s for s, p in self.lide.items() if p["note"] == ew.ZIJICI_POZN or p.get("extra")}
        na_mape = {s for m in self.site["places"] for skupina in m["lines"] for s in skupina["people"]}
        self.assertFalse(na_mape & skryti)

    # --- příbuzní z RODINA ---
    def test_rodina_ma_vlastni_stranky_a_vztah(self):
        marie = self.lide["marie-novakova-1892"]
        self.assertTrue(marie["extra"])
        self.assertEqual(marie["father"], self.podle_k[16]["slug"])
        self.assertTrue(marie["rel"].startswith("sestra osoby"))
        self.assertTrue(self.lide[self.slug("Tomáš Novák")]["rel"].startswith("syn osoby"))

    def test_rodina_ma_rodice_pro_graf_predku_a_mista(self):
        marie = self.lide["marie-novakova-1892"]
        self.assertEqual(marie["parents"], [self.podle_k[16]["slug"], self.podle_k[17]["slug"]])
        self.assertEqual(self.podle_k[8]["parents"], [self.podle_k[16]["slug"], self.podle_k[17]["slug"]])
        self.assertIn("holice", {m["slug"] for m in marie.get("places", [])})   # odkaz na místo i mimo přímou linii

    def test_adresa_s_rokem_umrti(self):
        self.assertIn("anicka-novakova-1879", self.lide)   # jediný rok v y je úmrtí – patří do adresy

    def test_deti_sourozenci_a_rodina(self):
        jan = self.podle_k[8]
        sour = {c["slug"] for c in jan["siblings"]}
        self.assertTrue({"marie-novakova-1892", "anicka-novakova-1879"} <= sour)
        deti16 = [c for c in self.podle_k[16]["kids"]]
        self.assertTrue(any(c["slug"] == jan["slug"] and c["line"] for c in deti16))
        rodina = self.site["families"][jan["family"]]
        self.assertTrue({jan["slug"], "marie-novakova-1892", "anicka-novakova-1879"} <= set(rodina["children"]))
        self.assertFalse({e.get("slug") for e in rodina["side"]} & set(rodina["children"]))   # s vlastní stránkou ne podruhé
        self.assertEqual([e["name"] for e in rodina["side"]], ["Josef Novák", "Karel Novák"])   # jen poznámky ze SIDE
        self.assertIn(self.slug("Tomáš Novák"), {c["slug"] for c in self.koren["kids"]})

    def test_dalsi_deti_ze_side(self):
        # SIDE: bratr dítěte v linii a syn předka = další děti předka; nevlastní bratr ne (nevíme, po kom je)
        deti = self.podle_k[16]["sideKids"]
        self.assertEqual([c["name"] for c in deti], ["František Novák", "Josef Novák"])
        self.assertEqual({c["slug"] for c in deti}, {self.podle_k[16]["slug"], self.podle_k[8]["slug"]})
        self.assertTrue(all(c["anchor"].startswith("pribuzny-") for c in deti))
        self.assertEqual(self.podle_k[8]["sideKids"], [])

    def test_partneri_s_podrobnostmi(self):
        anna = self.slug("Anna (příjmení neznámé)")
        self.assertIn(dict(slug=anna, text="sňatek 1890, Holice, ovdověl 1900"), self.podle_k[16]["partners"])
        self.assertIn(dict(slug=self.podle_k[16]["slug"], text="sňatek 1890, Holice, ovdověl 1900"), self.lide[anna]["partners"])

    def test_predci_bez_pribuznych(self):
        self.assertEqual(self.site["stats"]["ancestors"], sum(1 for p in self.lide.values() if p["k"] > 1))

    # --- vějíře ---
    def test_vejir_pro_libovolnou_osobu(self):
        gen = self.projekt / "web" / "src" / "generated"
        self.assertEqual(self.koren["fan"], "/vejir/")
        self.assertEqual(self.lide["marie-novakova-1892"]["fan"], "/vejir/marie-novakova-1892/")
        svg = (gen / "fan_marie-novakova-1892.svg").read_text(encoding="utf-8")
        self.assertIn("<title>Marie Nováková 1892–1970</title>", svg)          # uprostřed ona
        self.assertIn(f"<title>{self.podle_k[16]['name']} ", svg)               # nad ní otec
        self.assertEqual((gen / f"fan_{self.koren['slug']}.svg").read_bytes(), (gen / "fan.svg").read_bytes())
        self.assertIsNone(self.lide["josef-hruby-1855"]["fan"])         # bez známých rodičů vějíř není


@unittest.skipUnless(ew.magick_bin(), "chybí ImageMagick")
class ObrazkyProWeb(unittest.TestCase):
    """Export obrázky do webu zmenší a překóduje (méně přenesených dat) a upravené verze si pamatuje v pracovni/."""

    def test_zmenseni_preklad_a_mezipamet(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ukazka"
            self.assertEqual(novy_projekt(p, "--ukazka").returncode, 0)
            klic = "ukazka_krest_jan_novak_1890"
            # větší výřez než 1400 px, ať je co zmenšovat (výřezy ukázky jsou malé)
            for sub in ("vyrezy", "zdroje"):
                subprocess.run([ew.magick_bin(), str(p / sub / f"{klic}.jpg"), "-resize", "2400x2400", "-quality", "95",
                                str(p / sub / f"{klic}.jpg")], check=True)
            spust(p, "export_web.py")
            web_img, zdroj = p / "web" / "public" / "img" / f"{klic}.jpg", p / "web" / "public" / "zdroje" / f"{klic}.jpg"
            self.assertLessEqual(max(ew.size(str(web_img))), 1400)                       # na stránce nejvýš 1400 px
            self.assertEqual(max(ew.size(str(zdroj))), 2400)                             # plné rozlišení zůstane
            self.assertLess(zdroj.stat().st_size, (p / "zdroje" / f"{klic}.jpg").stat().st_size)   # jen překódované
            hotovy = p / "pracovni" / ".web_obrazky" / "img" / f"{klic}.jpg"
            self.assertTrue(hotovy.exists())
            cas = hotovy.stat().st_mtime
            r = spust(p, "export_web.py")                                              # podruhé z mezipaměti
            self.assertIn("zkopírováno 0 obrázků", r.stdout)
            self.assertEqual(hotovy.stat().st_mtime, cas)


class Poznamky(unittest.TestCase):
    """Web bez přístupů: „poznamky“ ve web.json zapne tlačítko a vyrobí funkci; vypnutí ji smaže."""

    def test_zapnout_a_vypnout(self):
        with tempfile.TemporaryDirectory() as tmp:
            projekt = Path(tmp) / "p"
            self.assertEqual(novy_projekt(projekt, "--ukazka").returncode, 0)
            cfg_path = projekt / "data" / "web.json"
            fce = projekt / "web" / "netlify" / "functions" / "poznamky.mjs"
            site = projekt / "web" / "src" / "data" / "site.json"
            spust(projekt, "export_web.py")
            self.assertFalse(fce.exists())
            self.assertFalse(json.loads(site.read_text(encoding="utf-8"))["config"]["poznamky"])
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg_path.write_text(json.dumps(dict(cfg, poznamky=True), ensure_ascii=False), encoding="utf-8")
            spust(projekt, "export_web.py")
            self.assertTrue(json.loads(site.read_text(encoding="utf-8"))["config"]["poznamky"])
            self.assertIn('"id": "vse"', fce.read_text(encoding="utf-8"))
            self.assertNotIn(cfg["prihlaseni"]["odpoved"], fce.read_text(encoding="utf-8"))
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
            spust(projekt, "export_web.py")
            self.assertFalse(fce.exists())


class Kontrola(unittest.TestCase):
    def test_rodina_a_partneri(self):
        with tempfile.TemporaryDirectory() as tmp:
            projekt = Path(tmp) / "p"
            self.assertEqual(novy_projekt(projekt, "--ukazka").returncode, 0)
            osoby = projekt / "data" / "osoby.py"
            with open(osoby, "a", encoding="utf-8", newline="\n") as f:
                f.write(DOPLNEK)
            r = spust(projekt, "kontrola.py", check=False)
            self.assertEqual(r.returncode, 0, r.stdout)        # otec=1 (dítě výchozí osoby) je v pořádku
            with open(osoby, "a", encoding="utf-8", newline="\n") as f:
                f.write('PARTNERI.append(dict(a=16, b="nikdo"))\nRODINA["sam"] = dict(n="Sám Samotný", sex="M")\n')
            r = spust(projekt, "kontrola.py", check=False)
            self.assertEqual(r.returncode, 1)
            self.assertIn("PARTNERI 16 × 'nikdo'", r.stdout)
            self.assertIn("upozornění: RODINA 'sam'", r.stdout)   # nespojená osoba = jen upozornění

    def test_partneri_bez_rodiny_a_citace_u_kazde_osoby(self):
        with tempfile.TemporaryDirectory() as tmp:
            projekt = Path(tmp) / "p"
            self.assertEqual(novy_projekt(projekt, "--ukazka").returncode, 0)
            osoby = projekt / "data" / "osoby.py"
            puvodni = osoby.read_text(encoding="utf-8")
            with open(osoby, "a", encoding="utf-8", newline="\n") as f:   # 0.7.0-fork.1 tu padal (UnboundLocalError)
                f.write("RODINA = {}\nPARTNERI = [dict(a=2, b=3)]\n")
            r = spust(projekt, "kontrola.py", check=False)
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(r.returncode, 0, r.stdout)
            osoby.write_text(puvodni + 'RODINA = {"a": dict(n="Anna", sex="F", otec=1, r=["neni-takovy"]),'
                             ' "b": dict(n="Bedřich", sex="M", otec=1)}\nPARTNERI = []\n', encoding="utf-8")
            r = spust(projekt, "kontrola.py", check=False)
            self.assertEqual(r.returncode, 1)
            self.assertIn("RODINA 'a' (Anna) cituje neexistující zápis 'neni-takovy'", r.stdout)


if __name__ == "__main__":
    unittest.main()
