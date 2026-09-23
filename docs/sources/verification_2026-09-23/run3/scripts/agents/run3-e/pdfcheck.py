"""python3 pdfcheck.py URL [URL ...] : download each PDF, report pages and first text, grep optional KW env (regex)."""
import sys, os, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h
from pypdf import PdfReader
KW = os.environ.get('KW')
N = int(os.environ.get('N', '400'))
for u in sys.argv[1:]:
    fn, code, ct, size, final, title = h.probe(u, quiet=True)
    print('==', code, ct, size, 'B', final)
    try:
        r = PdfReader(fn)
        txt = ''
        for p in r.pages[:6]:
            txt += (p.extract_text() or '') + '\n'
        clean = re.sub(r'\s+', ' ', txt)
        print('   pages', len(r.pages), '| chars in first 6 pages', len(clean.strip()))
        print('   ', clean[:N])
        if KW:
            alltxt = ''
            for p in r.pages:
                alltxt += (p.extract_text() or '') + '\n'
            alltxt = re.sub(r'\s+', ' ', alltxt)
            for m in list(re.finditer(KW, alltxt, re.I))[:4]:
                print('   [KW]', alltxt[max(0, m.start() - 150):m.end() + 150])
    except Exception as e:
        print('   pdf error', e)
