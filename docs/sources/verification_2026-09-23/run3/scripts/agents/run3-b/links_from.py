import re,html,sys
f,rx=sys.argv[1],sys.argv[2]
t=open(f,encoding="utf-8",errors="ignore").read()
seen=[]
for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.I|re.S):
    h=m.group(1); a=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",m.group(2)))).strip()
    if re.search(rx,h+" "+a,re.I) and (h,a) not in seen: seen.append((h,a))
print(len(seen)); print("; ".join(f"{h} [{a[:50]}]" for h,a in seen))
print("i-web signature:", bool(re.search(r"i-web\.ch|_rtr/|_doc/|_rte/", t)), re.findall(r"(stats\.i-web\.ch|pcdn\d?\.i-web\.ch|/_rte/[a-z]+|/_doc/)", t)[:5])
