import json,subprocess,sys,re,html
UA="Mozilla/5.0 swiss-grounding-check"
rx=re.compile(sys.argv[1],re.I)
for u in sys.argv[2:]:
    r=subprocess.run(["curl","-s","-g","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",u],capture_output=True,text=True)
    b,c=r.stdout.rsplit("\n",1)
    try: d=json.loads(b)
    except Exception: print("==",u,c,"non-JSON",b[:150]); continue
    tol=d.get("text_of_law",d)
    sv=tol.get("selected_version") or {}
    x=sv.get("xhtml_tol") or ""
    txt=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",x)))
    if not txt:
        txt=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",json.dumps(sv.get("json_content") or {},ensure_ascii=False))))
    print("==",u,c,"|",tol.get("systematic_number"),"|",(tol.get("title") or "")[:80],"| abbr:",tol.get("abbreviation"),"| enactment:",tol.get("enactment"),"| canonical:",tol.get("canonical_link"),"| textchars:",len(txt))
    for m in list(rx.finditer(txt))[:2]:
        print("   ~",txt[max(0,m.start()-150):m.end()+200])
