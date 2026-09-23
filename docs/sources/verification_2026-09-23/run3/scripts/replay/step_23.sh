S=<scratchpad>
cat > $S/guidance_s3a_rows.py <<'E'
# S3a guidance table as pasted by the user (Gemini, 2026-09-23). D: direct link, G: wrapped in google.com/search?q= (ungrounded). utm stripped.
BL='https://www.baselland.ch/politik-und-verwaltung/direktionen'
ROWS=[
('AG','dogs','G:https://www.ag.ch/de/verwaltung/dvis/veterinaerdienst/hunde'),('AG','tax','G:https://www.ag.ch/de/verwaltung/dfr/steuern/steuern-natuerliche-personen/steuererklaerung'),('AG','school','G:https://www.ag.ch/de/verwaltung/bks/volksschule/schulbetrieb/schulferien'),('AG','road','G:https://www.ag.ch/de/verwaltung/dvs/strassenverkehrsamt'),
('LU','dogs','D:https://veterinaerdienst.lu.ch/hunde'),('LU','tax','D:https://steuerbuch.lu.ch'),('LU','school','G:https://volksschulbildung.lu.ch/schulbetrieb_organisation/so_schulferien'),('LU','road','D:https://strassenverkehrsamt.lu.ch'),
('SG','dogs','G:https://www.sg.ch/gesundheit-soziales/verbraucherschutz-veterinaerwesen/veterinaerwesen/hunde.html'),('SG','tax','D:https://www.sg.ch/steuern-finanzen/steuern/steuerbuch.html'),('SG','school','G:https://www.sg.ch/bildung-sport/volksschule/schulferien.html'),('SG','road','G:https://www.sg.ch/verkehr/strassenverkehrsamt.html'),
('TG','dogs','G:https://veterinaeramt.tg.ch/hunde.html'),('TG','tax','G:https://steuerverwaltung.tg.ch/steuerbuch.html'),('TG','school','G:https://av.tg.ch/schule/volksschule/schulbetrieb/schulferien.html'),('TG','road','D:https://strassenverkehrsamt.tg.ch'),
('SO','dogs','G:https://so.ch/staat/departemente/volkswirtschaftsdepartement/veterinaeramt/hunde/'),('SO','tax','G:https://so.ch/staat/departemente/finanzdepartement/steueramt/steuerbuch/'),('SO','school','G:https://so.ch/staat/departemente/departement-fuer-bildung-und-kultur/amt-fuer-volksschule/schulferien/'),('SO','road','G:https://so.ch/staat/departemente/bau-und-justizdepartement/motorfahrzeugkontrolle/'),
('BL','dogs',f'G:{BL}/volkswirtschafts-und-gesundheitsdirektion/amt-fuer-lebensmittelsicherheit-und-veterinaerwesen/veterinaerwesen/hunde'),('BL','tax',f'G:{BL}/finanz-und-kirchendirektion/steuerverwaltung/steuerbuch'),('BL','school',f'G:{BL}/bildungs-kultur-und-sportdirektion/pats/schulferien'),('BL','road',f'G:{BL}/sicherheitsdirektion/mfk'),
('SZ','dogs','G:https://www.sz.ch/verwaltung/departement-des-innern/laboratorium-der-urkantone/veterinaerdienst/hunde.html'),('SZ','tax','G:https://www.sz.ch/verwaltung/finanzdepartement/kantonale-steuerverwaltung/steuerbuch.html'),('SZ','school','G:https://www.sz.ch/kultur-bildung-sport/volksschulen/schulbetrieb/schulferien.html'),('SZ','road','G:https://www.sz.ch/verwaltung/sicherheitsdepartement/verkehrsamt.html'),
('ZG','dogs','G:https://www.zg.ch/behoerden/gesundheits-und-sozialdirektion/amt-fuer-verbraucherschutz/veterinaerdienst/hunde'),('ZG','tax','G:https://www.zg.ch/behoerden/finanzdirektion/steuerverwaltung/steuerbuch'),('ZG','school','G:https://www.zg.ch/behoerden/direktion-fuer-bildung-und-kultur/amt-fuer-gemeindliche-schulen/schulferien'),('ZG','road','G:https://www.zg.ch/behoerden/sicherheitsdirektion/strassenverkehrsamt'),
('GR','dogs','G:https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/hunde/'),('GR','tax','G:https://www.gr.ch/DE/institutionen/verwaltung/dfg/stv/steuerbuch/'),('GR','school','G:https://www.gr.ch/DE/institutionen/verwaltung/ekud/avs/schulferien/'),('GR','road','G:https://www.gr.ch/DE/institutionen/verwaltung/djs/stva/'),
('SH','dogs','G:https://sh.ch/CMS/get/file/c822e118-2490-41bf-a3d8-33dfd2bbcbef'),('SH','tax','G:https://sh.ch/desktopdefault.aspx/tabid-127/'),('SH','school','G:https://sh.ch/desktopdefault.aspx/tabid-1980/'),('SH','road','D:https://www.strassenverkehrsamt.sh.ch'),
('AR','dogs','G:https://www.ar.ch/verwaltung/departement-gesundheit-und-soziales/amt-fuer-verbraucherschutz/hunde/'),('AR','tax','G:https://www.ar.ch/verwaltung/departement-finanzen/steuerverwaltung/steuerbuch/'),('AR','school','G:https://www.ar.ch/verwaltung/departement-bildung-und-kultur/amt-fuer-volksschule-und-sport/schulferien/'),('AR','road','G:https://www.ar.ch/verwaltung/departement-bau-und-volkswirtschaft/strassenverkehrsamt/'),
('AI','dogs','G:https://www.ai.ch/verwaltung/gesundheits-und-sozialdepartement/veterinaerdienst/hunde'),('AI','tax','G:https://www.ai.ch/verwaltung/finanzdepartement/steuerverwaltung/steuerbuch'),('AI','school','G:https://www.ai.ch/verwaltung/erziehungsdepartement/amt-fuer-volksschule/schulferien'),('AI','road','G:https://www.ai.ch/verwaltung/ratskanzlei/strassenverkehrsamt'),
('GL','dogs','G:https://www.gl.ch/verwaltung/sicherheit-und-justiz/veterinaerdienst/hunde.html'),('GL','tax','G:https://www.gl.ch/verwaltung/finanzen-und-gesundheit/steuerverwaltung/steuerbuch.html'),('GL','school','G:https://www.gl.ch/verwaltung/bildung-und-kultur/hauptabteilung-bildung/schulferien.html'),('GL','road','G:https://www.gl.ch/verwaltung/sicherheit-und-justiz/strassenverkehrs-und-schifffahrtsamt.html'),
('UR','dogs','G:https://www.ur.ch/dienstleistungen/3807'),('UR','tax','G:https://www.ur.ch/steuerbuch'),('UR','school','G:https://www.ur.ch/dienstleistungen/3328'),('UR','road','G:https://www.ur.ch/organisations/530'),
('OW','dogs','G:https://www.ow.ch/dienstleistungen/6216'),('OW','tax','G:https://www.ow.ch/steuerbuch'),('OW','school','G:https://www.ow.ch/dienstleistungen/14299'),('OW','road','G:https://www.ow.ch/organisations/1039'),
('NW','dogs','G:https://www.nw.ch/veterinaerdienst/417'),('NW','tax','G:https://www.nw.ch/steueramt/402'),('NW','school','G:https://www.nw.ch/amtamtsstelle/352'),('NW','road','G:https://www.nw.ch/verkehrsamt/365'),
]
E
python3 - "$S" <<'E'
import sys,subprocess,re,json,hashlib,concurrent.futures as cf
S=sys.argv[1];sys.path.insert(0,S)
from guidance_s3a_rows import ROWS
extra=[('city-real','Zürich AS (existing YAML)','R:https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung.html'),
 ('city-real','Genève (homepage link)','R:https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux'),
 ('city-real','Thun (homepage link)','R:https://www.thun.ch/reglementeverordnungen'),
 ('city-real','La Chaux-de-Fonds (homepage link)','R:http://www.chaux-de-fonds.ch/rapports-et-reglements'),
 ('city-real','Schaffhausen (homepage link)','R:https://www.stadt-schaffhausen.ch/rechtssammlung')]
