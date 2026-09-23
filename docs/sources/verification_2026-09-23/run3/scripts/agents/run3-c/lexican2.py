import subprocess, json
P='KArfO5bFd0CkaahGqsNmbQ'; J='<scratchpad>/run3-c/lexican_cookies.txt'
def get(u,accept='application/json'):
    r=subprocess.run(['curl','-sL','--compressed','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-b',J,'-c',J,'-H','Accept: '+accept,'-H','X-Requested-With: XMLHttpRequest','-w','\n%{http_code} %{content_type} %{size_download}',u],capture_output=True,text=True)
    b,meta=r.stdout.rsplit('\n',1); return meta,b
m,b=get(f'https://sh.lexican.cloud/Project/Details/{P}/article/aoFNqnTRdogvkpgo','text/html'); print('page',m)
print(open(J).read()[-400:])
for path in [f'/api/OutlineApi/full?projectId={P}', f'/api-nocache/ArticlesApi/index?projectId={P}&skip=0&take=5&requireTotalCount=true']:
    m,b=get('https://sh.lexican.cloud'+path); print(m,'|',path); print('   ',b[:600])

m,b=get(f'https://sh.lexican.cloud/api/OutlineApi/full?projectId={P}')
tree=json.loads(b)
def walk(nodes,d=0,acc=None):
    for x in nodes:
        acc.append((d,x['Title'],x['ArticleId'],x.get('Children')))
        walk(x.get('ChildArticles') or [],d+1,acc)
    return acc
acc=walk(tree,0,[])
print('TREE nodes',len(acc),'leaves',sum(1 for a in acc if not a[3]))
for a in acc[:14]: print('  '*a[0],a[1][:80],a[2])
