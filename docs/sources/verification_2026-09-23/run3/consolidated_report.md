# Run 3: source grids for all 26 cantons and 10 cities (consolidated, 2026-09-23)

Five agents (Opus 5.5, brief v5 "grid contract") each filled a fixed grid of **11 cells per canton**:
- **C1–C5:** courts home, court fees, court guidance, decisions, conciliation.
- **G1–G4:** dogs, tax guide, school holidays, road office.
- **D1:** commune directory.
- **D2:** chancellery and gazette.

They also covered city law (**L1**) for 10 cities. Each cell is one of three things:
- **VERIFIED:** a live URL with a quoted sample, fetched on 2026-09-23.
- **NONE:** comes with the search log (the "ladder") that failed.
- **BLOCKED.**

**Evidence labels in this report**
- **[re-checked]:** the orchestrator re-ran the request itself today. Results are in §9.
- **[agent]:** the agent verified it with its own request today. The request and sample are in its full report. Not re-run by the orchestrator.
- **[code]:** read from this repository today, with file and line.
- **[inferred]:** a conclusion no response shows directly.

**Full agent reports** are in `scratchpad/reports/`. The scratchpad is lost on restart; the session transcript keeps a copy.

| Report | Covers |
|---|---|
| `run3-a.md` | ZH, BE, BS, BL, SO, AG, plus Zürich, Bern, Thun |
| `run3-b.md` | LU, UR, SZ, OW, NW, GL, ZG |
| `run3-c.md` | SG, TG, AR, AI, SH, plus Schaffhausen |
| `run3-d.md` | FR, VD, NE, GE, JU, plus Lausanne, Neuchâtel, La Chaux-de-Fonds, Genève, Vernier |
| `run3-e.md` | TI, GR, VS, plus Lugano and the court-data links |

---

## 1. Result at a glance

Legend: ✓ verified · ◐ verified with a gap (see notes) · ✗ blocked or none.

| Canton | C1 | C2 | C3 | C4 | C5 | G1 | G2 | G3 | G4 | D1 | D2 | Gaps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ZH | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ◐ | D1 names/e-mail only; gazette robots |
| BE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette robots |
| BS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette robots |
| BL | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ◐ | C/G cells via bl-api (§2.3); no fee page; Steuerbuch behind Cloudflare; gazette robots |
| SO | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | fee ordinance only; gazette robots |
| AG | ✓ | ◐ | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | fee ordinance only; decision DB 503; gazette robots |
| LU | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ◐ | D1 no website/BFS; gazette print only |
| UR | ✓ | ◐ | ✓ | ✓ | ✓ | ◐ | ✓ | ✓ | ✓ | ◐ | ✓ | fee ordinance only; dogs law plus shared laburk.ch; D1 names only |
| SZ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette robots |
| OW | ✓ | ◐ | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | fee ordinance only; opencaselaw stale (2022-12-19); gazette robots |
| NW | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette robots |
| GL | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ◐ | no official commune list with links; amtsblatt.gl.ch/ipub not probed |
| ZG | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette robots |
| SG | ✓ | ✓ | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ◐ | publikationen.sg.ch robots (decisions, gazette); D1 no website |
| TG | ✓ | ◐ | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | fee law only; opencaselaw stale; gazette login |
| AR | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette robots |
| AI | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | fee law only; no online gazette |
| SH | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | fee law only; gazette robots; sh.ch pages are JS shells |
| FR | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | fo.fr.ch excludes AI bots (§2.2) |
| VD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| NE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette paid |
| GE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ◐ | D1 cantonal ids, no links; gazette CAPTCHA |
| JU | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| TI | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ◐ | fee law only; D1 names only; gazette robots |
| GR | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | gazette robots (DIAM) |
| VS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ✓ | ✓ | ◐ | holiday dates only colour-coded in PDF; gazette robots |

**Totals:** 286 cells: **240 ✓, 44 ◐, 2 ✗.** No cell is empty. The totals are tallied from the per-agent grids; the symbols are the orchestrator's summary of each report.

Where the gaps sit:
- **D2 (gazettes):** 23 cells. See §2.1.
- **C2 (no resident fee page, ordinance only):** 9.
- **D1 (list without BFS number or links):** 7.
- **C4 (decisions: blocked, down or stale):** 4.

All 10 cities are VERIFIED (§4).

---

## 2. Decisions

