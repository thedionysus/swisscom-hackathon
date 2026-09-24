"""The twenty citizen-facing topics and the SR-number prior for federal law."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    covers: str


TOPICS: tuple[Topic, ...] = (
    Topic("work", "Work and employment", "Employment contracts, notice and termination, working hours, holidays, wages, unemployment"),
    Topic("social_security", "Social security and pensions", "AHV/IV, pension funds, family allowances, social assistance, disability"),
    Topic("health", "Health and health insurance", "Compulsory health insurance, premiums and subsidies, doctors, hospitals, medicines, vaccinations, emergencies"),
    Topic("taxes", "Taxes", "Income, wealth, municipal and church tax, VAT, tax returns, deductions"),
    Topic("housing", "Housing and renting", "Renting, rent increases, deposits, tenancy disputes, home ownership"),
    Topic("building", "Building and land use", "Building permits, zoning, spatial planning, renovation, land register"),
    Topic("family", "Family and civil status", "Marriage, partnership, divorce, children, child support, names, inheritance, death"),
    Topic("residence", "Residence, migration and citizenship", "Permits, foreign nationals, asylum, naturalisation, registering a move"),
    Topic("politics", "Politics and voting", "Elections, popular votes, initiatives, political rights, authorities and their powers"),
    Topic("justice", "Justice, courts and criminal law", "Criminal law, fines, legal proceedings, debt collection, legal aid"),
    Topic("safety", "Public safety, police and civil protection", "Police, fire, civil protection, military service, weapons, public order, noise rules"),
    Topic("education", "Education and schools", "Compulsory school, school holidays, vocational training, universities, scholarships"),
    Topic("transport", "Transport, vehicles and parking", "Road traffic rules, driving licences, vehicles, parking and blue zones, public transport, cycling"),
    Topic("travel", "Travel, customs and borders", "Customs allowances, importing goods, identity documents, travelling abroad"),
    Topic("environment", "Environment, energy and nature", "Environmental protection, noise, water, forests, nature protection, energy"),
    Topic("animals", "Animals and pets", "Dog keeping and dog tax, leash rules, animal welfare, livestock, hunting and fishing"),
    Topic("waste", "Waste and recycling", "Collection days, fees, bulky and special waste, recycling points"),
    Topic("outdoors", "Leisure, sport and outdoors", "Hiking trails, mountains, sport, culture, public spaces and parks"),
    Topic("business", "Business and consumers", "Starting a company, commercial register, trades licences, consumer rights, contracts of sale"),
    Topic("municipal_services", "Municipal services and administration", "Opening hours, registration office, public holidays, municipal fees, documents and certificates"),
)
TOPIC_IDS: frozenset[str] = frozenset(t.id for t in TOPICS)

# (SR prefix, article range or None, topic). The longest matching prefix wins; among entries
# with that prefix, a range that contains the article wins over the open entry.
_SR_PRIORS: tuple[tuple[str, tuple[int, int] | None, str], ...] = (
    ("1", None, "politics"), ("14", None, "residence"), ("143", None, "travel"),
    ("210", None, "family"), ("211", None, "family"), ("211.4", None, "building"),
    ("22", None, "business"), ("220", None, "business"),
    ("220", (319, 362), "work"), ("220", (253, 274), "housing"),
    ("27", None, "justice"), ("28", None, "justice"), ("3", None, "justice"),
    ("41", None, "education"), ("415", None, "outdoors"),
    ("451", None, "environment"), ("455", None, "animals"),
    ("5", None, "safety"), ("514", None, "safety"),
    ("631", None, "travel"), ("64", None, "taxes"),
    ("700", None, "building"), ("704", None, "outdoors"),
    ("72", None, "transport"), ("73", None, "environment"), ("74", None, "transport"), ("76", None, "transport"),
    ("81", None, "health"), ("814", None, "environment"), ("814.6", None, "waste"),
    ("822", None, "work"), ("83", None, "social_security"), ("832", None, "health"),
    ("837", None, "work"), ("842", None, "housing"), ("85", None, "social_security"),
    ("916", None, "animals"), ("92", None, "environment"), ("922", None, "animals"), ("923", None, "animals"),
    ("94", None, "business"), ("95", None, "business"),
)


def sr_prior(sr: str, article: int | None = None) -> tuple[str, ...]:
    """The starting topic for an act's article, or () when no prior applies."""
    matches = [entry for entry in _SR_PRIORS if sr.startswith(entry[0])]
    if not matches:
        return ()
    longest = max(len(prefix) for prefix, _, _ in matches)
    best = [entry for entry in matches if len(entry[0]) == longest]
    if article is not None:
        for _, span, topic in best:
            if span is not None and span[0] <= article <= span[1]:
                return (topic,)
    for _, span, topic in best:
        if span is None:
            return (topic,)
    return ()
