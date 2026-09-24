"""Write run3_compatibility.csv: one row per Run 3 catalogue row (148). Reads conversion_report.json + decisions."""
import csv
import json
import os

import yaml

from run3_decisions import HTML, NEW

S = "<scratchpad>"
R3 = S + "/newpipe/run3_copy/docs/sources/verification_2026-09-23/run3"  # git archive of c93ae3f; wt-run3 was removed mid-session
OUT = S + "/newpipe"
rep = json.load(open(OUT + "/conversion_report.json"))
catalogue = list(csv.DictReader(open(R3 + "/source_catalogue.csv", encoding="utf-8")))
ready = {f[:-5]: yaml.safe_load(open(os.path.join(R3, "ready_sources", f), encoding="utf-8"))
         for f in os.listdir(R3 + "/ready_sources") if f.endswith(".yaml")}
row_manifest = rep["row_manifest"]
overlap = rep["overlap_with_declared"]
new_notes = {r: n["note"] for n in NEW for r in n["rows"]}

NOW, SMALL, NEWCONN, NODOC, DECL, PENDING = ("convertible now", "convertible with small pipeline change",
                                             "needs new connector", "not a document source", "already declared",
                                             "blocked: decision pending")
JSON_API = ("JSON API connector: paged JSON records -> one document per record, records_path, id/title/text "
            "templates, event date field, rolling date window {start}")
JSON_ATTR = "html connector: read links from JSON-valued attributes (i-web data-entities, stzh-datatable rows)"
FIXED_PDF = "fixed-URL PDF list (e.g. config.pdf_urls handed to the PDF connector without a linking page)"

