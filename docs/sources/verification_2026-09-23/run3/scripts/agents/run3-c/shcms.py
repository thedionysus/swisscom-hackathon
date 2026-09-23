"""Parse sh.ch CMS pages: window.CONTENT_DATA / CONTENT_LIST_DATA JSON. usage: shcms.py [-g REGEX] URL|FILE ..."""
import sys, re, json, html, subprocess, os, hashlib, time
B='<scratchpad>/run3-c'
args=sys.argv[1:]; pat=None
if args and args[0]=='-g': args.pop(0); pat=re.compile(args.pop(0),re.I)
def load(u):
    if os.path.exists(u): return '200 file',open(u,encoding='utf-8',errors='ignore').read()
    fn=B+'/pages/sh_'+hashlib.md5(u.encode()).hexdigest()[:10]+'.html'
    r=subprocess.run(['curl','-sL','--compressed','--max-time','40','-A','Mozilla/5.0 swiss-grounding-check','-o',fn,'-w','%{http_code} %{size_download}B %{url_effective}',u],capture_output=True,text=True)
    with open(B+'/requests.jsonl','a') as fh: fh.write(json.dumps({'t':time.strftime('%H:%M:%S'),'url':u,'curl':r.stdout})+'\n')
    return r.stdout, open(fn,encoding='utf-8',errors='ignore').read()
def clean(x):
    x=html.unescape(html.unescape(str(x)))
    x=re.sub(r'<[^>]+>',' ',x)
    return re.sub(r'\s+',' ',x).strip()
dec=json.JSONDecoder()
for u in args:
    meta,s=load(u)
    t=re.search(r'(?is)<title[^>]*>(.*?)</title>',s)
    print('=====',meta,'| title:',clean(t.group(1)) if t else '')
    print('   url:',u)
    for var in ['CONTENT_DATA','CONTENT_LIST_DATA']:
        m=re.search(r'window\.'+var+r'\s*=\s*',s)
        if not m: print('  no',var); continue
        try:
            obj,end=dec.raw_decode(s,m.end())
        except Exception as e:
            print('  decode fail',var,e); continue
        if isinstance(obj,str):
            try: obj=json.loads(obj)
            except Exception: pass
        items=obj if isinstance(obj,list) else (list(obj.values()) if isinstance(obj,dict) else [])
        print(f'  {var}: type={type(obj).__name__} n={len(items)}')
        for it in items[:60]:
            if not isinstance(it,dict): continue
            cid=it.get('contentid'); ct=it.get('contenttypeid')
            title=clean(it.get('data_kachellabel') or it.get('data_title') or it.get('title') or '')[:90]
            texts=[clean(v) for k,v in it.items() if k.startswith('data_') and isinstance(v,str) and ('content' in k or 'text' in k or 'lead' in k) and len(clean(v))>30]
            pdfs=re.findall(r'originalname\\?":\\?"([^"\\]+)',json.dumps(it,ensure_ascii=False))
            urls=re.findall(r'/CMS/get/file/[0-9a-f\-]{36}',json.dumps(it))
            print(f'   - id={cid} type={ct} date={it.get("transactiontime")} title="{title}" texts={len(texts)} chars={sum(len(x) for x in texts)} pdfs={pdfs[:3]} files={len(set(urls))}')
            if pat:
                for x in texts:
                    for mm in list(pat.finditer(x))[:2]:
                        print('       >>',x[max(0,mm.start()-120):mm.end()+160])

# --- permalink listing (appended) ---
def permalinks(s):
    m=re.search(r'window\.CONTENT_LIST_DATA\s*=\s*',s)
    out=[]
    if not m: return out
    obj,_=dec.raw_decode(s,m.end())
    for k,v in obj.items():
        for it in (v if isinstance(v,list) else []):
            if isinstance(it,dict) and it.get('permalink'):
                out.append((it.get('label',''),it['permalink'],it.get('contentid'),it.get('parent_repository'),it.get('publication_date')))
    return out
if os.environ.get('SH_LINKS'):
    for u in args:
        meta,s=load(u)
        pl=permalinks(s)
        print('  PERMALINKS',len(pl))
        for lab,p,cid,par,d in pl: print(f"     {str(cid):>9} parent={str(par):>9} {d} {clean(lab)[:60]} | https://sh.ch/CMS{p}")
