Gazette corrections are addressed with my own evidence:
- **Rubrics:** none of kabfr, kabvd, kabne, kabge or kabju has its own rubric. All 152 portal rubrics belong to other tenants; the SB, KK, AW and NA rubrics these tenants carry belong to `shab`. So the canton-own count is 0 in every case. I'll report all three numbers.
- **robots.txt:** amtsblattportal.ch is `Disallow: /`. fo.fr.ch blocks 23 named bots (including ClaudeBot, anthropic-ai, GPTBot and CCBot) but leaves `*` open. rsn.ne.ch and jurisprudence.vd.ch are `Disallow: /` for all agents.

Writing the final report.

# Run 3, group D: source grid for FR, VD, NE, GE and JU, plus city law for 5 cities

**Evidence.** Every status code, size, count and quote below comes from curl/python runs in this session (2026-09-23, about 12:20–14:15 CEST). Scripts and saved pages are in `<scratchpad>/run3-d/` (`probe.py`, `pages/`, `laws/`, `gazette3.out`).
- "(g5)" marks a source first verified in `reports/g5-guidance.md`. I re-fetched each one live.
- "inferred" marks a conclusion that no response shows directly.
- Paths inside a canton's grid are relative to that canton's base host.
- Commune counts were cross-checked against `<repo>/docs/sources/commune_sites.csv`: FR 119, VD 300, NE 24, GE 45, JU 51. Each matches the cantonal directory.

## Headlines
1. **NE has a sitemap.** The index at `https://www.ne.ch/sitemap.xml` (444 B) lists its two children on an internal host, `http://ne-prod-admin.ne.ch/sitemap.xml?page=N`, which does not resolve in DNS. The same paths on www answer 200:
   - `https://www.ne.ch/sitemap.xml?page=1` holds 5,000 URLs; `?page=2` holds 3,518. Total 8,518.
   - By section: communiqués 7,526, themes 684, autorites 266.
   - Rewriting the host filled every NE cell. This is why stage 0 parsed 0 URLs.
2. **None of the five gazettes lives on Amtsblattportal.**
   - Each tenant is flagged `external: true` and has 0 rubrics of its own. Everything it carries is in SHAB rubrics (SB, KK, AW, NA). amtsblattportal.ch robots.txt is `User-agent: * / Disallow: /`.
   - The real gazettes are:
     - fo.fr.ch: free HTML, but robots.txt blocks named AI bots.
     - faovd.ch: free HTML.
     - rsju.jura.ch: free weekly PDFs.
     - fao.ge.ch: behind a CAPTCHA.
     - NE Feuille officielle: paid subscription through the Guichet unique.
3. **Every court-fee ordinance is quoted with a CHF or point amount** from the official text: FR 130.11, VD 270.11.5, NE 164.1, GE E 1 05.10, JU 176.511 plus the JU Tribunal cantonal tariff.
4. **City law is reachable for all five cities:**
   - Lausanne: 193 texts.
   - Ville de Genève: 246 PDFs.
   - La Chaux-de-Fonds: 175 PDFs through a POST JSON API behind a JavaScript shell.
   - Neuchâtel: 79 current PDFs plus the former-commune lists.
   - Vernier: 52 regulation pages in the sitemap. Its Drupal pages returned 500 from 13:39 to 13:57 CEST; its static PDFs still loaded.
5. **Traps met:**
   - The jura.ch sitemap lacks the 2025 tax-guide page. I found it through WebSearch.
   - justice.ge.ch sitemap URLs contain `//`. Both forms answer 200.
   - WebSearch returned stale La Chaux-de-Fonds PDF URLs (500 and 404).
   - The NE Ville dog arrêté is a scanned PDF.

### Status matrix (V = VERIFIED)
| Cell | FR | VD | NE | GE | JU |
|---|---|---|---|---|---|
| C1 courts-home | V | V | V | V | V |
| C2 court-fees | V (resident page covers debt enforcement only; court amounts in ordinance) | V | V (page has no amounts; ordinance does) | V | V |
| C3 court-guidance | V | V | V | V | V |
| C4 decisions | V (opencaselaw latest date is in the future) | V (vd_findinfo STALE) | V | V | V |
| C5 conciliation | V | V | V | V | V |
| G1 dogs | V | V | V | V (g5, re-fetched) | V |
| G2 tax guide | V | V | V | V (g5, re-fetched) | V |
| G3 school holidays | V (ICS) | V | V | V (g5, ICS) | V |
| G4 road office | V | V | V | V | V |
| D1 communes | V (119, XLSX) | V (300) | V (24, with links) | V (45) | V (51, with links) |
| D2 chancellery + gazette | V (robots.txt blocks AI bots) | V | chancellery V, gazette BLOCKED (paywall) | chancellery V, gazette BLOCKED (CAPTCHA) | V |

---

