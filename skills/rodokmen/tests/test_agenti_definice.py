"""Definice agentů v agents/ (Fáze C, Q-C1, 4.1–4.7 návrhu): povinná pole, povolené nástroje, orchestrátor bez zápisu a webu, anglicky,
kritérium dokončení, odkazy na existující pravidla a nástroje, jen počáteční sada 9 agentů. Test běží nad skutečnými soubory."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
AGENTI = REPO / "agents"
POCATECNI = {"orchestrator", "researcher", "browser-reader", "verifier", "upstream-sync", "test-runner", "failure-analyst", "fixer",
             "test-author"}
NASTROJE = {"Read", "Glob", "Grep", "Bash", "PowerShell", "Edit", "Write", "Agent", "WebFetch", "WebSearch", "Monitor"}
MODELY = {"haiku", "sonnet", "opus", "inherit"}


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "chybí frontmatter"
    return {k: v.strip() for k, v in re.findall(r"(?m)^([a-z-]+):\s*(.*)$", m.group(1))}


class DefiniceAgentu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.soubory = {p.stem: p for p in AGENTI.glob("*.md")}
        cls.texty = {k: p.read_text(encoding="utf-8") for k, p in cls.soubory.items()}
        cls.ids = set(re.findall(r"(?m)^## (R-[A-Z]+-\d{3})$",
                                 "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "skills/rodokmen-agents/rules").glob("*.md"))))

    def test_pocatecni_sada_je_presne_devet_agentu(self):
        self.assertEqual(set(self.soubory), POCATECNI)

    def test_povinna_pole(self):
        for jmeno, text in self.texty.items():
            fm = frontmatter(text)
            self.assertEqual(fm.get("name"), jmeno, jmeno)
            self.assertGreaterEqual(len(fm.get("description", "")), 30, jmeno)
            self.assertIn(fm.get("model"), MODELY, jmeno)
            self.assertTrue(fm.get("tools"), jmeno)
            self.assertIn("rodokmen-agents", fm.get("skills", ""), jmeno)

    def test_nastroje_jen_ze_seznamu(self):
        for jmeno, text in self.texty.items():
            for n in re.split(r"\s*,\s*", frontmatter(text)["tools"]):
                zaklad = n.split("(")[0].strip()
                self.assertIn(zaklad, NASTROJE, f"{jmeno}: {n}")

    def test_orchestrator_nezapisuje_a_nema_web(self):
        fm = frontmatter(self.texty["orchestrator"])
        nastroje = {n.split("(")[0].strip() for n in re.split(r"\s*,\s*", fm["tools"])}
        self.assertFalse(nastroje & {"Edit", "Write", "WebFetch", "WebSearch", "PowerShell"}, nastroje)
        self.assertIn("Agent", nastroje)
        self.assertIn("Bash", nastroje)               # úzce hlídá hooks/hlidac_orchestratora.py
        povoleni = set(re.findall(r"Agent\(([^)]*)\)", fm["tools"]))
        self.assertTrue(povoleni, "Agent(...) musí vyjmenovat povolené podagenty")
        for p in re.split(r"\s*,\s*", ",".join(povoleni)):
            self.assertIn(p.strip(), POCATECNI - {"orchestrator"})

    def test_cteci_agenti_nemaji_zapis(self):
        for jmeno in ("verifier", "failure-analyst", "test-runner"):
            nastroje = {n.split("(")[0].strip() for n in re.split(r"\s*,\s*", frontmatter(self.texty[jmeno])["tools"])}
            self.assertFalse(nastroje & {"Edit", "Write"}, jmeno)

    def test_test_author_a_fixer_se_nepletou(self):
        self.assertNotIn("Agent", frontmatter(self.texty["fixer"])["tools"])
        self.assertIn("never", self.texty["failure-analyst"].lower())     # analytik nikdy neupravuje

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
            self.assertRegex(frontmatter(text)["description"], r"^(Use|Run|Read|Verify|Decide|Analy|Fix|Write|Sync|Orchestrate)", jmeno)

    def test_anglicky(self):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(REPO / "scripts" / "jazyk.py"), str(AGENTI)], capture_output=True,
                           text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_vystup_vysledku_ma_schema_v_dokumentaci(self):
        sk = (REPO / "skills/rodokmen-agents/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pracovni/vysledky", sk)


if __name__ == "__main__":
    unittest.main()
