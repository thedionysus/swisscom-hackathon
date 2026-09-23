# G1 report: commune bylaws and shared platforms (Opus 5.5 agent, 2026-09-23)
Run: 108 tool calls, ~185k tokens, ~40 min. Evidence: /tmp/sg-verify-g1-commune-law/ (scan.json, iweb_all.json,
tlex_hosts.txt, tlex_counts.txt). The harness blocked the agent's backup file, so this is the main session's transcription.
Method: fetched the homepages of all 2,103 communes in commune_sites.csv that list a website (2,060 returned 200) and detected CMS/vendor signatures.

**Spot-checked by the main session (live curl or the agent's data files, 2026-09-23). All matched:**
- baar.tlex.ch lightweight_index: 153 texts, 48 structured
- st.gallen.tlex.ch `/api/de/texts_of_law/412.9/show_as_json`: "Hundereglement", enactment 2020-11-01
- tlex_hosts.txt: 50 hosts
- wetzikon.ch/de/verwaltung/rechtssammlung/: 200, **191 unique Rechtssammlung PDFs**
- iweb_all.json: 496 i-web communes; 355 publikation + 83 rechtssammlung = **438**; rows 11,513 + 6,905 = **18,418**
Not re-checked: FR per-commune counts, terrara 1,484, Weblication 113, BL Plone 12/682, Romandie counts, Köniz 91.

**Conflict with G4:** G1 says LexFind `entities/{id}/systematics` returns nodes with empty `tols`. G4 says the texts
are filled in when you pass `tols_for_systematics[]=<node ids>` (batches of ≤100). **Resolved by the main session (curl, entity 28): without the param, 0 tols; with `tols_for_systematics[]` over 55 node ids, 317 tols. G4 is right, and G1 omitted the parameter.**

## Summary
| id | can we get it | format | fetcher | value |
|---|---|---|---|---|
| **tlex.ch (Sitrox LexWork for communes)** | Yes, new fetcher | JSON, article tree | LexWork commune | **high**: ≥49 communes, 4,002 texts, ~846k inhabitants |
| **i-web regulations module** | Yes, new fetcher | inline `data-entities` JSON → `/_doc/<id>` PDF | i-web regulations | **high**: 438 communes, 18,418 rows |
| G1-a Fribourg | Yes, new fetcher | HTML index + PDF text | PDF-index discoverer (+ i-web) | high: ~100/119 FR |
| Wetzikon (191 PDFs), Köniz (91 PDFs) | Yes, new fetcher | HTML + PDF text | PDF-index discoverer | med |
| Talus / Weblication | Yes, new fetcher | AJAX HTML list (wList.php) + PDF | Weblication list | med: ~113 communes, mostly BE |
| Webcloud7 → Kanton BL Plone | Yes, new fetcher | Plone REST JSON + PDF | Plone REST | low-med: 12 BL communes |
| Romandie | Yes, new fetcher | HTML + PDF | PDF-index discoverer + i-web | med-high: 401/542 homepages link to règlements |
| D1 LexFind | Communal: **No** (28 entities: CH + Intlex + 26 cantons) | JSON | – | low for communes |
| D3 terrara.ch | PDF list only | PDF text | – | low: commercial mirror of building regulations (1,484 PDFs), institutional |
| Cantonal central index of commune bylaws | **None found** (FR, SO, VD, BE only publish templates) | – | – | – |

## AI claims checked
- St. Gallen and Baar on "Tlex": **correct** (tlex.ch). Wetzikon and Köniz with article HTML: **wrong** (PDF lists).
- "Talus Cloud RIO": not found. Talus sites run on Weblication CMS, and gemeinde.ch is Talus's demo site.
- "Axsos / iPrime" in Romandie: **no trace** on 542 homepages.
- terrara "article-parsed": **wrong** (a PDF mirror).

## tlex / LexWork details
- Hosts are `<slug>.tlex.ch` (no wildcard DNS) plus own hosts: st.gallen.tlex.ch, lex.birsfelden.ch, reglemente.stadt-solothurn.ch,
  gesetzessammlung.chur.ch (its de index returns `{}`). Uznach's instance is empty. The host count is a lower bound.
- By canton: ZG 11 (all), BL 8, AG 6, SG 5, GR 4, TG 3, GL 3, ZH 3, BE 2, LU 2, JU 1, SO 1. Includes Winterthur (270 texts), Luzern,
  Biel/Bienne (de+fr), Aarau, Frauenfeld, Wil, Rapperswil-Jona, Delémont (fr).
- API: `/api/{de|fr}/texts_of_law/lightweight_index`, `/api/de/systematic_categories`, `/api/de/settings` (entity_description),
  `/api/de/texts_of_law/<nr>/show_as_json` (`text_of_law`: title, abbreviation, enactment, date_of_decision, canonical_link;
  `selected_version`: version_dates_str, pdf_link_tol, `json_content.document` tree of article/paragraph/title nodes with html_content).
  Unstructured texts: `/api/de/versions/<id>/pdf_file`. robots.txt disallows only the search routes.
- **This is the same API as the cantonal LexWork portals and intlex (G4).** One fetcher covers communes, cantons and concordats.
- Detect new hosts: `<title>LexWork</title>` or a 200 JSON answer from `/api/de/settings`.

## i-web details
- 496 of 2,060 homepages (ZH 91, AG 54, BE 50, SG 45, SO 44, VD 30, LU 27, FR 23).
- `<table class="icms-dt" data-entities='…'>` holds the whole table without pagination.
  - publikation: `name` (link to /_rte/publikation/<id>), `datum`, `kategorieId: "reglement"`, `herausgeber`. The detail page links `/_doc/<id>` (the PDF).
  - rechtssammlung: `title`, `_nummer`, `_rechtsgueltigkeit`, `_dokumentList` → `/_doc/<id>`.
- Paths: /reglemente 274, /gesetzessammlung 45, /rechtssammlung 42, /reglements 27.
- In a sample of 6 publikation pages, all contained a dog or waste regulation.

## Other platform notes
- FR CMS mix: TYPO3 30, WordPress 33, i-web 23, other 33. There is no common path. In a sample of 10, none had article HTML; all had PDF lists.
- Romandie CMS: WordPress 142, i-web 56, Quicksite 38 (VD), TYPO3 35, Joomla 22.
- GOViS CMS runs 254 commune homepages, with no shared regulations path found.
- The Kanton BL site (bl-api.webcloud7.ch, Plone REST) hosts 12 small communes' sites. Search results come 25 per page and need paging with `b_start`.

## New fetcher classes
1. **LexWork commune fetcher** (≥49 communes; the same code serves 19 cantons + intlex).
2. **i-web regulations fetcher** (438 communes, 22 cantons).
3. **Commune regulations PDF-index discoverer** (homepage → regulations link → PDF links → pypdf). The generic fallback.
4. **Weblication list fetcher** (~113 communes).
5. **Plone REST fetcher** (12 BL communes).
