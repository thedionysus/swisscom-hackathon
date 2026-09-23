S=<scratchpad>
python3 - "$S" <<'E'
import sys,json,re,glob,os,collections
S=sys.argv[1]
T={
 'dogs':r'\bhund|chien|\bcani\b|\bcane\b',
 'court_fees':None,
 'court_org':r'gerichtsorganisation|justizgesetz|organisation judiciaire|organizzazione giudiziaria|einführungsgesetz zur (schweizerischen )?zivilprozessordnung|introduction du code de procédure civile|gerichtsgesetz|justizverfassung',
 'conciliation':r'schlichtung|friedensricht|conciliation|juge de paix|justice de paix|conciliazione|giudic\w* di pace|mietgericht|tribunal des baux|arbeitsgericht|prud.hom',
 'holidays':r'schulferien|\bferien|vacances|vacanze',
 'tax':r'steuergesetz|gesetz über die (kantons|staats)?steuern|loi sur les impôts|loi fiscale|legge tributaria|impôts directs cantonaux',
 'road':r'strassenverkehr|motorfahrzeug|verkehrsabgabe|verkehrssteuer|véhicules|circulation routière|circolazione|veicoli',
}
FEE_A=re.compile(r'gebühr|kosten|tarif|émolument|frais|tariffa|spese|tasse di giustizia',re.I)
FEE_B=re.compile(r'gericht|justiz|rechtspflege|zivilprozess|strafprozess|verwaltungsverfahren|judiciaire|justice|juridiction|giudiziari|procédure|procedura|verfahrenskosten|prozesskosten',re.I)
hits=collections.defaultdict(lambda: collections.defaultdict(list))
for f in sorted(glob.glob(f'{S}/stage0/laws_*.json')):
    c=os.path.basename(f)[5:7];d=json.load(open(f))
    for x in d['items']:
        if x.get('abrogated') or x.get('is_active') is False: continue
        title=x.get('title') or '';nr=x.get('systematic_number','')
        url=(f"https://{d['host']}/api/{d['lang']}/texts_of_law/{nr}" if 'host' in d else f"https://www.lexfind.ch/api/fe/de/texts-of-law/{x['id']}")
        for topic,rx in T.items():
            ok = (FEE_A.search(title) and FEE_B.search(title)) if topic=='court_fees' else re.search(rx,title,re.I)
            if ok: hits[c][topic].append({'nr':nr,'title':title[:150],'api':url})
json.dump(hits,open(f'{S}/stage0/law_hits.json','w'),ensure_ascii=False,indent=1)
cols=list(T)
print('canton '+' '.join(f'{t[:11]:>11}' for t in cols))
for c in sorted(hits): print(f'{c:6} '+' '.join(f'{len(hits[c][t]):>11}' for t in cols))
print('\nexamples:')
for c in ('ZH','BE','GE','TI','ZG'):
    for t in ('dogs','court_fees','holidays'):
        for h in hits[c][t][:2]: print(f'  {c} {t:10} {h["nr"]:14} {h["title"][:95]}')
E