SPECIAL = {
    # ---- pdf rows and folds
    "ag_schulferien": (SMALL, "html", "TLS: per-source CA bundle / verify option in corpus_http "
                       "(corpus_source_commands.py:46-47); process-wide SSL_CERT_FILE is the only lever today",
                       "entry is in SECTION 2 of the candidates; parent page links the PDF (offline)"),
    "ai_ferienplan": (NOW, "html", "", "folded into ai_guidance: its '.pdf/download' link on the ferienplan start page is "
                      "found with pdf_link_patterns (offline)"),
    "sg_gerichte_kostenmerkblatt": (NOW, "html", "", "folded into sg_gerichte_info: merkblaetter.html (inside its prefix) "
                                    "links the leaflet folder (10 PDFs, offline)"),
    "zg-pdfs": (NOW, "html", "", "folded into zg_hunde_ferien: both PDFs linked from its start pages (offline)"),
    "ju-court-tariff": (NOW, "html", "", "folded into ju_justice; the circulars page links a newer tariff version "
                        "(24c70508..., modif. du 17.12.2024) than Run 3's ff78dbf9 URL, so the pin follows the page. "
                        "HEAD-404 blocker gone: the PDF connector sends GET only (pdf.py:124)"),
    "ju-tax-guide": (NOW, "html", "", "HEAD-404 blocker gone: GET only (pdf.py:124). " + new_notes["ju-tax-guide"]),
    "gl-pdfs": (SMALL, "html (partial)", FIXED_PDF,
                "Glarus Nord holiday PDF converted now as gl_pdfs; the cantonal Wegleitung PDF is linked from no page "
                "(run3-b.md:180)"),
    "nw-pdfs": (SMALL, "unsupported", JSON_ATTR + "; or " + FIXED_PDF,
                "NW holiday PDF /_doc/456520 is not an <a href> on /biddirektionssekrdienste/520 (0 matches offline; the "
                "documents table is data-entities JSON). steuern-nw.ch Wegleitung: no parent page identified"),
    "sh_ferien": (SMALL, "unsupported", FIXED_PDF + "; or the sh.ch CMS JSON connector",
                  "the linking page on schule.sh.ch is on the same JS-shell CMS as sh.ch (run3-c.md:365); not saved"),
    "stadt_bern_sssb_hunde_abfall_parkieren": (SMALL, "unsupported", FIXED_PDF + "; full collection: rewrite sitemap "
                                               "dgn-lex_<nr> locs to lex-<nr>.pdf",
                                               "stadtrecht.bern.ch pages are a 3,944-byte JS shell with 0 links (offline); "
                                               "authority would be municipal_law"),
    "stadt_schaffhausen_rs": (SMALL, "unsupported", JSON_ATTR + "; or " + FIXED_PDF,
                              "/rechtssammlung holds 215 rows only inside data-entities (0 <a href> PDFs offline; "
                              "run3-c.md:425); sitemap lists no /_rte/ or /_doc/ URLs"),
    "stadt_thun_abfall_parkieren": (SMALL, "unsupported", JSON_ATTR + "; or " + FIXED_PDF,
                                    "/reglementeverordnungen: 127 rows only inside data-entities (0 <a href> PDFs "
                                    "offline); sitemap lists no /_rte/ or /_doc/ URLs"),
    "stadt_zuerich_as_hunde_abfall_parkieren": (DECL, "html (declared: zuerich_city)",
                                                JSON_ATTR + "; plus pdf_allow_prefixes .../dam/web/de/politik-verwaltung/"
                                                "politik-recht/amtliche-sammlung/ on zuerich_city",
                                                "AS detail pages are inside zuerich_city's https://www.stadt-zuerich.ch/de/; "
                                                "the PDF link sits in <stzh-datatable rows=...> JSON (offline)"),
    "ge-ocv-fees": (DECL, "html (declared: ge_canton)", "none (manifest): add pdf_link_patterns "
                    "'^https://www\\.ge\\.ch/document/\\d+/telecharger$' to ge_canton",
                    "ge_canton owns all of https://www.ge.ch/ but has no pdf_link_patterns, so /document/<id>/telecharger "
                    "is fetched as a page and skipped as non-HTML (html_meta.py:150-151, html.py:257)"),
    "ti_dc_istruzioni_pf": (DECL, "html (declared: ti_canton)", "raise MAX_PDF_BYTES (30 MB, pdf.py:37) for a 43.7 MB PDF",
                            "ti_canton's pdf prefix https://www4.ti.ch/fileadmin/ covers it; the parent page links it "
                            "(offline) but the download aborts past 30 MB (pdf.py:134-143)"),
    "ti_calendario_scolastico": (DECL, "html (declared: ti_canton)", "",
                                 "www4.ti.ch calendar page links 4 calendars (offline); m4.ti.ch serves the same files "
                                 "(run3-e.md:37)"),
    "vd-tax-instructions": (DECL, "html (declared: vd_canton)", "",
                            "linked from /etat-droit-finances/impots/formulaires-directives-et-baremes (run3-d.md:126), "
                            "inside vd_canton; 68 pages, within max_pdfs 60 only if reached early"),
    "gr_schulferien": (DECL, "html (declared: gr_canton)", "", "www.gr.ch/DE/ belongs to gr_canton"),
    "gr_stv_wegleitung": (DECL, "html (declared: gr_canton)", "", "www.gr.ch/DE/ belongs to gr_canton"),
    # ---- api rows
    "bl_schulferien": (NEWCONN, "unsupported", JSON_API,
                       "ADR 0014: holidays are indexed documents, so a JSON connector must emit one document per record "
                       "(58 records, event dates); www.baselland.ch is behind Cloudflare, data.bl.ch is the open route"),
    "sz-schulferien": (NEWCONN, "unsupported", JSON_API,
                       "ADR 0014 applies as for BL (90 records, no event date field); alternative: the sz.ch Ferienplan "
                       "PDF (.../85734/..., run3-b.md:88) through html once its linking page is found"),
    "ar_amtsblatt": (NEWCONN, "unsupported", JSON_API + " + robots exemption", "superseded by amtsblatt_ar"),
    "sh_amtsblatt_regierung": (NEWCONN, "unsupported", JSON_API + " + robots exemption", "superseded by amtsblatt_sh"),
    # ---- needs-new-fetcher rows
    "bl_gerichte": (NEWCONN, "unsupported", "Plone REST JSON connector + robots policy exemption",
                    "bl-api.webcloud7.ch robots.txt answers 403, which load_robots turns into disallow-all "
                    "(html.py:60-61; offline mock)"),
    "bl_plone_rest": (NEWCONN, "unsupported", "Plone REST JSON connector + robots policy exemption",
                      "same host as bl_gerichte; decision 2026-09-23: use it"),
    "zg_steuerbuch_plone": (NEWCONN, "unsupported", "Plone REST JSON connector",
                            "wissen.zg.ch is Angular SSR (run3-b.md:208); whether its HTML carries the text was not "
                            "checked"),
    "sh_cms_json": (NEWCONN, "unsupported", "JSON-by-id connector (sh.ch CMS content API)",
                    "sh.ch HTML pages are JS shells (consolidated_report.md:210)"),
    "sh_ch_guidance": (NEWCONN, "unsupported", "JSON-by-id connector (sh.ch CMS content API)", "same API as sh_cms_json"),
    "sh_lexican_steuer": (NEWCONN, "unsupported", "lexican connector (session cookie + JSON outline + PDF)", ""),
    "sg_steuerbuch_pdfs": (NOW, "html", "", "merged into sg_steuerbuch: TOC links 248 PDFs (offline)"),
    "gr_steuer_praxis_pdfs": (DECL, "html (declared: gr_canton)", "",
                              "www.gr.ch/DE/ belongs to gr_canton; its 88 PDFs need gr_canton to reach the praxis page "
                              "and a max_pdfs above 60"),
    "ar_steuer_pdfs": (NOW, "html", "", new_notes["ar_steuer_pdfs"]),
    "ai_steuer_pdfs": (NOW, "html", "", new_notes["ai_steuer_pdfs"]),
    "ur_iweb_tables": (SMALL, "unsupported", JSON_ATTR,
                       "/rechtsprechung and /amtsblatt hold 444 decisions / 1,479 issues only in data-entities "
                       "(0 <a href> PDFs offline); single publication pages do link their PDF (/_rte/publikation/42868)"),
    "nw_iweb_tables": (SMALL, "unsupported", JSON_ATTR, "/obgrechtsprechung: 0 <a href> PDFs offline (data-entities)"),
    "stadt_thun_iweb": (SMALL, "unsupported", JSON_ATTR, "127 rows in data-entities (run3-a.md:544; 0 <a href> PDFs offline)"),
    "stadt_schaffhausen_iweb": (SMALL, "unsupported", JSON_ATTR, "215 rows in data-entities (run3-c.md:425)"),
    "stadt_zuerich_as": (DECL, "html (declared: zuerich_city)", JSON_ATTR + "; plus pdf_allow_prefixes on zuerich_city",
                         "AS pages are inside zuerich_city's scope; PDF links sit in <stzh-datatable rows=...> JSON"),
    "stadt_bern_sssb": (SMALL, "unsupported", "rewrite sitemap dgn-lex_<nr> locs to lex-<nr>.pdf, or " + FIXED_PDF,
                        "sitemap: 2,593 locs, 246 dgn-lex_ numbers (offline); pages are a JS shell"),
    "lausanne_recueil": (DECL, "html (declared: lausanne_city)", "none (manifest): add start URL, pdf_link_patterns "
                         "'serve\\.php\\?id=\\d+&kind=recueil' and max_pdfs ~200 to lausanne_city",
                         "index_recueil.php links 193 serve.php PDFs (offline, with that pattern)"),
    "geneve_ville_reglements": (DECL, "html (declared: geneve_city)", "none (manifest): add start URL, pdf_link_patterns "
                                "'^https://www\\.geneve\\.ch/administration-municipale/reglements-municipaux/lc\\d+' and "
                                "max_pdfs ~250 to geneve_city",
                                "list links /administration-municipale/reglements-municipaux/lc<nr>-<slug> (offline), "
                                "which serve the PDF (endpoints.md:82); pages ?page=0..24"),
    "neuchatel_ville_reglementation": (NOW, "html", "none if the /fr/ alternate serves the page; else keep PDF links of "
                                       "non-emitted pages (html.py:318-322)", new_notes["neuchatel_ville_reglementation"]),
    "chaux_de_fonds_reglementation": (NEWCONN, "unsupported", "POST JSON connector",
                                      "list comes from POST /Api/Page.svc/detail; saved list page has 0 PDF links (offline)"),
    "vernier_reglements": (NOW, "html", "", new_notes["vernier_reglements"]),
    "lugano_legislazione_all": (NOW, "html", "", "merged into lugano_legislazione (122 /law/ links, offline)"),
    "fr_ics_holidays": (NEWCONN, "unsupported", "ICS connector",
                        "text/calendar is skipped by the html connector (html.py:257) and rejected by the PDF connector "
                        "(pdf.py:131-133); the FR holiday page itself is converted (fr_school_holidays)"),
    "ju_journal_officiel": (NOW, "html", "", new_notes["ju_journal_officiel"]),
    "vd_faovd": (NOW, "html", "", new_notes["vd_faovd"]),
    "fr_feuille_officielle": (PENDING, "html (technically)", "a robots check for our own product token and named AI "
                              "bots, if the policy is to honour them",
                              "robots allows '*' and disallows ClaudeBot/anthropic-ai/GPTBot by name; the crawler checks "
                              "'*' only (html.py:38,184), so it would crawl it. User decision 2026-09-23 pending: not "
                              "added"),
    "tg_rechtsprechung_sitemap": (NOW, "html", "", new_notes["tg_rechtsprechung_sitemap"] if "tg_rechtsprechung_sitemap" in new_notes else ""),
    "ne_sitemap_rewrite": (SMALL, "unsupported", "sitemap host rewrite (ne-prod-admin.ne.ch -> www.ne.ch)",
                           "index and all 8,518 page locs name http://ne-prod-admin.ne.ch (offline); child sitemaps fail "
                           "and page locs fall outside allow_prefixes (sitemap.py:127-129, html.py:208-209). NE sources "
                           "work by link-following without it"),
}

