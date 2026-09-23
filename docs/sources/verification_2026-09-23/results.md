# Source verification results: sub-national discovery (2026-09-23)

Inputs: `candidate_links_2026-09-23.md` (AI Mode leads), handoff lead 1 (cantonal law portals), selected entries of
`awesome_ogd_switzerland_2026-09-23.md`. Method: a pilot (Sonnet 5, 4 leads), then 5 agents on Opus 5.5 with brief v3.
Per-group reports with evidence: `{pilot,g1-commune-law,g2-districts,g3-associations,g4-intercantonal,g5-guidance}.md` in this folder.
**Each report starts with the claims the main session re-ran itself (all matched).** Everything else is the agents' curl evidence,
not re-run by the main session. Items marked "inferred" or "not verified" are exactly that.
**Audit applied 2026-09-23:** overstatements corrected (intlex completeness, tlex totals, St. Gallen structure, ÖREB/geodienste coverage, SBB jurisdiction).

---

## 1. The headline: one API family covers communes, cantons and concordats
Sitrox **LexWork** serves the same JSON API on three levels:
| Level | Hosts | Coverage | Verified by main session |
|---|---|---|---|
| Canton | 19 cantonal law portals (12 known from the handoff + AG SG GR SO VS FR OW) | 19 of 26 cantons | AG 463, SG 732, GR 419, SO 539, FR 814, OW 517 texts; VS constitution xhtml. The 12 handoff cantons were not re-tested |
| Intercantonal | www.intlex.ch | 317 active agreements listed (HarmoS, IVHB, hooligan, IKAPOL, police, GSK 9.5-3…). Whether intlex is *complete* is not verified | 317 texts; HarmoS 4.2-2; GSK 9.5-3 title |
| Commune | `<slug>.tlex.ch` + own hosts | **45 tlex subdomains with texts: 3,555 texts, 2,671 structured** (verified from the agent's counts file; Uznach empty). Plus 4 communes on own hosts (St. Gallen, Birsfelden, Solothurn, Delémont; the agent reports 447 texts, not re-checked) = 49. ~846k inhabitants: **not verified** | Baar 153/48; St. Gallen 412.9 Hundereglement: structured JSON, but only 2 article nodes, so completeness is unverified |

Routes: `/api/{lang}/texts_of_law/lightweight_index` (listing; **it was missing before**),
`/texts_of_law/{nr}` or `/show_as_json` (articles as xhtml/JSON tree, PDF fallback; `show_as_json` with `json_content.document` confirmed on tlex **and** AG), `/status/recent_changes` (change feed, confirmed on intlex: 200 JSON with change_type and change_date).
**One "LexWork fetcher" would serve all three levels.** The 4 non-LexWork cantons (VD JSON, NE HTM/PDF, TI HTML, JU PDF) are
each reachable with a small dedicated fetcher. LexFind's listing route works with `tols_for_systematics[]` (resolved: 317 Intlex texts).

## 2. Can go in TODAY with YAML only (no code)
| Source | Strategy | Category | Jurisdiction | Report |
|---|---|---|---|---|
| BS school holidays (data.bs.ch 100397, 88 rows), BL (data.bl.ch 13350, 58 rows: schuljahr, startdatum, enddatum, name) | api | schools | CH-BS / CH-BL | g5 |
| Bern city waste zones (ArcGIS, 7 zones with weekdays and put-out rules) | api | waste | CH-BE-351 | g3 |
| SBB fare-network map (2,137 communes, one GET) | api (`records_path: ""`) | transport | **lands on CH** unless narrowing finds the commune in the text (`enrich.py:42-44`). **Test narrowing before adding** | g3 |
| BE school holidays PDF (+ French sibling) | pdf | schools | CH-BE | pilot |
| ZAB waste calendars (35 PDFs) | pdf | waste | multi-commune SG+TG | pilot |
| Zurich tax guide, 159 entries from the steuern-finanzen sitemap | html_crawl with listed start paths | taxes | CH-ZH | g5 |
| GE GeTax tax guide (98 pages), GE/ZH/BE/BS dog pages, road-traffic pages *(agent-verified only)* | html_crawl | taxes, dogs, transport | canton | g5 |
| gerichte-zh.ch /de/themen/ (249 pages), BE Regierungsstatthalter guidance *(agent-verified only)* | html_crawl | justice guidance (no category yet) | CH-ZH / CH-BE | g2 |
| BPUK IVHB, KKJPD, KKPKS, GESPA concordat PDFs *(agent-verified only)* | pdf / html_crawl | building, police, gambling (no category yet; safety?) | member cantons | g4 |
| Küssnacht (72), Einsiedeln (215), Gersau (22) regulation PDFs, as listed URLs | pdf | waste, parking, fees, building | CH-SZ-1331 / 1301 / 1311 | g2 |

## 3. New fetcher classes, ranked by coverage × value
| # | Fetcher | Serves | Coverage | Asked for by |
|---|---|---|---|---|
| 1 | **LexWork** (index → detail → articles; change feed) | cantonal law, concordats, commune law | 19 cantons + intlex + ≥49 communes | g1, g4 |
| 2 | **i-web / i-CMS regulations table** (`data-entities` JSON → `/_doc/<id>` PDF) | commune bylaws, school and fee regulations | **438 communes, 18,418 rows** | g1, g3 |
| 3 | **PDF index discoverer** (index page → PDF links → pypdf) | commune bylaws (FR, Romandie, Wetzikon, Köniz, SZ districts), BS tax PDFs, ZAB | generic fallback; 102/119 FR and 401/542 Romandie homepages link to regulations | pilot, g1, g2, g5 |
| 4 | **Sitemap-seeded crawler** (sitemap index → regex allowlist) | cantonal guidance ZH, GE, BS, BE offices | 4 cantons, probably more | g5 |
| 5 | **ICS calendar** | GE school holidays, REAL Luzern waste (22 communes), entsorglos (10) | ~35 communes + GE | g3, g5 |
| 6 | **ÖREB legal-provision harvester** | communal building regulations + responsible office | standard service in every canton; building-regulation links **confirmed only in SZ and ZH**. Needs a coverage probe before it is prioritised | g2 |
| 7 | **geodienste OGC API** (Nutzungsplanung `dokument`) | communal building regulations | ~20 cantons with free access (not ZH/TI/GL; NW/OW/VD need approval); links **confirmed only in a BE sample** | g2 |
| 8 | **Paginated JSON** (#38) | ODS datasets over 100 rows (ZAB 1,116 points) | many ODS portals | pilot |
| 9 | Weblication list (~113 communes, mostly BE), govis list (264 homepages), WordPress media API, Plone REST (12 BL communes) | commune bylaws | CMS-specific | g1, g2, g3 |
| 10 | XLSX (ZH school holidays, 185 Schulgemeinden), WFS-GML (Lausanne dog zones 225+308), phonemos (BE TaxInfo ≥591 pages), OCR PDF (SRFWL, SIGE, SZ ÖREB) | single sources | – | g2, g3, g5 |

## 4. What the AI Mode answer got wrong (for the record)
- ZH "dog rules" PDF = Ukraine pet-import guide. BS "Steuerwissen A–Z" no longer exists.
- ivhb.ch = a private law firm. The IKAPOL link = an outdated Zug version. terrara = a commercial PDF mirror, not article-parsed.
- Wetzikon and Köniz are PDF lists, not article HTML. "Talus Cloud RIO" and "Axsos / iPrime" were not found. LexFind has no communal law.
- The Fribourg card was guidance, not an index. Zollikon and Dietikon are single-commune schools. z-a-v.ch is an operators' forum.
- Both regional-planning domains were wrong. Bio Suisse was irrelevant. The lotteries and transport gaps were real.
- Correct: St. Gallen and Baar on tlex, Schwyz districts autonomous, 4 police concordats, the HarmoS count (15), GE holiday tables.

## 5. Design questions raised (not source questions)
1. **Multi-commune bodies** (ZAB 33–35 communes across SG+TG, SRFWL 7 across BL+SO, SIGE 8–10, REAL 22) cannot sit on one node.
2. **Concordat membership:** texts apply to a set of cantons. Intlex accession tables **miss withdrawals** (SZ left IVHB in 2022).
3. **Schulgemeinden ≠ communes** (the ZH holiday XLSX). A mapping is needed.
4. **Fees are mostly set per commune** even when an association runs the service.
5. **Authority edge cases:** an SG-published statute (ZAB) binds TG communes; tlex commune law → municipal_law. LAW_PLATFORM_HOSTS (branch feat/authority-routing-rules, 0f4f764) already lists all 26 cantonal portals but **not intlex.ch or tlex hosts**.
6. **BE TaxInfo** says it is for internal staff and communes, although it is publicly served. Confirm before ingesting.
7. **edudoc.ch** forbids robot harvesting (OAI policy). Use intlex instead.

8. **Categories:** the code allows only `dogs, health, hiking, housing, parking, safety, schools, taxes, transport, waste` (registry/categories CATEGORY_IDS). Building, water, fire service, gambling, courts and family law have no category yet.

## 6. Corrections to earlier docs (to apply later on the right branch)
- `ogd_lists_assessment.md:206` (§3.2) "There is no listing endpoint": **wrong**. `entities/{id}/systematics?tols_for_systematics[]=`.
- §7 (`:301`, ÖREB listed under "Not useful"): right for geometry, **wrong for LegalProvisions** (links to communal Baureglemente).
- The handoff §4 says the LexWork API is on 12 cantons: it is now **19**, and LexWork has a listing endpoint.
