S=<scratchpad>
cat > $S/s3b_s4_rows.py <<'E'
# S3b (FR/IT guidance) and S4 (cantonal directories) as pasted by the user, 2026-09-23. Plain URLs, no Gemini wrapper signal.
ROWS=[
('S3b','VD','dogs','https://www.vd.ch/themes/environnement/animaux/chiens'),('S3b','VD','tax','https://www.vd.ch/themes/etat-droit-finances/impots/pour-les-individus/remplir-ma-declaration-dimpot/instructions-g-et-annexes'),('S3b','VD','school','https://www.vd.ch/themes/formation/scolarite-obligatoire/vacances-et-jours-feries'),('S3b','VD','road','https://www.vd.ch/themes/mobilite/automobile'),
('S3b','VS','dogs','https://www.vs.ch/web/scav/chiens'),('S3b','VS','tax','https://www.vs.ch/web/scc/personnes-physiques'),('S3b','VS','school','https://www.vs.ch/web/se/vacances-scolaires'),('S3b','VS','road','https://www.vs.ch/web/scn'),
('S3b','FR','dogs','https://www.fr.ch/sanu/animaux/chiens/detention-de-chiens'),('S3b','FR','tax','https://www.fr.ch/scc/impots/personnes-physiques/guide-pour-la-declaration-dimpot'),('S3b','FR','school','https://www.fr.ch/formation-et-ecoles/scolarite-obligatoire/vacances-scolaires'),('S3b','FR','road','https://www.ocn.ch/'),
('S3b','NE','dogs','https://www.ne.ch/autorites/DDTE/SCAV/sante-animale/Pages/Chiens.aspx'),('S3b','NE','tax','https://www.ne.ch/autorites/DFS/SCCO/personnes-physiques/Pages/accueil.aspx'),('S3b','NE','school','https://www.ne.ch/autorites/DEF/SECO/Pages/vacances-scolaires.aspx'),('S3b','NE','road','https://www.scan-ne.ch/'),
('S3b','JU','dogs','https://www.jura.ch/DEN/SCAV/Sante-animale/Chiens.html'),('S3b','JU','tax','https://www.jura.ch/DFN/IMP/Personnes-physiques/Guide-de-la-declaration-d-impot.html'),('S3b','JU','school','https://www.jura.ch/DFCS/SEN/Vacances-scolaires/Vacances-scolaires.html'),('S3b','JU','road','https://www.jura.ch/DEN/OVJ/Office-des-vehicules.html'),
('S3b','TI','dogs','https://www4.ti.ch/dss/dsp/uvc/settori/sanita-animale/cani'),('S3b','TI','tax','https://www4.ti.ch/dfe/dc/dichiarazione/istruzioni-e-moduli'),('S3b','TI','school','https://www4.ti.ch/decs/ds/scuola/calendario-scolastico'),('S3b','TI','road','https://www4.ti.ch/di/sezione-della-circolazione/sezione-della-circolazione'),
('S4','AG','communes','https://www.ag.ch/de/verwaltung/dvi/gemeinde-fachbereich'),('S4','AG','chancellery','https://www.ag.ch/de/verwaltung/staatskanzlei'),
('S4','AI','communes','https://www.ai.ch/politik-und-verwaltung/gemeinden'),('S4','AI','chancellery','https://www.ai.ch/politik-und-verwaltung/ratskanzlei'),
('S4','AR','communes','https://www.ar.ch/kanton/gemeinden/'),('S4','AR','chancellery','https://www.ar.ch/verwaltung/ratskanzlei/'),
('S4','BL','communes','https://www.baselland.ch/politik-und-behorden/gemeinden'),('S4','BL','chancellery','https://www.baselland.ch/politik-und-behorden/regierungsrat/landeskanzlei'),
('S4','BS','communes','https://www.bs.ch/portrait/gemeinden'),('S4','BS','chancellery','https://www.staatskanzlei.bs.ch/'),
('S4','BE','communes','https://www.jgk.be.ch/de/start/gemeinden.html'),('S4','BE','chancellery','https://www.sta.be.ch/de/start.html'),
('S4','FR','communes','https://www.fr.ch/etat-et-droit/communes'),('S4','FR','chancellery','https://www.fr.ch/ce/chancellerie-detat-cha'),
('S4','GE','communes','https://www.ge.ch/dossier/communes-genevoises'),('S4','GE','chancellery','https://www.ge.ch/organisation/chancellerie-etat'),
('S4','GL','communes','https://www.gl.ch/kanton-und-gemeinden/gemeinden.html'),('S4','GL','chancellery','https://www.gl.ch/verwaltung/staatskanzlei.html'),
('S4','GR','communes','https://www.gr.ch/DE/kanton/gemeinden/'),('S4','GR','chancellery','https://www.gr.ch/DE/institutionen/verwaltung/staka/'),
('S4','JU','communes','https://www.jura.ch/DFN/SCOM/Communes/Communes-jurassiennes.html'),('S4','JU','chancellery','https://www.jura.ch/CHA/Chancellerie-d-Etat.html'),
('S4','LU','communes','https://gem.lu.ch/'),('S4','LU','chancellery','https://staatskanzlei.lu.ch/'),
('S4','NE','communes','https://www.ne.ch/autorites/DDTE/SCOM/Pages/accueil.aspx'),('S4','NE','chancellery','https://www.ne.ch/autorites/CE/CH/Pages/accueil.aspx'),
('S4','NW','communes','https://www.nw.ch/gemeinden'),('S4','NW','chancellery','https://www.nw.ch/staatskanzlei'),
('S4','OW','communes','https://www.ow.ch/kanton/gemeinden'),('S4','OW','chancellery','https://www.ow.ch/staatskanzlei'),
('S4','SH','communes','https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Gemeinden-32338-DE.html'),('S4','SH','chancellery','https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Regierung/Staatskanzlei-1153163-DE.html'),
('S4','SZ','communes','https://www.sz.ch/kanton/gemeinden-bezirke.html'),('S4','SZ','chancellery','https://www.sz.ch/kanton/staatskanzlei.html'),
('S4','SO','communes','https://so.ch/staat/gemeinden/'),('S4','SO','chancellery','https://so.ch/staatskanzlei/'),
('S4','SG','communes','https://www.sg.ch/kanton-staat/gemeinden.html'),('S4','SG','chancellery','https://www.sg.ch/kanton-staat/kantonale-verwaltung/staatskanzlei.html'),
('S4','TG','communes','https://tg.ch/kanton/gemeinden.html'),('S4','TG','chancellery','https://staatskanzlei.tg.ch/'),
('S4','TI','communes','https://www4.ti.ch/di/sel/comuni/elenco-dei-comuni-ticinesi'),('S4','TI','chancellery','https://www4.ti.ch/can/oltre-confine/cancelleria-dello-stato'),
('S4','UR','communes','https://www.ur.ch/gemeinden'),('S4','UR','chancellery','https://www.ur.ch/staatskanzlei'),
('S4','VS','communes','https://www.vs.ch/web/sifom/communes'),('S4','VS','chancellery','https://www.vs.ch/web/che'),
('S4','VD','communes','https://www.vd.ch/toutes-les-communes'),('S4','VD','chancellery','https://www.vd.ch/etat-de-vaud/chancellerie-detat'),
('S4','ZG','communes','https://www.zg.ch/behoerden/gemeinden'),('S4','ZG','chancellery','https://www.zg.ch/behoerden/staatskanzlei'),
('S4','ZH','communes','https://www.zh.ch/de/politik-staat/gemeinden.html'),('S4','ZH','chancellery','https://www.zh.ch/de/staatskanzlei.html'),
]
E
python3 - "$S" <<'E'
import sys,subprocess,re,json,hashlib,time,threading,collections,concurrent.futures as cf
from urllib.parse import urlparse
S=sys.argv[1];sys.path.insert(0,S)
from s3b_s4_rows import ROWS
print('rows',len(ROWS),'unique',len({r[3] for r in ROWS}))
UA='Mozilla/5.0 swiss-grounding-check'
NF=re.compile(r'404|not found|nicht gefunden|introuvable|non trovat|existiert nicht|n.existe pas|ungültige adresse|fehler|erreur|just a moment',re.I)
SLOW={'www.sz.ch','www.gl.ch'};locks=collections.defaultdict(threading.Lock)
def probe(row):
    src,c,t,url=row;host=urlparse(url).netloc.lower()
    f='<scratchpad>/sgchk/courts/s34_'+hashlib.md5(url.encode()).hexdigest()
    lk=locks[host] if host in SLOW else threading.Lock()
    with lk:
        out=subprocess.run(['curl','-sL','-g','--max-time','25','-A',UA,'-o',f,'-w','%{http_code}|%{size_download}|%{url_effective}',url],capture_output=True,text=True).stdout
        if host in SLOW: time.sleep(3)
    try: code,size,final=out.split('|',2)
    except ValueError: code,size,final='ERR','0',''
    try: body=open(f,encoding='utf-8',errors='ignore').read()
    except Exception: body=''
    m=re.search(r'<title[^>]*>(.*?)</title>',body,re.S|re.I);title=re.sub(r'\s+',' ',m.group(1)).strip()[:70] if m else ''
    links=len(re.findall(r'<a\s[^>]*href',body,re.I))
    words=len(re.sub(r'<[^>]+>',' ',re.sub(r'(?s)<(script|style)[^>]*>.*?</\1>','',body)).split())
    def n(x):
        p=urlparse(x);return p.netloc.lower().removeprefix('www.').split(':')[0]+p.path.rstrip('/')
    if code in('000','ERR'): k='no-response'
    elif code!='200': k=f'http-{code}'
    elif NF.search(title): k='soft-404'
    elif n(final)==n(url): k='ok'
    elif urlparse(final).path.rstrip('/') in('','/fr','/de','/it','/de/home','/fr/home'): k='redirect-to-home'
    else: k='redirect'
    return dict(src=src,canton=c,topic=t,url=url,code=code,cls=k,final=final,title=title,size=int(float(size or 0)),links=links,words=words)
with cf.ThreadPoolExecutor(6) as ex: res=list(ex.map(probe,ROWS))
json.dump(res,open(f'{S}/s3b_s4_probe.json','w'),ensure_ascii=False,indent=1)
for src in ('S3b','S4'):
    L=[r for r in res if r['src']==src];print(src,len(L),dict(collections.Counter(r['cls'] for r in L)))
print()
for r in res:
    print(f"{r['src']:3} {r['canton']} {r['topic']:11} {r['cls']:16} {r['code']} {r['url'][:78]:78} -> {r['final'][:55] if r['cls']!='ok' else ''} | {r['title'][:42]} | l{r['links']} w{r['words']}")
E
