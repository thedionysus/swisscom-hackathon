"""List candidate content containers (id/class containing content/main) with their text size, offline."""
import json, re, sys
from bs4 import BeautifulSoup
S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
url = sys.argv[1]
html = open(idx[url], "rb").read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")
body_text = len(soup.body.get_text(" ", strip=True)) if soup.body else 0
print("body text chars:", body_text)
pat = re.compile(sys.argv[2] if len(sys.argv) > 2 else r"content|main|inhalt|article", re.I)
for el in soup.find_all(True):
    ident = el.get("id") or ""
    cls = " ".join(el.get("class") or [])
    if pat.search(ident) or pat.search(cls) or el.name in ("main", "article"):
        t = len(el.get_text(" ", strip=True))
        hs = [h.name + ":" + h.get_text(" ", strip=True)[:30] for h in el.find_all(["h1", "h2"])][:3]
        if t > 200:
            print(f"<{el.name} id={ident!r} class={cls[:60]!r}> text={t} headings={hs} in_form={el.find_parent('form') is not None}")
