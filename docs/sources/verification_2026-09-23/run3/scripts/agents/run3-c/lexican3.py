import subprocess, json, re, html
P='KArfO5bFd0CkaahGqsNmbQ'; J='<scratchpad>/run3-c/lexican_cookies.txt'
def get(u):
    r=subprocess.run(['curl','-sL','--compressed','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-b',J,'-c',J,'-H','X-Requested-With: XMLHttpRequest','-w','\n%{http_code} %{content_type} %{size_download}',u],capture_output=True,text=True)
    b,meta=r.stdout.rsplit('\n',1); return meta,b
A='RYyIYQMgFlXXkgUR'
for pre in ['/api','/api-nocache']:
    for ep in ['content','info']:
        m,b=get(f'https://sh.lexican.cloud{pre}/ArticlesApi/{ep}?articleId={A}&projectId={P}')
        t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',b)))
        print(m,'|',pre,ep,'|',t[:420])

m,b=get(f'https://sh.lexican.cloud/api/ArticlesApi/content?articleId={A}&projectId={P}')
print('RAW', b[:1144])
fid=re.findall(r'fileId=([A-Za-z0-9]+)|data-file-id="([^"]+)"|/Files/[A-Za-z]+\?[^"]*?fileId=([A-Za-z0-9]+)',b)
print('file ids',fid)
