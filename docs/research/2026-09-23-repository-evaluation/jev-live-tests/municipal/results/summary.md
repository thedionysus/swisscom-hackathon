# Municipal / cantonal Jev test

Label files complete: True (missing: [])

## Labeller agreement

- Junk flag: Cohen's κ = 1.00; agree on 75/75 chunks
- Primary topics per (chunk, category): Cohen's κ = 0.78 over 750 pairs
- Gold topic pairs: 11 positive, 704 negative, 35 ambiguous (excluded)
- Chunks with ≥ 2 gold topics: 0; with exactly 1: 11; with none: 64; gold junk: 35 of 75 agreed

## M1: topics (original-language text; rules fixed in advance)

Chunks answered: 75/75

| subset | rule | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|
| all (n=75) | R1 | 7 | 17 | 4 | 0.29 | 0.64 |
| all (n=75) | R2 | 9 | 22 | 2 | 0.29 | 0.82 |
| all (n=75) | 0.3 | 6 | 6 | 5 | 0.50 | 0.55 |
| all (n=75) | 0.5 | 6 | 2 | 5 | 0.75 | 0.55 |
| random (n=60) | R1 | 5 | 12 | 1 | 0.29 | 0.83 |
| random (n=60) | R2 | 5 | 17 | 1 | 0.23 | 0.83 |
| random (n=60) | 0.3 | 4 | 4 | 2 | 0.50 | 0.67 |
| random (n=60) | 0.5 | 4 | 1 | 2 | 0.80 | 0.67 |
| targeted (n=15) | R1 | 2 | 5 | 3 | 0.29 | 0.40 |
| targeted (n=15) | R2 | 4 | 5 | 1 | 0.44 | 0.80 |
| targeted (n=15) | 0.3 | 2 | 2 | 3 | 0.50 | 0.40 |
| targeted (n=15) | 0.5 | 2 | 1 | 3 | 0.67 | 0.40 |
| German (n=49) | R1 | 1 | 14 | 4 | 0.07 | 0.20 |
| German (n=49) | R2 | 3 | 19 | 2 | 0.14 | 0.60 |
| German (n=49) | 0.3 | 0 | 3 | 5 | 0.00 | 0.00 |
| German (n=49) | 0.5 | 0 | 1 | 5 | 0.00 | 0.00 |
| French (n=26) | R1 | 6 | 3 | 0 | 0.67 | 1.00 |
| French (n=26) | R2 | 6 | 3 | 0 | 0.67 | 1.00 |
| French (n=26) | 0.3 | 6 | 3 | 0 | 0.67 | 1.00 |
| French (n=26) | 0.5 | 6 | 1 | 0 | 0.86 | 1.00 |
| ≥2 gold topics (n=0) | R1 | 0 | 0 | 0 | — | — |
| ≥2 gold topics (n=0) | R2 | 0 | 0 | 0 | — | — |
| ≥2 gold topics (n=0) | 0.3 | 0 | 0 | 0 | — | — |
| ≥2 gold topics (n=0) | 0.5 | 0 | 0 | 0 | — | — |

Top category is a gold topic: 9/11 = 0.82 (95% CI 0.52–0.95)
Gold-junk chunks given a topic under R1: 22/35

## M2: junk screening (substance < 0.3 ⇒ junk; jev-mcp wording)

Chunks with agreed junk label: 75 (35 junk, 40 content)
- Junk caught (recall): 6/35 = 0.17 (95% CI 0.08–0.33)
- Flagged junk that is junk (precision): 6/6 = 1.00 (95% CI 0.61–1.00)
- **Content wrongly flagged as junk** (the costly error): 0/40 = 0.00 (95% CI -0.00–0.09)
- Substance score separates content from junk: AUC 0.98; junk median 0.66, content median 0.98

## M3: in-force date of Basel-Stadt laws (gold = portal API `enactment`)

Correct: 12/12 = 1.00 (95% CI 0.76–1.00); gold among candidates in 11/12

| SR | gold | Jev picked | confidence | correct | #candidates |
|---|---|---|---|---|---|
| 365.100 | 2007-02-01 | 01.02.2007 | 0.5 | True | 11 |
| 365.110 | 2007-07-01 | 1. Juli 2007 | 0.54 | True | 19 |
| 300.100 | 2012-01-01 | 1. 1. 2012 | 0.61 | True | 20 |
| 310.170 | 2013-10-27 | 27.10.2013 | 0.75 | True | 15 |
| 410.120 | 2014-08-18 | 18. August 2014 | 0.55 | True | 5 |
| 410.700 | 2013-08-12 | 12. August 2013 | 0.47 | True | 20 |
| 510.100 | 1997-07-01 | 01.07.1997 | 0.99 | True | 17 |
| 640.100 | 2001-01-01 | none_of_them | 0.88 | True | 17 |
| 650.500 | 1967-01-01 | 1. Januar 1967 | 0.58 | True | 14 |
| 730.320 | 2017-01-29 | 29. 1. 2017 | 0.38 | True | 4 |
| 786.100 | 2026-01-01 | 1. Januar 2026 | 0.59 | True | 6 |
| 911.600 | 2002-01-01 | 01.01.2002 | 0.67 | True | 10 |

## Operations

{"http_attempts": 94, "status_counts": {"200": 87, "429": 4, "503": 3}, "latency_ms_median": 385, "tokens_in": 116764, "cost_reported": ["0"]}

## Human spot-check (10 chunks, seed 424242, fixed in advance)

