"""tools/spotreba.py (analyza/navrh-optimalizace.md, E7): skutečná spotřeba sezení podle rolí ze záznamů Claude Code. Jen čte; tah modelu
počítá jednou, pomocníka přiřadí úkolu podle ID v zadání, text zadání nevypisuje. Bez sítě, smyšlené záznamy v dočasné složce."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import spotreba  # noqa: E402


def tah(mid, model, vstup=0, zapis=0, cteni=0, vystup=0, cas="2026-11-14T18:00:00Z", vedlejsi=False):
    return {"type": "assistant", "timestamp": cas, "isSidechain": vedlejsi,
            "message": {"id": mid, "model": model, "usage": {"input_tokens": vstup, "cache_creation_input_tokens": zapis,
                                                             "cache_read_input_tokens": cteni, "output_tokens": vystup}, "content": []}}


def zapis(p, radky):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in radky) + "\n", encoding="utf-8")


class Spotreba(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        os.environ["RODOKMEN_PREPISY"] = str(d)
        zapis(d / "aaaa1111.jsonl", [
            tah("m1", "claude-opus-5-5", vstup=100, zapis=1000, vystup=10),
            tah("m1", "claude-opus-5-5", vstup=100, zapis=1000, vystup=10),                    # tentýž tah podruhé (další blok obsahu)
            tah("m2", "claude-sonnet-5-5", cteni=10000, vystup=20, cas="2026-11-15T08:00:00Z"),
            tah("x1", "claude-sonnet-5-5", vstup=999999, vedlejsi=True)])                      # vedlejší vlákno v hlavním souboru se nepočítá
        sub = d / "aaaa1111" / "subagents"
        zapis(sub / "agent-r1.jsonl", [
            {"type": "user", "timestamp": "2026-11-14T18:01:00Z", "message": {"content": "Tajné zadání U-0045: Josef Vzorný"}},
            tah("r1", "claude-sonnet-5-5", zapis=10000, vystup=100, cas="2026-11-14T18:01:01Z"),
            {"type": "user", "message": {"content": [{"type": "tool_result", "is_error": True, "content": "x"}]}},
            tah("r2", "claude-sonnet-5-5", cteni=10000, vystup=100, cas="2026-11-14T18:02:00Z")])
        (sub / "agent-r1.meta.json").write_text(json.dumps({"agentType": "rodokmen:researcher"}), encoding="utf-8")
        zapis(sub / "agent-f1.jsonl", [
            {"type": "user", "message": {"content": "zapiš"}},
            tah("f1", "claude-haiku-5-5", zapis=8000, vystup=40, cas="2026-11-14T18:03:00Z")])
        (sub / "agent-f1.meta.json").write_text(json.dumps({"agentType": "rodokmen:fixer", "description": "deník pro U-0045"}), encoding="utf-8")

    def tearDown(self):
        os.environ.pop("RODOKMEN_PREPISY", None)
        self.tmp.cleanup()

    def run_(self, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kod = spotreba.main(list(a))
        self.out = out.getvalue()
        return kod

    def test_sezeni_po_rolich(self):
        self.run_("sezeni", "--json")
        v = json.loads(self.out)
        self.assertEqual(v["hlavni"]["tahu"], 2)                                   # duplicitní tah jednou, vedlejší vlákno ne
        self.assertEqual(v["hlavni"]["ekv"], round(100 + 1250 + 50 + 1000 + 100))
        self.assertEqual(v["hlavni"]["modelu"], 2)
        r = {x["role"]: x for x in v["pomocnici"]}
        self.assertEqual(r["researcher"]["ekv"], round(12500 + 500 + 1000 + 500))
        self.assertEqual((r["researcher"]["behu"], r["researcher"]["chyb"], r["researcher"]["start_median"]), (1, 1, 10000))
        self.assertEqual(r["fixer"]["model"], "haiku-5-5")
        self.assertEqual(v["ekv_celkem"], v["hlavni"]["ekv"] + r["researcher"]["ekv"] + r["fixer"]["ekv"])

    def test_tabulka_upozorni_na_zmenu_modelu_a_nevypise_zadani(self):
        self.run_("sezeni")
        self.assertIn("měnilo model", self.out)
        self.assertIn("researcher", self.out)
        self.assertNotIn("Vzorný", self.out)

    def test_casove_okno(self):
        self.run_("sezeni", "--od", "2026-11-15T00:00:00+00:00", "--json")
        v = json.loads(self.out)
        self.assertEqual(v["hlavni"]["tahu"], 1)
        self.assertEqual(v["pomocnici"], [])

    def test_ukol_podle_zadani_i_popisu(self):
        self.assertEqual(self.run_("ukol", "U-0045", "--json"), 0)
        v = json.loads(self.out)
        self.assertEqual(v["behu"], 2)
        self.assertNotIn("Vzorný", self.out)
        self.assertEqual(self.run_("ukol", "U-0099"), 1)

    def test_neexistujici_sezeni(self):
        with self.assertRaises(SystemExit):
            self.run_("sezeni", "--sezeni", "zzzz")

    def test_slozka_podle_cesty_projektu(self):
        os.environ.pop("RODOKMEN_PREPISY")
        s = spotreba.slozka_prepisu()
        self.assertIn(os.path.join(".claude", "projects"), s)
        self.assertRegex(os.path.basename(s), r"^[A-Za-z0-9-]+$")


if __name__ == "__main__":
    unittest.main()
