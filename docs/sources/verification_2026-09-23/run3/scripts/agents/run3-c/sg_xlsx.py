import subprocess, os, re, zipfile
B='<scratchpad>/run3-c'
url='https://www.sg.ch/content/dam/sgch/politik-verwaltung/gemeinden/%C3%BCber-die-gemeinden/politische%20Gemeinden.xlsx'
fn=B+'/sg_polgem.xlsx'
r=subprocess.run(['curl','-sL','-A','Mozilla/5.0 swiss-grounding-check','-o',fn,'-w','%{http_code} %{content_type} %{size_download}B %{url_effective}',url],capture_output=True,text=True)
print(r.stdout)
try:
    import openpyxl
    wb=openpyxl.load_workbook(fn,read_only=True)
    ws=wb.active
    rows=list(ws.iter_rows(values_only=True))
    print('rows',len(rows))
    for x in rows[:5]: print(x)
    data=[x for x in rows if x and isinstance(x[0],(int,float))]
    print('numbered rows',len(data)); print('last',data[-1] if data else None)
    print('names sample',[x[1] for x in data[:8]])
    # URL-ish cells?
    urls=[c for x in rows for c in (x or []) if isinstance(c,str) and ('http' in c or 'www.' in c)]
    print('url cells',len(urls),urls[:3])
except ImportError as e:
    print('openpyxl missing',e)
    z=zipfile.ZipFile(fn)
    sh=z.read('xl/worksheets/sheet1.xml').decode()
    print('rows',len(re.findall(r'<row ',sh)))
