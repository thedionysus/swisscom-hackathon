import re,html,subprocess
D="<scratchpad>/run3-b"
t=open(D+"/pages/ca3c9f3a016b",encoding="utf-8",errors="ignore").read()
links=re.findall(r'href="(/gemeinden/wahlkreise/[^/"]+/[^/"]+)"[^>]*>([^<]+)<',t)
uniq={}
for h,a in links: uniq[h]=a.strip()
print("commune detail links:",len(uniq))
print("wahlkreise:",sorted(set(h.split('/')[3] for h in uniq)))
print(list(uniq.items())[:3], list(uniq.items())[-2:])
mails=set(re.findall(r"spamschutz\('[^']*','([^']+)'\)",t))
print("distinct e-mail domains:",len(mails))
