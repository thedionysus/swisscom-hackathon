import subprocess, json, sys
for u in sys.argv[1:]:
    r=subprocess.run(['curl','-sL','--compressed','--max-time','30','-A','Mozilla/5.0 swiss-grounding-check','-H','Accept: application/json','-H','X-Requested-With: XMLHttpRequest','-w','\n%{http_code} %{content_type} %{size_download}',u],capture_output=True,text=True)
    b,meta=r.stdout.rsplit('\n',1)
    print(meta,'|',u); print('   ',b[:400].replace('\n',' '))
