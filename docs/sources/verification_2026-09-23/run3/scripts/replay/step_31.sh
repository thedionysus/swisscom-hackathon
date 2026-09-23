S=<scratchpad>
python3 - "$S" <<'E'
import sys,json,re,os,collections
S=sys.argv[1];sm=json.load(open(f'{S}/stage0/sitemaps_summary.json'))
TOP={
 'courts':r'gericht|tribunal|tribunale|/justice|justiz|pouvoir-judiciaire|potere-giudiziario|/ojv|pretur|schlichtung|conciliation|friedensricht|juge-de-paix|justice-de-paix|prozesskosten|gerichtsgeb|emoluments?-judic',
 'dogs':r'hund|chien|/cani|/cane(?![a-z])',
 'tax':r'steuerbuch|wegleitung|steuererkl|impot|impôt|declaration-d-?impot|dichiarazione|fiscal|/steuern',
 'holidays':r'schulferien|ferienplan|/ferien|vacances|vacanze|calendario-scolastico',
 'road':r'strassenverkehr|motorfahrzeug|fahrzeug|automobile|vehicule|véhicule|circolazione|/mfk|/svsa|/stva|verkehrsamt|permis-de-conduire|fuehrerausweis|führerausweis',
 'communes':r'/gemeinden|/communes|/comuni',
 'chancellery':r'staatskanzlei|chancellerie|cancelleria|ratskanzlei|standeskanzlei|landeskanzlei',
 'city_law':r'rechtssammlung|reglement|règlement|regolament|amtliche-sammlung|stadtrecht|recueil',
}
out={};rows=[]
for c,hosts in sm['hosts'].items():
    out[c]={}
    for t,rx in TOP.items():
        L=[]
        for h in hosts:
            f=f'{S}/stage0/sitemaps/{h}.txt'
            if os.path.exists(f):
                L+=[u for u in open(f).read().split('\n') if u and re.search(rx,u,re.I)]
        L=sorted(set(L),key=lambda u:(len(u),u))
        out[c][t]={'count':len(L),'shortest':L[:40]}
    rows.append((c,[out[c][t]['count'] for t in TOP]))
json.dump(out,open(f'{S}/stage0/sitemap_topic_candidates.json','w'),ensure_ascii=False,indent=1)
print('canton '+' '.join(f'{t[:9]:>9}' for t in TOP))
for c,v in sorted(rows): print(f'{c:6} '+' '.join(f'{x:>9}' for x in v))
print('\nsample (shortest URLs):')
for c,t in (('SG','courts'),('AG','dogs'),('GE','holidays'),('ZG','tax'),('JU','road'),('SO','courts')):
    print(f' {c} {t}:',out[c][t]['shortest'][:3])
E