rows_out = []
for r in catalogue:
    rid = r["id"]
    y = ready.get(rid)
    old = r["fetch_strategy"] or "(none)"
    manifest_id = row_manifest.get(rid, "")
    if rid in SPECIAL:
        status, conn, change, notes = SPECIAL[rid]
    elif r["readiness"].startswith("resolver input"):
        status, conn, change, notes = NODOC, "n/a", "", "commune directory: input for the location resolver, not evidence"
    elif y and y["fetch_strategy"] == "api":
        status, conn, change = NEWCONN, "unsupported", JSON_API + " + robots exemption for amtsblattportal.ch"
        notes = ("gazette: robots.txt Disallow: / on amtsblattportal.ch (endpoints.md:39-40) and load_robots would refuse "
                 "it; list endpoint has titles only (notice text needs /publications/<id>/xml); personal data "
                 "(e.g. 732 ZH 'Todesanzeige')")
    elif y and y["fetch_strategy"] == "html_crawl" and rid in overlap:
        sid = next(iter(overlap[rid]))
        status, conn, change = DECL, f"html (declared: {sid})", ""
        notes = f"inside {sid}'s prefix {overlap[rid][sid][0]}"
    elif y and y["fetch_strategy"] == "html_crawl":
        d = HTML[rid]
        status, conn, change = NOW, "html", ""
        parts = []
        if d.get("lu"):
            parts.append("old blocker: a page-wide <form id=mainform> is dropped by DROP_TAGS and <body> is the root, so 0 "
                         "sections; content_selector #mainContent fixes it (offline: 21/21 saved LU pages yield sections). "
                         "Selector found offline, not in an agent report")
        for k in ("note", "fold_note"):
            if d.get(k):
                parts.append(d[k])
        notes = "; ".join(parts)
        if rid == "gerichte_zh_themen":
            change = "optional: retry transport errors (RemoteProtocolError) like 429/503"
    elif rid in new_notes:
        status, conn, change, notes = NOW, "html", "", new_notes[rid]
    else:
        raise SystemExit(f"unhandled row {rid}")
    if status == DECL and not manifest_id:
        manifest_id = ""
    rows_out.append(dict(id=rid, canton=r["canton"] or (y["default_extent_id"].split("-")[1] if y else ""),
                         old_strategy=old, new_connector=conn, status=status, required_pipeline_change=change,
                         notes=notes, manifest_id=manifest_id))

with open(OUT + "/run3_compatibility.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0]))
    w.writeheader()
    w.writerows(rows_out)
from collections import Counter
print(len(rows_out), "rows")
print(Counter(r["status"] for r in rows_out))
print(Counter((r["old_strategy"], r["status"]) for r in rows_out))
print("rows mapped to a manifest entry:", sum(1 for r in rows_out if r["manifest_id"]),
      "| distinct manifest ids:", len({r["manifest_id"] for r in rows_out if r["manifest_id"]}))
