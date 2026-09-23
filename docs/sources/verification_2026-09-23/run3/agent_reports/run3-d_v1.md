I have evidence for every cell across the five cantons and all five cities. Here is the complete report.

# Run 3, group D: FR · VD · NE · GE · JU, plus city law for 5 cities

Every status, title, size, count and quote below comes from requests made in this session (2026-09-23, about 12:20–14:00 CEST). Scratch files are in `scratchpad/run3-d/` (`probe.py`, `pages/`, `laws/`, `ne_sitemap_urls.txt`). "(cited: g5)" means the item was already verified in `reports/g5-guidance.md` and I only re-checked it live. Anything marked "inferred" was not proven by a request.

## Headlines
1. **NE has a usable sitemap after all.** `https://www.ne.ch/sitemap.xml` is an index whose two children are written on an internal host, `http://ne-prod-admin.ne.ch/sitemap.xml?page=N`, which does not resolve in DNS. The same paths on www.ne.ch answer 200: page 1 has 5,000 URLs and page 2 has 3,518, so 8,518 in total (684 under /themes, 266 under /autorites, 7,526 press releases). Swapping the host back to www.ne.ch fills every NE cell.
2. **The Romandie gazettes are not really on Amtsblattportal.** The tenants `kabfr`, `kabvd`, `kabne`, `kabge` and `kabju` all carry `external: true`. With `tenant=` they hold only debt and bankruptcy notices (rubrics SB, KK, AW, NA): VD 21,235, GE 31,589, FR 6,863, JU 2,076, NE 387. The `tenants=` parameter is ignored: every tenant returned the same 2,851,291. The real gazettes:
   - fo.fr.ch: free HTML.
   - faovd.ch: free HTML.
   - rsju.jura.ch: weekly PDFs.
   - fao.ge.ch: CAPTCHA.
   - NE: paid, through the Guichet unique.
3. **Every court-fee ordinance has a CHF quote from the official text**: FR 130.11, VD 270.11.5, NE 164.1, GE E 1 05.10, JU 176.511, plus the JU Tribunal cantonal tariff. Four of these were missing from `law_hits.json` (NE 164.1, GE E 1 05.10, FR 130.11/130.16). I found them in `laws_XX.json`.
4. **City law is reachable for all 5 cities:**
   - Lausanne: 193 texts.
   - Ville de Genève: 246.
   - La Chaux-de-Fonds: 175, through a POST JSON API hidden behind a JS page.
   - Neuchâtel: 79 current plus lists from the merged former communes.
   - Vernier: 52 regulation pages in its sitemap. Its Drupal pages answered 500 from 13:39 to 13:57 CEST, but its static PDFs were still served.

---

## FR (base `https://www.fr.ch`)
| Cell | Status | URL | Evidence (HTTP · title · format · size) | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/etat-et-droit/justice`; `/pj/tc` | 200 · "Justice \| Etat de Fribourg" · server HTML · 98,565 B, 78 links, 773 words. TC: 200 "Tribunal cantonal (TC) \| Etat de Fribourg" | "Il existe trois types de juridictions ou d'organes du Pouvoir judiciaire : les juridictions civiles (s'occupent de conflits entre particuliers), pénales…" | yaml-now:html_crawl |
| C2 | VERIFIED | `/etat-et-droit/justice/tarifs`; ordinance RSF **130.11** RJ `https://bdlf.fr.ch/app/fr/texts_of_law/130.11` (+130.16) | tarifs: 200 "Tarifs \| Etat de Fribourg", 442 words. 130.11 API: 200 JSON 1,433,906 B, version in force since 01.12.2025 | tarifs: "…jusqu'à 100.00 21.00 … Valable dès le 1er janvier 2024." RJ: "émolument de conciliation de 50 à 10'000 francs." | The resident page is the debt-enforcement advance-fee table, not court fees. A sitemap grep (22 hits for frais/cout/emolument/assistance-judiciaire) found no court-cost page. law_hits' 76.16/710.16/150.12 are special tariffs. 130.16 is the TC tariff (in force 01.02.2016). |
| C3 | VERIFIED | 10 URLs below | Sitemap: 138 FR URLs under /etat-et-droit/justice (40 archive/admin → 98 guidance-type), 67 under /poursuites-et-faillites (36 procedure pages), 141 DE mirror pages. Fetched pages: 200, 442–1,865 words | Justices de paix: "La justice de paix est en premier lieu l'autorité de protection de l'enfant et de l'adulte." | Fetched: justices-de-paix (1,126 w), commissions-de-conciliation-…-bail (1,075), tribunal-des-prudhommes (720), mediation-judiciaire (1,464), competences-territoriales (1,087), indications-complementaires (1,865), tarifs (442). Sitemap-only: faq-mp, …/procedure-de-poursuite/requisition-de-poursuite, …/pouvoir-judiciaire-tribunaux-darrondissement |
| C4 | VERIFIED | `/pj/tc/jurisprudence-du-tribunal-cantonal`; search `https://publicationtc.fr.ch/?locale=fr` | TC page: 200, 105,190 B, 99 links, lists the latest rulings with direct PDFs `publicationtc.fr.ch/tribunavtplus/ServletDownload/<dossier>_<hash>.pdf?path=…`. Search: 200, 19,593 B, 0 links (JS app) | "102 2026 206 22.09.2026 09h00 Arrêt de la IIe Cour d'appel civil du Tribunal cantonal - Annulation de la faillite (art. 174 LP)." | opencaselaw fr_gerichte 14,768 decisions, 2002-07-31 → **2027-07-27**: a future latest date is a data anomaly, not staleness. fr_anwaltsaufsicht: 3, sparse, no dates. |
| C5 | VERIFIED | `/etat-et-droit/justice/pouvoir-judiciaire-commissions-de-conciliation-en-matiere-de-bail-et-tribunal-des-baux`; justices de paix; prud'hommes | 200, 92,054 B, 1,075 words | "Des frais judiciaires ne sont pas perçus dans les litiges portant sur des baux à loyer d'habitations lorsque l'objet du bail constitue le logement principal du locataire et qu'il n'est pas luxueux." | Guidance and fees both on the page; "il existe trois commissions de conciliation". Laws 222.3.1, 862.2. |
| G1 | VERIFIED | `/vie-quotidienne/animaux-de-compagnie/chiens` (+`/impot-sur-les-chiens`) | 200 "Chiens \| Etat de Fribourg", 156,573 B, 701 words. Tax page: 200, 510 words | "…soumis à un impôt cantonal d'un montant de CHF 100.- par chien, auquel est ajouté un montant de CHF 5.-…" | Law 725.3 LDCh (version 01.01.2024), 725.31 RDCh. Category dogs. |
| G2 | VERIFIED | `/document/57721` → `…/2026-05/instructions-generales-concernant-la-declaration-d-impot_0.pdf` | 200 PDF, 324,278 B, 50 pages, 122,632 characters of text | "Le montant minimal est de Fr. 100.- par année fiscale et le montant maximal est li- mité à 20% du revenu net (code 4.910)." | Enumerable: 79 FR /impots/ URLs in the sitemap; PDFs are `/document/<id>` links that redirect to dated files with a `?v=` parameter. Law 631.1. |
| G3 | VERIFIED | `/dfac/vacances-scolaires`; ICS `/document/508696` | 200 HTML, 2,476 words. ICS: 200 text/calendar, 437,002 B, 11 VEVENTs | "Vacances d'automne 12 octobre 2026 23 octobre 2026 (inclus)"; `DTSTART;VALUE=DATE:20261012` / `SUMMARY;LANGUAGE=fr-ch:Vacances d'automne` | **Who sets them:** the DFAC sets 3 reference calendars (majoritaire, Morat/Murten, Kerzers), and "chaque cercle scolaire a la possibilité de donner 1 jour (ou 2 pour la région de Murten/Morat)". There is one ICS per calendar per school year up to 2029/30 (508696, 508646, 513541, 508701 …). The PDF's text layer is garbled, so use the ICS. |
| G4 | VERIFIED | `https://www.ocn.ch/fr`; `/fr/conduire/vehicules/immatriculation`; `…/que-coute-le-permis-de-conduire`; `…/duree-et-tarif-des-expertises-de-vehicules` | All 200, server HTML (Drupal), 129–138 KB, about 370 links | "Le permis de conduire une voiture (catégorie B) coûte Fr. 190.-." | Sitemap: 856 URLs (428 fr / 428 de), 19 FR fee pages. Law 781.16 (version 01.09.2025). |
| D1 | VERIFIED | `/etat-et-droit/communes/reglements-annuaire-et-infoscom-pour-les-collectivites-publiques/listes-des-collectivites-publiques-locales` → XLSX `/document/580206` | Page 200, 710 words. XLSX 200, 87,961 B, sheet "CO-GEM 2026": **119** commune rows (BFS number + name, grouped by district) | `2008 \| Châtillon (FR)` | No website links (0 cells). Yearly files 2021–2026. Law 112.51. Destination: resolver. |
| D2 | VERIFIED | `/cha`; gazette `https://fo.fr.ch` | CHA: 200, 1,023 words. FO: 200 "Articles \| Feuille officielle du canton de Fribourg"; `/archive/2026/38/18` 200, 1,606 words | "Les membres du Conseil général de la commune de Châtel-Saint-Denis sont convoqués en séance ordinaire le mercredi 30 septembre 2026, à 19 h 30…" | Weekly, free, HTML per issue and rubric (`/archive/<y>/<no>/<rubric>`). Law 124.21. |

