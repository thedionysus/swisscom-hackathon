import re,subprocess,collections
D="<scratchpad>/run3-b/pages/"
main=open(D+"wissen_main.js",encoding="utf-8",errors="ignore").read()
chunks=sorted(set(re.findall(r'chunk-[A-Z0-9]+\.js',main)))
hits=collections.Counter()
for c in chunks:
    r=subprocess.run(["curl","-s","--compressed","-A","Mozilla/5.0 swiss-grounding-check","https://wissen.zg.ch/"+c],capture_output=True)
    s=r.stdout.decode("utf-8","ignore")
    for m in re.findall(r'["`\'](/?(?:api|rest|backend|services?)/[A-Za-z0-9_/${}.:-]{2,80})["`\']',s): hits[(c,m)]+=1
    for m in re.findall(r'https?://[a-z0-9.-]+\.zg\.ch/[A-Za-z0-9_/.-]{0,60}',s): hits[(c,m)]+=1
for (c,m),n in hits.most_common(25): print(n,c,m)
print("chunks:",len(chunks))
