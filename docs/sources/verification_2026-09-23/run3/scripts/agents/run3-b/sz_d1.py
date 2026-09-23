import re,hashlib,html
D="<scratchpad>/run3-b/pages/"
u="https://www.sz.ch/verwaltung/finanzdepartement/steuerverwaltung/steuerbezug-steuerrechnung/gemeinden-bezirke.html/8756-8758-8802-10332-10354-10494-10498"
raw=open(D+hashlib.md5(u.encode()).hexdigest()[:12],encoding="utf-8",errors="ignore").read()
main=re.search(r"<main[^>]*>(.*?)</main>",raw,re.S).group(1)
links=[(h,re.sub(r"<[^>]+>","",t).strip()) for h,t in re.findall(r'<a\s[^>]*href="(https?://www\.[^"]+)"[^>]*>(.*?)</a>',main,re.S)]
sites=[(h,t) for h,t in links if "sz.ch" not in h and "google" not in h]
print("commune website links:",len(sites)); print([t for h,t in sites])
u2="https://www.sz.ch/verwaltung/bildungsdepartement/amt-fuer-volksschulen-und-sport/schulorganisation/ferienplaene.html/8756-8758-8802-9466-9467-11460-11466"
raw2=open(D+hashlib.md5(u2.encode()).hexdigest()[:12],encoding="utf-8",errors="ignore").read()
m=re.search(r"<main[^>]*>(.*?)</main>",raw2,re.S)
t=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",m.group(1) if m else raw2)))
for mm in list(re.finditer(r"Ferien",t))[:4]: print("  ~",t[max(0,mm.start()-200):mm.end()+250])
print([h for h in re.findall(r'href="([^"]+)"',m.group(1) if m else raw2) if "erien" in h][:6])
