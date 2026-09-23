import re
S="<scratchpad>/stage0/sitemaps/www.sz.ch.txt"
urls=[l.strip() for l in open(S) if l.strip()]
print("sz urls:",len(urls))
want=["/behoerden/justiz.html/","verwaltungsgericht/kosten-und-entschaedigungen","kantonsgericht/gesetze-und-richtlinien","verwaltungsgericht/themen","kantonsgericht/eingaben","/entscheidsammlungen","kantonsgericht/rechtsprechung","/vermittleraemter","baudepartement/verkehrsamt.html/","verkehrsamt/strassenverkehr.html/","fahrzeuglenker/fuehrerausweis.html/","staatskanzlei.html/","staatskanzlei/amtsblatt","/kanton/amtsblatt","schwyzer-steuerbuch/steuerrechtliche-weisungen","schwyzer-steuerbuch/tarife"]
for w in want:
    for u in urls:
        if w in u: print(w,"=>",u); break
print("--- schul/ferien/bezirk/gemeinde/gebuehr/steuerbuch counts")
for k in ["volksschul","schulferien","ferien","bezirk","gemeinde","gebuehr","schwyzer-steuerbuch","justiz/","verkehrsamt","veterin","laboratorium"]:
    hits=[u for u in urls if k in u.lower()]
    print(k,len(hits), [re.sub(r"https://www.sz.ch","",h) for h in hits[:6]])
