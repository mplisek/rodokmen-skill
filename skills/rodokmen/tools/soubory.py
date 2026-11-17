#!/usr/bin/env python3
"""Bezpečný zápis souborů projektu (svazky.json, zvyrazneni.json, mista.json, data webu).

Soubor se zapíše celý naráz: nejdřív do dočasného souboru vedle, pak se vymění. Když nástroj spadne nebo ho někdo
přeruší uprostřed zápisu, zůstane původní soubor celý – nikdy ne useknutý napůl. Konce řádků vždy LF (i na Windows).
"""
import json, os


def zapis_text(path, text):
    """Zapíše text (UTF-8, LF) atomicky."""
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):   # zápis selhal – dočasný soubor nenechávat
            os.remove(tmp)


def zapis_json(path, data, indent=1, konec=""):
    """JSON stejně jako dosud (ensure_ascii=False, odsazení 1), jen atomicky. `konec` = text za JSON (např. „\\n“)."""
    zapis_text(path, json.dumps(data, ensure_ascii=False, indent=indent) + konec)


if __name__ == "__main__":   # samokontrola: python3 -I tools/soubory.py
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "data", "x.json")
        zapis_json(p, {"a": "č"})
        assert open(p, encoding="utf-8").read() == '{\n "a": "č"\n}'
        try:
            zapis_json(p, {"b": object()})   # nejde převést na JSON – původní soubor musí zůstat
        except TypeError:
            pass
        assert open(p, encoding="utf-8").read() == '{\n "a": "č"\n}' and os.listdir(os.path.dirname(p)) == ["x.json"]
    print("soubory.py: samokontrola OK")
