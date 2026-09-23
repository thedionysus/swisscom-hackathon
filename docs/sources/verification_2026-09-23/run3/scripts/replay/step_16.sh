S=<scratchpad>; mkdir -p <scratchpad>/sgchk/courts
python3 - "$S" <<'E'
import sys,subprocess,re,json,hashlib,concurrent.futures as cf
S=sys.argv[1];sys.path.insert(0,S)
from courts_s1_rows import ROWS
u={}
for r in ROWS:
    for c in r[2:]: u.setdefault(c[2:],set()).add(c[0])
UA='Mozilla/5.0 swiss-grounding-check'
def probe(url):
    f='<scratchpad>/sgchk/courts/'+hashlib.md5(url.encode()).hexdigest()
    try:
        out=subprocess.run(['curl','-sL','-g','--max-time','25','-A',UA,'-o',f,'-w','%{http_code}|%{content_type}|%{size_download}|%{url_effective}',url],capture_output=True,text=True,timeout=40).stdout
        code,ct,size,final=out.split('|',3)
    except Exception as e:
        return url,{'code':'ERR','err':str(e)[:60]}
    try: body=open(f,encoding='utf-8',errors='ignore').read()
    except Exception: body=''
    t=re.search(r'<title[^>]*>(.*?)</title>',body,re.S|re.I)
    title=re.sub(r'\s+',' ',t.group(1)).strip()[:80] if t else ''
    links=len(re.findall(r'<a\s[^>]*href',body,re.I))
    words=len(re.sub(r'<[^>]+>',' ',re.sub(r'(?s)<(script|style)[^>]*>.*?</\1>','',body)).split())
    return url,{'code':code,'ct':ct.split(';')[0],'size':int(float(size)),'final':final,'title':title,'links':links,'words':words}
res={}
with cf.ThreadPoolExecutor(8) as ex:
    for url,r in ex.map(probe,list(u)): res[url]=r; res[url]['grounded']='D' in u[url]
json.dump(res,open(f'{S}/courts_s1_probe.json','w'),ensure_ascii=False,indent=1)
print('probed',len(res))
E