**Site recipe (FR)**
- www.fr.ch: Drupal with Acquia Site Studio (signatures "Site Studio" and /sites/default/files). robots.txt: 29 Disallow, no Sitemap line, no crawl-delay. `/sitemap.xml` has 67,964 URLs.
- www.ocn.ch: Drupal, 856 URLs. fo.fr.ch: Drupal, 58 Disallow. bdlf.fr.ch: LexWork.
- publicationtc.fr.ch: Tribuna JS app. The `/tribunavtplus/` path is visible in the PDF links.
- No bot walls met.

**YAML (FR)**
```yaml
# fr-justice | official_info | CH-FR | category missing: courts
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.fr.ch/etat-et-droit/justice], path_allowlist: [/etat-et-droit/justice/, /etat-et-droit/poursuites-et-faillites/procedure-de-], language: fr}
# needs a deny rule for /etat-et-droit/justice/arrets-de-la-section-* (40 archive pages)
---
# fr-dogs | official_info | CH-FR | dogs
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.fr.ch/vie-quotidienne/animaux-de-compagnie/chiens], path_allowlist: [/vie-quotidienne/animaux-de-compagnie/chiens], language: fr}
---
# fr-tax-instructions | official_info | CH-FR | taxes
fetch_strategy: pdf
fetch_config: {urls: [https://www.fr.ch/document/57721], language: fr}
---
# fr-holidays-html | official_info | CH-FR | schools   (ICS → fetcher:ics)
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.fr.ch/dfac/vacances-scolaires], path_allowlist: [/dfac/vacances-scolaires], language: fr}
---
# fr-ocn | official_info | CH-FR | transport
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.ocn.ch/fr/conduire], path_allowlist: [/fr/conduire/, /fr/changements-de/], language: fr}
```
Landing contract: ICS gives event_date=DTSTART, title=SUMMARY, identifier=DTSTART+SUMMARY (DTEND is exclusive). HTML pages carry "Dernière modification : 19.12.2023" in the footer, which can fill published_at.

**Claim checks (FR)**
- fr.ch/pouvoir-judiciaire/{tribunal-cantonal, frais-et-emoluments, themes, jurisprudence, tribunaux-darrondissement}: **Wrong**, all 404. Correct pages: `/pj/tc`, `/etat-et-droit/justice/tarifs` + RJ 130.11, `/etat-et-droit/justice`, `/pj/tc/jurisprudence-du-tribunal-cantonal`, `/etat-et-droit/justice/pouvoir-judiciaire-tribunaux-darrondissement`.
- Dogs `/sanu/animaux/chiens/detention-de-chiens`: **Wrong** (404); correct is `/vie-quotidienne/animaux-de-compagnie/chiens`.
- Tax `/scc/impots/…/guide-pour-la-declaration-dimpot`: **Wrong** (404); correct is `/document/57721`.
- School `/formation-et-ecoles/…/vacances-scolaires`: **Partly**, it redirects to `/dfac/vacances-scolaires`.
- Road `ocn.ch`: **Confirmed**.
- Communes `/etat-et-droit/communes`: **Partly**, it is a landing page; the list is the XLSX.
- Chancellery `/ce/chancellerie-detat-cha`: **Wrong** (404); correct is `/cha`.

---

