import json, subprocess, re, html, io, sys
UA='Mozilla/5.0 swiss-grounding-check'
def get(u, acc='*/*', raw=False):
    r=subprocess.run(['curl','-s','-g','-L','--compressed','--max-time','90','-A',UA,'-H','Accept: '+acc,'-w','\n%{http_code}',u],capture_output=True)
    b,c=r.stdout.rsplit(b'\n',1); return c.decode(),(b if raw else b.decode('utf-8','ignore'))
def plain(t):
    try: t=json.dumps(json.loads(t),ensure_ascii=False)
    except Exception: pass
    t=t.replace('\\n',' ').replace('\\"','"')
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
def pdftext(b):
    from pypdf import PdfReader
    return re.sub(r'\s+',' ',' '.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(b)).pages))
# quotes not found in saved pages
c,b=get('https://www.sz.ch/public/upload/assets/85734/Kanton_Schwyz_Ferienplan_Schuljahr_2026-2027.pdf',raw=True)
try: print('[Q SZ Schulräte]',c,'Verbindlich sind die von den Schulräten' in pdftext(b))
except Exception as e: print('[Q SZ]',c,type(e).__name__,b[:60])
c,b=get('https://av.tg.ch/themen/ferienplan.html/13415','text/html'); print('[Q TG DEK]',c,'Departement für Erziehung und Kultur die Ferientermine' in plain(b))
c,b=get('https://bl-api.webcloud7.ch/politik-und-behorden/direktionen/bildungs-kultur-und-sportdirektion/schulferien','application/json'); print('[Q BL canton-wide]',c,'Die Regelung der Schulferien gilt für die Volksschulen' in plain(b))
c,b=get('https://www.fr.ch/dfac/vacances-scolaires','text/html'); print('[Q FR cercle]',c,'cercle scolaire a la possibilité de donner 1 jour' in plain(b))
c,b=get('https://gdb.ow.ch/api/de/texts_of_law/818.3/show_as_json','application/json'); print('[Q OW 818.3]',c,'können durch Verordnung eine Hundesteuer einführen' in plain(b))
c,b=get('https://amtsblatt.tg.ch/','text/html'); t=b.lower(); print('[TG gazette login]',c,'password field:', 'type="password"' in t, '| login words:', any(w in t for w in ('anmelden','login','benutzername')))
# robots.txt claims marked [agent]
for h in ['amtsblatt.ar.ch','amtsblatt.sh.ch','amtsblatt.nw.ch','amtsblatt.ow.ch','www.ur.ch','www.kantonsamtsblatt.gr.ch','www.vs.ch','prestations.vd.ch','amtsblatt.gl.ch']:
    c,b=get(f'https://{h}/robots.txt','text/plain'); dis=re.findall(r'(?im)^Disallow:\s*(\S*)',b) if c=='200' else []
    print(f'[R {h}]',c,'| Disallow /:', '/' in dis,'| first rules:',dis[:5])
# AG 221.150 abrogated?
c,b=get('https://gesetzessammlungen.ag.ch/api/de/texts_of_law/221.150','application/json')
try:
    d=json.loads(b); s=json.dumps(d,ensure_ascii=False); m=re.search(r'"abrogated"\s*:\s*(true|false)',s); ti=re.search(r'"title"\s*:\s*"([^"]{0,60})',s)
    print('[AG 221.150]',c,'abrogated=',m.group(1) if m else None,'| title',ti.group(1) if ti else None)
except Exception: print('[AG 221.150]',c,b[:120])
# City counts marked [agent]
c,b=get('https://stadtrecht.bern.ch/sitemap.xml','application/xml'); print('[Bern SSSB numbers]',c,len(set(re.findall(r'dgn-lex_([\w.]+?)(?:[/<"#?]|$)',b))))
c,b=get('https://www.neuchatelville.ch/votre-commune/reglementation','text/html'); print('[Neuchâtel PDFs]',c,len(set(re.findall(r'href="([^"]+\.pdf)"',b))))
