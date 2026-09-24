"""Offline checks of the NEW connectors' robots/politeness/HEAD behaviour with httpx.MockTransport (no network).
Robots texts are reconstructed from the rules quoted in the Run 3 report, not fetched."""
import urllib.robotparser
import httpx
from protego import Protego
from swiss_grounding.corpus.connectors.html import HtmlConnector, CrawlPolicy, load_robots, ROBOTS_USER_AGENT
from swiss_grounding.corpus.connectors.pdf import PdfConnector
from swiss_grounding.corpus.connectors.politeness import HostThrottle
from swiss_grounding.corpus.models import SourceSpec, DiscoveredPdf

print("ROBOTS_USER_AGENT used by the crawler:", repr(ROBOTS_USER_AGENT))

# (d) rsn.ne.ch: 'Disallow: /' then 'Allow: /DATA/' (consolidated_report.md:148)
rsn = "User-agent: *\nDisallow: /\nAllow: /DATA/\n"
u = "https://rsn.ne.ch/DATA/program/books/rsne/pdf/164.1.pdf"
rp = urllib.robotparser.RobotFileParser(); rp.parse(rsn.splitlines())
print("(d) protego can_fetch /DATA/ :", Protego.parse(rsn).can_fetch(u, "*"), "| urllib.robotparser:", rp.can_fetch("*", u))
be = "User-agent: *\nDisallow: /content/\nAllow: /content/dam/\nCrawl-delay: 10\n"
print("(d) be.ch-style /content/dam/ :", Protego.parse(be).can_fetch("https://www.be.ch/content/dam/x.pdf", "*"),
      "| crawl_delay('*') =", Protego.parse(be).crawl_delay("*"))

# (g) fo.fr.ch-style: named AI bots disallowed, '*' allowed (consolidated_report.md:127)
fo = "User-agent: ClaudeBot\nDisallow: /\n\nUser-agent: anthropic-ai\nDisallow: /\n\nUser-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
p = Protego.parse(fo); url = "https://fo.fr.ch/archive/2026/38/18"
print("(g) can_fetch as '*':", p.can_fetch(url, "*"), "| as 'ClaudeBot':", p.can_fetch(url, "ClaudeBot"),
      "| as 'swiss-grounding':", p.can_fetch(url, "swiss-grounding"))

# robots.txt answering 403 (bl-api.webcloud7.ch, consolidated_report.md:135)
def robots_403(request):
    return httpx.Response(403, text="<html>forbidden</html>")
with httpx.Client(transport=httpx.MockTransport(robots_403)) as http:
    parser, problem = load_robots(http, "https://bl-api.webcloud7.ch")
    print("robots 403 ->", problem, "| can_fetch any page:", parser.can_fetch("https://bl-api.webcloud7.ch/politik-und-behorden/gerichte", "*"))

# (f) Crawl-delay: pages vs PDFs, and (b) which HTTP methods are sent
methods, sleeps = [], []
clock = [0.0]
def fake_sleep(s):
    sleeps.append(round(s, 2)); clock[0] += s
PAGE = '<html lang="de"><body><main><h1>Ferien</h1><p>' + "x" * 200 + '</p><a href="/content/dam/ferien.pdf">Ferienplan</a></main></body></html>'
PDF = b"%PDF-1.4 minimal"
def handler(request):
    methods.append((request.method, request.url.path, request.headers.get("user-agent")))
    if request.url.path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\nCrawl-delay: 10\n")
    if request.url.path.endswith(".pdf"):
        return httpx.Response(200, content=PDF, headers={"content-type": "application/pdf"})
    return httpx.Response(200, text=PAGE, headers={"content-type": "text/html"})
throttle = HostThrottle(clock=lambda: clock[0])
with httpx.Client(transport=httpx.MockTransport(handler), headers={"user-agent": "UA-under-test"}) as http:
    html = HtmlConnector(http, CrawlPolicy(respect_robots=True, delay_seconds=0.5), sleep=fake_sleep, throttle=throttle)
    spec = SourceSpec(id="t", name="t", publisher="t", authority="official_info", level="cantonal", extent_id="CH-BE",
                      connector="html", tier=2, languages=("de",),
                      config={"start_urls": ["https://www.example-be.ch/de/ferien.html"],
                              "allow_prefixes": ["https://www.example-be.ch/de/"],
                              "pdf_allow_prefixes": ["https://www.example-be.ch/content/dam/"], "max_pages": 2, "max_pdfs": 5})
    result = html.run(spec, {})
    t_after_pages = clock[0]
    print("(f) html delays applied (s):", sleeps, "| host delay stored:", html._delays)
    sleeps.clear()
    pdfc = PdfConnector(http, "<scratchpad>/newpipe/_mockdata",
                        sleep=fake_sleep, delay_seconds=0.5, throttle=throttle)
    try:
        pdfc.run_pdfs(spec, result.pdfs, {})
    except Exception as exc:
        print("pdf parse (expected to fail on the dummy body):", type(exc).__name__)
    print("(f) PDF delay applied before the PDF request (s):", sleeps, "(host Crawl-delay was 10)")
print("(b)/(g) requests sent (method, path, user-agent):")
for m in methods:
    print("    ", m)
print("discovered PDFs:", [(p.url, p.title_hint) for p in result.pdfs])