## FR: Fribourg (base https://www.fr.ch)
| Cell | Status | URL | Evidence (HTTP · title · format · size) | Sample | Notes / legal basis |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/etat-et-droit/justice`; `/pj/tc` | 200 · "Justice \| Etat de Fribourg" · server HTML (Drupal + Site Studio) · 98,565 B, 78 links, 773 words. TC: 200 "Tribunal cantonal (TC) \| Etat de Fribourg", 91,310 B | "Il existe trois types de juridictions ou d'organes du Pouvoir judiciaire : les juridictions civiles (s'occupent de conflits entre particuliers), pénales…" | |
| C2 | VERIFIED | Resident page `/etat-et-droit/justice/tarifs`. Ordinance RSF 130.11 Règlement sur la justice (RJ): `https://bdlf.fr.ch/app/fr/texts_of_law/130.11` | tarifs: 200 "Tarifs \| Etat de Fribourg", HTML, 442 words. RJ via LexWork API: 200 JSON, 1,433,906 B, version in force since 01.12.2025 | tarifs: "Créance en CHF Montant de l'avance de frais en CHF jusqu'à 100.00 21.00 … Valable dès le 1er janvier 2024." RJ: "émolument de conciliation de 50 à 10'000 francs." | /tarifs is the debt-enforcement advance table published by the Offices des poursuites, not court fees. A sitemap grep for frais/coût/émolument/assistance-judiciaire (22 hits) found no court-cost page for residents. Also 130.16 (Tribunal cantonal tariff, in force 01.02.2016). The law_hits court_fees entries (76.16, 710.16, 150.12) are special tariffs. |
| C3 | VERIFIED | Fetched (all 200, server HTML): `…/justice/pouvoir-judiciaire-justices-de-paix` (1,126 words), `…/pouvoir-judiciaire-commissions-de-conciliation-en-matiere-de-bail-et-tribunal-des-baux` (1,075), `…/pouvoir-judiciaire-tribunal-des-prudhommes` (720), `…/mediation-judiciaire` (1,464), `…/competences-territoriales` (1,087), `…/indications-complementaires` (1,865), `…/tarifs` (442). In the sitemap only, not fetched: `…/faq-mp`, `/etat-et-droit/poursuites-et-faillites/procedure-de-poursuite/requisition-de-poursuite`, `…/pouvoir-judiciaire-tribunaux-darrondissement` | Sitemap counts: 138 French URLs under /etat-et-droit/justice. Of these, 40 are archive or admin pages (e.g. `arrets-de-la-section-*-20xx`), leaving 98 guidance-type pages. Also 67 under /poursuites-et-faillites (36 procedure pages) and 141 German mirror pages | "La justice de paix est en premier lieu l'autorité de protection de l'enfant et de l'adulte." | The justices de paix page also links PDFs: "Informations sur la succession" and "Entretien de l'enfant, guide pour les parents". |
| C4 | VERIFIED | `/pj/tc/jurisprudence-du-tribunal-cantonal`; search app `https://publicationtc.fr.ch/?locale=fr` | TC page: 200, HTML, 105,190 B, 99 links. It lists the latest rulings with direct PDF links (`publicationtc.fr.ch/tribunavtplus/ServletDownload/<dossier>_<hash>.pdf?path=…`). Search app: 200, 19,593 B, 0 links, so a JavaScript app (Tribuna VTPlus, per the path) | "102 2026 206 22.09.2026 09h00 Arrêt de la IIe Cour d'appel civil du Tribunal cantonal - Annulation de la faillite (art. 174 LP)." | opencaselaw `fr_gerichte` 14,768 decisions, 2002-07-31 → **2027-07-27**. The future latest date is a data anomaly; the court is not stale. `fr_anwaltsaufsicht` has 3 decisions, sparse, no dates. Atom feed `https://mcp.opencaselaw.ch/api/atom/fr_gerichte.xml` not checked. |
| C5 | VERIFIED | Tenancy conciliation page (C3 list) plus the justices de paix page | 200 · "Pouvoir judiciaire - Commissions de conciliation en matière de bail et tribunal des baux" · 1,075 words | "Des frais judiciaires ne sont pas perçus dans les litiges portant sur des baux à loyer d'habitations lorsque l'objet du bail constitue le logement principal du locataire et qu'il n'est pas luxueux." | "il existe trois commissions de conciliation". Guidance and fee information both present. Law: 222.3.1 (bail), 862.2 (collective labour conciliation). |
| G1 | VERIFIED | `/vie-quotidienne/animaux-de-compagnie/chiens`; `…/chiens/impot-sur-les-chiens` | 200 "Chiens \| Etat de Fribourg", HTML, 156,573 B, 701 words. Tax page: 200, 510 words | "…soumis à un impôt cantonal d'un montant de CHF 100.- par chien, auquel est ajouté un montant de CHF 5.- comprenant un émolument administratif et la contribution à l'assurance responsabilité civile collective." | Law 725.3 LDCh (current version since 01.01.2024) and 725.31 RDCh (since 01.01.2024), both on bdlf LexWork. |
| G2 | VERIFIED | `/document/57721` → `/sites/default/files/2026-05/instructions-generales-concernant-la-declaration-d-impot_0.pdf` | 200 application/pdf, 324,278 B, 50 pages, text layer of 122,632 chars | "Le montant minimal est de Fr. 100.- par année fiscale et le montant maximal est li- mité à 20% du revenu net (code 4.910)." | Linked from `/impots/personnes-physiques/impot-des-personnes-physiques-themes-particuliers` (200). Enumerable: the sitemap lists 79 French and 79 German /impots pages. PDFs are `/document/<id>`, which redirect to a dated file with `?v=`. Law 631.1 LICD. |
| G3 | VERIFIED | `/dfac/vacances-scolaires`; ICS `/document/508696` | Page: 200, 134,543 B, 2,476 words, HTML tables. ICS: 200 text/calendar, 437,002 B, 11 VEVENTs | "Vacances d'automne 12 octobre 2026 23 octobre 2026 (inclus)". ICS: `DTSTART;VALUE=DATE:20261012` / `SUMMARY;LANGUAGE=fr-ch:Vacances d'automne` | **Who sets them:** the DFAC sets 3 reference calendars (majoritaire, Morat/Murten, Kerzers). "Chaque cercle scolaire a la possibilité de donner 1 jour (ou 2 pour la région de Murten/Morat) de congé supplémentaire." One ICS per calendar and school year up to 2029/30 (e.g. /document/508646, /513541). The PDF (54,686 B) has a garbled text layer, so use the ICS. |
| G4 | VERIFIED | `https://www.ocn.ch/fr`; `/fr/conduire/vehicules/immatriculation`; `/fr/conduire/apprendre-conduire/apprendre-conduire-une-voiture/que-coute-le-permis-de-conduire`; `/fr/conduire/expertise-des-vehicules/duree-et-tarif-des-expertises-de-vehicules` | All 200, HTML (Drupal), 129–138 KB, about 370 links, 1,847–2,249 words | "Le permis de conduire une voiture (catégorie B) coûte Fr. 190.-." Expertise tariff: "Voiture de tourisme (véhicule jusqu'à 15 ans) Jusqu'à 3.5 t 15 50" (minutes, Fr.) | ocn.ch sitemap: 856 URLs (428 fr, 428 de), including 19 French fee pages. Law 781.16 (road-traffic fees, version since 01.09.2025). |
| D1 | VERIFIED | `/etat-et-droit/communes/reglements-annuaire-et-infoscom-pour-les-collectivites-publiques/listes-des-collectivites-publiques-locales` → XLSX `/document/580206` | Page: 200, 710 words. XLSX: 200, 87,961 B, sheet "CO-GEM 2026" with **119 commune rows** (No OFS, Commune), grouped by district | "2008 \| Châtillon (FR)" | No website links in the file (0 cells with http or www). Yearly XLSX files for 2021–2026. Law 112.51 ONCD (version since 01.01.2026). |
| D2 | VERIFIED; **robots.txt blocks named AI bots** | `/cha`; gazette `https://fo.fr.ch` | CHA: 200 "Chancellerie de l'Etat de Fribourg (CHA)", 1,023 words. FO: 200 "Articles \| Feuille officielle du canton de Fribourg". Issue page `/archive/2026/38/18`: 200, 50,523 B, 1,606 words | "Les membres du Conseil général de la commune de Châtel-Saint-Denis sont convoqués en séance ordinaire le mercredi 30 septembre 2026, à 19 h 30…" | Weekly, free, HTML per issue and rubric (`/archive/<year>/<no>/<rubric>`). fo.fr.ch robots.txt: `User-agent: *` allowed, apart from Drupal paths; `Disallow: /` for 23 named bots including ClaudeBot, anthropic-ai, Claude-Web, GPTBot, CCBot, Google-Extended and PerplexityBot. Amtsblattportal: cantons=FR 81,133; tenant=kabfr 6,862 of 6,863 in SHAB rubrics; own rubrics 0. Law 124.21. |

**Site recipe.**
- **www.fr.ch:** Drupal with Acquia Site Studio. Sitemap `/sitemap.xml`, an index, 67,964 URLs. robots.txt 200 with 29 Disallow rules, no crawl-delay, no bot walls. Content is French with a German mirror under `/de/…`.
- **www.ocn.ch:** Drupal, `/sitemap.xml` with 856 URLs.
- **fo.fr.ch:** Drupal; AI bots blocked by name (see D2).
- **Laws:** bdlf.fr.ch (LexWork). **Decisions:** publicationtc.fr.ch (JavaScript app).

**Draft YAMLs** (authority official_info, default_extent_id CH-FR):
```yaml
- id: fr-justice            # C1/C3/C5 — category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.fr.ch/etat-et-droit/justice], path_allowlist: [/etat-et-droit/justice/, /etat-et-droit/poursuites-et-faillites/procedure-de-], language: fr}
  # needs a denylist (or sitemap seeding) to skip 40 /etat-et-droit/justice/arrets-de-la-section-* archive pages
- id: fr-dogs               # category dogs
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens], path_allowlist: [/vie-quotidienne/animaux-de-compagnie/chiens], language: fr}
- id: fr-tax-instructions   # category taxes
  fetch_strategy: pdf
  fetch_config: {urls: [https://www.fr.ch/document/57721], language: fr}
- id: fr-school-holidays    # category schools; ICS part -> fetcher:ics (/document/508696, 508646, 513541, …)
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.fr.ch/dfac/vacances-scolaires], path_allowlist: [/dfac/vacances-scolaires], language: fr}
- id: fr-ocn                # category transport
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.ocn.ch/fr/conduire], path_allowlist: [/fr/conduire/, /fr/changements-de/], language: fr}
```

**Landing-contract fields.**
- **HTML sources:** url is the page; title is the page `<title>` minus " | Etat de Fribourg"; sections come from h2/h3; published_at is the footer "Dernière modification : …" (seen on /tarifs).
- **ICS:** identifier is DTSTART+SUMMARY; event_date is DTSTART; DTEND is exclusive.

**Claim checks.**

| AI link | Result | Correct URL |
|---|---|---|
| fr.ch/pouvoir-judiciaire/{tribunal-cantonal, frais-et-emoluments, themes, jurisprudence, tribunaux-darrondissement} | Wrong: all 404 | /pj/tc; /etat-et-droit/justice/tarifs plus RJ 130.11; /etat-et-droit/justice; /pj/tc/jurisprudence-du-tribunal-cantonal |
| Dogs: /sanu/animaux/chiens/detention-de-chiens | Wrong: 404 | /vie-quotidienne/animaux-de-compagnie/chiens |
| Tax: /scc/impots/personnes-physiques/guide-pour-la-declaration-dimpot | Wrong: 404 | /document/57721 |
| School holidays | Partly: redirects | /dfac/vacances-scolaires |
| Road office: ocn.ch | Confirmed | ocn.ch/fr |
| Communes: /etat-et-droit/communes | Partly: landing page only | The list is XLSX /document/580206 |
| Chancellery: /ce/chancellerie-detat-cha | Wrong: 404 | /cha |

