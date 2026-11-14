"""reference/nocni_rezim.md: rozhodovací postup směrování úkolů, struktura úkolu k rozhodnutí a nejisté čtení (analyza/navrh-router-uloh.md, S-002, S-003).
Test hlídá, že pravidla v dokumentaci jsou a že odpovídají nástroji (povinná pole úkolu k rozhodnutí)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import fronta  # noqa: E402

REF = Path(__file__).resolve().parents[1] / "reference" / "nocni_rezim.md"


class NocniRezimPravidla(unittest.TestCase):
    def setUp(self):
        self.t = REF.read_text(encoding="utf-8")

    def test_rozhodovaci_postup_ma_vsechny_vetve(self):
        for s in ("už v datech", "čtením online zdrojů", "k bádání", "dotaz", "pro rodinu", "k rozhodnutí"):
            self.assertIn(s, self.t, s)

    def test_rodina_jen_3_4_generace_a_zajimavosti(self):
        self.assertIn("nejvýš 3–4 generace", self.t)
        self.assertIn("zajímavosti", self.t)
        self.assertIn("`fam`", self.t)                       # rodina je důkaz nižšího stupně, nepřebije matriku

    def test_vecne_otazky_nejsou_rozhodnuti(self):
        self.assertIn("nepatří", self.t.lower())
        self.assertIn("věcné otázky", self.t)
        self.assertIn("přečíst znovu", self.t)

    def test_pole_ukolu_k_rozhodnuti_odpovidaji_nastroji(self):
        for pole in fronta.POVINNA_ROZHODNUTI:
            self.assertIn(pole, self.t, pole)

    def test_nejiste_cteni_nejde_primo_do_rozhodnuti(self):
        i = self.t.index("## Nejisté čtení")
        odstavec = self.t[i:i + 1200]
        self.assertIn("druhé čtení naslepo", odstavec)
        self.assertNotIn("potvrdit, zamítnout, nebo přečíst znovu", odstavec)

    def test_router_je_popsany(self):
        for s in ("ukoly_vstup.md", "fronta.py smeruj", "Definice hotového", "fronta.py rozdel", "fronta.py zaparkuj", "stav:čeká"):
            self.assertIn(s, self.t, s)

    def test_selhani_portalu_je_popsano(self):
        for s in ("fronta.py selhani", "za dvě noci", "o víkendu", "v pracovní době", "jedno rozhodnutí za portál", "opakovani"):
            self.assertIn(s, self.t, s)

    def test_sablona_ma_vstupni_frontu_a_orchestrator_router(self):
        repo = Path(__file__).resolve().parents[3]
        self.assertTrue((repo / "skills/rodokmen/template/data/ukoly_vstup.md").is_file())
        o = (repo / "agents/orchestrator.md").read_text(encoding="utf-8")
        for s in ("fronta.py smeruj", "fronta.py selhani", "ukoly_vstup.md", "Definice hotového"):
            self.assertIn(s, o, s)

    def test_historie_a_metadata_cteni_jsou_popsane(self):
        for s in ("ukoly_historie.jsonl", "fronta.py historie", "fronta.py znovu", "--ukol", "--snimky", "--nastroj", "--denik"):
            self.assertIn(s, self.t, s)
        repo = Path(__file__).resolve().parents[3]
        o = (repo / "agents/orchestrator.md").read_text(encoding="utf-8")
        for s in ("--ukol", "--snimky", "fronta.py znovu"):
            self.assertIn(s, o, s)

    def test_rozpocet_a_identita_id_jsou_popsane(self):
        for s in ("rozpocet", "fronta.py plan", "fronta.py kalibrace", "Schváleno:", "stav:probíhá", "neuvolní", "levné napřed"):
            self.assertIn(s, self.t, s)
        repo = Path(__file__).resolve().parents[3]
        o = (repo / "agents/orchestrator.md").read_text(encoding="utf-8")
        for s in ("fronta.py plan", "XL", "budget"):
            self.assertIn(s, o, s)
        import json
        rezim = json.loads((repo / "skills/rodokmen/template/data/rezim.json").read_text(encoding="utf-8"))
        self.assertIn("rozpocet", rezim)

    def test_cekani_odesilani_a_typy_jsou_popsane(self):
        for s in ("fronta.py cekajici", "fronta.py odeslano", "--uzivatel", "odpoved_dnu", "Odesílá vždy člověk", "ukoly_na_skill.md",
                  "poznamky_pro_skill.md"):
            self.assertIn(s, self.t, s)
        self.assertNotIn("`skill` (úprava skillu), `test`, `údržba`", self.t)             # typy zrušeny
        repo = Path(__file__).resolve().parents[3]
        o = (repo / "agents/orchestrator.md").read_text(encoding="utf-8")
        for s in ("fronta.py cekajici", "odeslano", "poznamky_pro_skill.md"):
            self.assertIn(s, o, s)


if __name__ == "__main__":
    unittest.main()
