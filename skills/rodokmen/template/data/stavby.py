# Významné stavby a domy předků – dějiny jednotlivých domů (volitelné; zobrazí se na stránce Domy).
#
# Poloha domu (souřadnice, jistota, výřez skici) je v data/domy/ (výstup skillu stare-adresy). Sem patří to, co o domu
# víme jinak: kdo ho držel, kdo v něm žil, co se s ním dělo a co ještě nevíme. Postup a formát: reference/stavby.md.
# Kontrola: python3 -I tools/stavby.py kontrola     Náměty z rodokmenu: python3 -I tools/stavby.py kandidati
#
# Klíč = id adresy z data/domy/adresy.json (obec-čp bez diakritiky: "nova-ves-12"). Příklad jednoho záznamu:
#
# "nova-ves-12": dict(
#     nazev="Hostinec U Nováků", typ="hostinec", dum="nova-ves-12", st="prob", verejne=True,
#     popis="Rodinný hostinec, nejméně tři generace.",
#     cisla=[("1790–1830", "čp. 21 (?)"), ("od 1830", "čp. 12")],
#     udalosti=[dict(rok="1838", text="Dřevěná budova na indikační skici.", st="doc", zdroj="Indikační skica CAS…, 1838")],
#     drzitele=[dict(od="1786", do="1820", n="Jan Novák", os=12, jak="koupě", st="doc", r=["klic_zapisu"])],
#     obyvatele=[dict(os=6, role="hostinský", st="doc", r=["klic_zapisu"])],
#     pamatka=None,
#     otevrene=["Kdo dům držel před 1786? (pozemková kniha)"],
# ),
#
# Stavy (st): doc přečteno v pramenu (s r nebo zdroj) · lit z literatury (se zdroj) · prob pravděpodobné (v note proč) ·
#             fam od rodiny · unk neznámé.   os = Kekulého číslo z P (celé číslo) nebo klíč z RODINA; jinak jen n="Jméno".
# Žijící a lidé z posledních ~100 let: jen jméno a role. Držitel po roce 1950 jen se souhlasem (pole souhlas).

D = {
}

# Otevřené otázky ke stavbám, které nepatří k jednomu domu
ISSUES = []
