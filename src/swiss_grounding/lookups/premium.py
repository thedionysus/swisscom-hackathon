"""swiss_premium: cheapest basic-insurance premiums for a municipality, age and deductible."""
import psycopg

from swiss_grounding.locations.models import Level
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.lookups.premium_data import SOURCE_URL, age_class

DEDUCTIBLES = {"child": (0, 100, 200, 300, 400, 500, 600),
               "young_adult": (300, 500, 1000, 1500, 2000, 2500),
               "adult": (300, 500, 1000, 1500, 2000, 2500)}
MODELS = ("any", "standard", "family_doctor", "hmo", "telmed", "other")
SINGLE_REGION = 0   # BAG's number for the one premium region of a canton not divided into regions
SQL = ("select p.insurer_name, p.model, p.model_label, p.premium_chf from serving.premium p "
       "where p.year = %(year)s and p.canton = %(canton)s and p.region = %(region)s and p.age_class = %(age)s "
       "and p.accident = %(accident)s and p.deductible = %(deductible)s "
       "and (%(model)s = 'any' or p.model = %(model)s) order by p.premium_chf limit %(limit)s")


def _bad(message: str) -> dict:
    return {"status": "invalid_request", "message": message}


def _region(conn: psycopg.Connection, year: int, bfs_id: int, canton: str) -> dict | None:
    """The municipality's premium region. BAG's region list names only the municipalities of cantons
    divided into regions; a canton it does not list at all has a single region."""
    listed = conn.execute("select canton, region from serving.premium_region where year = %s and bfs_id = %s",
                          (year, bfs_id)).fetchone()
    if listed is not None:
        return listed
    divided = conn.execute("select 1 from serving.premium_region where year = %s and canton = %s limit 1",
                           (year, canton)).fetchone()
    return None if divided else {"canton": canton, "region": SINGLE_REGION}


def cheapest_premiums(conn: psycopg.Connection, tree: LocationTree, *, location_id: str, age: int,
                      deductible: int, accident: bool, model: str, year: int, limit: int) -> dict:
    klass = age_class(age)
    if deductible not in DEDUCTIBLES[klass]:
        return _bad(f"A {klass.replace('_', ' ')} can choose a deductible of {DEDUCTIBLES[klass]} CHF.")
    if model not in MODELS:
        return _bad(f"model must be one of {MODELS}.")
    loc = tree.get(location_id)
    if loc.level is Level.NEIGHBORHOOD:          # a Kreis: premiums follow its municipality
        loc = tree.get(loc.parent_id)
    if loc.level is not Level.MUNICIPALITY:      # canton bfs ids (1-26) collide with commune numbers
        return _bad("Give a municipality (not a canton): premiums depend on the municipality's premium region.")
    region = _region(conn, year, loc.bfs_id, canton=loc.id.split("-")[1])
    if region is None:
        return {"status": "no_evidence", "message": f"No {year} premium region is loaded for {loc.label('de')}."}
    rows = conn.execute(SQL, {"year": year, "canton": region["canton"], "region": region["region"], "age": klass,
                              "accident": accident, "deductible": deductible, "model": model,
                              "limit": limit}).fetchall()
    return {"status": "results" if rows else "no_evidence", "municipality": loc.label("de"),
            "canton": region["canton"], "premium_region": region["region"], "year": year, "age_class": klass,
            "deductible": deductible, "accident_included": accident,
            "premiums": [{**r, "premium_chf": float(r["premium_chf"])} for r in rows],
            "unit": "CHF per month", "source_url": SOURCE_URL}