---

## VD: Vaud (base https://www.vd.ch)
| Cell | Status | URL | Evidence | Sample | Notes / legal basis |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/ojv`; `/ojv/tribunal-cantonal` | 200 "Ordre judiciaire vaudois (OJV) \| État de Vaud", HTML (TYPO3), 40,667 B, 114 links, 1,113 words. TC: 200, 33,012 B, 842 words | "Le Tribunal cantonal est l'autorité judiciaire supérieure du canton." | |
| C2 | VERIFIED | `/justice/la-justice-civile/combien-coute-une-procedure-civile`. Ordinance BLV 270.11.5 TFJC: `https://prestations.vd.ch/pub/blv-publication/actes/consolide/270.11.5?id=5848c893-424d-4a98-8f8d-a613dcd497b9` | Page: 200, 28,806 B, 829 words. BLV API `api/actes/CONSOLIDE?id=…&cote=270.11.5`: 200 JSON, 5,301 B (in force since 01.01.2011, current version 01.01.2025, EN_VIGUEUR). Text via `api/actes/ffd39db6-…/html`: 200 xhtml, 415,687 B | Page: "des frais judiciaires sont perçus par les autorités judiciaires. Les frais judiciaires comprennent essentiellement l'émolument forfaitaire…". TFJC: "L'émolument forfaitaire de conciliation est fixé en principe comme il suit : … de 0 à 2'000 francs : 150 francs - de 2'001 à 5'000 francs : 210 francs" | In the sitemap: `/justice/la-justice-administrative/combien-coute-une-procedure-administrative` and `/justice/la-justice-penale/qui-paie-les-frais-engendres-par-une-procedure-penale`. |
| C3 | VERIFIED | Fetched (200): `/justice/la-justice-civile` (606 words), `/justice/la-justice-civile/conciliation-en-matiere-civile` (906), `/justice/la-justice-civile/combien-coute-une-procedure-civile` (829), `/justice/conseils-et-assistance` (583). Sitemap only: `/justice/la-justice-civile/successions`, `…/conflits-du-travail`, `…/consensus-parental`, `/justice/conseils-et-assistance/mediation`, `/justice/curatelles-et-tutelles`, `/justice/la-justice-penale/qui-paie-les-frais-engendres-par-une-procedure-penale` | Sitemap counts: **82** URLs under /justice/ and **73** under /ojv/ | "…une procédure de conciliation doit précéder tout litige judiciaire civil, quel que soit la valeur litigieuse." | |
| C4 | VERIFIED | `/justice/jurisprudence-et-lois/jurisprudence-du-tribunal-cantonal-et-du-tripac` → `https://jurisprudence.vd.ch/scripts/nph-omniscgi.exe?…Schema=VD_TA_WEB…` | Page: 200, 736 words. Search: 200 "Jurisprudence: Recherche simple", 20,833 B, iso-8859-1 Omnis FindInfo form, 6 links | "INFORMATION CONCERNANT LA JURISPRUDENCE DE LA COUR DE DROIT ADMINISTRATIF ET PUBLIC ET DE LA COUR CONSTITUTIONNELLE" | opencaselaw: `vd_findinfo` 74,714 (latest 2025-12-20, **STALE**); `vd_gerichte` 68,645 (latest 2026-09-03); `vd_omni` 28,033 (latest 2026-02-09). jurisprudence.vd.ch robots.txt: `Disallow: /` for all agents. |
| C5 | VERIFIED | `/ojv/justices-de-paix`; conciliation page (C3); `/etat-droit-finances/districts-/-prefectures/prefectures/prestations-des-prefectures/commissions-prefectorales-de-conciliation/bail-a-loyer-ou-a-ferme-non-agricole` | 200 (1,364 words); 200 (906); 200 (978) | Conciliation "…menée par le juge matériellement compétent pour le procès au fond, sauf pour un conflit dans le domaine du droit du bail où l'autorité de conciliation est la Commission de conciliation en matière de baux à loyer". Préfecture: "rendre une décicion dans les litiges dont la valeur patrimoniale est inférieure à Fr. 2'000.-" | Tenancy conciliation is handled by the préfecture commissions. No fee text on the conciliation page; the TFJC sets fees. Laws 173.655 LJB and 173.655.310821.1 (temporary free proceedings at the Tribunal des baux). |
| G1 | VERIFIED | `/population/veterinaires-et-animaux/police-des-chiens` | 200 "Police des chiens \| État de Vaud", 34,207 B, 972 words | "Les cours obligatoires pour détenteurs de chiens ont été supprimés depuis le 1er janvier 2017." | Laws BLV 133.75 LPolC, 133.75.1 RLPolC, 652.31.1 (cantonal dog tax). |
| G2 | VERIFIED | `/fileadmin/user_upload/organisation/dfin/aci/fichiers_pdf/21001_2025.pdf` (listed on `/etat-droit-finances/impots/formulaires-directives-et-baremes`) | PDF: 200, 4,121,012 B, 68 pages, 229,072 chars. List page: 200, 359 links, 5,333 words | "DÉDUCTION POUR FRAIS DE GARDE CODE 670 La déduction s'élève à CHF 25 800 francs au maximum par enfant." | Enumerable by filename pattern `21001_<year>.pdf` (2024 and 2025 seen), with complementary 21003/21004/21007. 119 /etat-droit-finances/impots/ URLs in the sitemap. Law 642.11. |
| G3 | VERIFIED | `/formation/jours-feries-et-vacances-scolaires`; `…/jours-feries-et-vacances-scolaires-2026` | 200 (683 words); 200 (914 words) | "Le Département de l'enseignement et de la formation professionnelle (DEF) a la compétence de fixer les dates des vacances scolaires." / "Vacances d'automne : du sa. 10 octobre au di. 25 octobre 2026" | **The canton (DEF) sets them.** Year pages exist for 2026–2031, plus a PDF "jusqu'en 2031". No ICS found. |
| G4 | VERIFIED | `/mobilite/automobile-et-navigation`; `…/frais-des-prestations-du-san/permis-de-conduire` | 200 (57,409 B, 1,511 words); 200 (641 words) | "Etablissement d'un permis d'élève ou d'un duplicata 30.-" | 8 fee sub-pages in the sitemap. Law 741.15.1 (SAN fees). |
| D1 | VERIFIED | `/etat-droit-finances/communes/liste-des-communes-et-districts` | 200 "Communes vaudoises et districts", 57,548 B. HTML table with **300 rows** (Commune, District, No OFS), plus an XLS file | "Aclens \| Morges \| 5621" | No website links: the 20 links in the table are A–Z anchors (inferred from the header row). Law 132.15. |
| D2 | VERIFIED | `/cha`; gazette `https://www.faovd.ch` | CHA: 200, 882 words. faovd.ch: 200 "Feuille des Avis Officiels du canton de Vaud", 41,441 B. `/rubrique/communes/`: 200, 1,048,547 B, 31,108 words | "18.09.2026 / FAO N° 75"; "EYSINS 18.09.2026 / FAO n° 75" | Published Tuesdays and Fridays, free HTML. faovd.ch has no robots.txt (404). Amtsblattportal: cantons=VD 234,066; tenant=kabvd 21,235, of which 21,227 in SHAB rubrics; own rubrics 0. Law 170.551. |

**Site recipe.**
- **www.vd.ch:** TYPO3. robots.txt names the sitemap `https://www.vd.ch/sitemap?type=1533906435` (index of 51 files, 27,472 URLs); 18 Disallow rules, no crawl-delay. The old `/themes/` prefix is gone, which is why the AI links fail.
- **Laws:** prestations.vd.ch BLV API. Its robots.txt answers 403.
- **Decisions:** jurisprudence.vd.ch (Omnis FindInfo; `Disallow: /`).

