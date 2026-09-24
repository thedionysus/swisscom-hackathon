# Labelling guide for the fresh topic sample

Two people (or two independent agents) each label every chunk in `chunks.json` alone. Neither sees the
other's labels, the production topics (`baseline.json`) or Jev's answers. This is the guide both used
in the first test, updated to the twenty topics (ADR 0007) and the production boilerplate definition.

## Output

One file per labeller, `labels_A.json` and `labels_B.json`. Each is a JSON object keyed by chunk id, and
every id in `chunks.json` must be present:

```json
{"12345:de": {"primary": ["animals"], "acceptable": [], "junk": false}}
```

## Rules

- Label from each chunk's own text, heading and page title only.
- **primary**: every topic a resident asking about that topic would want this chunk as evidence for,
  because the chunk's own content concerns the topic, not a passing mention. There may be zero, one or
  several. Production allows up to three (`corpus/describe.py:27`); list more if they truly apply.
- **acceptable**: topics that are defensible but tangential. They count neither for nor against. Use this
  for genuine borderline cases, not as a hedge.
- **junk**: true when the chunk is page furniture, not substance. Use the production definition
  (`corpus/describe.py:60-61`): "navigation, a cookie notice, contact details or other page furniture
  with no substantive content". A bare heading with no informative content is also junk. A junk chunk
  has no primary topics.
- A substantive chunk that fits none of the twenty topics gets no topic. That is a correct answer, not a gap.

## The twenty topics (`src/swiss_grounding/corpus/topics.py`, ADR 0007)

| id | Label | Covers |
|---|---|---|
| `work` | Work and employment | Employment contracts, notice and termination, working hours, holidays, wages, unemployment |
| `social_security` | Social security and pensions | AHV/IV, pension funds, family allowances, social assistance, disability |
| `health` | Health and health insurance | Compulsory health insurance, premiums and subsidies, doctors, hospitals, medicines, vaccinations, emergencies |
| `taxes` | Taxes | Income, wealth, municipal and church tax, VAT, tax returns, deductions |
| `housing` | Housing and renting | Renting, rent increases, deposits, tenancy disputes, home ownership |
| `building` | Building and land use | Building permits, zoning, spatial planning, renovation, land register |
| `family` | Family and civil status | Marriage, partnership, divorce, children, child support, names, inheritance, death |
| `residence` | Residence, migration and citizenship | Permits, foreign nationals, asylum, naturalisation, registering a move |
| `politics` | Politics and voting | Elections, popular votes, initiatives, political rights, authorities and their powers |
| `justice` | Justice, courts and criminal law | Criminal law, fines, legal proceedings, debt collection, legal aid |
| `safety` | Public safety, police and civil protection | Police, fire, civil protection, military service, weapons, public order, noise rules |
| `education` | Education and schools | Compulsory school, school holidays, vocational training, universities, scholarships |
| `transport` | Transport, vehicles and parking | Road traffic rules, driving licences, vehicles, parking and blue zones, public transport, cycling |
| `travel` | Travel, customs and borders | Customs allowances, importing goods, identity documents, travelling abroad |
| `environment` | Environment, energy and nature | Environmental protection, noise, water, forests, nature protection, energy |
| `animals` | Animals and pets | Dog keeping and dog tax, leash rules, animal welfare, livestock, hunting and fishing |
| `waste` | Waste and recycling | Collection days, fees, bulky and special waste, recycling points |
| `outdoors` | Leisure, sport and outdoors | Hiking trails, mountains, sport, culture, public spaces and parks |
| `business` | Business and consumers | Starting a company, commercial register, trades licences, consumer rights, contracts of sale |
| `municipal_services` | Municipal services and administration | Opening hours, registration office, public holidays, municipal fees, documents and certificates |

When done, note the number of chunks labelled, how many are junk, how many have two or more primary
topics, and the ids you found hard, each with one short reason.
