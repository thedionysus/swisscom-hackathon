import subprocess, json, sys
P='KArfO5bFd0CkaahGqsNmbQ'
def get(u):
    r=subprocess.run(['curl','-sL','--compressed','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-H','Accept: application/json','-w','\n%{http_code} %{content_type} %{size_download}',u],capture_output=True,text=True)
    b,meta=r.stdout.rsplit('\n',1); return meta,b
for path in [f'/api/OutlineApi/full?projectId={P}', f'/api-nocache/ArticlesApi/index?projectId={P}&skip=0&take=5&requireTotalCount=true', f'/api-nocache/FilesApi/index?projectId={P}&skip=0&take=3&requireTotalCount=true']:
    meta,b=get('https://sh.lexican.cloud'+path)
    print(meta,'|',path)
    try:
        d=json.loads(b)
        if isinstance(d,dict): print('   keys',list(d.keys())[:8],'| totalCount',d.get('totalCount')); items=d.get('data') or []
        else: items=d; print('   list len',len(d))
        def count(nodes):
            n=0
            for x in nodes:
                n+=1; n+=count(x.get('ChildArticles') or x.get('items') or [])
            return n
        if 'Outline' in path: print('   tree nodes total:',count(items)); 
        for it in items[:5]: print('   ',json.dumps(it,ensure_ascii=False)[:260])
    except Exception as e: print('   not json',b[:200])
