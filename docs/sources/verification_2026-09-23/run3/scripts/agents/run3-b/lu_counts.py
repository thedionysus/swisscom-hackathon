import re,collections,subprocess,html
S="<scratchpad>/stage0/sitemaps/"
g=[l.strip() for l in open(S+"gerichte.lu.ch.txt") if l.strip()]
print("gerichte.lu.ch urls:",len(g))
c=collections.Counter(u.split("/")[3] for u in g if u.count("/")>=3)
print(" top-level sections:",dict(c))
rg=[u for u in g if "/rechtsgebiete" in u]
print(" /rechtsgebiete:",len(rg), dict(collections.Counter(u.split("/")[4] for u in rg if u.count("/")>=4)))
print(" /organisation/schlichtungsbehoerden:",sum("schlichtungsbehoerden" in u for u in g))
s=[l.strip() for l in open(S+"steuerbuch.lu.ch.txt") if l.strip()]
print("steuerbuch.lu.ch urls:",len(s), dict(collections.Counter(u.split("/")[3] for u in s if u.count("/")>=3)))
w=[l.strip() for l in open(S+"www.lu.ch.txt") if l.strip()]
print("www.lu.ch urls:",len(w)," kantonsblatt:",[u for u in w if "antonsblatt" in u.lower()], " gemeinden:",[u for u in w if "gemeinden" in u.lower()][:5])
v=[l.strip() for l in open(S+"strassenverkehrsamt.lu.ch.txt") if l.strip()]
print("strassenverkehrsamt.lu.ch urls:",len(v))
vs=[l.strip() for l in open(S+"volksschulbildung.lu.ch.txt") if l.strip()]
print("volksschulbildung.lu.ch urls:",len(vs)," ferien:",[u for u in vs if "ferien" in u.lower()])
r=subprocess.run(["curl","-s","-A","Mozilla/5.0 swiss-grounding-check","-w","\n%{http_code} %{content_type} %{size_download}","https://gerichte.lu.ch/recht_sprechung/lgve/Ajax?EnId=11116"],capture_output=True,text=True)
body,meta=r.stdout.rsplit("\n",1)
t=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",re.sub(r"<script.*?</script>|<style.*?</style>","",body,flags=re.S))))
print("LGVE Ajax EnId=11116:",meta); i=t.find("Instanz"); print("  ",t[max(0,i-100):i+400] if i>=0 else t[:500])
