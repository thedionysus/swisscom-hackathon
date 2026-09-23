import re
S="<scratchpad>/stage0/sitemaps/zg.ch.txt"
urls=[l.strip() for l in open(S) if l.strip()]
de=[u for u in urls if "/de/" in u]
print("zg urls:",len(urls),"de:",len(de))
topics={"C1/C3 gerichte":r"/de/gerichte($|/)|/de/recht-justiz($|/)","C2 kosten":r"kosten|gebuehr|tarif","C4 entscheide":r"entscheid|rechtsprechung|urteil","C5 schlichtung":r"schlicht|friedens|vermittl","G1 hunde":r"hund|veterin|tierschutz","G2 steuer":r"steuerbuch|wegleitung|steuerpraxis|/steuern($|/)|steuerverwaltung","G3 ferien":r"ferien|schuljahr","G4 strassenverkehr":r"strassenverkehrsamt","D1 gemeinden":r"/gemeinden($|/)|gemeinden$","D2 kanzlei/amtsblatt":r"staatskanzlei($|/)|amtsblatt"}
for k,rx in topics.items():
    hits=sorted([u for u in de if re.search(rx,u,re.I)],key=len)
    print(f"--- {k}: {len(hits)}")
    for u in hits[:14]: print("   ",u.replace("https://zg.ch",""))
