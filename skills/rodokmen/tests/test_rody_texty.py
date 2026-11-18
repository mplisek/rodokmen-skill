"""Rody jako vazba obsahu (fáze 3): zajímavosti, karty na úvodu, příběhy, otázky, prameny, úvod, varování a chyba odkazu.

Testy vycházejí ze zadání, ne z implementace. Obsah se k rodu váže zakladatelem = číslem osoby v rodokmenu správce
(rod 8 = Jan Novák, rod 12 = Antonín Dvořák). Přístup „Otcova větev“ má kořen 2 (jeho rodiči jsou správcovy 4, 5,
tedy v jeho přímé linii je zakladatel 8, ne 12), „Matčina větev“ má kořen 3 (zakladatel 12, ne 8).
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import novy_projekt, spust  # noqa: E402

# názvy rodů z pohledu přístupů (všechna čísla 8–15, aby nezáleželo na tom, pod kterým číslem zakladatel padne)
JMENA_A = {str(k): [f"Alfovci{k}", f"Popis alfovců {k}"] for k in range(8, 16)}
JMENA_B = {str(k): [f"Betovci{k}", f"Popis betovců {k}"] for k in range(8, 16)}
NAZVY_A = {v[0] for v in JMENA_A.values()}
NAZVY_B = {v[0] for v in JMENA_B.values()}

PRISTUPY = [
    {"nazev": "Otcova větev", "koren": [2], "odpoved": "odp-a", "rody": JMENA_A,
     "uvod": {"odstavce": ["Úvod přístupu A."]}},
    {"nazev": "Matčina větev", "koren": [3], "odpoved": "odp-b", "rody": JMENA_B,
     "uvod": {"odstavce": ["Úvod přístupu B."]}},
    # s právem texty a bez názvů rodů (varování)
    {"nazev": "Otcova větev texty", "koren": [2], "odpoved": "odp-c",
     "prava": {"soukrome": False, "texty": True, "poznamky": False},
     "uvod": {"odstavce": ["Úvod přístupu C."]}},
]
ID = {"a": "otcova-vetev", "b": "matcina-vetev", "c": "otcova-vetev-texty"}


def zajimavosti(r8, r12):
    return f"""# Zajímavosti

## Zajímavost obecná
Text bez rodu ZOBEC.

## Zajímavost osmičky
Rod: [Novákové](/rod/{r8}/)

Text osmičky ZOSM s odkazem na rod [Novákové](/rod/{r8}/).

## Zajímavost dvanáctky
<!-- rody: 12 -->
Text dvanáctky ZDVA.

## Zajímavost obou
<!-- rody: 8, 12 -->
Text obou ZOBA.
"""


def pribeh(titulek, rod_radek, telo):
    radky = ["---", f"title: {titulek}", f"lead: Perex {titulek}"]
    if rod_radek:
        radky.append(rod_radek)
    radky += ["---", "", telo, ""]
    return "\n".join(radky)


OTAZKY = """# Otázky pro rodinu

Úvodní věta.

## Obecně
- Obecná otázka OOBEC

## Novákové
- Otázka Nováků ONOV
- Otázka jen pro devítku ODEV <!-- rody: 9 -->
- Otázka jen pro dvanáctku ODVA <!-- rody: 12 -->

## Pokorní
- Otázka Pokorných OPOK

## Dvořákové
- Otázka Dvořáků ODVO
- Otázka jen pro osmičku OOSM <!-- rody: 8 -->
"""

DOTAZY = """# Prameny mimo online matriky

## SOA Zámrsk
- **Obecný pramen** PARCH

## Novákové
- **Pramen Nováků** PNOV

