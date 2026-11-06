#!/usr/bin/env python3
"""Osobní odkazy na rodinný web (vstup bez rodinné otázky, každý člověk má svůj).

  python3 -I tools/pozvanky.py pridej "Teta Jana"        nový odkaz (vypíše se jen jednou)
  python3 -I tools/pozvanky.py pridej "Teta Jana" --pristup matcina-rodina
                                                         odkaz jen na verzi webu pro jeden přístup (web.json → pristupy)
  python3 -I tools/pozvanky.py pristup p1 matcina-rodina změna přístupu u odkazu („vse“ = celý web)
  python3 -I tools/pozvanky.py seznam                    kdo má odkaz
  python3 -I tools/pozvanky.py prejmenuj p1 "Jana Nováková"
  python3 -I tools/pozvanky.py nova p1                   náhrada ztraceného odkazu, starý přestane platit
  python3 -I tools/pozvanky.py zrus p1                   zrušení odkazu (záznam zůstane bez otisku, id se znovu nepoužije)
  (Windows: python -I -X utf8 …)

V data/pozvanky.json je u každého odkazu jen otisk klíče (SHA-256), klíč sám se nikam neukládá.
Adresa odkazu je prihlaseni.adresa z data/web.json. Změny platí na webu až po nasazení (`npm run nasadit`):
export vloží otisky do brány web/netlify/edge-functions/brana.js. Docker/CapRover osobní odkazy neumí.
"""
import datetime, hashlib, json, os, secrets, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I nepřidává složku skriptu
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

SOUBOR = "pozvanky.json"
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
NASADIT = "Na webu to začne platit po nasazení: cd web && npm run nasadit"


def otisk(klic):
    return hashlib.sha256(klic.encode()).hexdigest()


def load(data_dir):
    path = os.path.join(data_dir, SOUBOR)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(data_dir, odkazy):
    """Celý soubor naráz přes dočasný soubor: při chybě zápisu zůstane původní."""
    path = os.path.join(data_dir, SOUBOR)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(odkazy, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def adresa(data_dir):
    try:
        with open(os.path.join(data_dir, "web.json"), encoding="utf-8") as f:
            return ((json.load(f).get("prihlaseni") or {}).get("adresa") or "").rstrip("/")
    except (OSError, ValueError, AttributeError):
        return ""


def pristupy(data_dir):
    """Id přístupů z data/web.json → pristupy (fork), nebo None, když web přístupy nemá."""
    try:
        with open(os.path.join(data_dir, "web.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return None
    from pohled import nacti_pristupy   # stejné id jako export webu (tools/pohled.py)
    seznam = nacti_pristupy(cfg)
    return [p["id"] for p in seznam] if seznam else None


def over_pristup(data_dir, pid):
    """Chybová hláška, když přístup pid ve web.json není; jinak None. „vse“ = celý web (bez přístupů vždy)."""
    ids = pristupy(data_dir)
    if ids is None:
        return None if pid == "vse" else f"CHYBA: web.json nemá přístupy (pristupy), odkaz může vést jen na celý web"
    if pid not in ids:
        return f"CHYBA: přístup „{pid}“ ve web.json není (jsou: {', '.join(ids)})"
    return None


def vypis_odkaz(data_dir, jmeno, klic):
    base = adresa(data_dir)
    print(f"Odkaz pro {jmeno} (uložte si ho, znovu se neukáže):")
    print(f"  {base}/?k={klic}")
    if not base:
        print("POZOR: v data/web.json chybí prihlaseni.adresa (třeba https://<název>.netlify.app), "
              "před /?k= doplňte adresu webu.")


def main(argv, data_dir, today):
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "seznam" and not args:
        odkazy = [z for z in load(data_dir) if "zruseno" not in z]
        if not odkazy:
            print("Žádné odkazy. Nový: pozvanky.py pridej \"Jméno\"")
        for z in odkazy:
            print(f"{z['id']:>4}  {z['vytvoreno']}  {z['jmeno']}" + (f"  (přístup {z['pristup']})" if z.get("pristup") else ""))
        return 0
    pid = None
    if cmd == "pridej" and len(args) == 3 and args[1] == "--pristup":
        args, pid = args[:1], args[2]
        chyba = over_pristup(data_dir, pid)
        if chyba:
            print(chyba, file=sys.stderr)
            return 1
    if cmd == "pridej" and len(args) == 1 and args[0].strip():
        odkazy = load(data_dir)
        klic = secrets.token_urlsafe(16)   # 128 bitů, 22 znaků
        cisla = [int(z["id"][1:]) for z in odkazy]
        odkazy.append({"id": f"p{max(cisla, default=0) + 1}", "jmeno": args[0].strip(),
                       "otisk": otisk(klic), "vytvoreno": today, **({"pristup": pid} if pid and pid != "vse" else {})})
        save(data_dir, odkazy)
        vypis_odkaz(data_dir, args[0].strip(), klic)
        print(NASADIT)
        return 0
    if cmd in ("prejmenuj", "pristup", "nova", "zrus") and len(args) == (2 if cmd in ("prejmenuj", "pristup") else 1):
        odkazy = load(data_dir)
        z = next((z for z in odkazy if z["id"] == args[0] and "zruseno" not in z), None)
        if z is None:
            print(f"CHYBA: odkaz {args[0]} neexistuje nebo je zrušený (seznam: pozvanky.py seznam)", file=sys.stderr)
            return 1
        if cmd == "pristup":
            chyba = over_pristup(data_dir, args[1])
            if chyba:
                print(chyba, file=sys.stderr)
                return 1
            if args[1] == "vse":
                z.pop("pristup", None)
            else:
                z["pristup"] = args[1]
            save(data_dir, odkazy)
            print(f"{z['id']} ({z['jmeno']}) teď vede na " + ("celý web." if args[1] == "vse" else f"přístup {args[1]}."))
        elif cmd == "prejmenuj":
            if not args[1].strip():
                print("CHYBA: prázdné jméno", file=sys.stderr)
                return 1
            z["jmeno"] = args[1].strip()
            save(data_dir, odkazy)
            print(f"{z['id']} se teď jmenuje {z['jmeno']}.")
        elif cmd == "nova":
            klic = secrets.token_urlsafe(16)
            z["otisk"], z["vytvoreno"] = otisk(klic), today
            save(data_dir, odkazy)
            vypis_odkaz(data_dir, z["jmeno"], klic)
            print("Starý odkaz přestane platit.")
        else:
            del z["otisk"]   # záznam zůstane, aby se id nedostalo jinému člověku
            z["zruseno"] = today
            save(data_dir, odkazy)
            print(f"Odkaz {z['id']} ({z['jmeno']}) zrušen.")
        print(NASADIT)
        return 0
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], DATA, datetime.date.today().isoformat()))
