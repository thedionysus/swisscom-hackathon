"""Minimal XLSX reader (no openpyxl): prints rows of sheet1. usage: xlsx_read.py FILE [maxrows]"""
import sys, zipfile, re, html
fn=sys.argv[1]; mx=int(sys.argv[2]) if len(sys.argv)>2 else 12
z=zipfile.ZipFile(fn)
names=z.namelist()
ss=[]
if 'xl/sharedStrings.xml' in names:
    x=z.read('xl/sharedStrings.xml').decode('utf-8')
    for si in re.findall(r'(?s)<si>(.*?)</si>',x):
        ss.append(html.unescape(''.join(re.findall(r'(?s)<t[^>]*>(.*?)</t>',si))))
sheets=sorted(n for n in names if n.startswith('xl/worksheets/sheet'))
for sn in sheets:
    sh=z.read(sn).decode('utf-8')
    rows=re.findall(r'(?s)<row [^>]*>(.*?)</row>',sh)
    out=[]
    for r in rows:
        cells=[]
        for attrs,body in re.findall(r'(?s)<c ([^>]*?)(?:/>|>(.*?)</c>)',r):
            t=re.search(r't="(\w+)"',attrs); v=re.search(r'(?s)<v>(.*?)</v>',body or '')
            val=v.group(1) if v else ''
            if t and t.group(1)=='s' and val: val=ss[int(val)]
            if t and t.group(1)=='inlineStr': val=''.join(re.findall(r'(?s)<t[^>]*>(.*?)</t>',body))
            cells.append(val)
        out.append(cells)
    print('##',sn,'rows',len(out),'hyperlinks',len(re.findall(r'<hyperlink ',sh)))
    for c in out[:mx]: print('  ',c[:12])
    num=[c for c in out if c and re.fullmatch(r'\d+(\.0)?',c[0] or '')]
    print('   numbered rows:',len(num))
    if num: print('   last:',num[-1][:12])