**Recorded 2026-09-23 (user):**
1. **Gazettes (§2.1): use the documented Amtsblattportal API.** Cantonal notices come from `tenant=kab<xx>` plus the canton's own rubric codes, with `publicationStates=PUBLISHED`. Open questions on how to handle notices with personal data: see §2.1.
2. **fo.fr.ch (§2.2): FR must not be left out; find another way.** Being investigated: the FO terms of use, alternative official channels, and a permission request to the Chancellery. The crawler will not disguise its identity.
3. **Basel-Landschaft (§2.3): use bl-api.webcloud7.ch.** It needs the new `plone-rest` fetcher, with document URLs rewritten to www.baselland.ch.

The sections below give the evidence each decision rests on.

### 2.1 Official gazettes and robots.txt
**robots.txt says `User-agent: *` / `Disallow: /` on the central platform and most canton gazettes.**
- [re-checked] amtsblattportal.ch and www.amtsblattportal.ch.
- [re-checked] amtsblatt.zh.ch, amtsblatt.be.ch, kantonsblatt.ch (BS), www.amtsblatt.bl.ch, amtsblatt.so.ch, amtsblatt.zg.ch, amtsblatt.sz.ch, foglioufficiale.ti.ch, bulletin-officiel.vs.ch, amtsblatt.ar.ch, amtsblatt.sh.ch, amtsblatt.nw.ch, amtsblatt.ow.ch.

**Who publishes there.** The platform's rubric list has 16 tenants that own rubrics [re-checked against the list agent B saved]:
- 14 cantons: AR, BE, BL, BS, GR, NW, OW, SH, SO, SZ, TI, VS, ZG, ZH. **GR owns only 1 rubric (AA-GR)**, because its gazette runs elsewhere (DIAM).
- `kabda`, which is not a canton.
- `shab`, the federal commercial gazette.

Own-notice counts [agent A]: ZH 19,659 · BE 20,165 · BS 9,462 · BL 5,619 · SO 1,580. AG has no rubrics on the platform.

**The API docs say something different.**
- `ogd_lists_assessment.md:236` quotes the API docs: "The API is freely accessible for anyone to use". The orchestrator did not re-read the docs today.
- Agent C reports that the docs require authentication only to submit or to read unpublished items [agent].
- Consistent with that, the API returns **401 without `publicationStates=PUBLISHED` and 200 with it** (same client, same query) [re-checked].

**Personal data.** `cantons=ZH&keyword=Todesanzeige` returns 732 notices whose titles start with "Todesanzeige –" [re-checked].

**How to count a canton's own notices.**
- `cantons=XX` also returns federal SHAB notices. In the first 500 TI notices since 1 Sept, 356 are `shab` and 144 `kabti`; for VS, 288 and 212 [re-checked].
- Cantonal notices only: `tenant=kab<xx>&rubrics=<the canton's own rubric codes>`. ZG with its 12 codes gives 2,213 [re-checked].
- `tenants=` is ignored: 32,718 notices published since 1 Sept 2026, the same as with no filter [re-checked].
- The five French-speaking tenants (kabfr, kabvd, kabne, kabge, kabju) are `external: true` [re-checked]. They have **0 own rubrics** and carry only SHAB rubrics [agent].

**Gazettes by status.**

| Status | Gazettes |
|---|---|
| Open and free | **VD** faovd.ch: no robots.txt (404) [re-checked]. **JU** rsju.jura.ch Journal officiel: weekly PDFs, no Disallow [re-checked]. **UR** Amtsblatt as an i-web table on ur.ch: 1,479 issues [agent]; the www.ur.ch robots.txt has no Disallow [re-checked]. **OW** year archives up to 2025 on ow.ch [agent]. |
| Open to generic crawlers, closed to AI bots | **FR** fo.fr.ch (§2.2). |
| Blocked | **AG** amtsblatt.ag.ch: robots.txt disallows `/publikationen/` and `/ekab/` [re-checked]. **GR** www.kantonsamtsblatt.gr.ch: same two paths [re-checked]. **SG** publikationen.sg.ch: `*` Disallow `/`; only named search engines are allowed [re-checked]. **TG** amtsblatt.tg.ch: the home page is a login form with a password field [re-checked]; per agent C, shared credentials are printed on the page, and they were not used [agent]. **GE** fao.ge.ch: CAPTCHA [re-checked]. **NE**: paid, "53 francs par an" [re-checked in the page agent D saved]. |
| Not online | **LU**: the Kantonsblatt page describes a print subscription ("Jahresabonnement Kantonsblatt") [re-checked in the page agent B saved]; "digital from 2028" appears only in news headlines [agent]. **AI**: "Appenzeller Volksfreund, ist zugleich das amtliche Publikationsorgan" [re-checked in the page agent C saved]. |
| Not probed | **GL** amtsblatt.gl.ch/ipub. That host has no robots.txt (404) [re-checked]. |

