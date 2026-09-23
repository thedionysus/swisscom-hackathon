# G4 report: intercantonal agreements + cantonal law platforms (Opus 5.5 agent, 2026-09-23)
Run: 88 tool calls, ~147k tokens, ~29 min. Evidence: /tmp/sg-verify-g4-intercantonal/.
The full report text is in the session transcript (subagent hand-back). Below is the agent's backup copy.

**Spot-checked by the main session (live curl, 2026-09-23). All matched:**
- intlex.ch `/api/de/texts_of_law/lightweight_index`: 40 categories, 317 texts, 317 active
- intlex `/api/de/texts_of_law/4.2-2` title = "Interkantonale Vereinbarung über die Harmonisierung der obligatorischen Schule"
- lightweight_index on AG 463, SG (www.) 732, FR 814, OW 517 texts (these match the agent's "active" column)
- lex.vs.ch `/api/fr/texts_of_law/101.1`: "Constitution du canton du Valais", xhtml 242,785 chars
Not re-checked: the LexFind systematics listing, NE/JU/TI/VD platform routes, the concordat member lists, the edudoc WAF.

---
# g4-intercantonal report (backup copy)
See the SubagentHandback message for the full text. Key finds:
- intlex.ch (Interkantonales Publikationsorgan iSR) is a LexWork portal: /api/de/texts_of_law/lightweight_index lists 317 active intercantonal agreements; /api/de/texts_of_law/{nr} JSON; PDFs with text layer and an accession table (Beitrittstabelle).
- LexWork listing endpoint: /api/{lang}/texts_of_law/lightweight_index[?text_of_law_type_ids[]=N&show_abrogated=true] works on intlex, BS, AG, SG, GR, SO, VS, FR, OW, ZG, LU, BL, BE.
- AG, SG, GR, SO, VS, FR, OW are LexWork (constitution JSON with xhtml_tol). NE, JU, TI, VD are not (PDF/HTML/own JSON API).
- LexFind listing: /api/fe/{lang}/entities/{id}/systematics?active_only=true&tols_for_systematics[]=<node ids> (chunk at 100 ids; longer URLs get 414).
- edudoc.ch (EDK PDFs) sits behind an AWS WAF challenge (HTTP 202, 0 bytes); OAI-PMH metadata works.

---
## Full findings (transcribed from the agent's hand-back by the main session)

### Headline
**www.intlex.ch** ("Interkantonales Publikationsorgan iSR") is an official **LexWork** portal for intercantonal
agreements: 317 active texts, with a listing endpoint. The **same listing endpoint works on every LexWork canton portal.**

### Per lead
| id | Claim check | Real location | Format | Can we get it | Authority |
|---|---|---|---|---|---|
| U1 EDK | Partly | edk.ch page (server HTML, 65 links → edudoc.ch PDFs) | edudoc PDFs: **HTTP 202 / 0 B, AWS WAF challenge**. OAI-PMH metadata works, but its policy says full content may not be harvested by robots | Metadata only. Use intlex for texts | official_info |
| U2 HarmoS members | Confirmed (15), not from the ZH page | intlex `/api/de/versions/1747/pdf_file` (9 pages, text) | PDF Beitrittstabelle | Yes (pdf + table parser) | cantonal_law |
| U3/D14/C9 IVHB | Partly. **ivhb.ch is a private law firm (institutional)** | bpuk.ch/bpuk/konkordate/ivhb + PDFs (text, Anhang 1, Stand_Beitritte 2022) | server HTML + PDF text | Yes today | intlex = cantonal_law, BPUK = official_info |
| U4 KKJPD | Confirmed | kkjpd.ch page, files via `?action=get_file&...&resource_link_id=<hex>`, RSS `?id=62&mod_action=rss` | PDF text | Yes today (pdf) | official_info |
| U5 LexFind IKAPOL | Partly. 114768 is a **version id**, an outdated Zug copy | Current IKAPOL = intlex 5.3-2 (in force 01.01.2025) | JSON + PDF | Yes, new fetcher | cantonal_law |
| U6 KKPKS | Confirmed (4 concordats, ZH+TI outside) | kkpks.ch/de/polizeilandschaft/konkordate + /clcpc /pknw /zpk /ostpol | server HTML + PDF | Yes today | official_info |
| Gap: GSK lotteries | Found | gespa.ch/de/gesetze-und-bewilligungen/regulierungsgrundlagen (comlot.ch redirects there). intlex 9.5-3/-4/-5 | server HTML + PDF text | Yes today | intlex = cantonal_law, GESPA = official_info |

**Concordat membership (from the intlex accession tables and conference pages):**
- HarmoS 15: ZH BE GL FR SO BS BL SH SG TI VD VS NE GE JU
- IVHB 17 per BPUK: AG AI BE BL FR GR JU LU NE NW OW SH SO TG VS UR ZG. **SZ left on 22.09.2022, but intlex still lists SZ, so intlex tables miss withdrawals**
- Hooligan concordat: 2007 version 25 cantons (no TI); 2012 amendment 24 cantons (incl. TI, without BS/BL)
- Police concordats: Westschweiz FR GE JU NE VD VS · PKNW AG BL BS BE SO · ZPK LU NW OW SZ UR ZG · Ostpol AR AI GL GR SH SG TG (+ city police Chur, St. Gallen, FL)
- GSK: all 26 cantons (in force 01.01.2021), so jurisdiction CH works in practice

### Cantonal law platforms (handoff lead 1)
**LexWork confirmed on 7 more cantons, so 19 in total.** Constitution returned 200 JSON with xhtml:
| Canton | Host | Const. nr | Active texts | Interkant. Vereinbarungen (active) |
|---|---|---|---|---|
| AG | gesetzessammlungen.ag.ch | 110.000 | 463 | 81 |
| SG | **www.**gesetzessammlung.sg.ch | 111.1 | 732 | 148 |
| GR | **www.**gr-lex.gr.ch | 110.100 | 419 | 49 |
| SO | bgs.so.ch | 111.1 | 539 | 83 |
| VS | lex.vs.ch (fr) | 101.1 | 690 | 39 |
| FR | bdlf.fr.ch (fr) | 10.1 | 814 | 67 |
| OW | gdb.ow.ch | 101.0 | 517 | 67 |

**LexWork API routes** (found in the JS bundle):
- `GET /api/{lang}/texts_of_law/lightweight_index[?text_of_law_type_ids[]=<id>&show_abrogated=true]` → `{category_id: [{id, systematic_number, systematic_category_id, title, abrogated, structured_document_id}]}` (**the missing listing endpoint**)
- `/api/{lang}/texts_of_law/{nr}` (detail: `selected_version.xhtml_tol`, `pdf_link_tol`, dates)
- `/api/{lang}/text_of_law_types` (type id 2 = Interkantonale Vereinbarungen on every portal checked)
- `/api/{lang}/systematic_categories`, `/api/{lang}/status/recent_changes`, `/status/future_changes` (**change feed**)
- `/api/{lang}/texts_of_law/{nr}/versions/{id}/show_as_json`
Cantonal copies of concordats often have **xhtml** where intlex has PDF only (SG 211.41 HarmoS: 1,350 words of xhtml).

**Not LexWork** (LexFind counts of active texts):
- NE rsn.ne.ch (823): `/DATA/program/books/rsne/pdf/{nr}.pdf` or `/htm/{nr}.htm` (windows-1252 HTML)
- JU rsju.jura.ch (855): `viewdocument.html?idn=20002&id=X&download=1` returns the PDF
- TI www3.ti.ch (622): `/CAN/RLeggi/public/index.php/raccolta-leggi/legge/num/{n}` (server HTML). The root returns 403
- VD prestations.vd.ch/pub/blv-publication/ (902): Angular app with a JSON API: `api/recueil-systematique`, `api/actes/CONSOLIDE?id=<uuid>&cote=<nr>`, `api/actes/<htmlId>/html` (XHTML), `/pdf`

**LexFind listing (corrects ogd_lists_assessment §3.2):** `GET /api/fe/{lang}/entities/{id}/systematics?active_only=true&tols_for_systematics[]=<node>…`
returns acts with ids. Over ~100 node ids gives HTTP 414, so batch the requests. `texts-of-law/{id}` → `original_url`. Also `/by-version/{id}`, fulltext-search (POST). Entity 28 = Intlex.

### New fetcher classes
1. **LexWork collection fetcher** (index → detail → xhtml articles, PDF fallback, change feed). Covers **19 cantons + intlex**.
2. **Concordat membership parser** (regex on the intlex Beitrittstabelle, cross-checked against the conference lists).
3. **LexFind enumerator** (systematics listing → original_url).
4. **VD BLV JSON fetcher**. 5. **NE RSN fetcher**. 6. **TI RLeggi HTML fetcher**. 7. **JU rsju PDF fetcher**.
8. (Not recommended) a browser-based fetcher for edudoc.ch (WAF; robots policy forbids harvesting).