## Dvořákové
- **Pramen Dvořáků** PDVO
"""


class RodyTexty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls._tmp.name) / "ukazka"
        r = novy_projekt(cls.p, "--ukazka")
        assert r.returncode == 0, r.stdout + r.stderr
        cls.data = cls.p / "data"
        cls.web_json = cls.data / "web.json"
        # správce: slugy rodů a osob
        spust(cls.p, "export_web.py")
        cls.vse = cls.nacti_site()
        cls.r8 = cls.slug_rodu(cls.vse, 8)
        cls.r12 = cls.slug_rodu(cls.vse, 12)
        cls.os8 = cls.slug_osoby(cls.vse, 8)     # Jan Novák – jen v přímé linii A
        cls.os12 = cls.slug_osoby(cls.vse, 12)   # Antonín Dvořák – jen v přímé linii B
        cfg = json.loads(cls.web_json.read_text(encoding="utf-8"))
        cfg["pristupy"] = PRISTUPY
        cfg["prihlaseni"]["odpoved"] = "vse-odpoved"
        cfg["prihlaseni"]["adresa"] = "https://rod.example"
        cfg["uvod"]["odstavce"] = ["Společný úvod SU."]
        cfg["zajimavosti_na_uvodu"] = [
            {"nadpis": "Karta obecná", "text": "Karta bez rodu."},
            {"nadpis": "Karta osmičky", "text": "Karta rodu 8.", "rody": [8]},
            {"nadpis": "Karta dvanáctky", "text": "Karta rodu 12.", "rody": [12]},
        ]
        cls.cfg = cfg
        cls.zapis_cfg(cfg)
        cls.zapis_obsah()
        cls.admin_r = spust(cls.p, "export_web.py", check=False)
        cls.admin = cls.sber()
        cls.vystup, cls.v = {}, {}
        for klic, pid in ID.items():
            r = spust(cls.p, "export_web.py", "--pristup", pid, check=False)
            cls.vystup[klic] = r
            cls.v[klic] = cls.sber()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # --- pomůcky ---
    @classmethod
    def zapis_cfg(cls, cfg):
        cls.web_json.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def zapis_obsah(cls):
        (cls.data / "zajimavosti.md").write_text(zajimavosti(cls.r8, cls.r12), encoding="utf-8")
        (cls.data / "otazky_pro_rodinu.md").write_text(OTAZKY, encoding="utf-8")
        (cls.data / "archivni_dotazy.md").write_text(DOTAZY, encoding="utf-8")
        pr = cls.data / "pribehy"
        pr.mkdir(exist_ok=True)
        for f in pr.glob("*.md"):
            f.unlink()
        (pr / "pribeh-osm.md").write_text(pribeh(
            "Příběh osmičky", "rod: 8",
            f"Text PBOSM, [Jan Novák](/osoba/{cls.os8}/), rod [Novákové](/rod/{cls.r8}/)."), encoding="utf-8")
        (pr / "pribeh-dvanact.md").write_text(pribeh(
            "Příběh dvanáctky", "rod: 12", f"Text PBDVA, rod [Dvořákové](/rod/{cls.r12}/)."), encoding="utf-8")
        (pr / "pribeh-oba.md").write_text(pribeh(
            "Příběh obou", "rody: 8, 12", f"Text PBOBA, rody [A](/rod/{cls.r8}/) a [B](/rod/{cls.r12}/)."),
            encoding="utf-8")
        (pr / "pribeh-obecny.md").write_text(pribeh("Příběh obecný", None, "Text PBOBEC bez rodu."),
                                              encoding="utf-8")

    @classmethod
    def sber(cls):
        """Načte výstup posledního exportu (site.json a vygenerované texty)."""
        web = cls.p / "web" / "src"
        gen = web / "generated"

        def cti(cesta):
            return cesta.read_text(encoding="utf-8") if cesta.exists() else ""
        pribehy_json = gen / "pribehy.json"
        return dict(
            site=json.loads((web / "data" / "site.json").read_text(encoding="utf-8")),
            zaj=cti(gen / "zajimavosti.md"), otazky=cti(gen / "otazky.md"), dotazy=cti(gen / "dotazy.md"),
            pribehy=json.loads(pribehy_json.read_text(encoding="utf-8")) if pribehy_json.exists() else [],
            pribeh_md={f.stem: f.read_text(encoding="utf-8") for f in (gen / "pribehy").glob("*.md")}
            if (gen / "pribehy").exists() else {})

    @classmethod
    def nacti_site(cls):
        return json.loads((cls.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))

    @staticmethod
    def slug_rodu(site, k):
        for slug, ln in site["lines"].items():
            if ln["k"] == k:
                return slug
        raise AssertionError(f"rod {k} není v site.lines")

    @staticmethod
    def slug_osoby(site, k):
        for slug, p in site["people"].items():
            if p["k"] == k:
                return slug
        raise AssertionError(f"osoba {k} není v site.people")

    def tituly(self, klic):
        return {s["title"] for s in self.v[klic]["pribehy"]}

    def vsechny_texty(self, klic):
        v = self.v[klic]
        return "\n".join([v["zaj"], v["otazky"], v["dotazy"], *v["pribeh_md"].values()])

    # --- 0. základ ---
    def test_exporty_prosly(self):
        for klic, r in self.vystup.items():
            self.assertEqual(r.returncode, 0, f"{klic}: {r.stdout}\n{r.stderr}")

    def test_spravce_vidi_vsechno(self):
        self.assertEqual(self.admin_r.returncode, 0, self.admin_r.stdout + self.admin_r.stderr)
        a = self.admin
        for znacka in ("ZOBEC", "ZOSM", "ZDVA", "ZOBA"):
            self.assertIn(znacka, a["zaj"])
        for znacka in ("OOBEC", "ONOV", "ODEV", "ODVA", "OPOK", "ODVO", "OOSM"):
            self.assertIn(znacka, a["otazky"])
        for znacka in ("PARCH", "PNOV", "PDVO"):
            self.assertIn(znacka, a["dotazy"])
        self.assertEqual(len(a["pribehy"]), 4)

    # --- 1. zajímavosti ---
    def test_zajimavosti_bez_prava_texty(self):
        a, b = self.v["a"]["zaj"], self.v["b"]["zaj"]
        # oddíl bez rodu vidí všichni, i bez práva texty
        self.assertIn("ZOBEC", a)
        self.assertIn("ZOBEC", b)
        # oddíl s rodem jen přístup se zakladatelem v přímé linii
        self.assertIn("ZOSM", a)
        self.assertNotIn("ZDVA", a)
        self.assertIn("ZDVA", b)
        self.assertNotIn("ZOSM", b)
        # oddíl s víc rody vidí oba
        self.assertIn("ZOBA", a)
        self.assertIn("ZOBA", b)

    def test_zajimavosti_s_pravem_texty_stejne(self):
        c = self.v["c"]["zaj"]
        self.assertIn("ZOBEC", c)
        self.assertIn("ZOSM", c)
        self.assertNotIn("ZDVA", c)

    def test_zajimavosti_radek_rod_je_prepsan_na_rod_pristupu(self):
        a = self.v["a"]
        self.assertNotRegex(a["zaj"], r"(?m)^Rod:\s*\[")
        m = re.search(r'<span class="rod-znak"><span class="dot" style="background:([^"]+)"></span>'
                      r'<a href="/rod/([^/"]+)/">([^<]+)</a></span>', a["zaj"])
        self.assertIsNotNone(m, a["zaj"])
        barva, slug, nazev = m.groups()
        self.assertIn(slug, a["site"]["lines"])
        self.assertEqual(a["site"]["lines"][slug]["color"], barva.strip().rstrip(";"))
        self.assertIn(nazev, NAZVY_A)

    def test_zajimavosti_odkazy_na_rody_jsou_funkcni(self):
        for klic in ID:
            lines = self.v[klic]["site"]["lines"]
            for text in (self.v[klic]["zaj"], *self.v[klic]["pribeh_md"].values()):
                for slug in re.findall(r"/rod/([^/\s\"')]+)/", text):
                    self.assertIn(slug, lines, f"{klic}: nefunkční odkaz na rod {slug}")

    def test_zajimavosti_nazvy_rodu_spravce_nezustaly(self):
        # názvy z pohledu správce („Novákové“) se v textu přístupu s vlastními názvy rodů neobjeví jako rod
        self.assertNotIn(f"/rod/{self.r8}/", self.v["a"]["zaj"] + "".join(self.v["a"]["pribeh_md"].values())
                         ) if self.r8 not in self.v["a"]["site"]["lines"] else None
        self.assertNotIn("[Novákové]", self.v["a"]["zaj"])

    # --- 2. karty na úvodu ---
    def test_karty_na_uvodu(self):
        def nadpisy(klic):
            return [k["nadpis"] for k in self.v[klic]["site"]["config"]["zajimavosti_na_uvodu"]]
        # karta bez rodu je obecný text – jen s právem texty (recenze: dřív ji přístup bez textů neviděl)
        self.assertEqual(nadpisy("a"), ["Karta osmičky"])
        self.assertEqual(nadpisy("b"), ["Karta dvanáctky"])
        self.assertEqual(nadpisy("c"), ["Karta obecná", "Karta osmičky"])

    def test_karty_rody_jsou_slugy_rodu_pristupu(self):
        for klic in ("a", "b"):
            site = self.v[klic]["site"]
            karty = {k["nadpis"]: k for k in site["config"]["zajimavosti_na_uvodu"]}
            karta = karty["Karta osmičky" if klic == "a" else "Karta dvanáctky"]
            self.assertEqual(len(karta["rody"]), 1)
            self.assertIn(karta["rody"][0], site["lines"])
            self.assertNotIn("Karta obecná", karty)

    # --- 3. příběhy ---
    def test_pribehy_bez_prava_texty(self):
        self.assertEqual(self.tituly("a"), {"Příběh osmičky", "Příběh obou"})
        self.assertEqual(self.tituly("b"), {"Příběh dvanáctky", "Příběh obou"})

    def test_pribehy_s_pravem_texty_pridaji_obecny(self):
        self.assertEqual(self.tituly("c"), {"Příběh osmičky", "Příběh obou", "Příběh obecný"})

    def test_pribehy_rod_je_cislo_rodu_pristupu(self):
        for klic, nazvy in (("a", NAZVY_A), ("b", NAZVY_B)):
            v = self.v[klic]
            for s in v["pribehy"]:
                self.assertIn(s["rod"], range(8, 16), s)
                self.assertEqual(s["rody"][0], s["rod"], s)
                for n in s["rody"]:
                    radek = [ln for ln in v["site"]["lines"].values() if ln["k"] == n]
                    self.assertEqual(len(radek), 1, (klic, n))
                    self.assertIn(radek[0]["name"], nazvy)
            obou = next(s for s in v["pribehy"] if s["title"] == "Příběh obou")
            self.assertEqual(len(obou["rody"]), 1, "oba rody 8 a 12 patří v pohledu přístupu k jednomu rodu")

    def test_pribehy_frontmatter_ma_rod_pristupu(self):
        for klic in ("a", "b"):
            v = self.v[klic]
            for s in v["pribehy"]:
                md = v["pribeh_md"][s["slug"]]
                m = re.match(r"\A---\r?\n(.*?)\r?\n---", md, re.S)
                self.assertIsNotNone(m, md)
                rod = re.search(r"(?m)^rod:\s*(\d+)\s*$", m.group(1))
                self.assertIsNotNone(rod, m.group(1))
                self.assertEqual(int(rod.group(1)), s["rod"])
                self.assertNotRegex(m.group(1), r"(?m)^rody:")

    def test_pribeh_neviditelny_se_nevygeneruje(self):
        self.assertNotIn("PBDVA", "".join(self.v["a"]["pribeh_md"].values()))
        self.assertNotIn("PBOSM", "".join(self.v["b"]["pribeh_md"].values()))
        self.assertNotIn("PBOBEC", "".join(self.v["a"]["pribeh_md"].values()))
        self.assertIn("PBOBEC", "".join(self.v["c"]["pribeh_md"].values()))

    # --- 4. otázky pro rodinu ---
    def test_otazky_bez_prava_texty(self):
        a, b = self.v["a"]["otazky"], self.v["b"]["otazky"]
        # oddíl bez rodu („Obecně“) jen s právem texty
        self.assertNotIn("OOBEC", a)
        self.assertNotIn("Obecně", a)
        self.assertNotIn("OOBEC", b)
        # oddíl rodu jen se zakladatelem v přímé linii
        self.assertIn("ONOV", a)
        self.assertNotIn("ONOV", b)
        self.assertNotIn("ODVO", a)
        self.assertIn("ODVO", b)
        # rod 9 (Pokorní) je u otcovy větve, ne u matčiny
        self.assertIn("OPOK", a)
        self.assertNotIn("OPOK", b)

    def test_otazky_odrazky_s_rody(self):
        a, b = self.v["a"]["otazky"], self.v["b"]["otazky"]
        self.assertIn("ODEV", a)
        self.assertNotIn("ODVA", a)
        self.assertNotIn("OOSM", b)
        self.assertNotIn("<!--", a + b)

    def test_otazky_s_pravem_texty_vidi_obecne(self):
        c = self.v["c"]["otazky"]
        self.assertIn("OOBEC", c)
        self.assertIn("ONOV", c)
        self.assertNotIn("ODVO", c)

    def test_otazky_nadpis_je_prepsan_na_rod_pristupu(self):
        for klic, nazvy in (("a", NAZVY_A), ("b", NAZVY_B)):
            otazky = self.v[klic]["otazky"]
            self.assertNotRegex(otazky, r"(?m)^##\s+(Novákové|Pokorní|Dvořákové)\s*$")
            nadpisy = re.findall(r'(?m)^##\s+.*?class="rod-znak".*?<a href="/rod/([^/"]+)/">([^<]+)</a>', otazky)
            self.assertTrue(nadpisy, otazky)
            for slug, nazev in nadpisy:
                self.assertIn(slug, self.v[klic]["site"]["lines"])
                self.assertIn(nazev, nazvy)

    def test_otazky_prazdne_oddily_se_vynechaji(self):
        # Hrubí/Pokorní bez obsahu pro přístup nemají nadpis; B nevidí oddíl Pokorní ani Nováků
        b = self.v["b"]["otazky"]
        self.assertEqual(len(re.findall(r"(?m)^##\s", b)), 1, b)

    # --- 5. prameny ---
    def test_dotazy_bez_prava_texty(self):
        a, b = self.v["a"]["dotazy"], self.v["b"]["dotazy"]
        self.assertNotIn("PARCH", a + b)
        self.assertNotIn("SOA Zámrsk", a + b)
        self.assertIn("PNOV", a)
        self.assertNotIn("PDVO", a)
        self.assertIn("PDVO", b)
        self.assertNotIn("PNOV", b)

    def test_dotazy_s_pravem_texty(self):
        c = self.v["c"]["dotazy"]
        self.assertIn("PARCH", c)
        self.assertIn("PNOV", c)
        self.assertNotIn("PDVO", c)

    def test_dotazy_nadpis_je_rod_pristupu(self):
        a = self.v["a"]["dotazy"]
        self.assertIn('class="rod-znak"', a)
        self.assertNotRegex(a, r"(?m)^##\s+Novákové\s*$")

    # --- 6. úvod ---
    def test_uvod_bez_prava_texty_jen_odstavce_pristupu(self):
        self.assertEqual(self.v["a"]["site"]["config"]["uvod"]["odstavce"], ["Úvod přístupu A."])
        self.assertEqual(self.v["b"]["site"]["config"]["uvod"]["odstavce"], ["Úvod přístupu B."])

    def test_uvod_s_pravem_texty_spolecny_a_pak_pristupu(self):
        self.assertEqual(self.v["c"]["site"]["config"]["uvod"]["odstavce"], ["Společný úvod SU.", "Úvod přístupu C."])

    # --- 7. názvy rodů a varování ---
    def test_lines_maji_nazvy_pristupu(self):
        for klic, nazvy in (("a", NAZVY_A), ("b", NAZVY_B)):
            lines = self.v[klic]["site"]["lines"]
            self.assertEqual({ln["name"] for ln in lines.values()}, nazvy)
            for slug, ln in lines.items():
                self.assertEqual(ln["slug"], slug)
                self.assertIn("color", ln)

    def test_chybejici_nazvy_rodu_davaji_varovani(self):
        r = self.vystup["c"]
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        vystup = r.stdout + r.stderr
        self.assertIn("POZOR", vystup)
        self.assertIn(ID["c"], vystup)

    def test_uplne_nazvy_rodu_nedavaji_varovani_o_rodech(self):
        for klic in ("a", "b"):
            vystup = self.vystup[klic].stdout + self.vystup[klic].stderr
            self.assertNotRegex(vystup, rf"POZOR[^\n]*{ID[klic]}", vystup)

    # --- 8. odkazy na osoby ---
    def test_odkaz_na_neviditelnou_osobu_je_chyba(self):
        site_a = self.v["a"]["site"]
        self.assertNotIn(self.os12, site_a["people"], "předpoklad testu: A osobu 12 nevidí")
        puvodni = (self.data / "zajimavosti.md").read_text(encoding="utf-8")
        (self.data / "zajimavosti.md").write_text(
            puvodni + f"\n## Zajímavost se špatným odkazem\n<!-- rody: 8 -->\nVíc u [cizí osoby](/osoba/{self.os12}/).\n",
            encoding="utf-8")
        try:
            r = spust(self.p, "export_web.py", "--pristup", ID["a"], check=False)
            rs = spust(self.p, "export_web.py", check=False)
        finally:
            (self.data / "zajimavosti.md").write_text(puvodni, encoding="utf-8")
        vystup = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, vystup)
        self.assertIn("CHYBA", vystup)
        self.assertIn(self.os12, vystup)
        # správce osobu vidí, případně jen varování
        self.assertEqual(rs.returncode, 0, rs.stdout + rs.stderr)

    def test_odkaz_na_viditelnou_osobu_je_v_poradku(self):
        # příběh osmičky odkazuje na Jana Nováka (rod 8), kterého A vidí
        self.assertIn(self.os8, self.v["a"]["site"]["people"])
        self.assertIn(f"/osoba/{self.os8}/", self.v["a"]["pribeh_md"]["pribeh-osm"])


if __name__ == "__main__":
    unittest.main()