**Options:**
- (a) Follow robots.txt: no Amtsblattportal gazettes. Use VD, JU, UR, OW (and FR, if §2.2 allows).
- (b) Use the documented API for cantonal rubrics only, excluding rubrics with personal data.
- (c) Ask SECO or the cantons first.

### 2.2 Sites that exclude AI crawlers by name
- fo.fr.ch allows `*`, but sends `Disallow: /` to 23 named bots. They include ClaudeBot, anthropic-ai, Claude-Web, GPTBot, CCBot, Google-Extended and PerplexityBot [re-checked].
- Our crawler checks robots.txt only for `*` (`robots.can_fetch("*", url)`, `html_crawl.py:94`) [code]. It would crawl this site.
- **Recommendation:** leave fo.fr.ch out.
- The other sources have not been checked for rules that name AI bots.

### 2.3 Basel-Landschaft through its backend API
- www.baselland.ch answers 403 with a Cloudflare challenge [re-checked].
- The same content is open as Plone REST JSON at `bl-api.webcloud7.ch`. For example, `/politik-und-behorden/gerichte` returns `@type` "direktion", 25 items, modified 2026-09-22 [re-checked].
- That host's robots.txt answers 403 with an HTML page, so its usage policy is unknown [re-checked].
- That the paths map 1:1 to www.baselland.ch is [inferred] from matching URLs.
- Using bl-api goes around the canton's bot wall.
- Agent A also tried the public site once with a full Chrome user-agent [agent, disclosed].

**Options:**
- (a) Use bl-api.
- (b) Ask the canton.
- (c) Treat BL as blocked. Use only data.bl.ch (holidays dataset 13350: 58 records; communes dataset 10510: 86 records with `website`) [re-checked] and bl.clex.ch (LexWork).

### 2.4 Gaps in how our fetchers follow crawl rules (these matter if you choose 2.1a)
- **Only the HTML crawler reads robots.txt.** `robotparser` appears only in `html_crawl.py` (lines 5, 77–94). The `pdf` and `api` fetchers never check robots.txt [code, grep].
- **Python's `robotparser` applies the first matching rule.**
  - rsn.ne.ch sends `Disallow: /` followed by `Allow: /DATA/` [re-checked].
  - For `/DATA/program/books/rsne/pdf/164.1.pdf`, `robotparser` returns False [re-checked].
  - Under longest-match rules (RFC 9309), the more specific `Allow: /DATA/` wins, so the site allows its law PDFs [inferred: from the RFC rule, not a tool output].
- **Crawl-delay is ignored.** There is one global delay of 0.5 s and a cap of 200 pages (`config.py:22–23`) [code]. Sites that ask for 10 s:
  - getax.ch (`Crawl-delay: 10`) [re-checked];
  - 9 BE office hosts and www.bs.ch (the Stage 0 sitemap summary shows "delay 10.0" for each) [re-checked].
- **Other robots.txt findings:**
  - jurisprudence.vd.ch: `Disallow: /` [re-checked].
  - www.vs.ch disallows `/documents/`, `/*.pdf` and `/*.docx` [re-checked]; per agent E, also `*.xlsx` [agent].
  - The prestations.vd.ch (BLV) robots.txt answers 403 [re-checked].

---

## 3. Registry fit: categories
- The registry has 10 categories: hiking, waste, dogs, taxes, housing, transport, parking, schools, health, safety (`categories.py:11–22`) [code].
- None fits courts (C1–C5) or official notices (D2). Every court YAML in the agent reports is marked "category missing: courts".
- Adding a `courts` category and an `official_notices` category would unlock the C cells and the open gazettes.

---

## 4. City law (L1)

