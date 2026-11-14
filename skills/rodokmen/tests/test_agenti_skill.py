"""Skutečná anglická vrstva v repozitáři (Fáze E, ADR 0005): pravidla pro agenty mají platné otisky zdrojů, tenký skill rodokmen-agents je
malý, správně označený, odkazuje jen na existující pravidla a soubory a neopakuje SKILL.md; anglická vrstva je anglicky. Test běží nad
skutečnými soubory, takže po změně zdrojového oddílu v zrcadle (třeba po sloučení z originálu) neprojde, dokud se pravidla nepřezkoumají."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / "skills" / "rodokmen-agents"
ZRCADLO_SKILL = REPO / "skills" / "rodokmen" / "SKILL.md"


def skript(jmeno, *args):
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(REPO / "scripts" / jmeno), *args], capture_output=True, text=True,
                          encoding="utf-8")


class AgentiSkill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        cls.pravidla = {p.stem: p for p in (SKILL / "rules").glob("*.md")}
        cls.ids = set(re.findall(r"(?m)^## (R-[A-Z]+-\d{3})$", "\n".join(p.read_text(encoding="utf-8") for p in cls.pravidla.values())))

    def test_pravidla_maji_platne_otisky_zdroju(self):
        r = skript("pravidla.py", "overit")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(len(self.ids), 20)

    def test_anglicka_vrstva_je_anglicky(self):
        r = skript("jazyk.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_skill_je_maly_a_spravne_oznaceny(self):
        self.assertLessEqual(len(self.text.splitlines()), 120)
        m = re.match(r"---\n(.*?)\n---\n", self.text, re.S)
        self.assertTrue(m, "chybí frontmatter")
        fm = m.group(1)
        self.assertRegex(fm, r"(?m)^name: rodokmen-agents$")
        self.assertRegex(fm, r"(?m)^description: .{20,}")
        self.assertRegex(fm, r"(?m)^user-invocable: false$")
        self.assertNotIn("disable-model-invocation", fm)          # jinak by se skill nepřednačetl agentům

    def test_odkazy_ze_skillu_existuji(self):
        for soubor in re.findall(r"`(rules/[\w.-]+\.md)`", self.text):
            self.assertTrue((SKILL / soubor).exists(), soubor)
        for rid in re.findall(r"\bR-[A-Z]+\b", self.text):
            self.assertTrue(any(i.startswith(rid + "-") for i in self.ids), f"téma {rid} nemá pravidla")
        # každý soubor s pravidly je ve skillu uveden
        for jmeno in self.pravidla:
            self.assertIn(f"rules/{jmeno}.md", self.text, jmeno)

    def test_skill_neopakuje_radky_ze_SKILL_md_zrcadla(self):
        zrcadlo = {l.strip() for l in ZRCADLO_SKILL.read_text(encoding="utf-8").splitlines() if len(l.strip()) >= 40}
        opakovane = [l.strip() for l in self.text.splitlines() if len(l.strip()) >= 40 and l.strip() in zrcadlo]
        self.assertEqual(opakovane, [])

    def test_pravidla_neopakuji_text_jine_pravidla(self):
        videno = {}
        for p in self.pravidla.values():
            for l in p.read_text(encoding="utf-8").splitlines():
                l = l.strip()
                if len(l) >= 60 and re.match(r"(when|do|why): ", l):
                    self.assertNotIn(l, videno, f"{p.name}: stejný řádek jako {videno.get(l)}")
                    videno[l] = p.name


if __name__ == "__main__":
    unittest.main()