## VD (base `https://www.vd.ch`)
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/ojv`; `/ojv/tribunal-cantonal` | 200 "Ordre judiciaire vaudois (OJV) \| État de Vaud", 40,667 B, 114 links, 1,113 words (TYPO3). TC: 200, 842 words | "Le Tribunal cantonal est l'autorité judiciaire supérieure du canton." | yaml-now:html_crawl |
| C2 | VERIFIED | `/justice/la-justice-civile/combien-coute-une-procedure-civile`; **270.11.5 TFJC** (BLV) | Page: 200, 829 words. BLV `api/actes/CONSOLIDE?id=5848c893-…&cote=270.11.5` 200 JSON (in force 01.01.2011, version 01.01.2025) → `api/actes/ffd39db6-…/html` 200 xhtml, 415,687 B | "des frais judiciaires sont perçus par les autorités judiciaires. Les frais judiciaires comprennent essentiellement l'émolument forfaitaire…"; TFJC: "de 0 à 2'000 francs : 150 francs - de 2'001 à 5'000 francs : 210 francs" | Also administrative and penal cost pages in the sitemap. |
| C3 | VERIFIED | `/justice/la-justice-civile`, `…/conciliation-en-matiere-civile`, `…/successions`, `…/conflits-du-travail`, `…/consensus-parental`, `…/combien-coute-une-procedure-civile`, `/justice/conseils-et-assistance`, `…/mediation`, `/justice/curatelles-et-tutelles`, `/justice/la-justice-penale/qui-paie-les-frais-engendres-par-une-procedure-penale` | Sitemap: **82** under /justice/ + **73** under /ojv/. Fetched pages 200, 583–906 words | "une procédure de conciliation doit précéder tout litige judiciaire civil, quel que soit la valeur litigieuse." | 5 of the 10 were fetched; the others come from the sitemap. |
| C4 | VERIFIED | `/justice/jurisprudence-et-lois/jurisprudence-du-tribunal-cantonal-et-du-tripac` → `https://jurisprudence.vd.ch/scripts/nph-omniscgi.exe?…Schema=VD_TA_WEB…` | Search: 200 "Jurisprudence: Recherche simple", 20,833 B, iso-8859-1 (Omnis FindInfo form) | "INFORMATION CONCERNANT LA JURISPRUDENCE DE LA COUR DE DROIT ADMINISTRATIF ET PUBLIC…" | opencaselaw: vd_findinfo 74,714 (latest 2025-12-20, **STALE**); vd_gerichte 68,645 (latest 2026-09-03); vd_omni 28,033 (latest 2026-02-09). |
| C5 | VERIFIED | `/ojv/justices-de-paix`; conciliation page (C3); `/etat-droit-finances/districts-/-prefectures/prefectures/prestations-des-prefectures/commissions-prefectorales-de-conciliation/bail-a-loyer-ou-a-ferme-non-agricole` | 200 (1,364 w); 200 (906 w); 200 (978 w) | "rendre une décicion dans les litiges dont la valeur patrimoniale est inférieure à Fr. 2'000.-" (the typo is on the site) | Tenancy conciliation is done by the préfecture commissions. The conciliation page states no fees (grep for gratuit/frais: 0 hits); TFJC sets them. Laws 173.655, 173.655.310821.1. |
| G1 | VERIFIED | `/population/veterinaires-et-animaux/police-des-chiens` | 200 "Police des chiens \| État de Vaud", 34,207 B, 972 words | "Les cours obligatoires pour détenteurs de chiens ont été supprimés depuis le 1er janvier 2017." | Laws 133.75, 133.75.1, 652.31.1 (cantonal dog tax). |
| G2 | VERIFIED | `/fileadmin/user_upload/organisation/dfin/aci/fichiers_pdf/21001_2025.pdf` | 200 PDF, 4,121,012 B, 68 pages, 229,072 characters of text | "DÉDUCTION POUR FRAIS DE GARDE CODE 670 La déduction s'élève à CHF 25 800 francs au maximum par enfant." | Enumerable: filenames follow `21001_<year>.pdf` (2024 and 2025 seen), plus 21003/21004/21007, on `/etat-droit-finances/impots/formulaires-directives-et-baremes` (359 links). 119 /impots/ URLs in the sitemap. |
| G3 | VERIFIED | `/formation/jours-feries-et-vacances-scolaires`; `…/jours-feries-et-vacances-scolaires-2026` | 200 (683 w); 200 (914 w) | "Le Département de l'enseignement et de la formation professionnelle (DEF) a la compétence de fixer les dates des vacances scolaires."; "Vacances d'automne : du sa. 10 octobre au di. 25 octobre 2026" | **Canton (DEF) sets them.** Year pages 2026–2031 and a PDF up to 2031. No ICS found. |
| G4 | VERIFIED | `/mobilite/automobile-et-navigation`; `…/frais-des-prestations-du-san/permis-de-conduire` | 200 (1,511 w); 200 (641 w) | "Etablissement d'un permis d'élève ou d'un duplicata 30.-" | 8 fee subpages. Law 741.15.1. |
| D1 | VERIFIED | `/etat-droit-finances/communes/liste-des-communes-et-districts` | 200, 57,548 B; HTML table with **300** rows (Commune, District, No OFS) + XLS | "Aclens \| Morges \| 5621" | No website links. Law 132.15. Destination: resolver. |
| D2 | VERIFIED | `/cha`; FAO `https://www.faovd.ch` | CHA: 200. faovd.ch: 200, 41,441 B. `/rubrique/communes/`: 200, 1,048,547 B, 31,108 words | "EYSINS 18.09.2026 / FAO n° 75" | Appears Tuesday and Friday, free. faovd.ch has no robots.txt (404). Law 170.551. |

**Site recipe (VD)**
- www.vd.ch: TYPO3 (fileadmin). robots.txt names the sitemap `https://www.vd.ch/sitemap?type=1533906435` (27,472 URLs); 18 Disallow, no crawl-delay.
- The old `/themes/` prefix is gone, which explains the AI 404s.
- Law comes from prestations.vd.ch BLV. Decisions: jurisprudence.vd.ch (Omnis).

**YAML (VD)**
```yaml
# vd-justice | official_info | CH-VD | category missing: courts
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.vd.ch/justice, https://www.vd.ch/ojv/justices-de-paix], path_allowlist: [/justice/, /ojv/justices-de-paix, /ojv/tribunal-des-baux], language: fr}
---
# vd-dogs | dogs
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.vd.ch/population/veterinaires-et-animaux/police-des-chiens], path_allowlist: [/population/veterinaires-et-animaux/police-des-chiens], language: fr}
---
# vd-tax-instructions | taxes
fetch_strategy: pdf
fetch_config: {urls: [https://www.vd.ch/fileadmin/user_upload/organisation/dfin/aci/fichiers_pdf/21001_2025.pdf], language: fr}
---
# vd-holidays | schools
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.vd.ch/formation/jours-feries-et-vacances-scolaires], path_allowlist: [/formation/jours-feries-et-vacances-scolaires], language: fr}
---
# vd-san | transport
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.vd.ch/mobilite/automobile-et-navigation], path_allowlist: [/mobilite/automobile-et-navigation/], language: fr}
```