| City (BFS) | Texts | Dogs · waste · parking | Platform → fetcher | Evidence |
|---|---|---|---|---|
| Zürich (261) | 791 entries, 622 in force | 554.510 · 712.110 · 551.310/551.311/741.500 | Amtliche Sammlung; PDF links sit inside a JSON attribute → new `stzh-as` | Counts [agent]. The existing `stadt_zuerich.yaml` already has the Amtliche Sammlung page as a start path, shared with 3 other sections under the 200-page cap [code: stadt_zuerich.yaml, `config.py:22`]. It can never fetch the texts, because html_crawl skips `.pdf` (`html_crawl.py:14`) [code] |
| Bern (351) | **246** SSSB numbers in the sitemap [re-checked: 2,593 locs, 246 distinct `dgn-lex_` numbers]. Agent A reported 218; the difference is unexplained | 559.61 · 822.1/822.111 · 761.232 | stadtrecht.bern.ch `lex-<nr>.pdf` export → `pdf` now, `idparc-export` later | `lex-559_61.pdf` returns a PDF, 821,158 B [re-checked]; the rest [agent] |
| Thun (942) | 127 | **none** · 822.1 · several parking texts | i-web table → `iweb-table` | 127 rows, 0 mention "Hund" [re-checked] |
| Schaffhausen (2939) | 215 | 353.2 (Fr. 160 for the first dog) · 740.1 · 400.41 | i-web table → `iweb-table` | 215 rows; 353.2 and 740.1 present [re-checked]; amounts [agent] |
| Lausanne (5586) | 193 | 503.1 · 830.x · 710.1–710.3 | PHP app, PDFs with text layer → `pdf-index` | "193 résultats", 193 ids [re-checked] |
| Neuchâtel (6458) | 79 current, plus lists of the merged former communes | 12.21 (scanned) · 705.x · 810.x | TYPO3 PDF list → `pdf-index` + OCR | 79 distinct PDF links [re-checked]; the rest [agent] |
| La Chaux-de-Fonds (6421) | 175 | 41.13 · 62.1x · 63.101/63.105 | POST `/Api/Page.svc/detail` → `post-json-index` | API answers, 9 themes [re-checked]; 175 [agent] |
| Genève (6621) | 246 | cantonal (M 3 45) · LC 21 911 · LC 21 154.1 | paginated Drupal list → `pdf-index` | pages 0–24 hold 10 each, page 25 is empty [re-checked]; 246 [agent] |
| Vernier (6643) | 52 | none · 3 texts · 1 text | Drupal list → `pdf-index` | back up (200) [re-checked]; the rest [agent] |
| Lugano (5192) | 122 | 2.6.1 · 4.1/4.1.1/4.1.2 · 2.2.x | CMS list plus PDF endpoint → `pdf-index` | 122 ids; dog ordinance is a PDF [re-checked] |

---

## 5. What current fetchers can ingest now

**`api`**
- **SZ holidays:** data.sz.ch `ferienplan-kanton-schwyz`, 90 records, CC BY 4.0.
  - Agent B's YAML uses only fields that exist, and its 90 ids are unique [re-checked].
  - `api.py` reads `url`, `records_path`, `title_template` and `text_template` at `api.py:96–114`, and `id_template` at `api.py:38–41` [code].
- **BL holidays:** data.bl.ch 13350, 58 records with fields `name`, `schuljahr`, `startdatum`, `enddatum`, and 58 unique ids [re-checked]. `event_date_field` is supported (`api.py:73–74`) [code].
- **Fetch test with the repo's `ApiFetcher` and these two configs:** SZ gave 90 documents, 0 errors. BL gave 58 documents, 0 errors, with event dates filled [re-checked].
  - SZ has no `event_date_field`, so its documents carry no event date.
  - Tagging, embedding and storage were **not** run.

**`pdf`** (fixed URL lists in the agent reports)
- Holiday plans for TI, GR, LU, UR, OW, NW, AI, AR, SH, BE, AG and SO.
- Tax guides for FR, VD, NE, JU, TI, GR, UR, OW, NW and GL.
- The JU court tariff.
- City-law samples for Bern, Schaffhausen and Lugano.
- Caveat: the pdf fetcher never reads robots.txt (§2.4), and vs.ch disallows `*.pdf`.

**`html_crawl`** (YAMLs per canton in the agent reports)

| Limit | Detail |
|---|---|
| Page cap | 200 pages (`config.py:22`) [code]. gerichte-zh.ch `/de/themen` has 248 pages and the AG road section 202 [re-checked in the Stage 0 sitemaps]. |
| PDFs | Skipped (`html_crawl.py:14`) [code] |
| Query strings | Kept (`html_sections.py:155` strips only fragments; `html_crawl.py:92` checks only the path) [code] |
| JS-only sites | Will fail: sh.ch pages show 21 visible words [re-checked], La Chaux-de-Fonds, and the Tribuna/FindInfo decision apps [agent] |

---

## 6. New fetchers, ranked by reach