**Draft YAMLs** (official_info, CH-VD):
```yaml
- id: vd-justice   # category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.vd.ch/justice, https://www.vd.ch/ojv/justices-de-paix], path_allowlist: [/justice/, /ojv/justices-de-paix, /ojv/tribunal-des-baux], language: fr}
- id: vd-dogs      # dogs
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.vd.ch/population/veterinaires-et-animaux/police-des-chiens], path_allowlist: [/population/veterinaires-et-animaux/police-des-chiens], language: fr}
- id: vd-tax-instructions   # taxes
  fetch_strategy: pdf
  fetch_config: {urls: [https://www.vd.ch/fileadmin/user_upload/organisation/dfin/aci/fichiers_pdf/21001_2025.pdf], language: fr}
- id: vd-school-holidays    # schools
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.vd.ch/formation/jours-feries-et-vacances-scolaires], path_allowlist: [/formation/jours-feries-et-vacances-scolaires], language: fr}
- id: vd-san                # transport
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.vd.ch/mobilite/automobile-et-navigation], path_allowlist: [/mobilite/automobile-et-navigation/], language: fr}
```

**Claim checks.**

| AI link | Result | Correct URL |
|---|---|---|
| `/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/tribunal-cantonal` | Confirmed (redirects) | /ojv/tribunal-cantonal |
| `…/tribunaux-darrondissement` | Confirmed (redirects) | /ojv/tribunaux-darrondissement |
| `…/frais-et-emoluments` | Wrong: 404 | /justice/la-justice-civile/combien-coute-une-procedure-civile plus TFJC |
| `…/themes` | Wrong: 404 | /justice |
| `…/jurisprudence` | Wrong: 404 | /justice/jurisprudence-et-lois/jurisprudence-du-tribunal-cantonal-et-du-tripac |
| `…/cour-de-droit-administratif-et-public` | Wrong: 404 | Correct page not checked |
| Dogs: `/themes/environnement/animaux/chiens` | Wrong: 404 | /population/veterinaires-et-animaux/police-des-chiens |
| Tax: `…/instructions-g-et-annexes` | Wrong: 404 | 21001_2025.pdf |
| School holidays: `/themes/formation/…` | Wrong: 404 | /formation/jours-feries-et-vacances-scolaires |
| Road office: `/themes/mobilite/automobile` | Partly: redirects | /mobilite/automobile-et-navigation |
| Communes: `/toutes-les-communes` | Wrong: 404 | /etat-droit-finances/communes/liste-des-communes-et-districts |
| Chancellery: `/etat-de-vaud/chancellerie-detat` | Wrong: 404 | /cha |

---

