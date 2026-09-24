"""Crawl three registered sources with OUR HtmlCrawlFetcher (robots, allowlist, sectioner as in production)."""
import json, pathlib
import httpx
from swiss_grounding.registry.loader import load_source_yaml
from swiss_grounding.ingest.fetchers.html_crawl import HtmlCrawlFetcher, CrawlLimits

HERE = pathlib.Path(__file__).parent
SRC = HERE.parent.parent / "main/src/swiss_grounding/registry/sources"
UA = "swiss-grounding/0.1 (+https://github.com/thedionysus/swisscom-hackathon)"  # config.py:27
out = []
with httpx.Client(timeout=20, headers={"user-agent": UA}, follow_redirects=False) as http:
    for sid in ("stadt_zuerich", "ge_ville", "zh_ch"):
        source = load_source_yaml((SRC / f"{sid}.yaml").read_text())
        res = HtmlCrawlFetcher(http=http, limits=CrawlLimits(max_pages=25, delay_seconds=1.0)).fetch(source, {})
        for d in res.documents:
            out.append({"source": sid, "url": d.url, "title": d.title, "language": d.language,
                        "sections": [{"heading_path": s.heading_path, "text": s.text} for s in d.sections]})
        print(sid, "documents:", len(res.documents), "sections:", sum(len(d.sections) for d in res.documents),
              "errors:", len(res.errors), flush=True)
(HERE / "pages.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print("saved", len(out), "documents")