| # | Fetcher | Serves | Reach |
|---|---|---|---|
| 1 | `sitemap-crawl`: sitemap seeding, per-source delay and page cap, host rewrite, deny patterns, `<main>` extraction, link-following | NE (8,518 URLs after the host rewrite [re-checked]); TG steuerpraxis (3,866 URLs, 7 versions [re-checked]) and rechtsprechung.tg.ch (6,350 [re-checked]); gerichte-zh.ch; AG, SO, BS and BE (delay 10); FR, VD, GE; JU (incomplete sitemap, so link-following is needed) | about 12 cantons |
| 2 | `pdf-index`: listing page → PDFs | Tax: SG Steuerbuch (250 PDFs), GR practice (88), AR (54), AI (51), SZ, OW, NW. City law: Lausanne, Genève, Neuchâtel, Vernier, Lugano. The JU journal. Court leaflets [agent] | about 14 cantons plus 5 cities |
| 3 | `iweb-table` | UR (444 decisions, 1,479 gazette issues), NW (558 decisions, 1,748 publications), OW, Thun (127), Schaffhausen (215) | 3 cantons plus 2 cities |
| 4 | resolver inputs (`xlsx`/JSON/HTML lists) | AG 196 with BFS number and website [re-checked]; BE 334 with Homepage column [re-checked]; BL 86 [re-checked]; FR 119 with BFS; VD 300 with BFS; SG 75; ZH 160; TI 100; VS 122 pages (BFS number, website, commune judge); GR 99 domains plus a BFS PDF [agent] | 10 cantons |
| 5 | `plone-rest` | ZG Steuerbuch, 1,343 items [re-checked]; BL, depending on §2.3 | 2 cantons |
| 6 | `amtsblattportal` (eSHAB) | 14 cantonal tenants; GR has only 1 rubric | **blocked on §2.1** |
| 7 | `ics` | FR holidays (11 events per file [re-checked]); GE (g5) | 2 cantons |
| 8 | `pdf-table`: holiday rows per school body | GR (about 172 bodies), LU (79 communes), SO, UR [agent] | 4 cantons |
| 9 | single-site fetchers | `sh-cms-json` (the whole SH site [re-checked]); `lexican` (SH tax manual, 168 nodes, 143 articles [re-checked]); `stzh-as`; `idparc-export`; `post-json-index` | 1 canton plus 3 cities |
| 10 | `gazette-html` | faovd.ch; fo.fr.ch depends on §2.2 | 1–2 cantons |
| 11 | law platforms | `lexwork` (existing), `vd-blv`, `ne-rsn` (the robots nuance in §2.4), `ju-rsju`, silgeneve (GE); SZ laws are SRSZ PDFs through LexFind entity 19 [agent] | – |
| 12 | OCR | Glarus Süd dog-tax regulation, Neuchâtel dog arrêté 12.21 [agent] | – |

**Decisions (C4).** opencaselaw covers the decision portals. These are out of date or odd:

| Court | Newest decision | Note |
|---|---|---|
| OW | 2022-12-19 | stale |
| TG Obergericht | 2025-01-29 | stale |
| ZG Kantonsgericht | 2024-12-18 | stale |
| SG publikationen | 2024-04-29 | stale |
| SG Handelsgericht | 2024-07-02 | stale |
| VD findinfo | 2025-12-20 | stale |
| SH Obergericht | 2025-12-16 | stale |
| FR | **2027-07-27** | a future date: a data error |

All eight rows are [re-checked]. In addition, the AG decision database agve.weblaw.ch answers 503 [re-checked].

---

## 7. Findings that matter for jurisdiction and narrowing

### 7.1 Who sets school holidays (G3)
The quotes are in the agent reports.

**Audit status of the quotes:**
- Found word for word, either in the pages the agents saved today or on a live re-fetch: AG, AR, LU, UR, SZ (in the PDF), SG, TG (in the holiday PDF, not the HTML page), VD, GE, BL, GR (the law text) and ZG.
- **FR is paraphrased.** The live page says "les cercles scolaires disposent d'un jour de congé supplémentaire par année (deux jours pour la région de Murten/Morat)". The substance matches.
- Not re-checked: BE, NW, GL, AI, SH, TI, JU, NE, ZH, SO, OW, VS.

