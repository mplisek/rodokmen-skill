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
        for cislo in (9, 10):
            self.assertTrue(z[cislo].get("k_rucni_kontrole"), cislo)
        md = self.denik("vykresli").stdout
        self.assertNotIn("| 9 |", md)
        self.assertNotIn("| 10 |", md)
        protokol = (self.p / "pracovni" / "migrace_denik.md").read_text(encoding="utf-8")
        self.assertIn("9", protokol)
        self.assertIn("10", protokol)

    def test_migruj_neprepise_existujici_denik(self):
        self.migruj()
        pred = (self.p / "data" / "denik.jsonl").read_bytes()
        r = self.denik("migruj")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((self.p / "data" / "denik.jsonl").read_bytes(), pred)
        self.assertEqual(self.denik("migruj", "--znovu").returncode, 0)                    # výslovně lze


if __name__ == "__main__":
    unittest.main()
