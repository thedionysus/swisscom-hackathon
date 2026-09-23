import csv, re, sys
p=sys.argv[1]
rows=list(csv.DictReader(open(p)))
ABS=re.compile(r'https?://[^\s`\'"<>\]\)|,;]+')
c1host={}
for r in rows:
    if r['cell']=='C1' and r['urls']:
        c1host.setdefault(r['canton'], re.match(r'https?://[^/]+', r['urls'].split()[0]).group(0))
for r in rows:
    guess=[]
    if not r['urls']:
        cell=ABS.sub(' ', r['url_cell'])
        # host without scheme, e.g. www.baselland.ch/politik-und-behorden/gerichte
        for m in re.finditer(r'(?<![\w./…])((?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.ch/[^\s`\'"<>\]\)|,;=]*)', cell):
            guess.append('https://'+m.group(1).rstrip('.'))
        cell2=re.sub(r'(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.ch/[^\s`\'"<>\]\)|,;]*',' ',cell)
        host=c1host.get(r['canton'])
        for m in re.finditer(r'(?<![\w.…/])(/[A-Za-z0-9%_\-./?=&:~+]+)', cell2):
            path=m.group(1).rstrip('.,')
            if host and len(path)>2 and not path.startswith('//'): guess.append(host+path)
    r['urls_inferred_host']=' '.join(dict.fromkeys(guess))
fields=list(rows[0].keys())
fields.insert(fields.index('urls_elsewhere_in_row')+1, fields.pop(fields.index('urls_inferred_host')))
with open(p,'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
none=[r for r in rows if not (r['urls'] or r['urls_elsewhere_in_row'] or r['urls_inferred_host'])]
print('rows',len(rows),'| explicit URLs',sum(1 for r in rows if r['urls']),'| inferred-host only',sum(1 for r in rows if not r['urls'] and r['urls_inferred_host']),'| still none',len(none))
for r in none: print('   none:',r['agent'],r['canton'],r['cell'],'|',r['url_cell'][:100])
