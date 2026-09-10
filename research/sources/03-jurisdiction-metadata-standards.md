# Standards, ontologies and identifier schemes for jurisdiction-, territory- and time-aware tagging of legal/official documents (Swiss focus)

## 1. Legislation identifiers: ELI, Fedlex/JOLux, ECLI

### ELI (European Legislation Identifier)
ELI is an FRBR-based ontology (Work = `eli:LegalResource`, Expression = `eli:LegalExpression`, Manifestation = `eli:Format`, plus `eli:LegalResourceSubdivision` for articles) with HTTP URIs built from a per-country template declared via `eli:uri_schema`. Ontology: http://data.europa.eu/eli/ontology. Technical guide: https://op.europa.eu/documents/2050822/2138819/ELI+-+A+Technical+Implementation+Guide.pdf/.

Properties useful for filtering/routing:

| Concern | ELI property | Range / vocabulary |
|---|---|---|
| Jurisdiction of origin | `eli:jurisdiction` (v1.1) | `eli:AdministrativeArea`; recommended values = EU ATU authority table |
| Territorial applicability | `eli:relevant_for` | `eli:AdministrativeArea` / ATU |
| Legal force | `eli:in_force` | `inForce`, `partiallyInForce`, `notInForce` |
| Dates | `eli:date_document`, `eli:date_publication`, `eli:first_date_entry_in_force`, `eli:date_no_longer_in_force`, `eli:date_applicability`, `eli:version_date` | xsd:date |
| Version | `eli:version`, `eli:consolidates` / `eli:consolidated_by`, `eli:amends`, `eli:repeals`, `eli:transposes`, `eli:based_on`/`basis_for` | Work/Expression links |
| Language | `eli:language` | EU Language authority table |
| Norm type (hierarchy proxy) | `eli:type_document` | `eli:ResourceType` |
| Enacting/competent body | `eli:passed_by`, `eli:responsibility_of` | `eli:Agent` |
| Subject | `eli:is_about` | SKOS concept, EuroVoc encouraged |

ELI v1.1 changelog: https://eur-lex.europa.eu/eli-register/news_item_9.html.

### Switzerland: Fedlex and JOLux
Fedlex publishes federal law with ELI URIs rooted at `https://fedlex.data.admin.ch/eli/` (e.g. `https://fedlex.data.admin.ch/eli/cc/1999/404` = SR 101 Federal Constitution). Sub-collections: `eli/cc` (SR, consolidated), `eli/oc` (AS), `eli/fga` (BBl), plus treaties and drafts. Human-readable form appends consolidation date and language: `https://www.fedlex.admin.ch/eli/cc/1999/404/20240101/de`. Sources: https://fedlex.data.admin.ch/, https://swiss.github.io/fedlex-jolux/introduction.html, https://github.com/swiss/fedlex-jolux.

