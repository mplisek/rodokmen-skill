"""hooks/hlidac_orchestratora.py (Fáze C, Q-C4, Q6): hook PreToolUse pluginu. Orchestrátor smí v Bashi jen výpis z fronta.py a kontext.py;
ostatní agenty a hlavní vlákno bez agenta se netýká. hooks/hooks.json ho zapojuje. Rozhraní: vstup a výstup hooku. Bez sítě."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "hlidac_orchestratora.py"


def hook(agent, prikaz, nastroj="Bash"):
    data = {"tool_name": nastroj, "tool_input": {"command": prikaz}}
    if agent:
        data["agent_type"] = agent
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return "allow", ""
    o = json.loads(r.stdout)["hookSpecificOutput"]
    return o["permissionDecision"], o["permissionDecisionReason"]


class HlidacOrchestratora(unittest.TestCase):
    def test_povolene_prikazy_orchestratora(self):
        for p in ("python3 -I tools/fronta.py seznam", "python3 -I tools/fronta.py frontier dotazy", "python -X utf8 tools/fronta.py kontrola",
                  "python3 -I tools/kontext.py --osoba 17 --tema identity,books", "python3 tools/fronta.py seznam rodina",
                  "python -I -X utf8 tools/fronta.py cekajici", "python -I tools/fronta.py plan noc", "python -I tools/fronta.py historie U-0001",
                  "python -I tools/fronta.py kalibrace"):
            self.assertEqual(hook("orchestrator", p)[0], "allow", p)

    def test_ostatni_prikazy_orchestratora_se_zamitnou(self):
        for p in ("rm -rf data", "git push", "curl https://example.org", "cat data/osoby.py", "python3 tools/zapis.py x",
                  "python3 tools/fronta.py pridej dotazy --text x", "python3 tools/fronta.py hotovo U-0001",
                  "python3 tools/fronta.py seznam; rm -rf data", "python3 tools/kontext.py --osoba 1 --tema a && git push",
                  "python3 tools/kontext.py --osoba 1 --tema a > data/x.json", "python3 tools/fronta.py seznam | tee data/x"):
            rozhodnuti, duvod = hook("orchestrator", p)
            self.assertEqual(rozhodnuti, "deny", p)
            self.assertIn("fronta.py", duvod)
            self.assertIn("kontext.py", duvod)

    def test_orchestrator_smi_ptat_se_mapy_knihy_jen_cist(self):
        for p in ("python3 -I tools/mapa.py hledej aron 03066862 --pismeno F", "python3 -I tools/mapa.py hledej aron 03066862 --rok 1856 --celkem 300",
                  "python3 -I tools/mapa.py stav aron 03066862"):
            self.assertEqual(hook("orchestrator", p)[0], "allow", p)
        for p in ("python3 -I tools/mapa.py zapis pracovni/vysledky/x.json", "python3 -I tools/mapa.py snimek aron 03066862 5",
                  "python3 -I tools/mapa.py naplnit-z-pracovni", "python3 -I tools/mapa.py hledej aron x --pismeno F; rm -rf data"):
            self.assertEqual(hook("orchestrator", p)[0], "deny", p)

    def test_orchestrator_smi_cist_vetev_a_stav_gitu(self):
        for p in ("git branch --show-current", "git status --short", "git log --oneline -5", "git log --oneline"):
            self.assertEqual(hook("orchestrator", p)[0], "allow", p)

    def test_orchestrator_nesmi_menit_git(self):
        for p in ("git commit -m x", "git add -A", "git checkout main", "git switch x", "git push", "git status --short; git push",
                  "git branch -D x", "git log --oneline | head"):
            self.assertEqual(hook("orchestrator", p)[0], "deny", p)

    def test_committer_smi_jen_bezpecne_git_prikazy(self):
        for p in ("git status --short", "git diff --stat", "git branch --show-current", "git log --oneline -3",
                  "git add data/denik.jsonl data/osoby.py vyrezy/x.jpg",
                  'git commit -m "Deník 366: ověřeno (Libice, sn. 54)"', 'git commit -m "A" -m "B: (x) y"'):
            self.assertEqual(hook("committer", p)[0], "allow", p)
        self.assertEqual(hook("rodokmen:committer", "git add data/x.json")[0], "allow")

    def test_committer_smi_atribuci_a_viceradkovou_zpravu_v_uvozovkach(self):
        """Poznámka z projektu (14. 11. 2026): řádek Co-Authored-By s <e-mail> a víceřádková zpráva v uvozovkách se nesmí blokovat."""
        for p in ('git commit -m "Fronty: nový úkol" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"',
                  'git commit -m "Titulek' + chr(10) + chr(10) + 'Tělo zprávy; s pomlčkou & ampersandem | rourou"',
                  "git commit -m 'Jednoduché uvozovky <a> & b'"):
            self.assertEqual(hook("committer", p)[0], "allow", p)

    def test_committer_stale_nesmi_nic_mimo_uvozovky(self):
        for p in ('git commit -m "ok" ; rm -rf data', 'git commit -m "ok" && git push', 'git commit -m "ok" > /dev/null',
                  'git commit -m "ok"' + chr(10) + "rm -rf data", 'git status' + chr(10) + 'rm -rf data', 'git commit -m "neuzavřená',
                  'git commit -m "$(rm -rf data)"', 'git commit -m "`id`"', 'git commit -m "cena $5"'):
            self.assertEqual(hook("committer", p)[0], "deny", p)

    def test_committer_nesmi_nic_nebezpecneho(self):
        for p in ("git add -A", "git add .", "git add --all", "git add -u", "git add -f pracovni/x", "git add ../x", "git add /etc/passwd",
                  "git commit -a -m x", "git commit --amend -m x", "git commit --no-verify -m x", "git commit -m x --allow-empty",
                  'git commit -m "$(rm -rf data)"', 'git commit -m "`id`"', "git commit -m x; git push", "git commit -m x && git push",
                  "git push", "git checkout main", "git switch main", "git reset --hard", "git merge x", "git rebase x", "git stash",
                  "git branch -D x", "git tag x", "git clean -fd", "git commit", "rm -rf data", "cat data/osoby.py",
                  "git add data/x.json > /dev/null"):
            self.assertEqual(hook("committer", p)[0], "deny", p)

    def test_jmeno_agenta_s_pluginem_je_taky_orchestrator(self):
        self.assertEqual(hook("rodokmen:orchestrator", "rm -rf data")[0], "deny")

    def test_ostatni_agenti_a_hlavni_vlakno_nic_nehlida(self):
        for agent in ("researcher", "fixer", "test-runner", None):
            self.assertEqual(hook(agent, "rm -rf data")[0], "allow", agent)

    def test_jine_nastroje_orchestratora_hlidac_neresi(self):
        self.assertEqual(hook("orchestrator", "x", nastroj="Read")[0], "allow")

    def test_rozbity_vstup_prikaz_pusti(self):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(HOOK)], input="není json", capture_output=True, text=True,
                           encoding="utf-8")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_hooks_json_zapojuje_hlidace(self):
        h = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        pre = h["hooks"]["PreToolUse"]
        text = json.dumps(pre)
        self.assertIn("hlidac_orchestratora.py", text)
        self.assertIn("CLAUDE_PLUGIN_ROOT", text)
        self.assertTrue(any("Bash" in x.get("matcher", "") for x in pre))


if __name__ == "__main__":
    unittest.main()
