"""python3 nuxtapi.py BASE js1 js2 ... : fetch JS bundles and grep API-like strings."""
import sys, re, subprocess
UA = 'Mozilla/5.0 swiss-grounding-check'
base = sys.argv[1]
found = set()
for js in sys.argv[2:]:
    u = base + js
    r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '60', '-A', UA, u], capture_output=True)
    t = r.stdout.decode('utf-8', errors='ignore')
    print('==', u, len(t), 'bytes')
    for m in re.findall(r'["\'`](/?(?:api|rest|graphql|search|v\d)[^"\'`\s]{0,80})["\'`]', t):
        found.add(m)
    for m in re.findall(r'https?://[a-z0-9.-]+\.[a-z]{2,}[^"\'`\s]{0,60}', t):
        if 'vs.ch' in m or 'api' in m:
            found.add(m)
for f in sorted(found)[:80]:
    print('  ', f)