Metadata in two models: ELI and JOLux (richer; shared with Luxembourg's Legilux). SPARQL: https://fedlex.data.admin.ch/sparqlendpoint. JOLux terms:
- Classes: `jolux:ConsolidationAbstract` (the abstract act), `jolux:Consolidation` (one dated consolidated version), `jolux:Draft`, `jolux:Act`, `jolux:Expression`.
- Temporal: `jolux:dateEntryInForce`, `jolux:dateApplicability`, `jolux:dateEndApplicability`, `jolux:inForceStatus` (`.../0` in force, `.../1` no longer published in SR, `.../3` no longer in force).
- Classification/hierarchy: `jolux:classifiedByTaxonomyEntry` -> SR legal taxonomy (`https://fedlex.data.admin.ch/vocabulary/legal-taxonomy/...`), `jolux:legalResourceGenre` and `jolux:typeDocument` (Bundesgesetz, Verordnung, Bundesbeschluss, cantonal constitution, treaty...), `jolux:isMemberOf`, `jolux:language`.
- The SR number itself is a hierarchy-by-subject code — https://www.fedlex.admin.ch/de/cc/explanations-cc. Fedlex ships ~40 controlled vocabularies as SKOS.

Gap: Fedlex covers federal law only (plus cantonal constitutions). Cantonal law lives in 26 separate collections with canton-specific systematic numbers (e.g. "ZH 554.5"); aggregators are LexFind and OpenCaseLaw. No canton publishes ELI URIs, so a Swiss retrieval system needs its own `{canton}/{systematic number}` identifier for cantonal norms.

### ECLI (court decisions)
`ECLI:[country]:[court]:[year]:[ordinal]` (https://e-justice.europa.eu/175/EN/european_case_law_identifier_ecli). Metadata is Dublin Core (`dcterms:coverage` for country, `dcterms:date`, `dcterms:language`, etc.). Switzerland is not an ECLI participant; Swiss decisions are cited by docket number ("2C_587/2021") and BGE/ATF/DTF references. OpenCaseLaw's schema is a good template: `decision_id = {court}_{docket_normalized}`, `court`, `canton` ("CH for federal, ZH/BE/GE... for cantonal"), `decision_date`, `language`.

## 2. Document markup standards

- **Akoma Ntoso / OASIS LegalDocML** (https://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part2-specs.html): `<meta>/<identification>` carries FRBR levels. `FRBRcountry` = ISO 3166-1 alpha-2; sub-national jurisdictions handled by naming convention (e.g. `/akn/ch-zh/...`); `FRBRauthor` = enacting body; `FRBRdate`. Temporal validity in `<lifecycle>` (event list) and `<temporalData>` (`timeInterval`). Naming convention: https://docs.oasis-open.org/legaldocml/akn-nc/v1.0/csprd01/akn-nc-v1.0-csprd01.html.
- **CEN MetaLex**: jurisdiction-neutral XML + OWL; mostly historical, superseded by ELI/AKN.
- **LKIF-Core**: conceptual vocabulary, no operable jurisdiction attachment at provision level.
- **LegalRuleML** (https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/legalruleml-core-spec-v1.0.html): explicitly models `appliesJurisdiction` and `appliesTemporalCharacteristics` on a `Context`, plus `Override` statements — the only one with first-class jurisdiction + time + defeasibility (relevant for lex specialis/posterior).

## 3. Web/catalog vocabularies

**schema.org/Legislation** (https://schema.org/Legislation) mirrors ELI: `legislationJurisdiction`, `jurisdiction`, `spatialCoverage`, `legislationLegalForce` (`InForce`, `NotInForce`, `PartiallyInForce`), `legislationDate`, `legislationDateOfApplicability`, `legislationDateVersion`, `temporalCoverage` (ISO 8601 interval, `2024-01-01/..`), `legislationType`, `legislationPassedBy`, `legislationIdentifier`, `legislationConsolidates`, `legislationAmends`, `legislationRepeals`, `inLanguage`. Pattern (https://sparna-git.github.io/legislation-schema.org-howto/): one node per base act and one per consolidated version.

**Dublin Core**: `dct:coverage` deprecated in DCAT-AP CH; use `dct:spatial` and `dct:temporal`.

**DCAT-AP CH 3.0** (https://dcat-ap.ch/releases/v3/3.0.0.html): `dct:spatial` 0..n, recommended values: LINDAS URIs (`https://ld.admin.ch/canton/1`, `https://ld.admin.ch/municipality/261`), EU Vocabularies, GeoNames fallback; `dct:temporal` mandatory for temporal references; `dcatap:applicableLegislation` (range `eli:LegalResource`) links a dataset to its legal basis via Fedlex ELI. opendata.swiss datasets are natively filterable by canton/commune URI.

## 4. Geographic identifiers for Swiss jurisdictions

| Scheme | Granularity | Form / example | Notes |
|---|---|---|---|
| ISO 3166-2:CH | canton | `CH-ZH`, `CH-BE` | 26 codes = plate abbreviations. eCH-0007 uses bare 2-letter `cantonAbbreviation` (+ `FL`) |
| BFS canton number | canton | 1 = ZH ... 26 = JU | used by LINDAS `ld.admin.ch/canton/N` |
| BFS Gemeindenummer | commune | 261 = Zürich | Amtliches Gemeindeverzeichnis, REST API https://www.agvchapp.bfs.admin.ch/de; ~2,100 communes, shrinking via mergers |
| eCH-0071 historicized register (histId) | commune-state | one histId per version of a commune | every merger/name change since 1848 is a mutation; needed for documents dated before a merger (https://www.ech.ch/de/ech/ech-0071/1.2.0) |
| LINDAS URIs | country/canton/district/commune | `https://ld.admin.ch/canton/4`, `/district/400`, `/municipality/1201` | `schema:identifier` (BFS no.), `schema:name`@de/fr/it/en, `schema:containsPlace`, `schema:containedInPlace`, `schema:validFrom`, `geo:hasGeometry`; geo.ld.admin.ch adds per-year versions (https://lindas.admin.ch/governance/URI-templates/) |
| NUTS/LAU | region/canton/commune | `CH01`...`CH07` NUTS2, 26 NUTS3 = cantons, LAU = BFS communes | for EU-style catalog interop, poor for legal routing |
| Wikidata | canton/commune | `P771` Swiss municipality code, `P300` ISO 3166-2, `P131` located-in | best hub for cross-linking labels in 4 languages |
| GeoNames | any | ADM1 = canton, ADM2 = district, ADM3 = commune | fallback |

How others do it:
- **EU**: Publications Office ATU authority list (`http://publications.europa.eu/resource/authority/atu`) is the value space for `eli:jurisdiction` and CPSV-AP `dct:spatial`; covers EU member states only, so Swiss sub-national units must come from LINDAS/ISO.
- **UK**: legislation.gov.uk's CLML puts `RestrictExtent` on any provision (`E`, `W`, `S`, `N.I.`, `E+W`, ...) alongside `RestrictStartDate`/`RestrictEndDate`; URI scheme encodes versions as dates (`/ukpga/1981/54/1999-09-27`) (https://legislation.github.io/clml-schema/). Provision-level extent + date pair is the cleanest model to copy for "applies in cantons X+Y from date D".
- **US**: Cornell LII organizes by jurisdiction path (`/uscode`, `/states/<state>`); no cross-jurisdiction identifier comparable to ELI.

## 5. Competence/authority and service vocabularies

- **CPSV-AP 3.2** (https://semiceu.github.io/CPSV-AP/releases/3.2.0/): `cv:PublicService` -> `cv:hasCompetentAuthority` (1..1, `cv:PublicOrganisation`), `dct:spatial` on both service and organisation, `cv:sector`, `cv:thematicArea`, `cv:isGroupedBy` -> `cv:LifeEvent`/`cv:BusinessEvent`, `cv:hasLegalResource` -> `eli:LegalResource`, `cv:hasChannel`. Namespace `http://data.europa.eu/m8g/`. This is the exact triple needed: (service, competent organisation, territory) plus legal basis.
- **Swiss eCH service standards**: eCH-0070 "Leistungsinventar CH" (Swiss-wide unique IDs and task-based classification for public services) — https://ech.ch/de/standards/60499. eCH-0007 (commune/canton codes), eCH-0071 (historicized commune register), eCH-0008 (countries).
- **LINDAS** hosts TERMDAT as linked data (5-language legal/administrative terminology, useful for synonym expansion), the canton/commune registers, and organisations (`https://ld.admin.ch/org/...`).
- **EuroVoc** is the ELI-recommended subject vocabulary; Fedlex uses its own SR legal taxonomy, so a crosswalk is needed.

## 6. Modelling hierarchy of norms and topic taxonomies

Norm hierarchy is not captured by any single off-the-shelf class; the practical pattern (MIREL D3.1 https://www.mirelproject.eu/publications/D3.1.pdf) is to derive it:
- **Lex superior**: rank = f(`eli:passed_by` agent level, `eli:type_document`). Encode a `level` enum {international, federal-constitution, federal-act, federal-ordinance, cantonal-constitution, cantonal-act, cantonal-ordinance, communal} and an `eli:based_on` chain (ordinance -> act -> constitution article).
- **Lex specialis**: `is_about` specificity comparison, or LegalRuleML `Override` statements.
- **Lex posterior**: `eli:date_document` / `jolux:dateApplicability` ordering within the same level.
- **Competence**: a CPSV-AP-style `(topic, level, territory) -> competent organisation` table; for Switzerland the federal/cantonal split is anchored in constitutional articles (BV art. 3, 42 ff.), so `eli:based_on` to the BV article is the machine-readable justification.

Public-sector topic taxonomies to reuse:
- **EU Single Digital Gateway, Regulation 2018/1724 Annex I** (https://www.legislation.gov.uk/eur/2018/1724/annex/I/adopted): citizens: Travel, Work and retirement, Vehicles, Residence, Education, Healthcare, Citizens' and family rights, Consumer rights, Personal data; businesses: Starting/running/closing a business, Employees, Taxes, Goods, Services, Funding, Public contracts, Health and safety.
- **GOV.UK topic taxonomy**: 21 top-level taxons, up to 5 levels, exposed via API (https://docs.publishing.service.gov.uk/manual/taxonomy.html).
- **Germany LeiKa/FIM**: ~5,000 services each with a 14-digit Leistungsschlüssel, designed to be independent of which level delivers; competence resolution is a separate XZuFi "Zuständigkeitsfinder" feed keyed by Amtlicher Gemeindeschlüssel (https://docs.fitko.de/fim/docs/leistungen_neu/fachkonzept/leistungskatalog/). This separation (service ID vs. competence-by-territory) is the model to copy.
- **Austria oesterreich.gv.at**: Lebenslagen-first structure.
- **Switzerland ch.ch**: topic tree in 5 languages, not exposed as API or SKOS; eCH-0070 task classification is the only formal Swiss topic scheme.

## Key takeaways

1. Use a compound territorial key: `country=CH`, `canton=BFS no./ISO 3166-2:CH`, `commune=BFS Gemeindenummer + eCH-0071 histId`. Resolve to LINDAS URIs because DCAT-AP CH, Wikidata P771 and geo.ld.admin.ch already converge there.
2. Copy legislation.gov.uk's provision-level `RestrictExtent` + `RestrictStartDate/EndDate` pattern: store `applies_to: [territory URIs]` and `valid_from/valid_to` on every chunk, populated for federal law from JOLux via Fedlex SPARQL.
3. Adopt ELI/schema.org property names as the metadata schema so Fedlex data drops in unchanged and cantonal/communal documents get equivalent fields; mint ELI-like URIs for cantonal law (`/eli/ch-zh/cc/554.5/...`).
4. Model hierarchy explicitly with a `level` enum plus `based_on` links; rank results by level and specificity.
5. For "which office handles X in commune Y", describe services in CPSV-AP and use SDG Annex I life events / eCH-0070 tasks as the topic axis; keep the service taxonomy separate from the competence-by-territory table.
6. Swiss caveats: no ECLI, no ELI outside Fedlex, no machine-readable ch.ch taxonomy, commune codes change yearly.
