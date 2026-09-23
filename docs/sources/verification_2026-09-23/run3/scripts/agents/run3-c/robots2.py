import subprocess, re, sys
for h in sys.argv[1:]:
    b=subprocess.run(['curl','-sL','--max-time','30','-A','Mozilla/5.0 swiss-grounding-check','https://'+h+'/robots.txt'],capture_output=True,text=True).stdout
    if '<html' in b[:500].lower(): print(h,': no robots.txt (HTML)'); continue
    cd=[l.strip() for l in b.splitlines() if re.match(r'(?i)\s*crawl-delay',l)]
    sm=[l.strip() for l in b.splitlines() if re.match(r'(?i)\s*sitemap',l)]
    print(h,': lines',len(b.splitlines()),'| crawl-delay:',cd or 'none','|',sm or 'no sitemap line')
