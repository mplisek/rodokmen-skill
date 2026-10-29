#!/usr/bin/env python3
"""Kramerius – fulltextové hledání v digitálních knihovnách (API v5): noviny, ročenky, adresáře, seznamy ztrát.

Použití: kramerius.py 'SOLR_DOTAZ' [počet] [--server https://adresa]
  např. kramerius.py 'text_ocr:"Jan Novák" AND datum_begin:[1860 TO 1920]'
  Výchozí server je Národní knihovna (kramerius5.nkp.cz). `--server` zkusí jinou knihovnu se stejným rozhraním v5
  (např. Digitální studovnu Ministerstva obrany – seznamy ztrát 1914–1918; z prostředí skillu byla nedostupná, takže NEVYZKOUŠENO).
  Knihovny s rozhraním v7 (adresa …/search/api/client/v7.0) tento nástroj neumí.
"""
import json, re, sys, urllib.error, urllib.parse, urllib.request
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

a = sys.argv[1:]
server = "https://kramerius5.nkp.cz"
if "--server" in a:
    i = a.index("--server")
    if i + 1 >= len(a):
        sys.exit("--server chce adresu knihovny (https://…).")
    server = a[i + 1].rstrip("/")
    del a[i:i + 2]
s = urllib.parse.urlsplit(server)
if s.scheme != "https" or not re.fullmatch(r"[A-Za-z0-9.-]+", s.hostname or "") or s.query or s.fragment:
    sys.exit("--server musí být adresa knihovny s https:// (např. https://kramerius5.nkp.cz).")
if not a:
    sys.exit(__doc__)
q = a[0]
rows = a[1] if len(a) > 1 else "30"
if not rows.isdigit():
    sys.exit("Počet výsledků musí být číslo.")
p = {"q": q + " AND fedora.model:page", "fl": "PID,root_title,root_pid,datum_str,details,dostupnost", "rows": rows, "wt": "json",
     "hl": "true", "hl.fl": "text_ocr", "hl.fragsize": "250"}
u = server + "/search/api/v5.0/search?" + urllib.parse.urlencode(p)
try:
    d = json.load(urllib.request.urlopen(u, timeout=90))
except (OSError, ValueError) as e:   # síť, HTTP chyba i odpověď, která není JSON (jiná verze rozhraní)
    sys.exit(f"Knihovna {s.hostname} neodpověděla jako Kramerius v5 ({type(e).__name__}: {str(e)[:100]}).")
print("found", d["response"]["numFound"])
hl = d.get("highlighting", {})
for x in d["response"]["docs"]:
    h = " | ".join(hl.get(x["PID"], {}).get("text_ocr", []))[:400].replace("\n", " ")
    print("-", x.get("datum_str"), "|", str(x.get("root_title"))[:60], "|", x.get("details"), "|", x["PID"], "|", x.get("dostupnost"))
    if h:
        print("   ", h)
