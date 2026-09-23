import re, html, json, subprocess, glob
B='<scratchpad>/run3-c'
S0='<scratchpad>/stage0/sitemaps'
def rd(p): return open(p,encoding='utf-8',errors='ignore').read()
def tx(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s)))
# 1 SG Steuerbuch
s=rd(B+'/pages/www_sg_ch_steuern_finanzen_steuern_steuerbuch_inhaltsverzeichnis_html_d24bfa')
hrefs=re.findall(r'href="([^"]+)"',s); pdf=[h for h in hrefs if '/steuerbuch/' in h and '.pdf' in h.lower()]
e=set(re.findall(r'StB (\d+[a-z]*) Nr\. ?(\d+)',tx(s)))
print('1) SG Steuerbuch: pdf links',len(pdf),'unique',len(set(pdf)),'| StB entries',len(e))
one=[h for h in pdf if re.search(r'/0\d\d_\d\.pdf',h)][:1]
print('   sample pdf',one)
# 5 SH sitemap fees
sh=rd(S0+'/sh.ch.txt').split()
print('5) SH sitemap URLs with Geb-hr|Kosten|Tarif:',[u for u in sh if re.search(r'Geb-hr|Kosten|Tarif',u)][:6])
# 6 AR Weisungen PDFs
a=rd(B+'/pages/ar_ch_verwaltung_departement_finanzen_steuerverwaltung_gesetzeweisungenmerkblaetter__225c90')
k=a.find('id="mainCol"'); ap=set(re.findall(r'href="([^"]+\.pdf)"',a[k:]))
print('6) AR tax Weisungen/Merkblätter PDF links (main col):',len(ap))
# 7 SH chancellery label search in saved SH pages
for f in glob.glob(B+'/pages/sh_*')+glob.glob(B+'/pages/sh_ch_*'):
    t=rd(f)
    for m in re.finditer(r'"contentid":"(\d+)"[^{}]{0,400}?"(?:kachellabel|label)":"Staatskanzlei"[^{}]{0,300}?"permalink":"([^"]+)"',t):
        print('7) SH Staatskanzlei item',m.group(1),m.group(2)); break
# 4 SH holiday PDF file id
for f in glob.glob(B+'/pages/sh_*'):
    t=rd(f)
    if 'Planung_Ferien-Brueckentage' in t:
        m=re.search(r'Planung_Ferien-Brueckentage_2025-2035\.pdf.{0,400}',t)
        ids=re.findall(r'/CMS/get/file/([0-9a-f\-]{36})',t[max(0,t.find('Planung_Ferien-Brueckentage')-1500):t.find('Planung_Ferien-Brueckentage')+200])
        print('4) SH holiday pdf file ids near name:',ids[:3]); break