**Claim checks (VD)**
- `/toutes-les-autorites/ordre-judiciaire-vaudois-ojv/tribunal-cantonal` and `…/tribunaux-darrondissement`: **Confirmed**, both redirect to /ojv/….
- `…/frais-et-emoluments`, `…/themes`, `…/jurisprudence`, `…/cour-de-droit-administratif-et-public`: **Wrong** (404). Correct: combien-coute… + TFJC; `/justice`; the jurisprudence page; `/ojv/tribunal-cantonal`.
- Dogs, tax and school `/themes/...`: **Wrong** (404). Correct: see G1–G3.
- Road `/themes/mobilite/automobile`: **Partly**, redirects to `/mobilite/automobile-et-navigation`.
- Communes `/toutes-les-communes`: **Wrong** (404); correct is D1.
- Chancellery `/etat-de-vaud/chancellerie-detat`: **Wrong** (404); correct is `/cha`.

---

## NE (base `https://www.ne.ch`; the sitemap must be recovered as in headline 1)
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/autorites/autorites-judiciaires` | 200 "Autorités judiciaires \| ne.ch", 512,082 B (about 500 links are the mega-menu), Drupal | Tribunal d'instance: "Le Tribunal d'instance est l'autorité judiciaire cantonale de première instance. Il est réparti en deux juridictions" | Extract only `<main>`. |
| C2 | VERIFIED | `/themes/etat-droit-et-finances/droits-et-justice/frais-de-justice`; **RSN 164.1** `https://rsn.ne.ch/DATA/program/books/rsne/pdf/164.1.pdf` | Page 200 (main content 11,446 characters). PDF 200, 296,961 B, 13 pages, text layer | Page: "facturation et recouvrement des jugements et décisions des tribunaux du canton"; LTFrais: "L'émolument forfaitaire de conciliation est fixé selon le tarif suivant : … jusqu'à 2'000.- 300.-" | The page has no CHF amounts. 164.1 is not in law_hits (found in laws_NE.json). |
| C3 | VERIFIED | `…/droits-et-justice/{assistance-judiciaire, mediation-en-cas-de-conflits, droit-du-bail, frais-de-justice, amendes-dordre, avocat-e-s, notaires}`, `/autorites/autorites-judiciaires/{tribunal-dinstance, tribunal-dinstance/apea, communication-electronique-…}` | Recovered sitemap: **23** droits-et-justice + **14** autorites-judiciaires URLs; all fetched pages 200 | "Avant d'engager une action civile devant un tribunal, vous devez, sauf exception, passer par une procédure de conciliation." | The Tribunal d'instance page alone has 3,808 words of guidance. |
| C4 | VERIFIED | `…/legislation-et-jurisprudence/jurisprudence` → `http://jurisprudence.ne.ch/` (2,173 B JS redirect) → `omnisapi.dll…Schema=NE_WEB` | 200 "Jurisprudence du Tribunal cantonal", 20,248 B (Omnis). Also jurisprudenceadm.ne.ch | "Cette base de données juridiques contient les principaux arrêts, pour la plupart non publiés…" | opencaselaw ne_gerichte 10,817 (latest 2026-08-20); ne_jurisprudence_adm 1,648 (latest 2026-02-05). Not stale. |
| C5 | VERIFIED | Tribunal d'instance (Chambre de conciliation); `…/droits-et-justice/droit-du-bail` | 200 (551,660 B); 200 | "Toute contestation doit être adressée aux chambres de conciliation des tribunaux régionaux selon la situation de l'immeuble." | No fee text on the page (grep: 0 hits); LTFrais art. 11 sets the fees. |
| G1 | VERIFIED | `/themes/vie-quotidienne-et-famille/animaux/soccuper-danimaux`; `/autorites/ddte/scav` | 200 (main content 102 KB, 5,572 words); 200 | "Toute nouvelle ou tout nouveau propriétaire d'un chien depuis le 1er janvier 2021 domicilié dans le canton…" (course "entre 300 et 400 francs") | Law **636.20** LChiens ("Art. 12 1Il est interdit de laisser errer un chien."), 636.201, 636.21. The dog tax is communal. Only 1 sitemap URL contains "chien", so a topic grep alone would miss this page. |
| G2 | VERIFIED | `/sites/default/files/2025-10/SCCO_I754_InstructionsGenerales_PP.pdf` (via `/themes/impots/documents-et-liens-utiles`) | 200 PDF, 2,717,944 B, 57 pages, text layer | "Montant à reporter sous chiffre 6.12, mais au maximum Fr. 5000.–" | 36 /themes/impots/ URLs; more than 19 SCCO_*.pdf files listed. Law 631.0 (not in law_hits). |
| G3 | VERIFIED | `/themes/scolarite-et-formation/calendrier-et-vacances-scolaires` (+ PDF `CalendrierScolaire2019-2030.pdf`) | 200 (main content 15 KB) | "Vacances d'automne Du lundi 5 octobre au vendredi 16 octobre 2026" | **One cantonal calendar** "valable pour l'enseignement obligatoire". The page does not name the deciding body. PDF not fetched. |
| G4 | VERIFIED | `https://www.scan-ne.ch/`; `/conducteur/permis/obtenir-un-permis/voiture-18-ans/`; `/vehicule/taxe/calculer-votre-taxe-automobile-et-remorque/`; fees RSN **761.43** | 200 TYPO3, 105,019 B, 310 links; 200; 200; 761.43 PDF 200, 12 pages, text layer | "En 2026, les voitures de tourisme neuchâteloises seront toujours taxées selon leurs émissions de CO₂ et leur âge"; 761.43: "Plaques de contrôle, en prêt, la paire … 50" | SCAN pages show no CHF fees. No sitemap (404); robots.txt empty. |
| D1 | VERIFIED | `/communes-neuchateloises` | 200: **24** communes by region, each linked to its website | "Région Littoral Boudry…" → `http://www.boudry.ch/` | Matches commune_sites.csv (24 NE rows). Destination: resolver. |
| D2 | VERIFIED (chancellery) / BLOCKED (gazette) | `/autorites/chan`; `/themes/etat-droit-et-finances/publications/feuille-officielle` | 200 "Chancellerie d'État \| ne.ch"; 200 | "Abonnez-vous via le Guichet unique pour 53 francs par an, ou achetez un numéro individuel pour 4 francs." | blocked:paywall (Guichet unique login). Law 150.20. |

