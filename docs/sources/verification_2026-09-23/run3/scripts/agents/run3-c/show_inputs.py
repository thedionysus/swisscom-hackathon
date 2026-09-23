import json
SP='<scratchpad>'
MY=('SG','TG','AR','AI','SH')
for fn in ['guidance_s3a_probe.json','s3b_s4_probe.json']:
    d=json.load(open(SP+'/'+fn))
    print('#####',fn,type(d).__name__,len(d))
    items=d if isinstance(d,list) else list(d.values())
    for it in items:
        if isinstance(it,dict) and it.get('canton') in MY:
            print(' ',it.get('canton'),it.get('topic'),it.get('kind'),it.get('code'),it.get('cls'),'|',it.get('url'),'->',it.get('final') if it.get('final')!=it.get('url') else '=','|',(it.get('title') or '')[:60],'|',it.get('size'))
d=json.load(open(SP+'/courts_s1_probe.json'))
print('##### courts_s1_probe my cantons')
for k,v in d.items():
    if any(x in k for x in ['sg.ch','tg.ch','ar.ch','ai.ch','sh.ch']):
        print(' ',v.get('code'),v.get('class'),'|',k,'->',v.get('final') if v.get('final')!=k else '=','|',(v.get('title') or '')[:60])