## NE: Neuchâtel (base https://www.ne.ch)
| Cell | Status | URL | Evidence | Sample | Notes / legal basis |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/autorites/autorites-judiciaires` | 200 "Autorités judiciaires \| ne.ch", HTML (Drupal), 512,082 B. About 500 of the links are the mega-menu | Tribunal d'instance page: "Le Tribunal d'instance est l'autorité judiciaire cantonale de première instance. Il est réparti en deux juridictions" | The AI's `/autorites/PJ/*` paths are all 404. |
| C2 | VERIFIED | `/themes/etat-droit-et-finances/droits-et-justice/frais-de-justice`. Ordinance RSN 164.1: `https://rsn.ne.ch/DATA/program/books/rsne/pdf/164.1.pdf` | Page: 200 "Frais de justice \| ne.ch", `<main>` holds 11,446 chars. 164.1: 200 PDF, 296,961 B, 13 pages, text layer | Page: "…facturation et recouvrement des jugements et décisions des tribunaux du canton". LTFrais: "L'émolument forfaitaire de conciliation est fixé selon le tarif suivant : … jusqu'à 2'000.- 300.-" | 164.1 is not in law_hits; I found it in laws_NE.json. The page describes billing and recovery; it states no amounts. |
| C3 | VERIFIED | Fetched (200): `…/droits-et-justice/assistance-judiciaire`, `…/droit-du-bail`, `…/frais-de-justice`, `…/legislation-et-jurisprudence/jurisprudence`, `/autorites/autorites-judiciaires/tribunal-dinstance` (3,808 words). Sitemap only: `…/mediation-en-cas-de-conflits`, `…/amendes-dordre`, `…/avocat-e-s`, `…/notaires`, `/autorites/autorites-judiciaires/tribunal-dinstance/apea` | Recovered sitemap: 23 URLs under droits-et-justice and 14 under autorites-judiciaires | "Avant d'engager une action civile devant un tribunal, vous devez, sauf exception, passer par une procédure de conciliation." | Pages are 490–600 KB; the text is inside `<main>`. |
| C4 | VERIFIED | `…/legislation-et-jurisprudence/jurisprudence` → `http://jurisprudence.ne.ch/` → `…/scripts/omnisapi.dll?…Schema=NE_WEB…`; also `http://jurisprudenceadm.ne.ch/` | The jurisprudence.ne.ch root is a 2,173 B JavaScript redirect. The Omnis home: 200 "Jurisprudence du Tribunal cantonal", 20,248 B, 20 links, iso-8859-1 | "Cette base de données juridiques contient les principaux arrêts, pour la plupart non publiés, rendus par les différentes cours du [Tribunal cantonal]" plus a "Derniers arrêts publiés" list | opencaselaw: `ne_gerichte` 10,817 (latest 2026-08-20); `ne_jurisprudence_adm` 1,648 (latest 2026-02-05). Not stale. |
| C5 | VERIFIED | `/autorites/autorites-judiciaires/tribunal-dinstance` ("Chambre de conciliation" section); `…/droits-et-justice/droit-du-bail` | 200, 551,660 B; 200 | "Toute contestation doit être adressée aux chambres de conciliation des tribunaux régionaux selon la situation de l'immeuble." | No fee text on the Tribunal d'instance page (grep for gratuit/frais/émolument/avance: 0 hits); LTFrais art. 11 sets the fees. Collective labour: `/page/office-cantonal-de-conciliation-en-matiere-de-conflits-collectifs-de-travail` (sitemap), law 810.40. |
| G1 | VERIFIED | `/themes/vie-quotidienne-et-famille/animaux/soccuper-danimaux`; `/autorites/ddte/scav` | 200, 589,236 B, `<main>` 102 KB, 5,572 words; SCAV page 200 | "Toute nouvelle ou tout nouveau propriétaire d'un chien depuis le 1er janvier 2021 domicilié dans le canton…" (mandatory course; "estimation entre 300 et 400 francs") | Law RSN 636.20 LChiens (PDF: "Art. 12 1Il est interdit de laisser errer un chien."), 636.201, 636.21. The dog tax is communal ("facture communale de la taxe des chiens"). Only 1 sitemap URL contains "chien", so a topic grep alone misses this page. |
| G2 | VERIFIED | `/sites/default/files/2025-10/SCCO_I754_InstructionsGenerales_PP.pdf` (from `/themes/impots/documents-et-liens-utiles`) | PDF: 200, 2,717,944 B, 57 pages, text layer | "Montant à reporter sous chiffre 6.12, mais au maximum Fr. 5000.–" | 36 /themes/impots/ URLs; the documents page lists instructions and notices 1–5 as `SCCO_*.pdf`. Law 631.0 LCdir (from laws_NE.json). |
| G3 | VERIFIED | `/themes/scolarite-et-formation/calendrier-et-vacances-scolaires` | 200, `<main>` 15 KB. Links `/sites/default/files/2025-08/CalendrierScolaire2019-2030.pdf` (not fetched) | "Vacances d'automne Du lundi 5 octobre au vendredi 16 octobre 2026" | **One cantonal calendar**, "valable pour l'enseignement obligatoire". The page does not name the deciding body. |
| G4 | VERIFIED | `https://www.scan-ne.ch/`; `/conducteur/permis/obtenir-un-permis/voiture-18-ans/`; `/vehicule/taxe/calculer-votre-taxe-automobile-et-remorque/`. Fees: RSN 761.43 PDF | SCAN: 200, TYPO3, 105,019 B, 310 links. Sub-pages 200 (90 KB, 106 KB). 761.43: 200 PDF, 12 pages, text layer | "En 2026, les voitures de tourisme neuchâteloises seront toujours taxées selon leurs émissions de CO₂ et leur âge". 761.43: "Plaques de contrôle, en prêt, la paire … 50" | SCAN pages carry no CHF amounts (0 hits); fees live only in 761.43. No sitemap (404); robots.txt 200 but empty. |
| D1 | VERIFIED | `/communes-neuchateloises` | 200, `<main>` 5,968 chars: **24 communes** by region, each linked to its website | "Région Littoral Boudry …" → `http://www.boudry.ch/` | 24 matches commune_sites.csv. |
| D2 | chancellery VERIFIED; gazette **BLOCKED (paywall)** | `/autorites/chan`; gazette info `/themes/etat-droit-et-finances/publications/feuille-officielle` | 200 "Chancellerie d'État \| ne.ch"; 200 | "Abonnez-vous via le Guichet unique pour 53 francs par an, ou achetez un numéro individuel pour 4 francs." | The online Feuille officielle requires a Guichet unique subscription (guichetunique.ch has no robots.txt). Amtsblattportal: cantons=NE 47,486; tenant=kabne 387, all in SHAB rubrics; own rubrics 0. Law 150.20. |

**Site recipe.**
- **www.ne.ch:** Drupal. robots.txt names `/sitemap.xml` (34 Disallow rules, no crawl-delay, no `Disallow: /`).
  - **Sitemap fix:** fetch `https://www.ne.ch/sitemap.xml?page=1` and `?page=2`, then rewrite `http://ne-prod-admin.ne.ch` to `https://www.ne.ch`.
  - Every NE page used above was taken from the rewritten list and answered 200.
  - Parse only `<main>`: the pages are 490–600 KB because of the menu.
- **www.scan-ne.ch:** TYPO3, no sitemap.
- **Laws:** rsn.ne.ch. **Its robots.txt is `User-agent: * / Disallow: /`,** which is a policy flag for `fetcher:ne-rsn`.

**Draft YAMLs** (official_info, CH-NE):
```yaml
- id: ne-justice      # category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.ne.ch/themes/etat-droit-et-finances/droits-et-justice, https://www.ne.ch/autorites/autorites-judiciaires], path_allowlist: [/themes/etat-droit-et-finances/droits-et-justice/, /autorites/autorites-judiciaires], language: fr}
  # skip …/legislation-et-jurisprudence/*-annee-20xx lists; extract <main>
- id: ne-dogs         # dogs
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.ne.ch/themes/vie-quotidienne-et-famille/animaux/soccuper-danimaux], path_allowlist: [/themes/vie-quotidienne-et-famille/animaux/], language: fr}
- id: ne-tax-instructions   # taxes
  fetch_strategy: pdf
  fetch_config: {urls: [https://www.ne.ch/sites/default/files/2025-10/SCCO_I754_InstructionsGenerales_PP.pdf], language: fr}
- id: ne-school-calendar    # schools
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.ne.ch/themes/scolarite-et-formation/calendrier-et-vacances-scolaires], path_allowlist: [/themes/scolarite-et-formation/calendrier-et-vacances-scolaires], language: fr}
- id: ne-scan         # transport
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.scan-ne.ch/], path_allowlist: [/conducteur/, /vehicule/], language: fr}
```

**Claim checks.**

| AI link | Result | Correct URL |
|---|---|---|
| `/autorites/PJ/{TC, frais, themes, jurisprudence, TR}` | Wrong: all 404 | /autorites/autorites-judiciaires, …/frais-de-justice, …/jurisprudence (→ jurisprudence.ne.ch), …/tribunal-dinstance |
| Dogs: `…/SCAV/sante-animale/Pages/Chiens.aspx` | Wrong: 404 | /themes/vie-quotidienne-et-famille/animaux/soccuper-danimaux |
| Tax: `…/SCCO/personnes-physiques/Pages/accueil.aspx` | Wrong: 404 | /themes/impots/impot-des-personnes-physiques plus the SCCO_I754 PDF |
| School holidays: `…/SECO/Pages/vacances-scolaires.aspx` | Wrong: 404 | /themes/scolarite-et-formation/calendrier-et-vacances-scolaires |
| Road office: scan-ne.ch | Confirmed | scan-ne.ch |
| Communes: `…/SCOM/Pages/accueil.aspx` | Wrong: 404 | /communes-neuchateloises |
| Chancellery: `/autorites/CE/CH/Pages/accueil.aspx` | Partly: redirects to the Conseil d'État page, not the chancellery | /autorites/chan |

---

## GE: Geneva (base https://www.ge.ch; courts on https://justice.ge.ch)
| Cell | Status | URL | Evidence | Sample | Notes / legal basis |
|---|---|---|---|---|---|
| C1 | VERIFIED | `https://justice.ge.ch/fr` | 200 "Page d'accueil \| Pouvoir judiciaire", HTML (Drupal), 115,403 B, 192 links | Menu: "Tribunal civil Tribunal de première instance Tribunal des baux et loyers Commission de conciliation en matière de baux et loyers…" | justice.ge.ch sitemap: 953 URLs, written as `https://justice.ge.ch//fr/…`. Both forms answer 200 (tested on the fees page). |
| C2 | VERIFIED | `https://justice.ge.ch/fr/contenu/frais-dune-procedure-civile`. Ordinance RSG E 1 05.10 RTFMC: `https://silgeneve.ch/legis/program/books/RSG/pdf/rsg_e1_05p10.pdf` | Page: 200, 105,901 B, 1,626 words. RTFMC: 200 PDF, 541,122 B, 10 pages, text layer | "Ces émoluments font donc en principe l'objet d'une avance de frais, exigée en début de procédure." RTFMC art. 15: "L'émolument forfaitaire de conciliation … jusqu'à 30 000 francs 100 francs" | law_hits gave only E 5 10.03 and E 6 15.06; I found E 1 05.10 in laws_GE.json. |
| C3 | VERIFIED | 14 theme pages `/fr/theme/{adoption, faillite, mainlevees, successions, assistance-juridique, separation-et-divorce, protection-de-ladulte, protection-de-lenfant, information-aux-temoins, consignation-des-loyers, information-aux-victimes, deroulement-dune-mediation, conflit-en-droit-du-travail, curatrices-curateurs-…}` | Sitemap: 14 French theme pages plus 137 /fr/contenu/ pages. separation-et-divorce: 200, 205,917 B, 6,115 words (the only theme page fetched) | "En cas de séparation conflictuelle, vous pouvez saisir de manière unilatérale le tribunal afin de demander des mesures protectrices de l'union conjugale." | |
| C4 | VERIFIED | `/fr/contenu/jurisprudence` → `https://justice.ge.ch/apps/decis/fr/capj/search` (also `/apps/decis/fr/jtp/search`) | 200 (817 words); search: 200 "Décisions \| Cour d'appel du Pouvoir judiciaire", 100,069 B, server HTML form | Page title "Décisions \| Cour d'appel du Pouvoir judiciaire" | opencaselaw: `ge_gerichte` 170,523 (latest 2026-09-14); `sav_kantone` 2 (sparse). Not stale. |
| C5 | VERIFIED | `/fr/contenu/commission-de-conciliation-en-matiere-de-baux-et-loyers` | 200, 154,009 B, 2,742 words | "La procédure devant la Commission de conciliation en matière de baux et loyers est gratuite." | Law E 3 15. Prud'hommes page `/fr/contenu/tribunal-des-prudhommes` is in the sitemap. |
| G1 | VERIFIED (g5 D17, re-fetched) | `/detenir-chien/regles-promener-son-chien` | 200 "Règles pour promener son chien \| ge.ch", 598 words | "Toujours en laisse : Dans les localités et sur les voies de circulation…" | 19 dog URLs under /detenir-chien, /impot-chiens and /agressions-canines. Law M 3 45 and M 3 45.01. |
| G2 | VERIFIED (g5 U10, re-fetched) | `https://www.getax.ch/support/guide/declaration2025/` | 200 "Table des matières", 58,854 B, 351 links | "Guide de la déclaration d'impôts des personnes physiques 2025 Télécharger le guide au format PDF" | 98 chapter pages (g5 figure, not re-counted). getax.ch robots.txt: **Crawl-delay 10**. Law D 3 08 LIPP. |
| G3 | VERIFIED (g5 D19, re-fetched) | `/vacances-scolaires-jours-feries`; ICS `/document/39777/telecharger` | 200 (405 words); ICS: 200 text/calendar, 391,179 B, 10 VEVENTs | "Le Conseil d'Etat fixe le calendrier des vacances scolaires des élèves des écoles primaires et secondaires." ICS: `DTSTART;VALUE=DATE:20270826` "Rentrée scolaire" | **The canton sets them.** The sitemap lists `ics-vacances-*` documents up to 2031. |
| G4 | VERIFIED (fetched now; g5 had inferred it) | `/organisation/office-cantonal-vehicules-ocv`; `/immatriculer-vehicule-obtenir-carte-grise`; fee extract `/document/24460/telecharger` | 200 (333 words); 200 (728 words); PDF 200, 701,323 B, 2 pages, text layer | "a) véhicules automobiles légers 80 francs b) remorques légères 80 francs c) véhicules automobiles lourds 240 francs" | Law H 1 05.08. |
| D1 | VERIFIED | `https://statistique.ge.ch/communes/welcome.asp` (found via WebSearch `site:ge.ch`) | 200, 184,270 B. **45** commune ids (`apercu.asp?commune=1…45`) | "liste des communes Aire-la-Ville Anières Avully Avusy Bardonnex …" | The ids are the canton's own 1–45, not BFS numbers, and there are no links to commune websites. `/dossier/communes-genevoises` re-checked: still 403 → /taxonomy/term/3084. Alternative: `/document/27069/telecharger`, the land-registry numbering (1 page; Genève split into 4 sections). |
| D2 | chancellery VERIFIED; gazette **BLOCKED (CAPTCHA)** | `/organisation/chancellerie-etat`; gazette `https://fao.ge.ch` | 200 "Chancellerie d' Etat \| ge.ch", 1,084 words. fao.ge.ch lands on `/captcha?baseURL=/` (8,619 B, "VERIFICATION PAR CAPTCHA") | "La chancellerie d'Etat assume les fonctions d'état-major du gouvernement cantonal." ge.ch/feuille-avis-officielle-fao: "(FAO) est disponible gratuitement en ligne. Depuis le 1er janvier 2017, elle est entièrement numérique." | fao.ge.ch has no robots.txt (404). Amtsblattportal: cantons=GE 256,395; tenant=kabge 31,589, all in SHAB rubrics; own rubrics 0. Law B 2 10. |

**Site recipe.**
- **www.ge.ch:** Drupal. robots.txt names `/sitemap.xml` (14 pages, 27,977 URLs); 24 Disallow rules.
- **justice.ge.ch:** Drupal; normalize `//` in sitemap URLs; decisions under /apps/decis.
- **getax.ch:** Crawl-delay 10.
- **Laws:** silgeneve.ch (via LexFind; robots.txt 404).
- **statistique.ge.ch:** ASP, iso-8859-1.

**Draft YAMLs** (official_info, CH-GE; the ge.ch sources are in g5):
```yaml
- id: ge-justice-themes   # category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://justice.ge.ch/fr/themes], path_allowlist: [/fr/theme/, /fr/contenu/frais-dune-procedure-civile, /fr/contenu/commission-de-conciliation-en-matiere-de-baux-et-loyers, /fr/contenu/tribunal-des-], language: fr}
- id: ge-ocv              # transport
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.ge.ch/immatriculer-vehicule-obtenir-carte-grise, https://www.ge.ch/plaques, https://www.ge.ch/passer-son-permis-conduire, https://www.ge.ch/impot-vehicules], path_allowlist: [/immatriculer-vehicule, /plaques, /passer-son-permis-conduire, /impot-vehicules], language: fr}
- id: ge-ocv-fees
  fetch_strategy: pdf
  fetch_config: {urls: [https://www.ge.ch/document/24460/telecharger], language: fr}
# ge-dogs / ge-getax / ge-holidays(ICS): as in g5 (D17, U10, D19)
```

**Claim checks.**

| AI link | Result | Correct URL |
|---|---|---|
| justice.ge.ch `/fr/{cour-de-justice, frais-et-emoluments, demarches, jurisprudence, chambre-administrative, tribunal-de-premiere-instance}` | Wrong: all 404 | /fr/contenu/cour-de-justice (sitemap), /fr/contenu/frais-dune-procedure-civile, /fr/themes, /fr/contenu/jurisprudence, /fr/contenu/tribunal-civil (sitemap). Chambre administrative: not checked |
| Communes: `/dossier/communes-genevoises` | Wrong: 403 | statistique.ge.ch/communes/welcome.asp |
| Chancellery: `/organisation/chancellerie-etat` | Confirmed | same |

---

## JU: Jura (base https://www.jura.ch)
| Cell | Status | URL | Evidence | Sample | Notes / legal basis |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/fr/Autorites/JUST/La-justice-jurassienne.html`; `/fr/Autorites/JUST/Instances-judiciaires/Tribunal-cantonal/Tribunal-cantonal.html` | 200 "Canton du Jura - Instances judiciaires", HTML, 68,853 B. TC page: 200, 888 words | "Toutes les instances judiciaires, à l'exception du Tribunal des mineurs, siègent à Porrentruy, au Château…" | |
| C2 | VERIFIED | TC circulars page `…/Tribunal-cantonal/Circulaires/Circulaires-du-Tribunal-cantonal-et-de-ses-sections.html` → PDF "Tarif des avances, émoluments et débours" (`/Htdocs/Files/v/ff78dbf9…/avances_emoluments_debours_juin-2016.pdf?download=1`). Resident page `/fr/Autorites/JUST/Domaines-du-droit/Droit-civil/Domaine-civil.html`. Ordinance RSJU 176.511 | Circulars: 200, 14 PDF links. Tariff: 200, 280,359 B, 5 pages, text layer ("état au 9 juin 2016"). 176.511: 200 PDF, 10 pages, text layer | Tariff: "4.5 Conciliation devant le président de la Cour civile Sous réserve de l'article 113 CPC : en principe 1'000 points." 176.511: "de 50 à 5 000 francs : de 15 à 300 points". Domaine civil: "…renseignements juridiques … contre paiement d'un émolument de 20 francs" | Fees are set in points; the point value is indexed yearly by arrêté. Ladder: sitemap grep (8 hits, none a court-fee page), then WebSearch `site:jura.ch`, then curl. |
| C3 | VERIFIED | Fetched (200): `/fr/Autorites/JUST/Assistance-judiciaire/Assistance-judiciaire.html` (910 words), `…/Domaines-du-droit/Droit-civil/Domaine-civil.html` (732), `…/Renseignements-juridiques/Droit-du-travail-et-du-bail/…` (663), Tribunal des baux (881). Sitemap only: Droit pénal, Droit administratif, Service de renseignements juridiques, Conseil de prud'hommes | 50 URLs under /fr/Autorites/JUST/ | "L'assistance judiciaire permet à une personne qui ne dispose pas des moyens financiers suffisants d'être dispensée d'avancer les frais de la procédure…" | |
| C4 | VERIFIED | `…/Tribunal-cantonal/Jurisprudence/Jurisprudence-du-Tribunal-cantonal.html` → `https://jurisprudence.jura.ch` | Page: 200. Its title reads "Cour administrative", which does not match the content. jurisprudence.jura.ch: 200, 19,593 B, 0 links; a JavaScript app (the HTML loads `TribunaVTPlus.css`) | "La jurisprudence du Tribunal cantonal est actuellement disponible sur https://jurisprudence.jura.ch" | opencaselaw `ju_gerichte` 1,201 (2011-01-17 → 2026-09-03). Not stale. |
| C5 | VERIFIED | Tribunal des baux page `…/Tribunal-de-premiere-instance/Tribunal-des-baux-a-loyer-et-a-ferme/…`; Droit du travail et du bail page | 200 (881 words); 200 (663 words) | "Toute requête doit être introduite au préalable devant la Commission de conciliation en matière de bail…"; "Les renseignements sont donnés gratuitement par téléphone ou sur rendez-vous au greffe du Conseil de prud'hommes." | Laws 182.351, 182.35, 182.34, 824.21. Fees: 1'000 points (see C2). |
| G1 | VERIFIED | `/fr/Autorites/Administration/DES/SCAV/Section-affaires-veterinaires/Chiens/Chiens.html` | 200, 84,207 B, 1,438 words | "…même si cela n'est pas oligatoire, le SCAV recommande aux personnes qui acquièrent un chien pour la première fois de suivre un cours facultatif…" | Law RSJU 645.1 Loi concernant la taxe des chiens and 645.11. **No dog-keeping law exists among the 855 active JU titles** (title search for "chien"). |
| G2 | VERIFIED | `/fr/Autorites/Administration/DFI/CTR/Formulaires/Formulaires-personnes-physiques/Annee-fiscale-2025/Annee-fiscale-2025.html` → `…/Guide-general-2025.pdf?download=1` | Page: 200, 717 words. PDF: 200, 1,549,163 B, 56 pages, 155,405 chars | "Revenu réalisé Fr. 15'000.- ./. déduction forfaitaire (20% max. Fr. 4'100.-) Fr. 3'000.-" | **This page is not in the jura.ch sitemap** (0 hits); found via WebSearch. The new DFI/Contributions-NEU pages say "En construction", and their forms page still lists Guide général 2019. Law 641.11. |
| G3 | VERIFIED | `/fr/Autorites/Administration/DFNS/SEN/Vacances-scolaires/Vacances-scolaires.html`; arrêté PDF 2025–2028 | 200 (720 words); PDF 200, 117,391 B, 2 pages, text layer | "Vacances d'automne Du lundi 5 octobre 2026 au vendredi 16 octobre 2026". Arrêté: "Il s'applique à l'ensemble des écoles publiques." | **The Gouvernement (canton) sets them.** The page mentions an ICS file, but its HTML has no `.ics` link. |
| G4 | VERIFIED | `/fr/Autorites/Administration/DEC/OVJ/Office-des-vehicules-OVJ.html`; `…/OVJ/Taxe-et-emoluments/Taxe-et-emoluments.html` | 200 (111,904 B, 2,273 words); 200 (2,597 words) | "Taxe maximale = 1'015 francs par année." | 31 OVJ URLs in the sitemap. Laws 741.11 and 741.611. |
| D1 | VERIFIED | `/fr/Autorites/Administration/DFI/COM/Les-communes-jurassiennes/Les-communes-jurassiennes.html` | 200, 88,012 B, with links to commune websites (e.g. `http://www.boecourt.ch/`) | "Le Canton du Jura compte 51 communes réparties dans quatre districts : Delémont, Franches-Montagnes, Moutier et Porrentruy." | 51 matches commune_sites.csv. The page also lists bourgeoisies. |
| D2 | VERIFIED | `/fr/Autorites/Administration/CHA/SCH/Secretariat-de-la-Chancellerie-d-Etat.html`; gazette `https://rsju.jura.ch/fr/Sommaire/Journal-officiel.html` | 200 (1,160 words). JO 2026 page: 200, 33 issue PDFs. JO No 33 PDF: 200, 182,004 B, 13 pages, text layer | "No 33 – Jeudi 17 septembre 2026 … Le « Journal officiel de la République et Canton du Jura » paraît chaque semaine, le jeudi." | Free weekly PDFs; year pages for 2022–2026. rsju.jura.ch robots.txt: `User-agent: *` plus a Sitemap line, no Disallow. Amtsblattportal: cantons=JU 20,763; tenant=kabju 2,076, of which 2,069 in SHAB rubrics; own rubrics 0. Law 170.513. |

**Site recipe.**
- **www.jura.ch:** Files are served as `/Htdocs/Files/v/<sha256>.pdf/<name>?download=1`; the CMS vendor is unknown.
  - robots.txt names `/sitemap/Francais_fr_fr_z1_sitemap.xml` (7,805 URLs; 1 Disallow rule).
  - **The sitemap is incomplete** (it misses the tax 2025 page).
  - Page text starts after the breadcrumb "Autorités » …".
- **rsju.jura.ch:** laws and the Journal officiel.
- **jurisprudence.jura.ch:** Tribuna JavaScript app.

**Draft YAMLs** (official_info, CH-JU):
```yaml
- id: ju-justice         # category missing: courts
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/JUST/La-justice-jurassienne.html], path_allowlist: [/fr/Autorites/JUST/], language: fr}
  # skip /Revue-jurassienne-de-jurisprudence/20xx archive pages
- id: ju-court-tariff
  fetch_strategy: pdf
  fetch_config: {urls: ["https://www.jura.ch/Htdocs/Files/v/ff78dbf9136f8cab273ea6f4352309fbc0f1d77137ab65c0610a20db98ee89c8.pdf/avances_emoluments_debours_juin-2016.pdf?download=1"], language: fr}
- id: ju-dogs            # dogs
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/Administration/DES/SCAV/Section-affaires-veterinaires/Chiens/Chiens.html], path_allowlist: [/fr/Autorites/Administration/DES/SCAV/Section-affaires-veterinaires/Chiens/], language: fr}
- id: ju-tax-guide       # taxes
  fetch_strategy: pdf
  fetch_config: {urls: ["https://www.jura.ch/Htdocs/Files/v/81cc78891c5f1637d43c7c3fa46061ce931b57ab3a48c0e43a09d8c662c2395d.pdf/Guide-general-2025.pdf?download=1"], language: fr}
- id: ju-school-holidays # schools
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/Administration/DFNS/SEN/Vacances-scolaires/Vacances-scolaires.html], path_allowlist: [/fr/Autorites/Administration/DFNS/SEN/Vacances-scolaires/], language: fr}
- id: ju-ovj             # transport
  fetch_strategy: html_crawl
  fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/Administration/DEC/OVJ/Office-des-vehicules-OVJ.html], path_allowlist: [/fr/Autorites/Administration/DEC/OVJ/], language: fr}
```

**Claim checks.**

| AI link | Result | Correct URL |
|---|---|---|
| `/pju/{Tribunal-cantonal, Emoluments, Themes, Jurisprudence, Tribunal-de-premiere-instance}.html` | Wrong: all 404 | /fr/Autorites/JUST/… |
| Dogs: `/DEN/SCAV/…` | Wrong: 404 (the department is DES, not DEN) | …/DES/SCAV/…/Chiens/Chiens.html |
| Tax: `/DFN/IMP/…` | Wrong: 404 | The CTR Année fiscale 2025 page |
| School holidays: `/DFCS/SEN/…` | Wrong: 404 | /DFNS/SEN/Vacances-scolaires/… |
| Road office: `/DEN/OVJ/Office-des-vehicules.html` | Wrong: 404 | /DEC/OVJ/Office-des-vehicules-OVJ.html |
| Communes: `/DFN/SCOM/…` | Wrong: 404 | /DFI/COM/Les-communes-jurassiennes/… |
| Chancellery: `/CHA/Chancellerie-d-Etat.html` | Wrong: 404 | /CHA/SCH/Secretariat-de-la-Chancellerie-d-Etat.html |

---

## L1: city law collections
Authority is official_info until these hosts are registered as law platforms.

| City (BFS) | Status | Real location | Platform and format | Texts | Dogs / waste / parking present? | Sample |
|---|---|---|---|---|---|---|
| **Lausanne (5586)** | VERIFIED | `https://www.lausanne.ch/apps/actualites/index_recueil.php`. The `/officiel/recueil-systematique-du-droit-communal.html` page (200) redirects there by meta refresh | Custom PHP app, server HTML (200, 941,968 B, 1,212 links). Each text downloads from `Next/serve.php?id=N&kind=recueil` as a PDF with a text layer (id=7: 34 pages) | **193** ("Tous les documents 193 résultats"; 193 distinct ids) | Dogs yes: 503.1 "Dispositions réglementaires municipales concernant les chiens", 503.2 tariff. Waste yes: 830.1–830.x (7 texts). Parking yes: 710.1 "Règlement sur la circulation et le stationnement", 710.2 resident parking, 710.3 tariff | "100.1 Règlement du Conseil communal de Lausanne – RCCL Adopté le: 12.11.1985 – En vigueur depuis le: 01.01.1986" |
| **Neuchâtel (6458)** | VERIFIED | `https://www.neuchatelville.ch/votre-commune/reglementation`, plus `/anciennes-communes/reglementation-{neuchatel,peseux,cc,valangin}` | TYPO3 fileadmin PDF list (200, 138,195 B, 781 links). PDFs have a text layer (Règlement général: 50 pages) **except the dog arrêté, which is scanned** (9 pages, 1 character) | **79** distinct current PDFs. The former-Neuchâtel page has 239 PDF links; the sitemap lists 120 regulation PDFs | Dogs: 12.21 "Arrêté concernant les modalités d'accès des chiens aux espaces publics, du 15 juin 2020" (former-commune list; needs OCR). Waste yes: 705, 705.1, 705.10. Parking yes: 810, 810.1 | "100 Règlement général de la Ville de Neuchâtel, du 7 juin 2021 – Dernière modification: 16 février 2026" |
| **La Chaux-de-Fonds (6421)** | VERIFIED through its API | The HTML at `https://www.chaux-de-fonds.ch/rapports-et-reglements/reglementation` is a JavaScript shell ("Chargement en cours..."). The data comes from `POST https://www.chaux-de-fonds.ch/Api/Page.svc/detail` with body `{"page":"/rapports-et-reglements/reglementation/<theme>"}` | Joomla front end; the content HTML contains SharePoint table classes (backend inferred). The JSON has `DetailResult{Content, Id, LastModified, Title, Url, WebParts}`. PDFs at `/rapports-et-reglements/reglementation/Documents/<nr>.pdf` (50_10.pdf: 200, 20 pages, text layer). Endpoint found by reading `media/biblio/js/Client.js` | **175** PDF links across 9 theme pages | Dogs yes: 41.13 "Arrêté … fixant la taxe annuelle des chiens". Waste yes: 62.13 "gestion des déchets", 62.130, 62.131, 62.12 "ordures". Parking yes: 63.101 zone bleue, 63.105 "stationnement public" | "50.10 Règlement du Conseil général de la Police, du 28 novembre 2011" |
| **Genève Ville (6621)** | VERIFIED | `https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux?page=0…24` | Drupal listing, 25 pages of 10. Each `/administration-municipale/reglements-municipaux/lc<nr>-<slug>` URL serves the PDF directly (lc21911: 200 application/pdf, 18 pages, text layer) | **246** distinct texts numbered LC 21 xxx, in 9 categories (LC 21 100 to 900) | Dogs: none (dogs are cantonal law, M 3 45). Waste yes: LC 21 911. Parking yes: LC 21 154.1 plus annexes | "Règlement sur la gestion des déchets LC 21 911 Adopté par le Conseil administratif le 25 janvier 2024 Entrée en vigueur le 1er février 2024 (Etat le 1er janvier 2026)" |
| **Vernier (6643)** | VERIFIED, with a site outage | `https://www.vernier.ch/administration-et-autorites/reglements-communaux` → `/administration-et-autorites/publications?category=38&profile=_all` | Drupal. The listing answered 200 at my first probe (69,510 B, 32 links). **From 13:39 to 13:57 CEST every Drupal page, including the home page, answered 500** ("The website encountered an unexpected error"). Cause unknown. Static `/sites/default/files/*.pdf` files kept answering 200 | **52** regulation-type publication URLs in the sitemap (out of 127 publications) | Dogs: no slug. Waste yes: 3 (collecte-transport-et-élimination-des-déchets, taxe-communale-…-déchets, proprement-vernier). Parking yes: 1 (stationnement-sur-les-parkings-privés-communaux) | PDF RSRV 722.0 (200, 9 pages, text layer): "…relatif à la Collecte, transport et élimination des déchets Du 30 août 2011 (État au 3 juin 2019)" |

**Claim checks (cities).** All five AI links were 404 in the pre-check (`cities_s2_links.txt`). The correct URLs are the ones in the table above.

**City fetcher hint.** One `pdf-index` fetcher covers all five, with per-site options:
- Lausanne: parse the app's rows (number, title, "Adopté le", "En vigueur depuis le", `serve.php` id).
- Genève: page through `?page=N`.
- Neuchâtel: an `<a href=".pdf">` list.
- La Chaux-de-Fonds: POST-JSON pre-step.
- Vernier: publication pages give a PDF under /sites/default/files; retry once the site is back.

Mapping: identifier is `<city>:<number>`; title is the link text; valid_from is the "En vigueur" date; sections are split on "Art." headings; extent is CH-XX-<BFS>.

---

## Cross-canton section
### New fetcher classes needed
Names reuse the brief's list.
- **`sitemap-crawl`** covers C1/C3/C5/G1/G3/G4 in all five cantons. It needs:
  - a host-rewrite option (NE child sitemaps point at `ne-prod-admin.ne.ch`);
  - `//` normalization (justice.ge.ch);
  - an archive denylist (FR `arrets-de-la-section-*`, JU `Revue-jurassienne-*`);
  - `<main>` extraction (NE pages are about 500 KB of menu);
  - link-following as a supplement, because the jura.ch sitemap misses pages.
- **`pdf-index`** covers:
  - the city collections: Lausanne 193, Genève 246, La Chaux-de-Fonds 175, Neuchâtel 79+, Vernier 52;
  - the JU Journal officiel: weekly PDFs, with text layer;
  - the NE SCCO tax PDFs and the FR `/document/<id>` tax documents.
- **`ics`** covers the FR school calendars (3 regional calendars × 4 years) and GE (g5). JU mentions an ICS file but links none.
- **`xlsx`** covers the FR commune list (a resolver use).
- **Law fetchers** (legal basis for C2/G1/G2): `lexwork` (bdlf.fr.ch), `vd-blv` (BLV API: CONSOLIDE JSON, then /html), `ne-rsn` (**robots.txt `Disallow: /`**), `ju-rsju` (viewdocument&download=1), `lexfind-enum` (GE silgeneve PDFs).
- **New: `post-json-page`**, only for La Chaux-de-Fonds (`POST /Api/Page.svc/detail`). It serves one city; the platform is not identified (a SharePoint backend is inferred).
- **New: `gazette-html`** for fo.fr.ch (`/archive/<yr>/<no>/<rubric>`) and faovd.ch (`/rubrique/<x>/`), 2 cantons. Needs per-notice splitting and per-commune narrowing. An Amtsblattportal XML fetcher adds nothing for these cantons: they have no own rubrics, and its robots.txt is `Disallow: /`.
- **`ocr-pdf`** for the Neuchâtel dog arrêté 12.21. For FR school calendars the ICS replaces the garbled PDF.

### Blocked items and policy flags
| Item | Status |
|---|---|
| fao.ge.ch (GE gazette) | blocked: CAPTCHA on entry |
| NE Feuille officielle | blocked: paywall (Guichet unique subscription, 53 francs per year) |
| fo.fr.ch robots.txt | Named AI bots (ClaudeBot, anthropic-ai, Claude-Web, GPTBot, CCBot, Google-Extended, PerplexityBot, …) get `Disallow: /`; `*` is allowed. Our user agent is not named, but the publisher's intent is explicit. Needs a policy decision |
| rsn.ne.ch robots.txt | `User-agent: * Disallow: /` on the NE law platform. Policy flag for `fetcher:ne-rsn` |
| jurisprudence.vd.ch and amtsblattportal.ch robots.txt | `Disallow: /` for all agents. Use opencaselaw for decisions; the gazette tenants are not needed |
| ge.ch `/dossier/communes-genevoises` | blocked: 403. Workaround: statistique.ge.ch |
| www.vernier.ch Drupal pages | 500 from 13:39 to 13:57 CEST; static PDFs still served. Retry needed |
| La Chaux-de-Fonds HTML | JavaScript-only; solved through the JSON API. The search-indexed PDF URLs are stale (10_10.pdf → 500, 21_10.pdf → 404); current names look like `RSC_10_10_20260701.pdf` |
| publicationtc.fr.ch and jurisprudence.jura.ch | Tribuna JavaScript apps with 0 links. Decisions come from opencaselaw, and the FR TC page links recent PDFs directly |
| Categories missing | courts (C1–C5) and gazette notices (D2). D1 lists are resolver data |

### Five best finds
1. **NE sitemap recovery.** Fetching `https://www.ne.ch/sitemap.xml?page=1` and `?page=2` and rewriting the host gives 8,518 URLs. That opens every NE guidance cell and turns "no sitemap" into `sitemap-crawl`.
2. **Lausanne's systematic collection** (`/apps/actualites/index_recueil.php`): 193 municipal texts, each with a number, adoption and in-force dates, and a text-layer PDF. Dog, waste and parking rules are all present.
3. **Ville de Genève's 246 LC 21 xxx regulations.** Each URL serves a text-layer PDF with adoption, in-force and consolidation dates.
4. **La Chaux-de-Fonds JSON API** behind a JavaScript shell (`POST /Api/Page.svc/detail`): 175 regulation PDFs in 9 themes, including dog tax 41.13, waste 62.13 and parking 63.105.
5. **FR data-grade sources:**
   - school-holiday ICS per region and year (11 VEVENTs per file);
   - a TC jurisprudence page that lists the newest rulings (22.09.2026) with direct PDF links;
   - the 119-commune XLSX with BFS numbers.

   Runner-up: faovd.ch `/rubrique/communes/`, free per-commune gazette notices in HTML (31,108 words).