**Site recipe (NE)**
- www.ne.ch: Drupal. robots.txt: `Sitemap: https://www.ne.ch/sitemap.xml`, 34 Disallow, no crawl-delay.
- Fix: fetch `https://www.ne.ch/sitemap.xml?page=1` and `?page=2`, then replace `http://ne-prod-admin.ne.ch` with `https://www.ne.ch`.
- Pages are 490–600 KB each; take the content from `<main>`.
- Law: rsn.ne.ch. Decisions: jurisprudence.ne.ch (Omnis). Road: scan-ne.ch (TYPO3, no sitemap).

**YAML (NE)**
```yaml
# ne-justice | official_info | CH-NE | category missing: courts
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.ne.ch/themes/etat-droit-et-finances/droits-et-justice, https://www.ne.ch/autorites/autorites-judiciaires], path_allowlist: [/themes/etat-droit-et-finances/droits-et-justice/, /autorites/autorites-judiciaires], language: fr}
---
# ne-dogs | dogs
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.ne.ch/themes/vie-quotidienne-et-famille/animaux/soccuper-danimaux], path_allowlist: [/themes/vie-quotidienne-et-famille/animaux/], language: fr}
---
# ne-tax-instructions | taxes
fetch_strategy: pdf
fetch_config: {urls: [https://www.ne.ch/sites/default/files/2025-10/SCCO_I754_InstructionsGenerales_PP.pdf], language: fr}
---
# ne-holidays | schools
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.ne.ch/themes/scolarite-et-formation/calendrier-et-vacances-scolaires], path_allowlist: [/themes/scolarite-et-formation/calendrier-et-vacances-scolaires], language: fr}
---
# ne-scan | transport
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.scan-ne.ch/], path_allowlist: [/conducteur/, /vehicule/], language: fr}
```

**Claim checks (NE)**
- `/autorites/PJ/{TC, frais, themes, jurisprudence, TR}`: **Wrong** (404). Correct: C1/C2/C3/C4 above.
- The .aspx pages for dogs, tax, school and communes: **Wrong** (404). Correct: G1/G2/G3/D1.
- `scan-ne.ch`: **Confirmed**.
- Chancellery `/autorites/CE/CH/Pages/accueil.aspx`: **Partly**, it redirects to `/autorites/conseil-etat` (the Council of State, not the chancellery). Correct is `/autorites/chan`.

---

## GE (base `https://www.ge.ch`; courts on `https://justice.ge.ch`)
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | `https://justice.ge.ch/fr` | 200 "Page d'accueil \| Pouvoir judiciaire", 115,403 B, 192 links (Drupal) | "Tribunal civil Tribunal de première instance Tribunal des baux et loyers Commission de conciliation…" | The sitemap (953 URLs) writes `https://justice.ge.ch//fr/…`; both forms answer 200. |
| C2 | VERIFIED | `https://justice.ge.ch/fr/contenu/frais-dune-procedure-civile`; **RSG E 1 05.10** `https://silgeneve.ch/legis/program/books/RSG/pdf/rsg_e1_05p10.pdf` | 200, 1,626 words; PDF 200, 541,122 B, 10 pages, text layer | "Ces émoluments font donc en principe l'objet d'une avance de frais, exigée en début de procédure."; RTFMC art. 15: "jusqu'à 30 000 francs 100 francs" | law_hits only had E 5 10.03 and E 6 15.06. |
| C3 | VERIFIED | `/fr/theme/{adoption, faillite, mainlevees, successions, assistance-juridique, separation-et-divorce, protection-de-ladulte, protection-de-lenfant, consignation-des-loyers, conflit-en-droit-du-travail, …}` | Sitemap: **14** FR theme pages + 137 /fr/contenu/. separation-et-divorce: 200, 205,917 B, 6,115 words | "En cas de séparation conflictuelle, vous pouvez saisir de manière unilatérale le tribunal afin de demander des mesures protectrices de l'union conjugale." | 1 of the 14 themes was fetched. |
| C4 | VERIFIED | `/fr/contenu/jurisprudence` → `https://justice.ge.ch/apps/decis/fr/capj/search` (+`/apps/decis/fr/jtp/search`) | 200; 200 "Décisions \| Cour d'appel du Pouvoir judiciaire", 100,069 B, server HTML form | Link label: "Jurisprudence (y compris les décisions rendues par la Cour d'appel de la magistrature)" | opencaselaw ge_gerichte 170,523 (latest 2026-09-14). Not stale. |
| C5 | VERIFIED | `/fr/contenu/commission-de-conciliation-en-matiere-de-baux-et-loyers` | 200, 154,009 B, 2,742 words | "La procédure devant la Commission de conciliation en matière de baux et loyers est gratuite." | Law E 3 15. |
| G1 | VERIFIED (cited: g5 D17 + live) | `/detenir-chien/regles-promener-son-chien` | 200, 598 words | "Toujours en laisse : Dans les localités et sur les voies de circulation…" | 19 dog URLs in the sitemap. Law M 3 45 / M 3 45.01. |
| G2 | VERIFIED (cited: g5 U10 + live) | `https://www.getax.ch/support/guide/declaration2025/` | 200 "Table des matières", 351 links | "Guide de la déclaration d'impôts des personnes physiques 2025" | g5 counted 98 chapter pages (not re-counted). Law D 3 08. |
| G3 | VERIFIED (cited: g5 D19 + live) | `/vacances-scolaires-jours-feries`; ICS `/document/39777/telecharger` | 200; ICS 200 text/calendar, 391,179 B, 10 VEVENTs | "Le Conseil d'Etat fixe le calendrier des vacances scolaires…"; `DTSTART;VALUE=DATE:20270826` "Rentrée scolaire" | **Canton sets them.** |
| G4 | VERIFIED (g5 D18 never fetched these; I did) | `/organisation/office-cantonal-vehicules-ocv`; `/immatriculer-vehicule-obtenir-carte-grise`; fee PDF `/document/24460/telecharger` | 200; 200 (728 w); PDF 200, 2 pages, text layer | "a) véhicules automobiles légers 80 francs b) remorques légères 80 francs c) véhicules automobiles lourds 240 francs" | Law H 1 05.08. |
| D1 | VERIFIED | `https://statistique.ge.ch/communes/welcome.asp` (found through WebSearch site:ge.ch) | 200, 184,270 B; **45** commune ids (`apercu.asp?commune=1…45`) | "liste des communes Aire-la-Ville Anières Avully…" | The ids are cantonal 1–45, not BFS numbers; no links to commune websites. `/dossier/communes-genevoises` re-checked: 403. |
| D2 | VERIFIED / BLOCKED | `/organisation/chancellerie-etat`; FAO `https://fao.ge.ch` | 200 "Chancellerie d' Etat \| ge.ch", 1,084 words; fao.ge.ch lands on `/captcha?baseURL=/` ("VERIFICATION PAR CAPTCHA") | "La chancellerie d'Etat assume les fonctions d'état-major du gouvernement cantonal." | blocked:captcha, although ge.ch says the FAO "est disponible gratuitement en ligne". Law B 2 10. |

