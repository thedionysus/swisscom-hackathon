"""Download PDFs and test the text layer. usage: pdf_check.py [-g REGEX] URL [URL ...]"""
import sys, subprocess, re, os, hashlib, json, time
B='<scratchpad>/run3-c'
os.makedirs(B+'/pdfs',exist_ok=True)
args=sys.argv[1:]; pat=None
if args and args[0]=='-g': args.pop(0); pat=re.compile(args.pop(0),re.I)
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader=None
for u in args:
    fn=B+'/pdfs/'+hashlib.md5(u.encode()).hexdigest()[:10]+'.pdf'
    r=subprocess.run(['curl','-sL','-g','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-o',fn,'-w','%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}',u],capture_output=True,text=True)
    print(r.stdout.replace('\t',' | '))
    print('   url:',u)
    with open(B+'/requests.jsonl','a') as fh: fh.write(json.dumps({'t':time.strftime('%H:%M:%S'),'url':u,'curl':r.stdout})+'\n')
    if PdfReader is None: print('   pypdf missing'); continue
    try:
        rd=PdfReader(fn); n=len(rd.pages)
        txt='\n'.join((p.extract_text() or '') for p in rd.pages[:6])
        t=re.sub(r'\s+',' ',txt)
        print(f'   pages {n} | chars(first<=6 pages) {len(t)} | text layer: {"yes" if len(t.strip())>50 else "NO (scanned?)"}')
        print('   start:',t[:260])
        if pat:
            k=0
            for m in pat.finditer(t):
                print('   >>',t[max(0,m.start()-120):m.end()+160]); k+=1
                if k>=3: break
            if not k: print('   >> (no match)')
    except Exception as e:
        print('   pdf error',e)
