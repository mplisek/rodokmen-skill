"""slusne.py: brzda proti zablokování archivem – rozestup dotazů, stopka po 429/503/403 pro všechny procesy, volné weby.

Síť ven nepotřebuje: archiv hraje místní HTTP server na 127.0.0.2 (brzdí se; volné jsou jen localhost a 127.0.0.1).
Stav brzdy jde do dočasné složky, ne do skutečného stavu uživatele.
"""
import contextlib
import http.server
import io
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pomocne import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import slusne  # noqa: E402

HOST = "127.0.0.2"


class Archiv(http.server.BaseHTTPRequestHandler):
    kody = {}        # cesta → stavový kód
    pocet = 0

    def do_GET(self):
        type(self).pocet += 1
        kod = self.kody.get(self.path, 200)
        self.send_response(kod)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def server_jde():
    try:
        s = http.server.ThreadingHTTPServer((HOST, 0), Archiv)
        s.server_close()
        return True
    except OSError:
        return False


class Brzda(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._puvodni = (slusne.STAV, list(slusne._slozka_), slusne.DOTAZ, slusne.OBRAZEK)
        slusne.STAV = self._tmp.name
        slusne._slozka_.clear()
        slusne._ohlaseno.clear()
        slusne.DOTAZ, slusne.OBRAZEK = 0.4, 0.0
        self._ticho = contextlib.redirect_stderr(io.StringIO())   # hlášky o stopce do výstupu testů nepatří
        self._ticho.__enter__()

    def tearDown(self):
        self._ticho.__exit__(None, None, None)
        slusne.STAV, slozka, slusne.DOTAZ, slusne.OBRAZEK = self._puvodni
        slusne._slozka_[:] = slozka
        self._tmp.cleanup()

    def test_skupiny_a_obrazky(self):
        self.assertEqual(slusne._skupina("localhost")[0], None)
        self.assertEqual(slusne._skupina("muj-web.netlify.app")[0], None)
        self.assertEqual(slusne._skupina("images.archives.cz")[0], "archives.cz")   # ZA Opava – vlastní limit
        self.assertEqual(slusne._skupina("www.mza.cz")[0], "www.mza.cz")
        self.assertTrue(slusne.je_obrazek("https://x.cz/a/TileGroup0/3-1-2.jpg"))
        self.assertTrue(slusne.je_obrazek("https://x.cz/fcgi-bin/iipsrv.fcgi?IIIF=a/full/full/0/default.jpg"))
        self.assertFalse(slusne.je_obrazek("https://x.cz/hledat?q=Holice"))

    def test_rozestup_dotazu_a_volne_obrazky(self):
        t0 = time.time()
        for _ in range(3):
            slusne.pockej("https://archiv.example/hledat")
        self.assertGreaterEqual(time.time() - t0, 0.75)       # 3 dotazy = aspoň 2 rozestupy 0,4 s
        t0 = time.time()
        for _ in range(5):
            slusne.pockej("https://archiv.example/x/TileGroup0/1-0-0.jpg")
        self.assertLess(time.time() - t0, 0.3)                # obrázky mají vlastní (zde nulový) rozestup
        t0 = time.time()
        for _ in range(5):
            slusne.pockej("http://localhost:4321/")           # místní web se nebrzdí
        self.assertLess(time.time() - t0, 0.3)

    def test_stopka_po_429_plati_i_pro_dalsi_proces(self):
        with self.assertRaises(slusne.Zastaveno):
            slusne.kontroluj_odpoved("archiv.example", 429, False)
        with self.assertRaises(slusne.Zastaveno):
            slusne.pockej("https://archiv.example/cokoli")
        kod = (f"import sys; sys.path.insert(0, {str(TOOLS)!r}); import slusne; slusne.STAV = {self._tmp.name!r}; "
               "slusne.pockej('https://archiv.example/jinde')")
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", "-c", kod], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, slusne.KOD)            # jiný proces stopku vidí taky
        self.assertIn("zastavený", r.stderr)

    def test_403_zastavi_jen_dotaz(self):
        slusne.kontroluj_odpoved("archiv.example", 403, True)   # obrázek: 403 = chybí snímek, ne blokace
        slusne.pockej("https://archiv.example/x")
        with self.assertRaises(slusne.Zastaveno):
            slusne.kontroluj_odpoved("archiv.example", 403, False)

    def test_odblokuj(self):
        with self.assertRaises(slusne.Zastaveno):
            slusne.zastav("archiv.example", "zkouška")
        with contextlib.redirect_stdout(io.StringIO()):
            slusne._odblokuj("archiv.example")
        slusne.pockej("https://archiv.example/x")             # už neskončí

    @unittest.skipUnless(server_jde(), f"na {HOST} nejde spustit místní server")
    def test_urllib_pres_brzdu(self):
        srv = http.server.ThreadingHTTPServer((HOST, 0), Archiv)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = f"http://{HOST}:{srv.server_address[1]}"
            Archiv.kody = {"/plno": 429}
            Archiv.pocet = 0
            self.assertEqual(urllib.request.urlopen(url + "/ok", timeout=5).status, 200)
            with self.assertRaises(slusne.Zastaveno):
                urllib.request.urlopen(url + "/plno", timeout=5)
            with self.assertRaises(slusne.Zastaveno):
                urllib.request.urlopen(url + "/ok", timeout=5)
            self.assertEqual(Archiv.pocet, 2)                 # třetí dotaz už na server vůbec nešel
        finally:
            srv.shutdown()
            srv.server_close()



class Certifikaty(unittest.TestCase):
    """Windows: po chybě ověření certifikátu doplnit kořen přes curl.exe, znovu načíst certifikáty a jednou zopakovat."""

    def setUp(self):
        self._puvodni = (slusne._s_connect[0], slusne._doplnit_koreny)
        self.volani = []

        def spojeni(conn):   # první pokus: kořen chybí; druhý projde
            self.volani.append(conn.host)
            if len(self.volani) == 1:
                raise ssl.SSLCertVerificationError("certificate verify failed: unable to get local issuer certificate")
        slusne._s_connect[0] = spojeni

    def tearDown(self):
        slusne._s_connect[0], slusne._doplnit_koreny = self._puvodni

    def spoj(self):
        conn = http.client.HTTPSConnection("archiv.example")
        conn._context = mock.Mock()
        conn.connect()
        return conn

    def test_po_doplneni_korenu_zopakuje(self):
        slusne._doplnit_koreny = lambda host: True
        conn = self.spoj()
        self.assertEqual(self.volani, ["archiv.example", "archiv.example"])
        conn._context.load_default_certs.assert_called_once()

    def test_kdyz_doplnit_nejde_chyba_zustane(self):
        slusne._doplnit_koreny = lambda host: False
        with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(ssl.SSLCertVerificationError):
            self.spoj()
        self.assertEqual(len(self.volani), 1)
        if os.name == "nt":
            self.assertIn("v prohlížeči", err.getvalue())

    def test_doplneni_jen_na_windows_a_jednou_za_web(self):
        slusne._doplnit_koreny = self._puvodni[1]
        slusne._doplneno.discard("archiv.example")
        with mock.patch.object(slusne.subprocess, "run") as run, mock.patch.object(slusne, "pockej"):
            prvni = slusne._doplnit_koreny("archiv.example")
            druhy = slusne._doplnit_koreny("archiv.example")
        if os.name == "nt":
            self.assertEqual((prvni, druhy), (True, False))
            prikaz = run.call_args[0][0]
            self.assertTrue(prikaz[0].lower().endswith("curl.exe"))
            self.assertIn("https://archiv.example/", prikaz)
        else:
            self.assertEqual((prvni, druhy), (False, False))
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