**Site recipe (GE)**
- www.ge.ch: Drupal. robots.txt: `Sitemap: https://www.ge.ch/sitemap.xml` (27,977 URLs), 24 Disallow.
- justice.ge.ch: Drupal, 953-URL sitemap with double slashes that must be normalized, 27 Disallow.
- Other hosts: getax.ch, silgeneve.ch (law PDFs), statistique.ge.ch (ASP, iso-8859-1), fao.ge.ch (CAPTCHA).

**YAML (GE)**, beyond g5's ge-dogs, getax, OCV and ICS entries:
```yaml
# ge-justice-themes | official_info | CH-GE | category missing: courts
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://justice.ge.ch/fr/themes], path_allowlist: [/fr/theme/, /fr/contenu/frais-, /fr/contenu/commission-de-conciliation, /fr/contenu/tribunal-], language: fr}
---
# ge-ocv-fees | official_info | CH-GE | transport
fetch_strategy: pdf
fetch_config: {urls: [https://www.ge.ch/document/24460/telecharger], language: fr}
```

**Claim checks (GE)**
- justice.ge.ch/fr/{cour-de-justice, frais-et-emoluments, demarches, jurisprudence, chambre-administrative, tribunal-de-premiere-instance}: **Wrong** (404). Correct: `/fr/contenu/cour-de-justice` (sitemap), `/fr/contenu/frais-dune-procedure-civile`, `/fr/themes`, `/fr/contenu/jurisprudence`, `/fr/contenu/tribunal-civil` (sitemap).
- Communes `/dossier/communes-genevoises`: **Wrong** (403); correct is statistique.ge.ch.
- Chancellery: **Confirmed**.

---

## JU (base `https://www.jura.ch/fr/Autorites`)
| Cell | Status | URL | Evidence | Sample | Notes |
|---|---|---|---|---|---|
| C1 | VERIFIED | `/JUST/La-justice-jurassienne.html`; `/JUST/Instances-judiciaires/Tribunal-cantonal/Tribunal-cantonal.html` | 200 "Canton du Jura - Instances judiciaires…", 68,853 B; 200, 888 words | "Toutes les instances judiciaires, à l'exception du Tribunal des mineurs, siègent à Porrentruy, au Château…" | |
| C2 | VERIFIED | TC circulars `/JUST/Instances-judiciaires/Tribunal-cantonal/Circulaires/Circulaires-du-Tribunal-cantonal-et-de-ses-sections.html` → "Tarif des avances, émoluments et débours" PDF; **RSJU 176.511** | Circulars: 200, 14 PDFs. Tariff PDF: 200, 280,359 B, 5 pages, text layer ("état au 9 juin 2016"). 176.511 PDF: 200, 10 pages | "4.5 Conciliation devant le président de la Cour civile … en principe 1'000 points"; 176.511: "de 50 à 5 000 francs : de 15 à 300 points"; Domaine civil: "…contre paiement d'un émolument de 20 francs" | Fees are in points, with the point value indexed yearly. Ladder: sitemap grep (8 hits, none a court-fee page), then WebSearch, which found the tariff. |
| C3 | VERIFIED | `/JUST/Domaines-du-droit/Droit-civil/Domaine-civil.html`, `/JUST/Assistance-judiciaire/…`, `/JUST/Renseignements-juridiques/…`, TPI pages | Sitemap: **50** URLs under /JUST/; all fetched pages 200, 65–73 KB | "L'assistance judiciaire permet à une personne qui ne dispose pas des moyens financiers suffisants d'être dispensée d'avancer les frais de la procédure…" | Content sits after the "Autorités »" breadcrumb. |
| C4 | VERIFIED | `…/Tribunal-cantonal/Jurisprudence/Jurisprudence-du-Tribunal-cantonal.html` → `https://jurisprudence.jura.ch` | 200 (the title reads "Cour administrative", a mismatch); search 200, 19,593 B, 0 links, JS app (TribunaVTPlus.css in the HTML) | "La jurisprudence du Tribunal cantonal est actuellement disponible sur https://jurisprudence.jura.ch" | opencaselaw ju_gerichte 1,201 (latest 2026-09-03). Not stale. |
| C5 | VERIFIED | `…/Tribunal-des-baux-a-loyer-et-a-ferme/Tribunal-des-baux-a-loyer-et-a-ferme.html`; `…/Droit-du-travail-et-du-bail/…` | 200 (881 w); 200 (663 w) | "Toute requête doit être introduite au préalable devant la Commission de conciliation en matière de bail…" | Fee: 1,000 points (C2). Laws 182.351, 182.35, 182.34, 824.21. |
| G1 | VERIFIED | `/Administration/DES/SCAV/Section-affaires-veterinaires/Chiens/Chiens.html` | 200, 84,207 B, 1,438 words | "…même si cela n'est pas oligatoire, le SCAV recommande aux personnes qui acquièrent un chien pour la première fois de suivre un cours facultatif…" | Law 645.1 (dog tax) + 645.11. A title search of all 855 active JU texts found no dog-keeping law. |
| G2 | VERIFIED | `/Administration/DFI/CTR/Formulaires/Formulaires-personnes-physiques/Annee-fiscale-2025/Annee-fiscale-2025.html` → `Guide-general-2025.pdf` | 200 (717 w); PDF 200, 1,549,163 B, 56 pages, 155,405 characters of text | "Revenu réalisé Fr. 15'000.- ./. déduction forfaitaire (20% max. Fr. 4'100.-) Fr. 3'000.-" | **The 2025 page is not in the jura.ch sitemap** (0 hits); WebSearch found it. The new DFI/Contributions-NEU pages say "En construction", and its forms page still lists Guide 2019. Law 641.11. |
| G3 | VERIFIED | `/Administration/DFNS/SEN/Vacances-scolaires/Vacances-scolaires.html` + arrêté PDF 2025–2028 | 200 (720 w); PDF 200, 2 pages, text layer | "Vacances d'automne Du lundi 5 octobre 2026 au vendredi 16 octobre 2026"; arrêté: "II s'applique à l'ensemble des écoles publiques." | **The Gouvernement (canton) sets them.** The page mentions an ICS file, but there is no .ics href in the server HTML. |
| G4 | VERIFIED | `/Administration/DEC/OVJ/Office-des-vehicules-OVJ.html`; `…/OVJ/Taxe-et-emoluments/Taxe-et-emoluments.html` | 200 (2,273 w); 200 (2,597 w) | "Taxe maximale = 1'015 francs par année." | 31 OVJ URLs in the sitemap. Laws 741.11, 741.611. |
| D1 | VERIFIED | `/Administration/DFI/COM/Les-communes-jurassiennes/Les-communes-jurassiennes.html` | 200, 88,012 B, with links to commune websites | "Le Canton du Jura compte 51 communes réparties dans quatre districts : Delémont, Franches-Montagnes, Moutier et Porrentruy." | 51 matches commune_sites.csv. The page also lists bourgeoisies. |
| D2 | VERIFIED | `/Administration/CHA/SCH/Secretariat-de-la-Chancellerie-d-Etat.html`; JO `https://rsju.jura.ch/fr/Sommaire/Journal-officiel.html` | 200; 2026 page: 33 issue PDFs; No 33 PDF 200, 13 pages, text layer | "No 33 – Jeudi 17 septembre 2026 … paraît chaque semaine, le jeudi." | Free weekly PDFs. Law 170.513. |