| Who sets them | Cantons |
|---|---|
| **The canton, one set** | BE (BKD; the sports week is free; the French part follows BEJUNE); BL; NW; GL; ZG (deciding body not verified); SG (Bildungsrat); TG (DEK); AI (two tracks); SH (by calendar-week rule, SHR 410.114); TI (DECS); VD (DEF); GE (Conseil d'Etat); JU (Gouvernement); NE (one calendar, body not named); OW (except Engelberg, [inferred] from the wording) |
| **Cantonal frame, local choice** | LU (communes within 14 weeks); UR (Erziehungsrat frame, schools decide); AR (communes choose 2 of 13 weeks); AG (Erziehungsrat 9 weeks, communes 4); GR (canton sets autumn and Christmas, school bodies the rest, BR 421.000 Art. 24 Abs. 3); FR (3 reference calendars, school circles add 1–2 days); VS (indicative frame) |
| **Local bodies** | ZH (Schulgemeinden; only school start and Christmas are binding, cited g5); SZ (Schulräte; the canton compiles the list); SO (Schulträger) |
| **Not stated** | BS (one canton-wide dataset; the canton [inferred]) |

- **Consequence:** holiday facts need narrowing below canton level in LU, UR, AR, AG, GR, FR, VS, ZH, SZ and SO.
- GR, ZH and SO also need a map from school body to BFS number.

### 7.2 Dog tax and dog rules (G1)

| Level | Cantons |
|---|---|
| **Cantonal dog tax** | NW, CHF 120 [re-checked]; AR, Fr. 120 [re-checked]; FR, CHF 100 plus 5 [re-checked in agent D's saved output]; SZ, Fr. 50 in cantonal law, communes may raise it [agent]; VD, cantonal tax law 652.31.1 [agent] |
| **Mixed** | GL: the Glarus Süd page says CHF 220, of which 55 goes to the canton [re-checked in the page agent B saved]. The legal basis for that share was not found [agent]. |
| **Communal rules or tax** | OW (818.3: "Die Einwohnergemeinden können durch Verordnung eine Hundesteuer einführen") [re-checked]; ZG ("Gesetze und Reglemente der Zuger Gemeinden") [re-checked in the page agent B saved]; SG, NE, BL (registration with the commune), GR (the VetG gives enforcement to the communes), VS (leash rules, LALPA art. 30) [agent]; TG [inferred] |

**Traps**
- The GR dog page also carries GL rules, because one office serves both cantons [agent].
- Some sources span several cantons: laburk.ch (UR, SZ, OW, NW) and vsz.ch (OW, NW). They need a multi-canton design, or one source per canton.

---

## 8. Corrections to existing documents and inputs

**PR #40, `subnational_sources.md:310`** ("Lugano … `not-a-source`")
- That verdict was about Lugano's open data: the CSV row S50 says "Lugano OGD" (`subnational_sources.csv:51`), and it traces to `g3-associations.md:32`.
- Lugano's law collection is a source: 122 texts [re-checked].
- **Fix:** narrow the line to Lugano OGD and add a row for the law collection.

**`ogd_lists_assessment.md` B.9 (Amtsblattportal)**
- It lists `tenants=` among the filters, but that filter is ignored [re-checked].
- It should add:
  - that `cantons=` includes SHAB notices [re-checked];
  - the per-canton method, `tenant=` plus the canton's own rubric codes [re-checked];
  - the robots.txt `Disallow: /` [re-checked].

**Stage 0 `law_hits.json`**

| Canton | Problem | Fix |
|---|---|---|
| SO | court_fees = 125.751.3, a Hague convention [re-checked] | BGS 615.11 "Gebührentarif" [re-checked: title and active status in Stage 0 `laws_SO.json`] |
| AG | no court_fees entry [re-checked] | SAR 662.110 "Gebührendekret" [re-checked in `laws_AG.json`]. The old 221.150 "Dekret über die Verfahrenskosten" is abrogated [re-checked: `abrogated: true` via the AG LexWork API] |
| SH | court_fees = 172.201, the administrative-fee ordinance [re-checked] | Justizgesetz 173.200. It contains "Im Schlichtungsverfahren beträgt die Pauschalgebühr Fr…" [re-checked] |
| NE, GE, FR | entries missing | NE 164.1; GE E 1 05.10; FR 130.11/130.16. All present and active in the Stage 0 listings, with the titles the agents gave [re-checked] |
| BS, SO | tax laws missing | BS 640.100; SO 614.11. Present and active [re-checked] |
| GR | dogs missing | VetG 914.000. Present and active [re-checked] |
| SZ | no LexWork collection | SRSZ PDFs through LexFind entity 19 [agent] |

**Stage 0 pre-check**
- GR courts live at www.justiz-gr.ch: the bare host has no DNS, www resolves, and its sitemap has 305 URLs [re-checked]. GR merged its courts into the Obergericht in 2025 [re-checked quote].
- www4.ti.ch answers 200; the brief said 403 [re-checked].
- The NE sitemap is recoverable [re-checked].
- gl.ch id 720 is a forestry page, so every AI court link ending in /720 is wrong. The only `/720` URL in the Stage 0 sitemap is `…/wald-und-naturgefahren/merkblaetter-richtlinien-links.html/720` [re-checked].

**Brief v5 path error (orchestrator)**
- `commune_sites.csv` and `ogd_lists_assessment.md` pointed at the PR #40 folder, where they do not exist.
- Fixed mid-run. Agents A and D were told; C noticed and read the repo copy.

---

## 9. Orchestrator re-check log (2026-09-23)
Scripts are in `scratchpad/recheck/`: `e_claims.py`, `abp_check.py`, `ti_mix.py`, `b_claims.py`, `c_claims.py`, `d_claims.py`, `a_claims.py`, `a_claims2.py`, plus the inline commands in the session.

| # | Claim (agent) | Result |
|---|---|---|
| 1 | www.justiz-gr.ch sitemap (E) | 200, 305 URLs ✓ |
| 2 | GR court merger 2025 (E) | quote found ✓ |
| 3 | Lugano 122 texts, dog PDF (E) | 122 ids; PDF 81,786 B ✓ |
| 4 | Amtsblattportal `cantons=` works, `tenants=` ignored (E) | TI 2,014, VS 1,942; `tenants=` 32,718 = unfiltered ✓ |
| 5 | 401 without `publicationStates` (E/C) | 401 without, 200 with, same client ✓ |
| 6 | VS JustSearch API (E) | count 5,006 ✓ |
| 7 | TI root 200 (E) | 200, redirect ✓ |
| 8 | NeueScraper licence (E) | AGPL-3.0, pushed 2026-09-18 ✓ |
| 9 | opencaselaw Atom feed GR (E) | 50 entries, updated today ✓ |
| 10 | Gazette robots.txt (B, A, C) | `Disallow: /` on 10 hosts, including amtsblattportal.ch ✓ |
| 11 | ZG own-rubric count (B) | 2,213 ✓ |
| 12 | ZG Steuerbuch Plone (B) | Book, 1,343 ✓ |
| 13 | SZ holidays dataset and YAML (B) | 90, CC BY 4.0, fields exist, ids unique ✓ |
| 14 | NW dog tax (B) | CHF 120 quote ✓ |
| 15 | OW and ZG opencaselaw staleness (B) | 2022-12-19 / 2024-12-18 ✓ |
| 16 | `cantons=` includes SHAB (orchestrator) | TI 356/500 shab; VS 288/500 ✓ |
| 17 | sh.ch JS shell and CMS JSON (C) | 21 words; JSON with the text ✓ |
| 18 | SH lexiCan (C) | 168 nodes, 143 leaves ✓ |
| 19 | TG steuerpraxis (C) | 3,866 URLs, 7 versions; **558** in 2026-09 (C said 559) |
| 20 | rechtsprechung.tg.ch (C) | 6,350 ✓ |
| 21 | TG, SH and SG opencaselaw staleness (C) | ✓ |
| 22 | Stadt Schaffhausen (C) | 215 rows; 353.2 and 740.1 ✓ |
| 23 | AR dog tax (C) | Fr. 120 ✓ |
| 24 | publikationen.sg.ch robots (C) | `*` Disallow `/` ✓ |
| 25 | SH court fees are in 173.200 (C) | sentence found; law_hits had 172.201 ✓ |
| 26 | NE sitemap host rewrite (D) | internal host has no DNS; 5,000 + 3,518 ✓ |
| 27 | Romandie tenants external (D) | all 5 `external: true`; VD 21,235, NE 387 ✓ |
| 28 | Lausanne 193 (D) | ✓ |
| 29 | Genève 246 (D) | 25 pages of 10 ✓ (not counted exactly) |
| 30 | La Chaux-de-Fonds API (D) | answers, 9 themes ✓ (175 not re-counted) |
| 31 | FR ICS (D) | 11 events, 2026-10-12 ✓ |
| 32 | FR future date, VD findinfo stale (D) | 2027-07-27 / 2025-12-20 ✓ |
| 33 | fao.ge.ch CAPTCHA (D) | redirect to /captcha ✓ |
| 34 | faovd.ch and rsju.jura.ch robots (D) | none / no Disallow ✓ |
| 35 | fo.fr.ch AI-bot groups (orchestrator) | `*` open; 23 named bots blocked ✓ |
| 36 | rsn.ne.ch, jurisprudence.vd.ch, getax.ch robots (D) | ✓; rsn.ne.ch also has `Allow: /DATA/` (D did not mention this) |
| 37 | Python `robotparser` on rsn.ne.ch (orchestrator) | False for /DATA/ PDFs |
| 38 | Vernier back up (D) | 200 ✓ |
| 39 | www.baselland.ch Cloudflare (A) | 403 challenge ✓ |
| 40 | bl-api open JSON; robots 403 (A) | ✓ |
| 41 | eSHAB XML export BA-SO (A) | total 248 ✓ |
| 42 | "JSON without `/xml` returns 401" (A) | **Wrong:** the same query as JSON gives 200, total 248 |
| 43 | ZH death notices (A) | 732 ✓ |
| 44 | Bern `lex-559_61.pdf` (A) | PDF ✓ |
| 45 | Thun 127 rows, no dog text (A) | ✓ |
| 46 | AG, BE, BL directories (A) | AG BFSNR + Internet, 16 Sept 2026; BE Homepage, 336 rows (header included); BL 86 with website ✓ |
| 47 | agve.weblaw.ch 503 (A) | still 503 ✓ |
| 48 | law_hits SO and AG (A) | Hague convention / missing ✓ |
| 49 | Code citations `config.py:22–23`, `html_crawl.py:14/94`, `api.py:73–74/96–114`, `categories.py:11–22` | read ✓ (`id_template` is at `api.py:38–41`) |
| 50 | Audit: robots.txt handling anywhere in `src/` | only `html_crawl.py` ✓ |
| 51 | Audit: AR, SH, NW, OW gazette robots; GR DIAM paths; www.ur.ch; www.vs.ch `*.pdf`; prestations.vd.ch 403 | ✓ all |
| 52 | Audit: 14 cantonal tenants own rubrics | ✓ (GR only 1: AA-GR) |
| 53 | Audit: Stage 0 law listings contain the corrected law numbers; AG 221.150 abrogated | ✓ |
| 54 | Audit: 17 quoted sentences in the pages agents saved; 4 more on a live re-fetch | ✓; FR paraphrased |
| 55 | Audit: ApiFetcher on the SZ and BL holiday configs | 90/0 and 58/0 documents/errors ✓ |
| 56 | Audit: Bern SSSB count | **246**, not 218 |
| 57 | Audit: Neuchâtel 79 PDFs; gerichte-zh 248; AG road 202; gl.ch /720 | ✓ |

---

## 10. Process notes
**Timeline**
- **05:30:** first launch.
- **05:39:** all five agents stalled; their logs end with an unanswered command, one of them an approval prompt.
- **09:14:** the laptop battery died.
- **12:04–12:09:** Stage 0 was rebuilt by replaying the recorded commands.
- **12:11:** relaunch.

**Agent run times:** E 85 min, B 99 min, C 111 min, D 114 min, A 118 min.

**Agents A and D ran a second time.** The orchestrator's correction reached D 70 ms after D's first final report (12:05:57.154Z vs 12:05:57.224Z in its transcript) [re-checked]. It restarted D. A was restarted the same way: the correction reached it 77 ms after its first final report (12:09:42.532Z vs 12:09:42.609Z) [re-checked]. Both second reports replace the first ones. A's second report adds own-rubric gazette counts.

**Disclosed conduct**
- C made 2 requests to publikationen.sg.ch before reading its robots.txt, then stopped.
- C did not use the TG gazette credentials printed on the page.
- A tried Cloudflare once with a Chrome user-agent.
- E ran one shell loop over local files.

**For brief v6**
- Forbid user-agent spoofing.
- Read robots.txt, including rules for named AI bots, before the first request to any new host.
- Count gazettes with `tenant=` plus the canton's own rubrics.
- Add the traps found in this run:
  - the jura.ch sitemap is incomplete;
  - justice.ge.ch sitemap URLs contain `//`;
  - gl.ch routes by trailing id;
  - the NE sitemap needs a host rewrite;
  - sh.ch pages are JS shells;
  - the La Chaux-de-Fonds data sits behind a POST API.

---

## 11. Open (not verified)
- The Amtsblattportal terms of use: the orchestrator did not read the docs.
- The bl-api usage policy, and whether its paths map 1:1 to www.baselland.ch.
- The BL Steuerbuch.
- The AGVE database format (host down).
- The role of GR's Justizgericht, and whether GR cantonal notices appear on Amtsblattportal.
- VS decisions: opencaselaw has 7,008, the court API 5,006. The difference is unexplained.
- Who sets school holidays in BS, ZG and NE.
- amtsblatt.gl.ch/ipub.
- robots.txt rules for named AI bots on all other sources.
- Exact counts for Genève (246) and La Chaux-de-Fonds (175).
- The Onlinekommentar resumption-token expiry date (2026-09-17).
