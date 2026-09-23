#!/usr/bin/env python3
"""robots.txt (Sitemap / Crawl-delay / Disallow count) + CMS signature per host."""
import glob
import re
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"
HOSTS = ["www.fr.ch", "www.ocn.ch", "fo.fr.ch", "www.vd.ch", "www.faovd.ch", "www.ne.ch", "www.scan-ne.ch",
         "www.ge.ch", "justice.ge.ch", "www.jura.ch", "rsju.jura.ch", "www.lausanne.ch", "www.neuchatelville.ch",
         "www.chaux-de-fonds.ch", "www.geneve.ch", "www.vernier.ch"]
SIG = {"drupal": r"Drupal|/sites/default/files|drupal-settings-json|data-drupal", "typo3": r"typo3|fileadmin/",
       "wordpress": r"wp-content|wp-json", "joomla": r"/media/jui/|Joomla", "site-studio": r"Site Studio|coh-",
       "sharepoint": r"ms-rteTable|_layouts/15", "aem": r"/etc\.clientlibs|/content/dam", "magnolia": r"magnolia",
       "i-web": r"i-web\.ch", "htdocs-files": r"/Htdocs/Files/"}
for h in HOSTS:
    r = subprocess.run(["curl", "-sL", "--max-time", "30", "-A", UA, "-w", "\n%{http_code}", f"https://{h}/robots.txt"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    body, _, code = r.stdout.rpartition("\n")
    is_txt = not body.lstrip().lower().startswith("<")
    sm = re.findall(r"(?im)^sitemap:\s*(\S+)", body) if is_txt else []
    cd = re.findall(r"(?im)^crawl-delay:\s*(\S+)", body) if is_txt else []
    dis = len(re.findall(r"(?im)^disallow:\s*\S", body)) if is_txt else 0
    pages = [p for p in glob.glob("pages/*") if h.replace(".", "_") in p.split("/")[-1][:60]]
    sigs = set()
    for p in pages[:6]:
        t = open(p, "rb").read(400000).decode("utf-8", "replace")
        for k, rx in SIG.items():
            if re.search(rx, t, re.I):
                sigs.add(k)
    print(f"{h}: robots {code}{'' if is_txt else ' (html, not robots)'} | sitemap={sm[:2]} | crawl-delay={cd} | "
          f"disallow={dis} | CMS signatures (from {len(pages[:6])} saved pages)={sorted(sigs)}")
    time.sleep(0.4)