**stadt_zuerich#24** (de, https://www.stadt-zuerich.ch/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung/1/101.html)
> 101 Gemeindeordnung — Seite vorlesen  101 Gemeindeordnung

- Labeller A: — (acceptable —), junk True
- Labeller B: — (acceptable —), junk True
- Jev: housing 0.18; substance 0.12

**stadt_zuerich#19** (de, https://www.stadt-zuerich.ch/de/stadtleben/sport-und-erholung.html)
> Sport und Erholung — Seite vorlesen  Sport und Erholung   Vielfältige Angebote für Bewegung und Erholung  Themen   Sport- und Badeanlagen Tennis, Zürifit, Laufen: Bewegen in der der Limmatstadt  Sport für Kinder und Jugendliche Kurse, Lager und Förderprogramme  Sport in meiner Umg

- Labeller A: — (acceptable ['hiking']), junk True
- Labeller B: — (acceptable —), junk True
- Jev: hiking 0.13, schools 0.10; substance 0.66

**stadt_zuerich#9** (de, https://www.stadt-zuerich.ch/de/mobilitaet/velo.html)
> Velo — Seite vorlesen  Velo   Mit dem Velo sicher und einfach durch Zürich  Themen   Velomassnahmen Laufende und abgeschlossene Massnahmen zur Veloförderung  Velovorzugsrouten Ein durchgehendes, sicheres und sichtbares Netz von Velovorzugsrouten  Sicher unterwegs Tip

- Labeller A: — (acceptable ['transport']), junk True
- Labeller B: — (acceptable —), junk True
- Jev: transport 0.96, parking 0.12; substance 0.57

**zh_ch#542** (de, https://www.zh.ch/de/umwelt-tiere/abfall-rohstoffe.html)
> Weiterführende Informationen > Links — * Massnahmenplan «Abfall- und Ressourcenwirtschaft» * Altlasten und belastete Standorte * Abfallanlagen

- Labeller A: — (acceptable ['waste']), junk True
- Labeller B: — (acceptable —), junk True
- Jev: waste 0.28; substance 0.37

**stadt_zuerich#20** (de, https://www.stadt-zuerich.ch/de/stadtleben/stadtportraet.html)
> Stadtporträt — Seite vorlesen  Stadtporträt  Zahlen und Fakten, Stadtgeschichte und geografische Daten  Themen   Zürichs Geschichte Archive, Aufarbeitung und Vermittlung  Zürich digital Zürich 4D und Geodaten  Zürich in Zahlen Alle statistischen Zahlen und Fakten zur Stadt Z

- Labeller A: — (acceptable —), junk True
- Labeller B: — (acceptable —), junk True
- Jev: —; substance 0.31

**ge_ville#193** (fr, https://www.geneve.ch/themes/durabilite)
> Genève, ville durable >  — Voluntary Local Review - Examen Volontaire Local de la Ville de Genève (2025)  Une revue de la mise en œuvre de la durabilité en Ville de Genève.  **80 pages**  Consulter la publication Examen Volontaire Local (VLR) de la Ville de Genève (mars 2025)  Titre du 

- Labeller A: — (acceptable —), junk True
- Labeller B: — (acceptable —), junk True
- Jev: —; substance 0.61

**stadt_zuerich#15** (de, https://www.stadt-zuerich.ch/de/mobilitaet/planung.html)
> Mobilitätsplanung — Seite vorlesen  Mobilitätsplanung  Grundlagen und Strategien für eine zukunftsgerichtete Mobilität  Themen   Strategien Die Grundlagen für die Mobilität in der Stadt Zürich.  Tempo 30 Mehr Sicherheit und Lebensqualität, weniger Lärm.  Mobilität erleben Ein Ang

- Labeller A: — (acceptable ['transport']), junk True
- Labeller B: — (acceptable —), junk True
- Jev: transport 0.91; substance 0.75

**stadt_zuerich#13** (de, https://www.stadt-zuerich.ch/de/mobilitaet/parkieren.html)
> Parkieren — Seite vorlesen  Parkieren   Parkkarten, Zufahrtsbewilligungen und Parkplätze auf öffentlichem Grund  Themen   Parkbewilligungen Bezug von Parkscheiben und Parkbewilligungen  Zufahrtsbewilligungen Zufahrt zu Fahrverbotszonen für Firmen und Private  Parkhäuser Z

- Labeller A: — (acceptable ['parking']), junk True
- Labeller B: — (acceptable —), junk True
- Jev: parking 0.87, transport 0.86; substance 0.87

**zh_ch#932** (de, https://www.zh.ch/de/umwelt-tiere/tiere/haustiere-heimtiere/meldestelle-fuer-findeltiere.html)
> Kontakt > Meldestelle für Findeltiere > Telefon — +41 84 884 82 44  Telefon  Telefonisch erreichbar:    Montag bis Freitag,    10 bis 12 Uhr.

- Labeller A: — (acceptable ['dogs']), junk True
- Labeller B: — (acceptable —), junk True
- Jev: dogs 0.14; substance 0.96

**zh_ch#599** (de, https://www.zh.ch/de/umwelt-tiere/boden.html)
> Aufbau des Bodens > C-Horizont: Muttergestein — Graue Farbtöne, unverwittertes Gestein (Kies, Fels), von Bodenbildungsprozessen noch nicht erfasst  Ein gut entwickelter Boden besteht aus einer Matrix aus festen Bestandteilen wie Steine, Sand, Ton und Humus und aus einem Porensystem, in dem sich neben Wasser

- Labeller A: — (acceptable —), junk False
- Labeller B: — (acceptable —), junk False
- Jev: —; substance 0.98
