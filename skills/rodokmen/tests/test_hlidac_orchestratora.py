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
                  "python3 tools/fronta.py smaz U-0001", "python3 tools/denik.py pridej --hledano x", "python3 tools/zapis.py zaznamy k x.json",
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

    def test_orchestrator_smi_zadani_a_kontrakt_s_textem_v_uvozovkach(self):
        """E1: zadání pro čtenáře a kontrola nálezů bez dalšího agenta; text jen v uvozovkách."""
        for p in ('python -I -X utf8 tools/zadani.py novy U-0101 --otazka "Najdi křest osoby 88 (rodiče; kmotři)." --hleda křtěnec '
                  '--osoba "88:křtěnec:* asi 1812, čp. 5" --svazek 0a1b2c3d --snimky 40-52 --vratit datum,otec',
                  'python -I tools/zadani.py rozsir U-0101 --snimky 53 --duvod "řádek pokračuje vpravo"',
                  "python -I -X utf8 tools/vysledek.py souhrn U-0101", "python -I tools/vysledek.py porovnej U-0101 c1 --json",
                  "python3 -I tools/vysledek.py over pracovni/vysledky/U-0101.json"):
            self.assertEqual(hook("orchestrator", p)[0], "allow", p)
        for p in ('python -I tools/zadani.py novy U-0101 --otazka "x" ; rm -rf data', 'python -I tools/zadani.py novy U-0101 --otazka "$(id)"',
                  'python -I tools/zadani.py novy U-0101 --otazka "x" > data/osoby.py', "python -I tools/zadani.py smaz U-0101",
                  "python -I tools/zapis.py zaznam x.json", "python -I /tmp/tools/zadani.py novy U-0101", 'python -c "import os"',
                  "python -I tools/vysledek.py souhrn U-0101 | tee x", 'python -I tools/zadani.py novy U-0101 --otazka "neuzavřená'):
            self.assertEqual(hook("orchestrator", p)[0], "deny", p)

    def test_orchestrator_zapisuje_jen_validujicimi_nastroji(self):
        """E2 (rozhodnutí uživatele 15. 11. 2026): fronty, přijatý výsledek a commit bez dalšího agenta; vstup zápisu jen ze souboru v pracovni/."""
        for p in ('python -I -X utf8 tools/fronta.py pridej vstup --text "křest osoby 88" --os 88', "python -I tools/fronta.py hotovo U-0001 --denik 12",
                  'python -I tools/fronta.py smeruj U-0002 --do noc --dod "řádek deníku" --cena S',
                  "python -I -X utf8 tools/zapis_vysledku.py pracovni/vysledky/U-0001_rozhodnuti.json --nanecisto",
                  "python -I tools/commit.py U-0001 --vetev migrace-test", "python -I -X utf8 tools/stav.py", "python -I tools/spotreba.py ukol U-0001",
                  'python -I tools/podnet.py "nástroj skončil chybou cesty; obchvat byl zadat --rules" --dopad cena'):
            self.assertEqual(hook("orchestrator", p)[0], "allow", p)
        for p in ("python -I tools/zapis_vysledku.py data/osoby.py", "python -I tools/zapis_vysledku.py pracovni/../data/x.json",
                  "python -I tools/zapis_vysledku.py /tmp/x.json", "python -I tools/commit.py", "git commit -m x", "git push",
                  "python -I tools/commit.py U-0001 && git push"):
            self.assertEqual(hook("orchestrator", p)[0], "deny", p)
        self.assertEqual(hook("rodokmen:badatel", "python -I tools/stav.py")[0], "allow")
        self.assertEqual(hook("rodokmen:badatel", "rm -rf data")[0], "deny")

    def test_badatel_ma_cestu_k_ukolum_od_metodiky(self):
        """Podnět z bádání 16. 11. 2026: role účastníků, opravný řádek deníku a soubory měření nešly zapsat ničím povoleným."""
        for p in ("python -I -X utf8 tools/ucastnici.py stav", "python -I tools/ucastnici.py navrh",
                  "python -I tools/ucastnici.py navrh --out pracovni/ucastnici_navrh.json",
                  "python -I -X utf8 tools/ucastnici.py zapis pracovni/ucastnici_navrh.json",
                  'python -I tools/denik.py pridej --opravuje 379 --hledano "křest" --zdroj "ARON 744" --vysledek nenalezeno --rozsah "sn. 66-70" --osoby 160',
                  'python -I tools/commit.py --soubory mereni/v0_hodnoceni.json --zprava "Hodnocení měření v0"',
                  "python -I tools/svazky.py pridej pracovni/svazek_ebad_14312.json", "python -I tools/svazky.py pridej pracovni/s.json --doplnit",
                  "python -I tools/svazky.py ukaz ebad_14312",
                  "python -I tools/oprava.py pracovni/oprava_druhu.json", "python -I -X utf8 tools/oprava.py pracovni/o.json --nanecisto",
                  "python -I tools/oprava.py vzor", "python -I tools/oprava.py --help", "python -I tools/svazky.py -h",
                  "python -I tools/zapis_vysledku.py --help"):
            self.assertEqual(hook("rodokmen:badatel", p)[0], "allow", p)
        for p in ("python -I tools/ucastnici.py zapis data/zaznamy.json", "python -I tools/ucastnici.py zapis pracovni/../data/x.json",
                  "python -I tools/ucastnici.py navrh --out data/x.json", 'python -I tools/denik.py pridej --hledano "x" --vysledek nalezeno',
                  "python -I tools/denik.py smaz 12", "python -I tools/svazky.py pridej data/svazky.json",
                  "python -I tools/svazky.py pridej pracovni/../x.json", "python -I tools/svazky.py smaz ebad_1",
                  "python -I tools/zapis.py zaznamy k pracovni/x.json", "python -I tools/zapis.py zaznamy k pracovni/x.json --prepsat",
                  "python -I tools/zapis.py --smazat k", "python -I tools/zapis.py prepisy k pracovni/x.json --sloucit",
                  "python -I tools/zapis.py zaznamy k - --sloucit", "python -I tools/zapis.py zaznamy k data/x.json --sloucit",
                  "python -I tools/zapis.py zaznamy k pracovni/x.json --sloucit", "python -I tools/oprava.py data/x.json",
                  "python -I tools/oprava.py pracovni/../x.json", "python -I tools/oprava.py pracovni/a.json pracovni/b.json",
                  "python -I tools/zapis.py --help", "python -I tools/oprava.py --help data/x.json"):
            self.assertEqual(hook("rodokmen:badatel", p)[0], "deny", p)

    def test_orchestrator_pise_soubory_jen_do_pracovni(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            def zapis(cesta, nastroj="Write", agent="orchestrator"):
                data = {"tool_name": nastroj, "tool_input": {"file_path": cesta, "content": "x"}, "agent_type": agent, "cwd": t}
                r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                                   encoding="utf-8")
                return "deny" if r.stdout.strip() else "allow"
            self.assertEqual(zapis("pracovni/vysledky/U-0001_rozhodnuti.json"), "allow")
            self.assertEqual(zapis(t + "/pracovni/x.json"), "allow")
            self.assertEqual(zapis("mereni/v0_hodnoceni.json", "Edit"), "allow")     # měření není rodinná data ani web
            for c in ("data/osoby.py", "data/denik.jsonl", "tools/fronta.py", "pracovni/../data/x.json", "web/src/x.astro", "../jinde.txt",
                      "mereni/../data/x.json"):
                self.assertEqual(zapis(c), "deny", c)
                self.assertEqual(zapis(c, "Edit"), "deny", c)
            self.assertEqual(zapis("data/osoby.py", agent="rodokmen:badatel"), "deny")
            self.assertEqual(zapis("data/x.json", agent="fixer"), "allow")       # jiné agenty tenhle hlídač neřeší (data chrání hlidac_zapisu)

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
        self.assertTrue(any("Bash" in x.get("matcher", "") and "Write" in x.get("matcher", "") for x in pre))


if __name__ == "__main__":
    unittest.main()
