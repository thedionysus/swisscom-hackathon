import json,subprocess
UA="Mozilla/5.0 swiss-grounding-check"
def get(u):
    r=subprocess.run(["curl","-s","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",u],capture_output=True,text=True)
    b,c=r.stdout.rsplit("\n",1); return c,b
c,b=get("https://www.lexfind.ch/api/fe/de/entities")
d=json.loads(b)
print(c,type(d),len(d))
for e in d:
    s=json.dumps(e,ensure_ascii=False)
    if '"SZ"' in s or "Schwyz" in s:
        print(s[:800])
