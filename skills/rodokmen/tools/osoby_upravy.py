#!/usr/bin/env python3
"""Úprava jedné položky v data/osoby.py beze změny zbytku souboru: osoba v P (číslo) nebo RODINA (zkratka), otevřená otázka
v ISSUES. Používá ji tools/oprava.py (kontrola, vše nebo nic, historie); sama nic nekontroluje genealogicky.

Položka se najde přes rozbor Pythonu (ast) a nahradí se jen její text; nová osoba nebo otázka se připíše na konec slovníku či
seznamu. Hodnoty musí být literály (text, číslo, seznam, slovník, True/False/None); jinak se položka neupravuje.
"""
import ast
import json

POSTUP = ("n", "y", "sex", "otec", "matka", "partner", "v", "st", "zap", "f", "r", "note", "vyz", "sour", "overeno")


def lit(v):
    """Literál Pythonu ve stylu osoby.py (dvojité uvozovky, české znaky)."""
    if isinstance(v, bool) or v is None:
        return repr(v)
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)):
        vnitrek = ", ".join(lit(x) for x in v)
        return f"[{vnitrek}]" if isinstance(v, list) else f"({vnitrek}{',' if len(v) == 1 else ''})"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{lit(k)}: {lit(x)}" for k, x in v.items()) + "}"
    raise ValueError(f"hodnota {v!r} není literál")


def dict_text(d, odsazeni=" "):
    """dict(n=…, y=…, f=[…]) – fakta na zvláštních řádcích, když je položka dlouhá."""
    poradi = [k for k in POSTUP if k in d] + [k for k in d if k not in POSTUP]
    casti = []
    for k in poradi:
        v = d[k]
        if k == "f" and isinstance(v, list) and sum(len(str(x)) for x in v) > 80:
            pod = odsazeni + "    "
            casti.append("f=[\n" + ",\n".join(pod + lit(x) for x in v) + "]")
        else:
            casti.append(f"{k}={lit(v)}")
    return "dict(" + ", ".join(casti) + ")"


def _offsety(text):
    out, n = [0], 0
    for radek in text.splitlines(keepends=True):
        n += len(radek)
        out.append(n)
    return out


def _pozice(text, uzel, konec=False):
    off = _offsety(text)
    radek, sloupec = (uzel.end_lineno, uzel.end_col_offset) if konec else (uzel.lineno, uzel.col_offset)
    # col_offset je v bajtech UTF-8: převést na znaky v řádku
    zacatek = off[radek - 1]
    radek_text = text[zacatek:off[radek]] if radek < len(off) else text[zacatek:]
    return zacatek + len(radek_text.encode("utf-8")[:sloupec].decode("utf-8", errors="ignore"))


def _prirazeni(strom, jmeno):
    for u in strom.body:
        if isinstance(u, ast.Assign) and any(isinstance(t, ast.Name) and t.id == jmeno for t in u.targets):
            return u.value
    return None


def _hodnota(uzel):
    """dict(...) nebo {...} s literály → slovník; jinak ValueError."""
    if isinstance(uzel, ast.Call) and isinstance(uzel.func, ast.Name) and uzel.func.id == "dict" and not uzel.args:
        return {kw.arg: ast.literal_eval(kw.value) for kw in uzel.keywords if kw.arg}
    if isinstance(uzel, ast.Dict):
        return {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(uzel.keys, uzel.values)}
    raise ValueError("položka není dict(...) s literály")


def nacti_osobu(text, skupina, klic):
    """Slovník osoby (P: číslo, RODINA: zkratka), nebo None, když není."""
    slovnik = _prirazeni(ast.parse(text), skupina)
    if not isinstance(slovnik, ast.Dict):
        return None
    for k, v in zip(slovnik.keys, slovnik.values):
        if k is not None and ast.literal_eval(k) == klic:
            return _hodnota(v)
    return None


def _vloz_na_konec(text, kontejner, radek):
    """Vloží text položky před uzavírací závorku slovníku/seznamu (s čárkou za předchozí položkou)."""
    konec = _pozice(text, kontejner, konec=True) - 1          # index uzavírací závorky
    pred = text[:konec].rstrip()
    carka = "" if pred.endswith((",", "{", "[")) else ","
    return pred + carka + "\n " + radek + ",\n" + text[konec:]


def uloz_osobu(text, skupina, klic, d):
    """Text osoby.py s novou hodnotou osoby (nebo nově přidanou osobou)."""
    slovnik = _prirazeni(ast.parse(text), skupina)
    if not isinstance(slovnik, ast.Dict):
        raise ValueError(f"{skupina} v data/osoby.py není slovník")
    for k, v in zip(slovnik.keys, slovnik.values):
        if k is not None and ast.literal_eval(k) == klic:
            _hodnota(v)                                        # ověří, že položka je literál
            a, b = _pozice(text, v), _pozice(text, v, konec=True)
            return text[:a] + dict_text(d) + text[b:]
    return _vloz_na_konec(text, slovnik, f"{lit(klic)}: {dict_text(d)}")


def otazky(text):
    """[(slovník, uzel)] otázek ISSUES ve tvaru dict(...)."""
    seznam = _prirazeni(ast.parse(text), "ISSUES")
    out = []
    for prvek in seznam.elts if isinstance(seznam, ast.List) else []:
        try:
            out.append((_hodnota(prvek), prvek))
        except ValueError:
            continue
    return out


def uloz_otazku(text, puvodni_otazka, d):
    """Nahradí otázku se stejným textem „otazka“, nebo připíše novou na konec ISSUES."""
    seznam = _prirazeni(ast.parse(text), "ISSUES")
    if not isinstance(seznam, ast.List):
        raise ValueError("ISSUES v data/osoby.py není seznam")
    for hodnota, uzel in otazky(text):
        if puvodni_otazka is not None and hodnota.get("otazka") == puvodni_otazka:
            a, b = _pozice(text, uzel), _pozice(text, uzel, konec=True)
            return text[:a] + "dict(" + ", ".join(f"{k}={lit(x)}" for k, x in d.items()) + ")" + text[b:]
    return _vloz_na_konec(text, seznam, "dict(" + ", ".join(f"{k}={lit(x)}" for k, x in d.items()) + ")")
