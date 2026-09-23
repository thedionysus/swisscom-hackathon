import sys, re, subprocess, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h
B = 'https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/dokumentation/praxis/Seiten/'
pages = ['einkommens_und_vermoegenssteuer.aspx', 'gewinn_und_kapitalsteuer.aspx', 'grundstueckgewinnsteuer.aspx',
         'verfahren.aspx', 'steuererlass.aspx', 'bezug_sicherung.aspx', 'steuerbefreiung.aspx']
allpdf = set()
for p in pages:
    fn, code, ct, size, final, title = h.probe(B + p, quiet=True)
    pdfs = sorted(set(x for x, _ in h.links(fn, r'\.pdf') if x.lower().endswith('.pdf') or '.pdf' in x.lower()))
    allpdf.update(pdfs)
    print(code, size, title, '| pdf links', len(pdfs), '|', pdfs[:2])
print('TOTAL distinct PDFs', len(allpdf))
w = 'https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/steuererklaerung/einkommens_und_vermoegenssteuer/Seiten/wegleitungen_merkblaetter.aspx'
fn, code, ct, size, final, title = h.probe(w, quiet=True)
wp = [(x, t) for x, t in h.links(fn, r'\.pdf')]
print('wegleitungen:', code, size, title, '| pdf links', len(wp))
for x, t in wp[:12]:
    print('   ', x, '|', t)
open(os.path.join(h.D, 'gr_tax_pdfs.txt'), 'w').write('\n'.join(sorted(allpdf)))
