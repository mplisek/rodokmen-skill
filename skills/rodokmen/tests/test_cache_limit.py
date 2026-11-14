"""tools/cache.py: výchozí limit sdílené mezipaměti snímků je 25 GB (proměnná RODOKMEN_SNIMKY_GB ho přepíše). Bez sítě."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402


def limit_gb(env_gb=None):
    env = {k: v for k, v in os.environ.items() if k != "RODOKMEN_SNIMKY_GB"}
    if env_gb is not None:
        env["RODOKMEN_SNIMKY_GB"] = env_gb
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", "-c",
                        f"import sys; sys.path.insert(0, r'{TOOLS}'); import cache; print(cache.LIMIT / 1024 ** 3)"],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stderr
    return float(r.stdout.strip())


class CacheLimit(unittest.TestCase):
    def test_vychozi_limit_je_25_gb(self):
        self.assertEqual(limit_gb(), 25.0)

    def test_promenna_limit_prepise(self):
        self.assertEqual(limit_gb("2.5"), 2.5)

    def test_prazdna_promenna_da_vychozi(self):
        self.assertEqual(limit_gb(""), 25.0)


if __name__ == "__main__":
    unittest.main()
