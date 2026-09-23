# Run 3 (2026-09-23): source grids for all 26 cantons and 10 cities

Five verification agents (Opus 5.5, brief v5) filled a fixed grid of 11 cells per canton, plus city law for 10 cities:
- **C1–C5:** courts home, court fees, court guidance, decisions, conciliation.
- **G1–G4:** dogs, tax guide, school holidays, road office.
- **D1:** commune directory.
- **D2:** chancellery and gazette.

The orchestrator re-checked the claims that decisions rest on, then audited the consolidated report.

**Result:** 286 canton cells: 240 verified, 44 verified with a gap, 2 blocked. No cell is empty. All 10 cities are verified.

## Start here
| File | What it is |
|---|---|
| `consolidated_report.md` | The merged, audited report: decisions (§2), coverage grid, city law, ingestible now, new fetchers ranked, jurisdiction findings, corrections to existing docs and inputs, and the orchestrator's re-check log (§9) |
| `endpoints.md` | Every machine-readable data endpoint confirmed in this run, with its format and who verified it |
| `confirmed_links.csv` | One row per grid cell (296 = 286 canton cells + 10 cities), extracted automatically from the agent grids. See the column notes below |
| `draft_sources/run3-{a..e}.yaml` | The agents' draft source configs, copied verbatim: 38 blocks, 99 entries, all parse as YAML. **Not registered sources.** |
| `agent_reports/run3-{a..e}.md` | The full agent reports. These are the authority for every cell: URL, HTTP status, title, format, quoted sample, site recipe, claim checks |
| `agent_reports/run3-{a,d}_v1.md` | First versions of the A and D reports. Both agents re-ran after a late orchestrator message; the files without `_v1` are the final ones |
| `agent_brief_v5.md` | The brief the agents followed, including the grid contract. Two path fixes were applied mid-run |

## Decisions recorded (2026-09-23, user)
1. **Gazettes:** use the documented Amtsblattportal API. Take cantonal notices by `tenant=kab<xx>` plus the canton's own rubric codes, with `publicationStates=PUBLISHED`.
2. **fo.fr.ch (FR gazette):** it cannot be left out; find another way. The site blocks ClaudeBot, anthropic-ai and other named AI bots in robots.txt.
3. **Basel-Landschaft:** use `bl-api.webcloud7.ch` (Plone REST) behind the www.baselland.ch Cloudflare wall.

## Agents and coverage
| Agent | Cantons | Cities |
|---|---|---|
| run3-a | ZH, BE, BS, BL, SO, AG | Zürich, Bern, Thun |
| run3-b | LU, UR, SZ, OW, NW, GL, ZG | – |
| run3-c | SG, TG, AR, AI, SH | Schaffhausen |
| run3-d | FR, VD, NE, GE, JU | Lausanne, Neuchâtel, La Chaux-de-Fonds, Genève, Vernier |
| run3-e | TI, GR, VS, plus court-data links (entscheidsuche, onlinekommentar, CLDS, opencaselaw Atom) | Lugano |

## `confirmed_links.csv` columns
| Column | Meaning |
|---|---|
| `urls` | Absolute URLs from the grid's URL column, plus backticked paths resolved against a host named in the same cell or the section's base |
| `urls_elsewhere_in_row` | Absolute URLs that appear only in the evidence, sample or notes columns |
| `urls_inferred_host` | **Inferred, not re-requested.** Relative paths resolved against the canton's C1 host, for rows with no explicit URL |
| `url_cell`, `evidence`, `sample`, `notes` | The agent's text, verbatim |

29 rows name pages only by abbreviated paths ("…/x"); read those in the agent report.

## Supporting material
| Path | Content |
|---|---|
| `stage0/` | Inputs prepared before the agents ran: `laws_XX.json` (all active cantonal law titles from LexWork/LexFind), `law_hits.json` (topic hits; known errors listed in consolidated §8), `sitemap_topic_candidates.json`, `sitemaps_summary.json`, `sitemap_fetch.py` |
| `stage0/precheck/` | Entry points verified per canton; the do-not-retry list; the probe results for the AI-suggested court, guidance and city links (`*_rows.py` + `*_probe.json`); opencaselaw coverage per court |
| `scripts/replay/` | The Stage 0 commands, replayed after the overnight crash (`run_all.sh`, `step_*.sh`, `run_all.log`). They regenerate everything in `stage0/`, including the full sitemaps |
| `scripts/recheck/` | The orchestrator's independent re-checks and audit scripts |
| `scripts/agents/run3-*/` | The agents' helper scripts (probe, Plone, eSHAB, i-web, LexWork, …) |
| `scripts/build_run3_commit.py`, `scripts/csv_postprocess.py` | How this folder, the CSV and the YAML files were built |
| `inputs_restored/` | Planning files from the overnight session, rebuilt from its transcript after the laptop shut down: coverage ledger, candidate links, the pasted AI-mode answers (inputs S1–S5), the awesome-ogd list, the source registry draft, verification results |
| `overnight_digests/` | What the five overnight agents did before they stalled at 05:39 (their logs, verbatim, results truncated) |

## Not included, and why
- **The full sitemaps** (`stage0/sitemaps/`, 50 MB, over 500,000 URLs): re-fetch them with `scripts/replay/step_30.sh`, which takes about 4 minutes.
- **The raw pages and PDFs each agent saved** (19–64 MB per agent): third-party copies that can be re-fetched. The reports quote every sample.

## Paths
Absolute paths in these files are replaced by placeholders:
- `<repo>` is the repository root.
- `<scratchpad>` is the session scratchpad the run used.
- `<scratchpad-overnight>` is the overnight session's scratchpad.

## Known corrections not yet applied to existing docs
Listed in `consolidated_report.md` §8:
- PR #40 `subnational_sources.md:310`: narrow the Lugano verdict to "Lugano OGD" and add Lugano's law collection.
- `ogd_lists_assessment.md` B.9: `tenants=` is ignored; `cantons=` includes SHAB notices; note the robots.txt rules.
- `law_hits.json` errors for SO, AG and SH, and missing laws for NE, GE, FR, BS, SO and GR.
