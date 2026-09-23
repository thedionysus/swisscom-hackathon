#!/usr/bin/env python3
"""Three-way gazette counts + named-AI-bot blocks in robots.txt of all hosts used."""
import json
import re
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"
API = "https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&pageRequest.size=1&"


def total(q):
    r = subprocess.run(["curl", "-s", "--max-time", "60", "-A", UA, API + q], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout).get("total")
    except Exception:  # noqa
        return "ERR " + r.stdout[:80]


print("=== counts: cantons=XX (includes federal SHAB) | tenant=kab<xx> | tenant + SHAB rubrics SB,KK,AW,NA")
for c in ["FR", "VD", "NE", "GE", "JU"]:
    t = "kab" + c.lower()
    a = total(f"cantons={c}")
    b = total(f"tenant={t}")
    c1 = total(f"tenant={t}&rubrics=SB&rubrics=KK&rubrics=AW&rubrics=NA")
    c2 = total(f"tenant={t}&rubrics=SB,KK,AW,NA")
    sb = total(f"tenant={t}&rubrics=SB")
    print(f"{c}: cantons={a} | tenant={b} | tenant+rubrics(repeated)={c1} | tenant+rubrics(csv)={c2} | tenant+SB only={sb}")
    time.sleep(0.5)

print("=== robots.txt: named bots with 'Disallow: /'")
HOSTS = ["www.fr.ch", "www.ocn.ch", "fo.fr.ch", "bdlf.fr.ch", "publicationtc.fr.ch", "www.vd.ch", "prestations.vd.ch",
         "jurisprudence.vd.ch", "www.faovd.ch", "www.ne.ch", "rsn.ne.ch", "jurisprudence.ne.ch", "www.scan-ne.ch",
         "www.ge.ch", "justice.ge.ch", "www.getax.ch", "silgeneve.ch", "statistique.ge.ch", "fao.ge.ch", "www.jura.ch",
         "rsju.jura.ch", "jurisprudence.jura.ch", "www.lausanne.ch", "www.neuchatelville.ch", "www.chaux-de-fonds.ch",
         "www.geneve.ch", "www.vernier.ch", "amtsblattportal.ch"]
for h in HOSTS:
    r = subprocess.run(["curl", "-sL", "--max-time", "30", "-A", UA, "-w", "\n%{http_code}", f"https://{h}/robots.txt"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    body, _, code = r.stdout.rpartition("\n")
    if body.lstrip().lower().startswith("<"):
        print(f"{h}: {code} no robots.txt (HTML)")
        continue
    blocked, star_root, agent = [], False, None
    for ln in body.splitlines():
        m = re.match(r"(?i)\s*user-agent:\s*(\S+)", ln)
        if m:
            agent = m.group(1)
            continue
        if re.match(r"(?i)\s*disallow:\s*/\s*$", ln):
            if agent == "*":
                star_root = True
            elif agent:
                blocked.append(agent)
    cd = re.findall(r"(?im)^crawl-delay:\s*(\S+)", body)
    ai = [b for b in blocked if re.search(r"claude|anthropic|gpt|ccbot|perplex|google-extended|cohere|bytespider", b, re.I)]
    print(f"{h}: {code} | '*' Disallow: / = {star_root} | named bots blocked: {len(blocked)} (AI: {ai[:6]}) | crawl-delay={cd}")
    time.sleep(0.3)
