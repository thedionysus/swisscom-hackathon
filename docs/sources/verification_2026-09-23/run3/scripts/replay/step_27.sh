S=<scratchpad>; mkdir -p $S/stage0
python3 - "$S" <<'E'
import sys,json,subprocess,concurrent.futures as cf
S=sys.argv[1]
UA='Mozilla/5.0 swiss-grounding-check'
LW={'BS':'gesetzessammlung.bs.ch','BE':'belex.sites.be.ch','BL':'bl.clex.ch','LU':'srl.lu.ch','ZG':'bgs.zg.ch','GL':'gesetze.gl.ch',
    'TG':'rechtsbuch.tg.ch','AR':'ar.clex.ch','AI':'ai.clex.ch','SH':'sh.clex.ch','NW':'gesetze.nw.ch','UR':'rechtsbuch.ur.ch',
    'OW':'gdb.ow.ch','SG':'gesetzessammlung.sg.ch','AG':'gesetzessammlungen.ag.ch','GR':'gr-lex.gr.ch','SO':'bgs.so.ch','VS':'lex.vs.ch','FR':'bdlf.fr.ch'}
LANG={'VS':['fr','de'],'FR':['fr','de']}
def get(url):
    r=subprocess.run(['curl','-sL','--max-time','40','-A',UA,url],capture_output=True,text=True)
    return r.stdout
def fetch(c):
    for host in (LW[c],'www.'+LW[c]):
        for lang in LANG.get(c,['de']):
            txt=get(f'https://{host}/api/{lang}/texts_of_law/lightweight_index')
            try: d=json.loads(txt)
            except Exception: continue
            items=[x for v in d.values() for x in v] if isinstance(d,dict) else []
            if items:
                json.dump({'host':host,'lang':lang,'items':items},open(f'{S}/stage0/laws_{c}.json','w'),ensure_ascii=False)
                return c,host,lang,len(items),sum(1 for x in items if not x.get('abrogated'))
    return c,None,None,0,0
with cf.ThreadPoolExecutor(6) as ex:
    for c,host,lang,n,act in ex.map(fetch,sorted(LW)):
        print(f'{c:3} {str(host):32} {str(lang):3} texts {n:5} active {act}')
E
