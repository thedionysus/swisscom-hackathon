"""Offline check: old urllib.robotparser vs new protego on the same robots.txt texts. No network."""
from urllib import robotparser

from protego import Protego

BE = "User-agent: *\nDisallow: /content/\nAllow: /content/dam/\nCrawl-delay: 10\n"
UA_SPECIFIC = "User-agent: swiss-grounding\nDisallow: /\n\nUser-agent: *\nAllow: /\n"


def old(text: str, url: str) -> bool:
    p = robotparser.RobotFileParser()
    p.parse(text.splitlines())
    return p.can_fetch("*", url)


def new(text: str, url: str, ua: str = "*") -> bool:
    return Protego.parse(text).can_fetch(url, ua)


print("be.ch PDF  /content/dam/x.pdf  old(urllib,'*'):", old(BE, "https://www.be.ch/content/dam/x.pdf"),
      "| new(protego,'*'):", new(BE, "https://www.be.ch/content/dam/x.pdf"))
print("be.ch page /content/page       old(urllib,'*'):", old(BE, "https://www.be.ch/content/page"),
      "| new(protego,'*'):", new(BE, "https://www.be.ch/content/page"))
print("old: robots non-200 -> parse([]) -> can_fetch:", old("", "https://x.ch/any"))
print("crawl_delay('*') protego on be.ch text:", Protego.parse(BE).crawl_delay("*"))
print("UA-specific group 'swiss-grounding' disallows all, '*' allows:",
      "evaluated as '*' ->", new(UA_SPECIFIC, "https://x.ch/a"),
      "| evaluated as sent UA ->", new(UA_SPECIFIC, "https://x.ch/a",
                                       "Mozilla/5.0 (compatible; swiss-grounding/0.2; +https://github.com/...)"))
