"""denik.py migruj / overit-migraci: převod dosavadního research_log.md na denik.jsonl bez ztráty informací (ADR 0002).
Rozhraní: příkazy denik.py nad vzorkem ve tvaru skutečného deníku (vymyšlená data): normální řádky, řádek se 6 sloupci,
řádek bez klíče výsledku, procesní údaje v textu, dlouhý výsledek a starší varianty hodnot výsledku."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

DLOUHY = ("Křest nalezen na sn. 31 pod č. 29. " + "Otec Josef Novák, domkář z Dolní Lhoty čp. 12, matka Marie rozená Králová, kmotři obvyklí. " * 6).strip()

LOG = f"""# Výzkumný deník

Konvence: každý řádek = jedno hledání, i neúspěšné.

| # | datum | zdroj | rozsah | hledáno | výsledek | citace |
|---|---|---|---|---|---|---|
| 1 | 2026-10-30 | ARON, Dolní Lhota, narození 1850–1860, sign. 1234 (apu aaaa1111) | sn. 20–35 | křest Jana Nováka * 1852 | **nalezeno** sn. 31, č. 29: Jan, otec Josef Novák, čp. 12. | „Jan, syn Josefa Nováka“ |
| 2 | 2026-10-30 | ARON, Dolní Lhota, oddaní 1870–1890, sign. 1235 | sn. 5, 40 | sňatek Jana Nováka × Marie Králová | **nenalezeno** v oddaných 1870–1880 (sn. 5–60 prohlédnuto). | – |
| 3 | 2026-10-31 | (stopa při čtení) ARON sign. 1234, sn. 340 | zahlédnuto | – | zjevně související výskyt příjmení Králová ve Lhotě čp. 3 | – |
| 4 | 2026-11-01 | ARON, Horní Lhota, úmrtí 1880–1900, sign. 1236 | sn. 100–120 | úmrtí Josefa Nováka | **nalezeno (ověřeno)** sn. 110, † 3. 5. 1886. Pomocník N3e přečetl rok jako 1888, opraveno čtyři oči (U-0011). | „zemřel“ |
| 5 | 2026-11-02 | ARON, Dolní Lhota, narození 1850–1860, sign. 1234 | sn. 1–200 | křest sourozenců Jana Nováka | **potvrzeno** sn. 33, sourozenci Anna a Karel. | – |
| 6 | 2026-11-02 | SOA Kutná Hora | sn. 12 | křest Marie Králové | **nedočteno** zápis je na okraji, nutný lepší snímek (pracovni/kh/12.jpg). | – |
| 7 | 2026-11-03 | ARON, Dolní Lhota, narození 1860–1870 | sn. 3 | křest Anny Novákové | **nenalezeno / nečitelné** vybledlé písmo. | – |
| 8 | 2026-11-03 | ARON, Dolní Lhota, narození 1870–1880, sign. 1237 | sn. 8 | křest Karla Nováka | **nalezeno** {DLOUHY} | – |
| 9 | 2026-11-04 | ARON, Dolní Lhota | sn. 9 | křest Josefa Nováka | nalezeno sn. 9 bez tučného klíče | – |
| 10 | 2026-11-04 | ARON, Dolní Lhota | křest Evy Novákové | **nalezeno** sn. 10 | – |
| 11 | 2026-11-05 | rodina, telefonát | – | datum úmrtí Marie | **nalezeno** † 1901, podle rodiny. | – |
| 12 | 2026-11-06 | Pomocník (sonnet): ARON, Horní Lhota, úmrtí 1880–1900, sign. 1236 | sn. 100–120 | úmrtí Anny Novákové | **kandidát z rejstříku** † 1890, nutné ověřit v matrice. | – |
| 13 | 2026-11-06 | ARON, Horní Lhota, oddaní 1860–1880 | sn. 1–50 | sňatek Karla Nováka | **zatím nenalezeno** v oddaných. | – |
| 14 | 2026-11-07 | ARON, Dolní Lhota, narození 1840–1850 | sn. 7 | křest Evy Králové | **ověřeno:** sn. 7, Eva dcera Jana Krále. | – |
| 15 | 2026-11-07 | ARON, Dolní Lhota, narození 1840–1850 | sn. 8 | křest Petra Králového | **Králové** nejasné slovo v záhlaví. | – |
| 16 | 2026-11-08 | ARON, Dolní Lhota, narození 1840–1850, sn. 7 | křest Evy Králové (12) | Královi (12, 13) | **nalezeno** sn. 7, Eva dcera Jana Krále. | – |
| 17 | 2026-11-08 | ARON, Dolní Lhota, oddaní 1860–1880, sn. 1–50 | Novákovi, Králové (70, 71) | 70, 71 | **Nenalezeno**: sňatek Jana Nováka × Evy Králové ani v rejstříku. | ARON 5 |
| 18 | 2026-11-09 | ARON, Dolní Lhota, narození 1840–1850, sn. 3–9 | křest Petra Králového | **nenalezeno** v sn. 3–9 | – |
| 19 | 2026-11-09 | ARON, Dolní Lhota, úmrtí 1890–1900 | děti Josefa Nováka 1887–1909 | ověření čtení pomocníka | **Ověřeno:** sn. 12, Josefa † 27. 7. 1887. | – |
| 20 | 2026-11-09 | ARON, Chlum, oddaní, sn. 5 | křest a sňatek Marie Vzorové | **křest nalezen**, sňatek nenalezen v rejstříku. | – |
| 22 | 2026-11-10 | ARON, Dolní Lhota, úmrtí 1880–1890 | sn. 4 | úmrtí Anny Novákové | **PŘEČTENO**: Anna † 2. 5. 1884, dcera Josefa. | – |
| 23 | 2026-11-10 | ARON, Dolní Lhota, úmrtí 1880–1890 | sn. 5–9 | úmrtí Evy Králové | **Rozkoš POTVRZENO (negativní)**: v sn. 5–9 žádná Eva. | – |
| 24 | 2026-11-10 | ARON, Dolní Lhota, úmrtí 1880–1890 | sn. 9 | úmrtí Petra Nováka | **Stopy (ověřeno)**: úmrtí Petra † 1884 v Horní Lhotě. | – |
| 25 | 2026-11-10 | ARON, Dolní Lhota, úmrtí 1880–1890 | sn. 9 | křest Karla Králového | **Vyloučeno**: kandidát Karel * 1850 je jiný, matka Anna. | – |
| 21 | 2026-11-10 | ARON, Dolní Lhota, oddaní 1860–1880, sn. 1–50 | Vzorové a Příkladovi (76–79) | – | **Nenalezeno**: křest Josefa Vzora ~1796 v rejstříku. | – |
"""


class Migrace(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        (self.p / "tools").mkdir()
        (self.p / "data").mkdir()
        (self.p / "pracovni").mkdir()
        for f in ("denik.py", "zaznamy_store.py", "soubory.py"):
            shutil.copy(TOOLS / f, self.p / "tools" / f)
        (self.p / "data" / "research_log.md").write_text(LOG, encoding="utf-8")
        self.src_radky = [r for r in LOG.splitlines() if r.startswith("| ") and not r.startswith("| #")]

    def tearDown(self):
        self._tmp.cleanup()

    def denik(self, *args):
        return subprocess.run([sys.executable, "-I", "-X", "utf8", str(self.p / "tools" / "denik.py"), *args],
                              cwd=self.p, capture_output=True, text=True, encoding="utf-8")

    def zaznamy(self):
        return {z["id"]: z for z in map(json.loads, (self.p / "data" / "denik.jsonl").read_text(encoding="utf-8").splitlines())}

    def migruj(self):
        r = self.denik("migruj")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return self.zaznamy()

    def test_kazdy_radek_ma_zaznam_a_puvodni_text_se_shoduje(self):
        z = self.migruj()
        self.assertEqual(len(z), len(self.src_radky))            # řádek se 6 sloupci se neztratí
        for radek in self.src_radky:
            cislo = int(radek.split("|")[1])
            self.assertEqual(z[cislo]["puvodni"], radek)          # doslova
        self.assertEqual(self.denik("overit-migraci").returncode, 0)

    def test_overit_migraci_selze_kdyz_radek_chybi_nebo_je_zmenen(self):
        self.migruj()
        cesta = self.p / "data" / "denik.jsonl"
        radky = cesta.read_text(encoding="utf-8").splitlines()
        cesta.write_text("\n".join(radky[1:]) + "\n", encoding="utf-8")              # chybí záznam 1
        r = self.denik("overit-migraci")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("1", r.stdout + r.stderr)
        z = json.loads(radky[1])
        z["puvodni"] = z["puvodni"].replace("nenalezeno", "NEnalezeno")
        cesta.write_text("\n".join([radky[0], json.dumps(z, ensure_ascii=False)] + radky[2:]) + "\n", encoding="utf-8")
        self.assertNotEqual(self.denik("overit-migraci").returncode, 0)                # změněný původní text

    def test_mapovani_vysledku(self):
        z = self.migruj()
        self.assertEqual((z[1]["vysledek"], z[1].get("overeno")), ("nalezeno", None))
        self.assertEqual(z[2]["vysledek"], "nenalezeno")
        self.assertEqual((z[4]["vysledek"], z[4]["overeno"]), ("nalezeno", True))         # nalezeno (ověřeno)
        self.assertEqual((z[5]["vysledek"], z[5]["overeno"]), ("nalezeno", True))         # potvrzeno
        self.assertEqual(z[6]["vysledek"], "částečně")                                    # nedočteno
        self.assertEqual(z[7]["vysledek"], "nečitelné")                                   # nenalezeno / nečitelné
        self.assertEqual(z[1]["zdroj"]["typ"], "archiv")
        self.assertEqual(z[3]["zdroj"]["typ"], "stopa")
        self.assertEqual(z[11]["zdroj"]["typ"], "rodina")

    def test_pripona_pomocnika_pred_zdrojem_se_odebere_a_zdroj_zustane(self):
        z = self.migruj()[12]
        self.assertTrue(z["zdroj"]["text"].startswith("ARON, Horní Lhota"), z["zdroj"])
        self.assertNotIn("Pomocník", z["zdroj"]["text"])
        self.assertTrue(any("sonnet" in x for x in z["proces"]))
        self.assertFalse(z.get("k_rucni_kontrole"))

    def test_volnejsi_klice_vysledku_se_mapuji_odhadem_a_neznama_jdou_rucne(self):
        z = self.migruj()
        self.assertEqual(z[12]["vysledek"], "částečně")                                  # kandidát z rejstříku
        self.assertEqual(z[13]["vysledek"], "nenalezeno")                                # zatím nenalezeno
        self.assertEqual((z[14]["vysledek"], z[14]["overeno"]), ("nalezeno", True))      # ověřeno:
        self.assertTrue(z[15].get("k_rucni_kontrole"))                                   # klíč není hodnota výsledku
        self.assertTrue(z[12].get("uprava_automaticky"))                                 # odhad mapování je v protokolu

    def test_zdroj_rozsah_hledano_a_nalez_se_prenesou(self):
        z = self.migruj()
        self.assertEqual(z[1]["rozsah"], "sn. 20–35")
        self.assertEqual(z[1]["hledano"], "křest Jana Nováka * 1852")
        self.assertIn("Jan, otec Josef Novák, čp. 12", z[1]["nalez"])
        self.assertEqual(z[1]["citace"], "„Jan, syn Josefa Nováka“")
        self.assertNotIn("citace", z[2])                                                  # „–“ znamená prázdné

    def test_dlouhy_vysledek_se_rozdeli_a_nic_se_neztrati(self):
        z = self.migruj()[8]
        self.assertLessEqual(len(z["nalez"]), 400)
        slova = DLOUHY.split()
        spolu = z["nalez"] + " " + z.get("poznamka", "")
        for slovo in slova:
            self.assertIn(slovo, spolu)

    def test_procesni_udaje_jdou_do_proces_a_ne_na_web(self):
        z = self.migruj()
        self.assertTrue(z[4]["proces"])                                                    # zachyceno v datech
        md = self.denik("vykresli").stdout
        for zakazane in ("N3e", "U-0011", "čtyři oči", "Pomocník", "pracovni/"):
            self.assertNotIn(zakazane, md)
        self.assertIn("sn. 110", md)                                                       # věcná část zůstala
        self.assertTrue(z[4].get("uprava_automaticky"))                                    # k případné kontrole v protokolu
        self.assertEqual(self.denik("over").returncode, 0)

    def test_nestandardni_radky_jsou_k_rucni_kontrole_a_ne_na_web(self):
        z = self.migruj()
        for cislo in (9, 15):
            self.assertTrue(z[cislo].get("k_rucni_kontrole"), cislo)
        md = self.denik("vykresli").stdout
        self.assertNotIn("| 9 |", md)
        self.assertNotIn("| 15 |", md)
        protokol = (self.p / "pracovni" / "migrace_denik.md").read_text(encoding="utf-8")
        self.assertIn("- 9:", protokol)
        self.assertIn("- 15:", protokol)

    # ---- sloupce, které se ve starém deníku používaly jinak (zjištěno na skutečném deníku: 163 z 300 řádků)
    def test_radek_bez_sloupce_rozsah_se_nepovazuje_za_chybny(self):
        z = self.migruj()
        self.assertFalse(z[10].get("k_rucni_kontrole"), z[10])
        self.assertEqual((z[10]["hledano"], z[10]["vysledek"], z[10]["rozsah"]), ("křest Evy Novákové", "nalezeno", ""))
        self.assertEqual(z[10]["puvodni"], self.src_radky[9])
        n = z[18]                                    # záporný výsledek: rozsah je ve zdroji
        self.assertFalse(n.get("k_rucni_kontrole"), n)
        self.assertEqual((n["hledano"], n["vysledek"]), ("křest Petra Králového", "nenalezeno"))
        self.assertEqual(n["rozsah"], n["zdroj"]["text"])

    def test_sloupec_hledano_s_cisly_osob_je_kontext_a_hledano_je_ve_sloupci_rozsah(self):
        z = self.migruj()
        a = z[16]
        self.assertEqual((a["hledano"], a["rozsah"], a["vysledek"]), ("křest Evy Králové", "", "nalezeno"))
        self.assertFalse(a.get("k_rucni_kontrole"), a)
        self.assertTrue(a.get("uprava_automaticky"))
        b = z[17]                                    # kontext jsou rody s čísly osob, hledání jen z textu výsledku
        self.assertEqual((b["hledano"], b["vysledek"]), ("Novákovi, Králové", "nenalezeno"))
        self.assertEqual(b["rozsah"], b["zdroj"]["text"])
        self.assertFalse(b.get("k_rucni_kontrole"), b)
        c = z[21]                                    # sloupec hledáno prázdný, rod s čísly je ve sloupci rozsah
        self.assertEqual((c["hledano"], c["vysledek"]), ("Vzorové a Příkladovi", "nenalezeno"))
        self.assertFalse(c.get("k_rucni_kontrole"), c)

    def test_cisla_osob_se_nedostanou_do_tabulky_na_webu(self):
        self.migruj()
        md = self.denik("vykresli").stdout
        self.assertNotIn("(12, 13)", md)
        self.assertNotIn("70, 71", md)
        self.assertNotIn("(76–79)", md)
        self.assertEqual(self.denik("over").returncode, 0)

    def test_hledano_zbyle_prazdne_po_odebrani_procesu_se_vezme_ze_sloupce_rozsah(self):
        z = self.migruj()[19]
        self.assertEqual((z["hledano"], z["rozsah"]), ("děti Josefa Nováka 1887–1909", ""))
        self.assertTrue(any("pomocník" in x for x in z["proces"]))
        self.assertFalse(z.get("k_rucni_kontrole"), z)

    def test_smisena_zjisteni_jsou_castecne(self):
        self.assertEqual(self.migruj()[20]["vysledek"], "částečně")

    def test_dalsi_vyslovne_klice_vysledku(self):
        z = self.migruj()
        self.assertEqual((z[22]["vysledek"], z[22].get("overeno")), ("nalezeno", True))    # PŘEČTENO
        self.assertEqual(z[23]["vysledek"], "nenalezeno")                                  # POTVRZENO (negativní)
        self.assertEqual(z[24]["vysledek"], "částečně")                                    # Stopy (ověřeno)
        self.assertEqual(z[25]["vysledek"], "vyvráceno")                                   # Vyloučeno
        for i in (22, 23, 24, 25):
            self.assertTrue(z[i].get("uprava_automaticky"), i)                             # odhad je v protokolu

    def test_bezne_radky_se_nezmeni(self):
        z = self.migruj()
        self.assertEqual((z[1]["rozsah"], z[1]["hledano"]), ("sn. 20–35", "křest Jana Nováka * 1852"))
        self.assertEqual((z[2]["rozsah"], z[2]["hledano"]), ("sn. 5, 40", "sňatek Jana Nováka × Marie Králová"))

    def test_deleni_dlouheho_textu_nerezne_za_zkratkou_ani_cislem_dne(self):
        sys.path.insert(0, str(TOOLS))
        import denik
        text = ("Josef Vzorný (22), syn Františka, domkáře z Horní Lhoty č. 12. Narodil se 5. 4. 1828 v Dolní Lhotě č. 9, a Kateřiny "
                "rozené Příkladové. ") * 8
        for max_ in (300, 360, 400):
            cast, zbytek = denik.rozdel(text, max_)
            self.assertLessEqual(len(cast), max_)
            self.assertEqual((cast + " " + zbytek).split(), text.split())                     # nic se neztratí
            self.assertNotRegex(cast, r"(?:\bč|\bčp|\bsn|\bstr|\d)\.?$")   # nekončí zkratkou ani číslem dne
            self.assertTrue(cast.endswith((".", "!", "?", ";")) or zbytek == "", cast[-30:])  # řez na konci věty

    def test_migruj_neprepise_existujici_denik(self):
        self.migruj()
        pred = (self.p / "data" / "denik.jsonl").read_bytes()
        r = self.denik("migruj")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((self.p / "data" / "denik.jsonl").read_bytes(), pred)
        self.assertEqual(self.denik("migruj", "--znovu").returncode, 0)                    # výslovně lze


if __name__ == "__main__":
    unittest.main()
