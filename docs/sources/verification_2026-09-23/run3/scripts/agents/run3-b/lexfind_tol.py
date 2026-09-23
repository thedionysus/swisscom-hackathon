import json,subprocess,sys
UA="Mozilla/5.0 swiss-grounding-check"
for i in sys.argv[1:]:
    u=f"https://www.lexfind.ch/api/fe/de/texts-of-law/{i}"
    r=subprocess.run(["curl","-s","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",u],capture_output=True,text=True)
    b,c=r.stdout.rsplit("\n",1)
    d=json.loads(b)
    print("==",u,c)
    def show(x,p=""):
        if isinstance(x,dict):
            for k,v in x.items():
                if isinstance(v,(dict,list)): show(v,p+k+".")
                elif v not in (None,"",[]) and any(s in k for s in ("url","title","number","date","version","abbrev","in_force","language")):
                    print("   ",p+k,"=",str(v)[:160])
        elif isinstance(x,list):
            for j,v in enumerate(x[:3]): show(v,p+f"[{j}].")
    show(d)