UA='Mozilla/5.0 swiss-grounding-check'
NF=re.compile(r'404|not found|nicht gefunden|introuvable|non trovat|existiert nicht|n.existe pas|ungültige adresse|fehler|erreur',re.I)
def probe(item):
    c,t,cell=item;url=cell[2:];f='<scratchpad>/sgchk/courts/g_'+hashlib.md5(url.encode()).hexdigest()
    out=subprocess.run(['curl','-sL','-g','--max-time','25','-A',UA,'-o',f,'-w','%{http_code}|%{size_download}|%{url_effective}',url],capture_output=True,text=True).stdout
    try: code,size,final=out.split('|',2)
    except ValueError: code,size,final='ERR','0',''
    try: body=open(f,encoding='utf-8',errors='ignore').read()
    except Exception: body=''
    m=re.search(r'<title[^>]*>(.*?)</title>',body,re.S|re.I);title=re.sub(r'\s+',' ',m.group(1)).strip()[:60] if m else ''
    if code in('000','ERR'): k='no-response'
    elif code!='200': k=f'http-{code}'
    elif NF.search(title): k='soft-404'
    else: k='ok' if final.rstrip('/').split('://')[-1].removeprefix('www.')==url.rstrip('/').split('://')[-1].removeprefix('www.') else 'redirect'
    return dict(canton=c,topic=t,kind=cell[0],url=url,code=code,cls=k,final=final,title=title,size=int(float(size or 0)))
with cf.ThreadPoolExecutor(6) as ex: res=list(ex.map(probe,ROWS+extra))
json.dump(res,open(f'{S}/guidance_s3a_probe.json','w'),ensure_ascii=False,indent=1)
import collections
for kind in ('D','G','R'):
    L=[r for r in res if r['kind']==kind];print(kind,len(L),dict(collections.Counter(r['cls'] for r in L)))
print()
for r in res:
    if r['cls']!='http-404' or r['kind']!='G':
        print(f"[{r['kind']}] {r['canton']:9} {r['topic']:26} {r['cls']:12} {r['url'][:70]:70} -> {r['final'][:60]} | {r['title'][:40]}")
E
