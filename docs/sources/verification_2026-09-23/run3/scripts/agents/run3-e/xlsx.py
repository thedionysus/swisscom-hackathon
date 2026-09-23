"""python3 xlsx.py FILE [maxrows] : minimal xlsx reader (shared strings + sheet1..n), prints rows."""
import sys, zipfile, re, html
fn = sys.argv[1]
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 15
z = zipfile.ZipFile(fn)
ss = []
if 'xl/sharedStrings.xml' in z.namelist():
    x = z.read('xl/sharedStrings.xml').decode('utf-8')
    for si in re.findall(r'<si>(.*?)</si>', x, re.S):
        ss.append(html.unescape(''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))))
sheets = sorted(n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml', n))
for sh in sheets:
    x = z.read(sh).decode('utf-8')
    rows = re.findall(r'<row[^>]*>(.*?)</row>', x, re.S)
    print('==', sh, 'rows', len(rows))
    out = []
    for r in rows:
        cells = []
        for attrs, body in re.findall(r'<c([^>]*)>(.*?)</c>', r, re.S):
            v = re.search(r'<v>(.*?)</v>', body, re.S)
            t = re.search(r't="(\w+)"', attrs)
            val = v.group(1) if v else re.sub(r'<[^>]+>', '', body)
            if t and t.group(1) == 's' and v:
                val = ss[int(val)]
            cells.append(val)
        out.append(cells)
    for c in out[:mx]:
        print('  ', c)
    if len(out) > mx:
        print('   ...', out[-2:])
    hl = re.findall(r'<hyperlink[^>]*>', x)
    print('   hyperlinks in sheet:', len(hl))
