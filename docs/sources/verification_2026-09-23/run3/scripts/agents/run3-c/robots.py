import subprocess, re, sys
for h in sys.argv[1:]:
    r=subprocess.run(['curl','-sL','--max-time','30','-A','Mozilla/5.0 swiss-grounding-check','-w','\n%{http_code}','https://'+h+'/robots.txt'],capture_output=True,text=True)
    b,code=r.stdout.rsplit('\n',1)
    keep=[l.strip() for l in b.splitlines() if re.match(r'(?i)\s*(sitemap|crawl-delay|user-agent|disallow)\s*:',l)]
    if '<html' in b[:500].lower(): keep=['(HTML, no robots.txt)']
    print(f'{h} [{code}]: '+' ; '.join(keep)[:420])
