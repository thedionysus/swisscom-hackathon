from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    description: str


CATEGORIES: tuple[Category, ...] = (
    Category("hiking", "Hiking and outdoor recreation", "Trails, safety, nature protection, alpine rules"),
    Category("waste", "Waste and recycling", "Collection schedules, fees, disposal rules"),
    Category("dogs", "Dogs and pets", "Dog tax, leash rules, registration, training requirements"),
    Category("taxes", "Taxes", "Income, wealth and municipal taxes, filing"),
    Category("housing", "Housing and building", "Renting, building permits, zoning"),
    Category("transport", "Transport and mobility", "Public transport, road traffic rules, cycling"),
    Category("parking", "Parking", "Blue zones, permits, fees"),
    Category("schools", "Schools and education", "Compulsory school, holidays, enrolment"),
    Category("health", "Health", "Insurance, hospitals, emergencies"),
    Category("safety", "Public safety and police", "Police, emergencies, public order"),
)

CATEGORY_IDS: tuple[str, ...] = tuple(c.id for c in CATEGORIES)
