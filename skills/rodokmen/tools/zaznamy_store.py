"""Společný základ ověřovaných úložišť (deník, později veřejné otázky): zápis jen na konec souboru JSONL pod zámkem, čtení
s číslem řádku u chyby, zakázané vzory v textech pro web a pomůcky pro vykreslení tabulky. Nic nestahuje (ADR 0002)."""
import datetime
import json
import os
import re
import time

# Texty, které jdou na web, nesmějí obsahovat procesní údaje (reference/zapisy.md): kdo práci udělal, jak se ověřila, čísla
# úkolů, cesty, opravy uvnitř textu a chyby tvaru. Pole puvodni a proces (jen v datech) se nekontrolují.
ZAKAZANE = [
    ("číslo úkolu", re.compile(r"\b(?:U-\d{2,}|N\d{1,2}[a-z])\b")),
    ("jméno agenta nebo modelu", re.compile(r"\b(?:pomocník\w*|subagent\w*|agent\w*|sonnet\w*|opus\w*|haiku\w*|claude)\b", re.I)),
    ("údaj o procesu", re.compile(r"čtyři oči|ověřeno na snímku|čteno na výřezu|\bvln[aeuyě]\b|hlavní agent", re.I)),
    ("cesta", re.compile(r"pracovni[/\\]|[A-Za-z]:\\|/tmp/", re.I)),
    ("oprava uvnitř textu", re.compile(r"dříve chybně|\bopraveno:|\boprava:", re.I)),
    ("mezera před dvojtečkou", re.compile(r"[^\W\d_] :")),
    ("šipka ->", re.compile(r"->")),
    ("první osoba (mnou)", re.compile(r"\bmnou\b", re.I)),
]


def zakazane_vzory(text):
    """[(název vzoru, nalezený text)] pro jeden text."""
    out = []
    for nazev, rx in ZAKAZANE:
        for m in rx.finditer(text or ""):
            out.append((nazev, m.group(0)))
    return out


def je_datum(text):
    try:
        datetime.date.fromisoformat(text)
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", text))
    except (TypeError, ValueError):
        return False


class Zamek:
    """Jednoduchý zámek souboru (vytvoření souboru .lock); starý zámek po 60 s se přebije."""

    def __init__(self, cesta, cekat=15.0):
        self.cesta, self.cekat = cesta + ".lock", cekat

    def __enter__(self):
        konec = time.time() + self.cekat
        while True:
            try:
                self.fd = os.open(self.cesta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.cesta) > 60:
                        os.remove(self.cesta)
                        continue
                except OSError:
                    pass
                if time.time() > konec:
                    raise TimeoutError(f"soubor {os.path.basename(self.cesta)} je zamčený jiným procesem")
                time.sleep(0.05)

    def __exit__(self, *a):
        os.close(self.fd)
        try:
            os.remove(self.cesta)
        except OSError:
            pass


def nacti(cesta):
    """[(číslo řádku, záznam nebo None, chyba nebo None)]; prázdné řádky se přeskočí."""
    out = []
    if not os.path.exists(cesta):
        return out
    with open(cesta, encoding="utf-8-sig") as f:
        for n, radek in enumerate(f, 1):
            if not radek.strip():
                continue
            try:
                z = json.loads(radek)
                out.append((n, z, None if isinstance(z, dict) else "řádek není objekt JSON"))
            except ValueError as e:
                out.append((n, None, f"neplatný JSON ({e})"))
    return out


def pridej_radek(cesta, zaznam):
    """Připojí jeden záznam na konec souboru (nic jiného se nepřepisuje)."""
    os.makedirs(os.path.dirname(cesta) or ".", exist_ok=True)
    text = json.dumps(zaznam, ensure_ascii=False, sort_keys=False)
    with open(cesta, "a", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")


def bunka(text):
    """Text do buňky tabulky Markdownu: bez zalomení, svislá čára ochráněná."""
    return re.sub(r"\s+", " ", str(text if text is not None else "")).strip().replace("|", "\\|")
