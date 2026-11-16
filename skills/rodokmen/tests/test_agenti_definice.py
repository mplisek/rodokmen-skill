"""Definice agentů v agents/ (Fáze C, Q-C1, 4.1–4.7 návrhu): povinná pole, povolené nástroje, orchestrátor bez zápisu a webu, anglicky,
kritérium dokončení, odkazy na existující pravidla a nástroje, jen počáteční sada 10 agentů. Test běží nad skutečnými soubory."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
AGENTI = REPO / "agents"
POCATECNI = {"orchestrator", "researcher", "browser-reader", "verifier", "upstream-sync", "test-runner", "failure-analyst", "fixer",
             "test-author", "committer"}
NASTROJE = {"Read", "Glob", "Grep", "Bash", "PowerShell", "Edit", "Write", "Agent", "WebFetch", "WebSearch", "Monitor"}
MODELY = {"haiku", "sonnet", "opus", "inherit"}
BEZ_PRAVIDEL = {"verifier"}   # čte naslepo jeden výřez; pravidla bádání nepotřebuje a start má být co nejmenší (E1)


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "chybí frontmatter"
    return {k: v.strip() for k, v in re.findall(r"(?m)^([A-Za-z-]+):\s*(.*)$", m.group(1))}


class DefiniceAgentu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.soubory = {p.stem: p for p in AGENTI.glob("*.md")}
        cls.texty = {k: p.read_text(encoding="utf-8") for k, p in cls.soubory.items()}
        cls.ids = set(re.findall(r"(?m)^## (R-[A-Z]+-\d{3})$",
                                 "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "skills/rodokmen-agents/rules").glob("*.md"))))

    def test_pocatecni_sada_je_presne_deset_agentu(self):
        self.assertEqual(set(self.soubory), POCATECNI)

    def test_povinna_pole(self):
        for jmeno, text in self.texty.items():
            fm = frontmatter(text)
            self.assertEqual(fm.get("name"), jmeno, jmeno)
            self.assertGreaterEqual(len(fm.get("description", "")), 30, jmeno)
            self.assertIn(fm.get("model"), MODELY, jmeno)
            self.assertTrue(fm.get("tools") or fm.get("disallowedTools"), jmeno)
            if jmeno not in BEZ_PRAVIDEL:
                self.assertIn("rodokmen-agents", fm.get("skills", ""), jmeno)

    def test_nastroje_jen_ze_seznamu(self):
        for jmeno, text in self.texty.items():
            fm = frontmatter(text)
            seznam = re.sub(r"\([^)]*\)", "", fm.get("tools") or fm["disallowedTools"])
            for n in re.split(r"\s*,\s*", seznam):
                self.assertIn(n.strip(), NASTROJE, f"{jmeno}: {n}")

    def test_orchestrator_nezapisuje_a_nema_web(self):
        fm = frontmatter(self.texty["orchestrator"])
        nastroje = {n.strip() for n in re.split(r"\s*,\s*", re.sub(r"\([^)]*\)", "", fm["tools"]))}
        self.assertFalse(nastroje & {"Edit", "WebFetch", "WebSearch", "PowerShell"}, nastroje)   # Write jen do pracovni/ (hlídá hook, E2)
        self.assertIn("Agent", nastroje)
        self.assertIn("Bash", nastroje)               # úzce hlídá hooks/hlidac_orchestratora.py
        povoleni = set(re.findall(r"Agent\(([^)]*)\)", fm["tools"]))
        self.assertTrue(povoleni, "Agent(...) musí vyjmenovat povolené podagenty")
        for p in re.split(r"\s*,\s*", ",".join(povoleni)):
            # agenti pluginu mají jméno s předponou pluginu (rodokmen:researcher); bez ní by seznam nic nepropustil („Available agents: none“)
            self.assertTrue(p.strip().startswith("rodokmen:"), p)
            self.assertIn(p.strip().split(":", 1)[1], POCATECNI - {"orchestrator"})
        self.assertIn("rodokmen:researcher", self.texty["orchestrator"].split("---", 2)[2])   # i v postupu volá agenty plným jménem

    def test_cteci_agenti_nemaji_zapis(self):
        for jmeno in ("failure-analyst", "test-runner"):
            nastroje = {n.split("(")[0].strip() for n in re.split(r"\s*,\s*", frontmatter(self.texty[jmeno])["tools"])}
            self.assertFalse(nastroje & {"Edit", "Write"}, jmeno)

    def test_verifier_cte_naslepo_a_vraci_jen_prepis(self):
        """E1 (A5): slepý ověřovatel nemůže posoudit shodu s tím, co nevidí. Píše jen svůj soubor ověření, shodu počítá vysledek.py porovnej."""
        fm = frontmatter(self.texty["verifier"])
        self.assertEqual({n.strip() for n in fm["tools"].split(",")}, {"Read", "Write"})
        v = self.texty["verifier"]
        self.assertIn("overeni/1", v)
        self.assertIn("_overeni_", v)
        self.assertNotRegex(v, r"`shoda`|`neshoda`")
        self.assertRegex(v, r"(?i)never see the first reading")
        self.assertIn("vysledek.py porovnej", self.texty["orchestrator"])

    def test_researcher_vraci_nalez_podle_kontraktu(self):
        r = self.texty["researcher"]
        for s in ("pracovni/zadani/", "nalez/1", "tools/vysledek.py over", "tools/vysledek.py vzor nalez", "never a name", "not the signature",
                  "rozpočet", "nedostupné"):
            self.assertIn(s, r, s)
        self.assertNotIn("--help", r.replace("no `--help` needed", ""))

    def test_test_author_a_fixer_se_nepletou(self):
        self.assertNotIn("Agent", frontmatter(self.texty["fixer"])["tools"])
        self.assertIn("never", self.texty["failure-analyst"].lower())     # analytik nikdy neupravuje

    def test_researcher_stahuje_pres_brzdu_a_vyrezy_do_sve_slozky(self):
        r = self.texty["researcher"]
        self.assertIn("tools/slusne.py tools/<script>.py", r)             # hook odmítne přímé volání stahovacího skriptu
        self.assertIn("vyrez.py", r)
        self.assertIn("--out pracovni/vysledky/", r)                       # výřezy mimo veřejné složky webu
        self.assertRegex(r, r"(?i)one row")                                # výřez jednoho řádku

    def test_orchestrator_jmenuje_radek_a_stranky_v_karte(self):
        o = self.texty["orchestrator"]
        self.assertRegex(o, r"(?i)name the (exact )?row|single row|one row")

    def test_committer_jen_commituje_vyjmenovane_soubory_na_zadane_vetvi(self):
        fm = frontmatter(self.texty["committer"])
        nastroje = {n.split("(")[0].strip() for n in re.split(r"\s*,\s*", fm["tools"])}
        self.assertFalse(nastroje & {"Edit", "Write", "Agent", "WebFetch", "WebSearch"}, nastroje)
        t = self.texty["committer"].lower()
        for slovo in ("branch", "git add <", "never", "push", "-a"):
            self.assertIn(slovo, t, slovo)

    def test_fixer_hlasi_presny_seznam_souboru_pro_commit(self):
        self.assertIn("exact list of files", self.texty["fixer"])

    def test_verifier_nehada_na_zmenseny_snimek_a_crops_jsou_v_plnem_rozliseni(self):
        """Verifier má jen Read (bez ořezu a zvětšení); velký snímek mu Read zmenší a čtení vyjde neprůkazné."""
        v = self.texty["verifier"]
        self.assertRegex(v, r"(?i)displayed at")                       # pozná zmenšení z hlášky Read
        self.assertRegex(v, r"(?i)crop too large")                    # místo hádání vrátí „výřez je příliš velký“
        self.assertIn("2000", v)
        r = self.texty["researcher"]
        self.assertIn("2000", r)                                       # výřez pro verifiera max. ~2000 px na delší straně
        self.assertIn("-deskew", r)                                    # narovnaný
        self.assertIn("2000", self.texty["orchestrator"])              # karta verifieru žádá plné rozlišení a malý výřez

    def test_orchestrator_audituje_frontu_rozhodnuti_a_zaklada_je_se_strukturou(self):
        o = self.texty["orchestrator"]
        self.assertRegex(o, r"(?i)audit")
        self.assertIn("fronta.py seznam rozhodnuti", o)
        self.assertIn("Výchozí postup", o)                              # povinná pole úkolu k rozhodnutí (S-003)
        self.assertRegex(o, r"(?i)only .*decision")                     # předloží jen skutečná rozhodnutí

    def test_orchestrator_zajistuje_commit_po_kazdem_overeni(self):
        o = self.texty["orchestrator"]
        self.assertIn("tools/commit.py", o)                             # E2: commit dělá nástroj, ne agent
        self.assertNotIn("rodokmen:committer", o)
        self.assertNotIn("rodokmen:fixer", o)                           # zápis dat dělá zapis_vysledku.py
        self.assertIn("tools/zapis_vysledku.py", o)
        self.assertRegex(o, r"(?i)after (each|every) (completed )?verif")
        self.assertIn("tools/stav.py", o)
        self.assertIn("git branch --show-current", o)                  # drží aktuální větev, nepřepíná ji
        self.assertRegex(o, r"(?i)never switch")

    def test_kazdy_agent_ma_kriterium_dokonceni(self):
        for jmeno, text in self.texty.items():
            self.assertRegex(text, r"(?mi)^#+\s+(Done when|Definition of done)", jmeno)

    def test_odkazy_na_pravidla_a_nastroje_existuji(self):
        for jmeno, text in self.texty.items():
            for rid in re.findall(r"\bR-[A-Z]+-\d{3}\b", text):
                self.assertIn(rid, self.ids, f"{jmeno}: {rid}")
            for nastroj in re.findall(r"`(?:tools/)?([a-z_]+\.py)`", text):
                self.assertTrue((REPO / "skills/rodokmen/tools" / nastroj).exists() or (REPO / "scripts" / nastroj).exists()
                                or (REPO / "hooks" / nastroj).exists(), f"{jmeno}: {nastroj}")

    def test_kazdy_agent_ma_jednu_spoustecí_podminku_v_popisu(self):
        for jmeno, text in self.texty.items():
            self.assertRegex(frontmatter(text)["description"], r"^(Use|Run|Read|Verify|Decide|Analy|Fix|Write|Sync|Orchestrate|Commit)", jmeno)

    def test_anglicky(self):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(REPO / "scripts" / "jazyk.py"), str(AGENTI)], capture_output=True,
                           text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_tvar_vysledku_ma_jediny_zdroj_v_nastroji(self):
        """E1 (A4): tvar souborů mezi agenty drží tools/vysledek.py (kontrola i vzor); SKILL.md na něj odkazuje a pole neopisuje."""
        sk = (REPO / "skills/rodokmen-agents/SKILL.md").read_text(encoding="utf-8")
        for s in ("tools/vysledek.py", "zadani/1", "nalez/1", "overeni/1"):
            self.assertIn(s, sk, s)
        sys.path.insert(0, str(REPO / "skills/rodokmen/tools"))
        import vysledek
        for jmeno, vzor in vysledek.VZORY.items():
            self.assertEqual(vzor["schema"], jmeno + "/1")


if __name__ == "__main__":
    unittest.main()