**Site recipe (JU)**
- www.jura.ch: files are served as `/Htdocs/Files/v/<sha256>.pdf/<name>.pdf?download=1` (CMS vendor unknown). robots.txt: `Sitemap: …/sitemap/Francais_fr_fr_z1_sitemap.xml` (7,805 URLs), 1 Disallow. **The sitemap is incomplete**, so crawl links as well.
- rsju.jura.ch holds law and the JO. jurisprudence.jura.ch is a Tribuna JS app.

**YAML (JU)**
```yaml
# ju-justice | official_info | CH-JU | category missing: courts   (deny …/Revue-jurassienne-de-jurisprudence/20xx/)
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/JUST/La-justice-jurassienne.html], path_allowlist: [/fr/Autorites/JUST/], language: fr}
---
# ju-court-tariff
fetch_strategy: pdf
fetch_config: {urls: ["https://www.jura.ch/Htdocs/Files/v/ff78dbf9136f8cab273ea6f4352309fbc0f1d77137ab65c0610a20db98ee89c8.pdf/avances_emoluments_debours_juin-2016.pdf?download=1"], language: fr}
---
# ju-dogs | dogs
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/Administration/DES/SCAV/Section-affaires-veterinaires/Chiens/Chiens.html], path_allowlist: [/Section-affaires-veterinaires/Chiens/], language: fr}
---
# ju-tax-guide | taxes
fetch_strategy: pdf
fetch_config: {urls: ["https://www.jura.ch/Htdocs/Files/v/81cc78891c5f1637d43c7c3fa46061ce931b57ab3a48c0e43a09d8c662c2395d.pdf/Guide-general-2025.pdf?download=1"], language: fr}
---
# ju-holidays | schools
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/Administration/DFNS/SEN/Vacances-scolaires/Vacances-scolaires.html], path_allowlist: [/DFNS/SEN/Vacances-scolaires/], language: fr}
---
# ju-ovj | transport
fetch_strategy: html_crawl
fetch_config: {start_paths: [https://www.jura.ch/fr/Autorites/Administration/DEC/OVJ/Office-des-vehicules-OVJ.html], path_allowlist: [/Administration/DEC/OVJ/], language: fr}
```

**Claim checks (JU)**
- `/pju/*.html`: **Wrong** (404).
- The department codes the AI used are wrong: DEN should be DES for dogs and DEC for the road office, DFCS should be DFNS, DFN/SCOM should be DFI/COM, and DFN/IMP should be DFI/CTR. All of those AI links were 404; the correct URLs are in the grid.
- Chancellery `/CHA/Chancellerie-d-Etat.html`: **Wrong** (404); correct is `/CHA/SCH/Secretariat-de-la-Chancellerie-d-Etat.html`.

---

## L1 city law (all were `official_info`; all 10 AI city links were 404 in the pre-check)
| City (BFS) | Status | Real URL | Platform / format | Texts | Dogs / waste / parking | Sample |
|---|---|---|---|---|---|---|
| Lausanne (5586) | VERIFIED | `https://www.lausanne.ch/apps/actualites/index_recueil.php` (the `/officiel/recueil-systematique-du-droit-communal.html` page meta-refreshes to it) | Custom PHP app, server HTML (941,968 B); each text links to `Next/serve.php?id=N&kind=recueil`, a PDF with a text layer (id=7: 34 pages) | **193** ("193 résultats"; 193 distinct ids) | Dogs yes (503.1, 503.2), waste yes (830.1–830.x, 7 texts), parking yes (710.1–710.3) | "100.1 Règlement du Conseil communal de Lausanne – RCCL Adopté le: 12.11.1985 – En vigueur depuis le: 01.01.1986" |
| Neuchâtel (6458) | VERIFIED | `https://www.neuchatelville.ch/votre-commune/reglementation` + `/anciennes-communes/reglementation-{neuchatel, peseux, cc, valangin}` | TYPO3 fileadmin list of PDFs (text layer, e.g. the Règlement général, 50 pages) | **79** distinct PDFs on the current page; the former Neuchâtel page has 239 PDF links | Waste yes (705, 705.1, 705.10); parking yes (810, 810.1); dogs: 12.21 "Arrêté concernant les modalités d'accès des chiens aux espaces publics, du 15 juin 2020" (**scanned**: 9 pages, 1 character of text) | "100 Règlement général de la Ville de Neuchâtel, du 7 juin 2021 – Dernière modification: 16 février 2026" |
| La Chaux-de-Fonds (6421) | VERIFIED (through the API) | The page `/rapports-et-reglements/reglementation` is a JS shell ("Chargement en cours..."). Data: `POST https://www.chaux-de-fonds.ch/Api/Page.svc/detail` with `{"page":"/rapports-et-reglements/reglementation/<theme>"}` | JSON `{DetailResult:{Content,Id,LastModified,Title,Url,WebParts}}`; PDFs at `/rapports-et-reglements/reglementation/Documents/<nr>.pdf` (50_10.pdf: 20 pages, text layer) | **175** PDFs across 9 themes | Dogs: 41.13 (dog tax); waste: 62.13, 62.130, 62.131, 62.12; parking: 63.101, 63.105 | "50.10 Règlement du Conseil général de la Police, du 28 novembre 2011" |
| Genève Ville (6621) | VERIFIED | `https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux?page=0…24` | Drupal listing; each `/administration-municipale/reglements-municipaux/lc<nr>-<slug>` serves the PDF directly (lc21911: 18 pages, text layer) | **246** texts (LC 21 100–900) | Waste yes (LC 21 911); parking yes (LC 21 154.1 + annexes); dogs none (a cantonal matter) | "Règlement sur la gestion des déchets LC 21 911 Adopté par le Conseil administratif le 25 janvier 2024 Entrée en vigueur le 1er février 2024" |
| Vernier (6643) | VERIFIED (listing) / Drupal down during the run | `https://www.vernier.ch/administration-et-autorites/reglements-communaux` → `/administration-et-autorites/publications?category=38&profile=_all` | Drupal. The listing answered 200 at first (69,510 B, "Tous les règlements"). From 13:39 to 13:57 CEST every Drupal page, including the home page, answered 500. Static `/sites/default/files/*.pdf` files still answered 200 | **52** regulation pages in the sitemap (of 127 publications) | Waste yes (3); parking yes (1); dogs no | PDF RSRV 722.0: "…Collecte, transport et élimination des déchets Du 30 août 2011 (État au 3 juin 2019)" (9 pages, text layer) |

