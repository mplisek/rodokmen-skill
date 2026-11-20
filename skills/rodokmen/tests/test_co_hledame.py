"""Stránka „Co hledáme“: ISSUES s osobou a stavem, otázky pro rodinu podle rodů, kontrola tvaru (kontrola.py)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS, novy_projekt, spust  # noqa: E402

sys.path.insert(0, str(TOOLS))
import export_web as ew  # noqa: E402

LINES = {"novakove": dict(k=8, slug="novakove", name="Novákové"), "kralove": dict(k=10, slug="kralove", name="Králové"),
         "hrubi": dict(k=11, slug="hrubi", name="Hrubí")}


class Funkce(unittest.TestCase):
    def test_issue_rows(self):
        r = ew.issue_rows([dict(k=16, otazka="A?", stav="hypotéza", text="t"),
                           ("B?", "Vyřešeno: už víme"), ("C?", "bez stavu"), "D?"],
                          lambda k: f"s{k}", lambda k: "novakove" if k == 16 else None)
        self.assertEqual(r[0], dict(title="A?", text="t", stav="hypotéza", person="s16", rod="novakove"))
        self.assertEqual((r[1]["stav"], r[1]["text"], r[1]["person"]), ("vyřešeno", "už víme", None))
        self.assertEqual((r[2]["stav"], r[2]["text"]), ("otevřené", "bez stavu"))
        self.assertEqual(r[3]["title"], "D?")

    def test_druh_zapisu_rejstrik_je_priznak(self):
        self.assertEqual(ew.druh_zapisu(dict(druh="Z", rejstrik=True)), ("Z", True))
        self.assertEqual(ew.druh_zapisu(dict(druh="I", klic="libice_index_umrti_x", nazev="Rejstřík zemřelých")), ("Z", True))
        self.assertEqual(ew.druh_zapisu(dict(druh="I", klic="libice_index_krtu_x", nazev="Rejstřík křtů")), ("N", True))
        self.assertEqual(ew.druh_zapisu(dict(druh="O")), ("O", False))
        self.assertEqual(ew.druh_zapisu(dict(druh="X")), ("J", False))

    def test_hvezdicka_narozeni_nerozbije_tucne(self):
        self.assertEqual(ew.hvezdicky_narozeni("- **Jan Novák (* 1890):** křest"), "- **Jan Novák (\\* 1890):** křest")
        self.assertEqual(ew.hvezdicky_narozeni("* bod seznamu\n**1890**"), "* bod seznamu\n**1890**")

    def test_rod_nadpisu_podle_kmene(self):
        self.assertEqual(ew.rod_nadpisu("Novákovi (Holice)", LINES)["k"], 8)
        self.assertEqual(ew.rod_nadpisu("Hrubí", LINES)["k"], 11)
        self.assertIsNone(ew.rod_nadpisu("Dokumenty doma", LINES))

    def test_podle_rodu(self):
        md = "Úvod.\n\n## Hrubí\n- h\n\n## Dokumenty doma\n- d\n\n## Novákové\n- n\n"
        self.assertEqual(ew.podle_rodu(md, LINES), "Úvod.\n\n## Dokumenty doma\n- d\n\n## Novákové\n- n\n## Hrubí\n- h\n\n")


class Ukazka(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.p = Path(cls._tmp.name) / "ukazka"
        assert novy_projekt(cls.p, "--ukazka").returncode == 0

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_export_a_kontrola(self):
        self.assertIn("Vše v pořádku", spust(self.p, "kontrola.py").stdout)
        spust(self.p, "export_web.py")
        site = json.loads((self.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        jakub = next(i for i in site["issues"] if i["title"].startswith("Odkud přišel Jakub"))
        self.assertEqual((jakub["rod"], jakub["stav"]), ("novakove", "otevřené"))
        self.assertTrue(site["people"][jakub["person"]]["name"].startswith("Jakub Novák"))
        otazky = (self.p / "web" / "src" / "generated" / "otazky.md").read_text(encoding="utf-8")
        # nadpisy oddílů rodů jsou znak rodu (barevný kruh + odkaz na rod), obecné oddíly nahoře
        poradi = [otazky.index(h) for h in ("## Dokumenty doma", '/rod/novakove/">Novákové', '/rod/hrubi/">Hrubí',
                                            '/rod/kucerovi/">Kučerovi')]
        self.assertEqual(poradi, sorted(poradi))

    def test_struktura_stranky_po_rodech_a_archivech(self):
        """Rozhodnutí uživatele 16. 11. 2026: otázky pro rodinu a otevřené otázky jeden kontejner na rod (Obecné první, pak rody
        podle čísla), prameny podle archivů s rodem u položky."""
        spust(self.p, "export_web.py")
        site = json.loads((self.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        h = site["hledame"]
        poradi = {s: l["k"] for s, l in site["lines"].items()}
        for cast in ("rodina", "otevrene"):
            rody = [c["rod"] for c in h[cast]]
            self.assertTrue(rody, cast)
            self.assertEqual(len(rody), len(set(rody)), cast)                        # jeden kontejner na rod
            if None in rody:
                self.assertEqual(rody[0], None, cast)                                # Obecné první
            ciselne = [poradi[r] for r in rody if r is not None]
            self.assertEqual(ciselne, sorted(ciselne), cast)
        obecne = h["rodina"][0]
        self.assertIsNone(obecne["rod"])
        self.assertIn("Dokumenty doma", [s["nadpis"] for s in obecne["skupiny"]])
        self.assertTrue(all(isinstance(p, str) and p for c in h["rodina"] for s in c["skupiny"] for p in s["polozky"]))
        self.assertTrue(h["prameny"])
        self.assertTrue(all(a["archiv"] and a["polozky"] for a in h["prameny"]))
        self.assertTrue(any(p["rod"] in poradi for a in h["prameny"] for p in a["polozky"]))
        self.assertFalse(any("<!--" in p["html"] for a in h["prameny"] for p in a["polozky"]))
        for a in h["prameny"]:                     # rod je v záhlaví karty – v textu položky se neopakuje (20. 11. 2026)
            for p in a["polozky"]:
                if p["rod"]:
                    self.assertFalse(p["html"].startswith(f"<strong>{site['lines'][p['rod']]['name']}"), p["html"])
        stranka = (self.p / "web" / "src" / "pages" / "hledame.astro").read_text(encoding="utf-8")
        self.assertNotIn("grid2", stranka)         # bloky pod sebou, ne vedle sebe
        self.assertIn("c.polozky.map((i) => (\n          <RodBox", stranka)   # otevřené otázky: kontejner na otázku

    def test_zajimavosti_v_kontejneru_rodu(self):
        spust(self.p, "export_web.py")
        site = json.loads((self.p / "web" / "src" / "data" / "site.json").read_text(encoding="utf-8"))
        md = (self.p / "web" / "src" / "generated" / "zajimavosti.md").read_text(encoding="utf-8")
        barva = site["lines"]["novakove"]["color"]
        self.assertIn(f'<div class="card rod-box" data-rod="novakove" style="--c:{barva}">', md)
        self.assertEqual(md.count('class="card rod-box"'), md.count("\n## ") + md.startswith("## "))   # každá zajímavost v kontejneru

    def test_kontrola_hlida_tvar(self):
        d = self.p / "data"
        puvodni = {f: (d / f).read_text(encoding="utf-8") for f in ("otazky_pro_rodinu.md", "archivni_dotazy.md", "osoby.py")}
        try:
            (d / "otazky_pro_rodinu.md").write_text(puvodni["otazky_pro_rodinu.md"] + "\n## Sousedé\n- 3. ODPOVĚZENO 6. 11.\n",
                                                    encoding="utf-8")
            (d / "archivni_dotazy.md").write_text("# P\n\n## Jan Novák (zapsáno 2026-10-31)\n- křest\n", encoding="utf-8")
            (d / "osoby.py").write_text(puvodni["osoby.py"] + '\nISSUES.append(("Kdo?", "Libice, kniha 737"))\n'
                                        'ISSUES.append(dict(k=99999, otazka="X?", stav="nevim"))\n'
                                        'RODINA["mk"] = dict(n="Marie Králová (Nováková)", otec=16)\n', encoding="utf-8")
            out = spust(self.p, "kontrola.py", check=False).stdout
            for hlaska in ("„Sousedé“ není rod", "zodpovězenou položku", "zapsáno", "nevypadá jako archiv",
                           "převeď na dict", "stav „nevim“", "k=99999", "příjmení po sňatku „Nováková“"):
                self.assertIn(hlaska, out)
        finally:
            for f, t in puvodni.items():
                (d / f).write_text(t, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
