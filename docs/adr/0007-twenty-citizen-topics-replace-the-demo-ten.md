---
status: accepted
date: 2026-09-23
---

# Twenty citizen-facing topics, modelled on ch.ch, replace the ten demo categories

The ten categories were chosen for a Zurich demo about dogs, waste and hiking. Once all of Fedlex and a dozen cantons are indexed, most content (employment law, pensions, residence permits, voting, marriage) fits none of them, and because topic is a hard filter an untagged chunk is invisible. Topics are assigned in the same model call that writes the chunk description, so choosing them before the encoding run costs nothing while changing them afterwards costs a second paid pass over the corpus. We adopted twenty multi-label topics shaped like the questions people ask, following the theme structure ch.ch already uses for official guidance, and for Fedlex a fixed mapping from SR number prefixes to topics serves as the starting guess that the model confirms or extends per article.

| id | Label | Covers | SR prior |
|---|---|---|---|
| `work` | Work and employment | Employment contracts, notice and termination, working hours, holidays, wages, unemployment | 220 (OR Art. 319–362), 822, 837 |
| `social_security` | Social security and pensions | AHV/IV, pension funds, family allowances, social assistance, disability | 83 (except 832), 85 |
| `health` | Health and health insurance | Compulsory health insurance, premiums and subsidies, doctors, hospitals, medicines, vaccinations, emergencies | 81 (except 814), 832 |
| `taxes` | Taxes | Income, wealth, municipal and church tax, VAT, tax returns, deductions | 64 |
| `housing` | Housing and renting | Renting, rent increases, deposits, tenancy disputes, home ownership | 220 (OR Art. 253–274), 842 |
| `building` | Building and land use | Building permits, zoning, spatial planning, renovation, land register | 700, 211.4 |
| `family` | Family and civil status | Marriage, partnership, divorce, children, child support, names, inheritance, death | 210, 211 |
| `residence` | Residence, migration and citizenship | Permits, foreign nationals, asylum, naturalisation, registering a move | 14 |
| `politics` | Politics and voting | Elections, popular votes, initiatives, political rights, authorities and their powers | 1 (except 14) |
| `justice` | Justice, courts and criminal law | Criminal law, fines, legal proceedings, debt collection, legal aid | 3, 27, 28 |
| `safety` | Public safety, police and civil protection | Police, fire, civil protection, military service, weapons, public order, noise rules | 5, 514 |
| `education` | Education and schools | Compulsory school, school holidays, vocational training, universities, scholarships | 41 |
| `transport` | Transport, vehicles and parking | Road traffic rules, driving licences, vehicles, parking and blue zones, public transport, cycling | 72, 74, 76 |
| `travel` | Travel, customs and borders | Customs allowances, importing goods, identity documents, travelling abroad | 631, 143 |
| `environment` | Environment, energy and nature | Environmental protection, noise, water, forests, nature protection, energy | 451, 73, 814, 92 (except 922) |
| `animals` | Animals and pets | Dog keeping and dog tax, leash rules, animal welfare, livestock, hunting and fishing | 455, 916, 922, 923 |
| `waste` | Waste and recycling | Collection days, fees, bulky and special waste, recycling points | 814.6 |
| `outdoors` | Leisure, sport and outdoors | Hiking trails, mountains, sport, culture, public spaces and parks | 704, 415 |
| `business` | Business and consumers | Starting a company, commercial register, trades licences, consumer rights, contracts of sale | 22, 94, 95 |
| `municipal_services` | Municipal services and administration | Opening hours, registration office, public holidays, municipal fees, documents and certificates | — |

## Considered Options

- Keep the ten: most of the new corpus would be untagged, and therefore unreachable under the hard filter.
- Fedlex's SR structure as the taxonomy: official and exact for law, but shaped like a law library rather than like questions; a question about keeping a dog in a rented flat spans three SR areas.

## Consequences

- Old ids map mechanically: `dogs` → `animals`, `hiking` → `outdoors`, `parking` → `transport`, `schools` → `education`; the others keep their ids. Probes are migrated with that map.
- Whether topic stays a hard filter or becomes a ranking signal is a query-time decision, revisited once evals exist; it does not require re-encoding.