Destinations: Lausanne, Neuchâtel, Genève Ville and Vernier → `fetcher:pdf-index`. La Chaux-de-Fonds → new `fetcher:post-json-index`. Neuchâtel's dog arrêté → `fetcher:ocr-pdf`.

---

## Cross-canton
**New fetcher classes needed**
- **`sitemap-crawl`** with three options: rewrite the host of child sitemaps (NE), extract only `<main>` (NE pages are about 500 KB), and deny patterns (FR court archives, JU case-law review archive). It also needs link-following, because the jura.ch sitemap misses pages. Covers all 5 cantonal portals plus justice.ge.ch and ocn.ch.
- **`ics`**: FR (3 calendars × 4 school years, about 12 files) and GE (cited: g5).
- **`pdf-index`**:
  - City law in 4 cities (Lausanne 193, Genève 246 with pagination, Neuchâtel 79 + former communes, Vernier 52).
  - JU official journal year pages (33 issues in 2026) and JU court circulars (14).
  - Yearly tax PDFs (VD 21001_<year>, NE SCCO_*, FR /document/<id>).
- **`post-json-index`** (new): La Chaux-de-Fonds (175 PDFs). Whether other towns use the same backend is not checked.
- **`xlsx` / resolver**: FR communes XLSX (119 rows). The VD commune list is an HTML table (300 rows).
- **`ocr-pdf`**: Neuchâtel dog arrêté 12.21. FR holiday PDFs have a garbled text layer, but the ICS files replace them.
- **Gazettes:** the Amtsblattportal XML fetcher is not enough for these 5 cantons, since their tenants are external and carry only debt/bankruptcy rubrics.
  - fo.fr.ch and faovd.ch can be crawled with `html_crawl`.
  - The JU journal needs `pdf-index`.
  - Category missing: official notices.
- **Law platforms:** `lexwork` (FR), `vd-blv`, `ne-rsn`, `ju-rsju`, `lexfind-enum` (GE silgeneve). All fee and dog-law URLs above resolved through them.

**Blocked or not ingestible**
- GE FAO (fao.ge.ch): CAPTCHA.
- NE Feuille officielle: paid subscription.
- Vernier: Drupal answered 500 from 13:39 to 13:57 CEST (possibly temporary).
- ge.ch/dossier/communes-genevoises: 403.
- La Chaux-de-Fonds: the HTML is a JS shell, and the PDF URLs indexed by search engines are stale (10_10.pdf → 500, 21_10.pdf → 404). The JSON API works around both.
- The Tribuna decision apps (publicationtc.fr.ch, jurisprudence.jura.ch) are JS-only. opencaselaw already covers them.
- JU holiday ICS: mentioned on the page, but no link exists.
- scan-ne.ch: no sitemap, and no fee amounts on the site.

**The 5 best finds**
1. NE sitemap recovery: 8,518 URLs by rewriting the internal child-sitemap host, which fills every NE cell.
2. Lausanne's law collection app: 193 texts, each with a number, adoption and in-force dates, and a text-layer PDF, covering dogs, waste and parking.
3. Ville de Genève: 246 regulation PDFs with LC numbers and in-force dates, from a plain paginated listing.
4. La Chaux-de-Fonds `POST /Api/Page.svc/detail`: 175 regulation PDFs hidden behind a JS page.
5. FR: school-holiday ICS files per region, plus the Tribunal cantonal page that lists the latest rulings with direct PDF links.

**Traps to add to the brief**
- The jura.ch sitemap is incomplete (the 2025 tax forms page is missing).
- justice.ge.ch sitemap URLs contain `//`.
- Amtsblattportal ignores `tenants=`; use `tenant=`.
- The JU case-law page's `<title>` says "Cour administrative".
- fr.ch `/document/<id>` links redirect to dated files carrying a changing `?v=` parameter.

**Sources used for WebSearch steps:** [Statistique Genève, 45 communes](https://statistique.ge.ch/communes/welcome.asp) · [La Chaux-de-Fonds regulations](https://www.chaux-de-fonds.ch/rapports-et-reglements/reglementation) · [JU tax year 2025](https://www.jura.ch/fr/Autorites/Administration/DFI/CTR/Formulaires/Formulaires-personnes-physiques/Annee-fiscale-2025/Annee-fiscale-2025.html) · [JU court fee tariff](https://www.jura.ch/Htdocs/Files/v/ff78dbf9136f8cab273ea6f4352309fbc0f1d77137ab65c0610a20db98ee89c8.pdf/avances_emoluments_debours_juin-2016.pdf?download=1) · [Vernier waste regulation PDF](https://www.vernier.ch/sites/default/files/2022-11/RSRV_-_722.0_Reglement_sur_la_collecte_le_transport_et_lelimination_des_dechets_-_29.05.2019.pdf). Each was confirmed with curl before it went into a cell.