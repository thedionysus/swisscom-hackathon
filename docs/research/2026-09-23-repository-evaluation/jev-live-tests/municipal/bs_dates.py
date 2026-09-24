"""Basel-Stadt laws from the official portal API; gold = the API's `enactment` (original in-force date)."""
import json, re, time, html, pathlib
import httpx
HERE = pathlib.Path(__file__).parent
SNS = ["365.100", "365.110", "300.100", "310.170", "410.120", "410.700", "510.100", "640.100", "650.500", "730.320", "786.100", "911.600"]
KW = re.compile(r"wirksam|in Kraft|Inkrafttreten|Inkraftsetzung", re.I)
out = []
with httpx.Client(timeout=40, follow_redirects=True, headers={"user-agent": "Mozilla/5.0"}) as c:
    for sn in SNS:
        r = c.get(f"https://www.gesetzessammlung.bs.ch/api/de/texts_of_law/{sn}")
        if r.status_code != 200:
            print(sn, "HTTP", r.status_code); continue
        t = r.json()["text_of_law"]
        raw = (t.get("selected_version") or {}).get("xhtml_tol") or ""
        txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)))
        # the in-force passages: windows around every keyword hit, merged, capped
        spans = []
        for m in KW.finditer(txt):
            a, b = max(0, m.start() - 300), min(len(txt), m.end() + 300)
            if spans and a <= spans[-1][1]: spans[-1][1] = b
            else: spans.append([a, b])
        doc = f"{t.get('title')}\n" + "\n…\n".join(txt[a:b] for a, b in spans)
        out.append({"sn": sn, "title": t.get("title"), "gold": t.get("enactment"),
                    "dates_str": t.get("text_of_law_dates_str"), "document": doc[:6000]})
        print(sn, "| gold", t.get("enactment"), "|", t.get("text_of_law_dates_str"), "| doc chars", min(len(doc), 6000), "|", (t.get("title") or "")[:50])
        time.sleep(1.0)
(HERE / "bs_laws.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
