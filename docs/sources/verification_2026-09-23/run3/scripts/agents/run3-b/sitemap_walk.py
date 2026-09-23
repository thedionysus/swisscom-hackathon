import sys,re,subprocess,gzip
UA="Mozilla/5.0 swiss-grounding-check"
def get(u):
    r=subprocess.run(["curl","-sL","--compressed","-A",UA,u],capture_output=True)
    b=r.stdout
    if b[:2]==b"\x1f\x8b": b=gzip.decompress(b)
    return b.decode("utf-8","ignore")
root=sys.argv[1]; rx=re.compile(sys.argv[2],re.I) if len(sys.argv)>2 else None
todo=[root]; urls=[]; seen=set()
while todo and len(seen)<60:
    s=todo.pop(0)
    if s in seen: continue
    seen.add(s)
    x=get(s)
    locs=re.findall(r"<loc>\s*([^<\s]+)\s*</loc>",x)
    if "<sitemapindex" in x:
        print("index",s,"children",len(locs)); todo+=locs
    else:
        print("urlset",s,len(locs)); urls+=locs
print("total urls:",len(urls))
if rx:
    hits=[u for u in urls if rx.search(u)]
    print("matching",rx.pattern,":",len(hits))
    for u in hits[:60]: print("  ",u)
