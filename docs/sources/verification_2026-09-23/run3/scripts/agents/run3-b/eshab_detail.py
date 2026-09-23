import json,subprocess,re
UA="Mozilla/5.0 swiss-grounding-check"
def get(url,acc="application/json"):
    r=subprocess.run(["curl","-s","--compressed","-A",UA,"-H","Accept: "+acc,"-w","\n%{http_code}\t%{content_type}",url],capture_output=True,text=True)
    body,meta=r.stdout.rsplit("\n",1)
    return meta,body
for dom in ["amtsblatt.sz.ch","amtsblatt.nw.ch","amtsblatt.ow.ch"]:
    meta,body=get(f"https://{dom}/robots.txt","text/plain")
    print(dom,"robots:",meta,repr(body[:60]))
pid="3a81280b-5acc-46ee-addc-40f4152ddde2"
for suffix,acc in [("", "application/json"),("/xml","application/xml")]:
    url=f"https://amtsblatt.zg.ch/api/v1/publications/{pid}{suffix}"
    meta,body=get(url,acc)
    print("==",url,meta,len(body),"B")
    if suffix=="":
        try:
            d=json.loads(body); print("   keys:",list(d.keys())); print("   content:",json.dumps(d.get("content"),ensure_ascii=False)[:700])
        except Exception: print(body[:400])
    else:
        txt=re.sub(r"<[^>]+>"," ",body); txt=re.sub(r"\s+"," ",txt)
        print("   xml text:",txt[:600])
