"""Fetch robots.txt + sitemap(s) (following sitemap indexes) for hosts. usage: sitemap.py HOST [HOST...]
Writes run3-c/sitemaps/<host>.txt; prints robots lines of interest and counts."""
import sys, subprocess, re, os, gzip, time, html
B='<scratchpad>/run3-c'
os.makedirs(B+'/sitemaps',exist_ok=True)
UA='Mozilla/5.0 swiss-grounding-check'
def get(u):
    r=subprocess.run(['curl','-sL','-g','--max-time','40','-A',UA,'-w','\n__META__%{http_code} %{content_type}',u],capture_output=True)
    out=r.stdout
    i=out.rfind(b'\n__META__'); body=out[:i]; meta=out[i+9:].decode(errors='ignore')
    if body[:2]==b'\x1f\x8b':
        try: body=gzip.decompress(body)
        except Exception: pass
    return meta, body.decode('utf-8',errors='ignore')
for host in sys.argv[1:]:
    print('=====',host)
    meta,rb=get(f'https://{host}/robots.txt')
    print(' robots',meta, '|', ' ; '.join(l.strip() for l in rb.splitlines() if re.match(r'(?i)\s*(sitemap|crawl-delay|disallow: /$)',l))[:400] if meta.startswith('200') and '<html' not in rb[:300].lower() else '(no robots)')
    cands=[l.split(':',1)[1].strip() for l in rb.splitlines() if l.lower().startswith('sitemap:')] if meta.startswith('200') else []
    if not cands: cands=[f'https://{host}/sitemap.xml',f'https://{host}/sitemap_index.xml']
    urls=[]; seen=set(); queue=list(cands); n=0
    while queue and n<60:
        sm=queue.pop(0)
        if sm in seen: continue
        seen.add(sm); n+=1
        meta,b=get(sm)
        locs=[html.unescape(x.strip()) for x in re.findall(r'<loc>(.*?)</loc>',b,re.S)]
        is_index='<sitemapindex' in b
        print(f'  {sm} -> {meta} locs={len(locs)} index={is_index}')
        if is_index: queue+=locs
        else: urls+=locs
        time.sleep(0.3)
    urls=list(dict.fromkeys(urls))
    open(f'{B}/sitemaps/{host}.txt','w').write('\n'.join(urls)+'\n')
    print(f'  TOTAL urls {len(urls)} -> sitemaps/{host}.txt')
