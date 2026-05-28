import os
from fastapi import FastAPI, Query, HTTPException
from SPARQLWrapper import SPARQLWrapper, JSON
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from backend.queries import SparqlQueries

app = FastAPI(title="Vienna Historical Map API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200/repositories/vienna")


def execute_sparql(query: str) -> dict:
    """Execute SPARQL query and return results"""
    sparql = SPARQLWrapper(GRAPHDB_URL)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL query failed: {str(e)}")


def wkt_to_latlng(wkt: str) -> tuple:
    """Convert WKT POINT to [lat, lng]"""
    wkt = wkt.replace("POINT", "").replace("(", "").replace(")", "").strip()
    lng_str, lat_str = wkt.split(" ")
    return float(lat_str), float(lng_str)


def collect_values(bindings, key):
    return list({
        b[key]["value"] for b in bindings
        if key in b
    })


@app.get("/entities")
def get_entities_in_area(
        lat: float = Query(..., description="Latitude"),
        lng: float = Query(..., description="Longitude"),
        radius: float = Query(500, ge=50, le=15000, description="Radius in meters"),
        from_year: int = Query(0, ge=0, le=2026, description="Start year"),
        to_year: int = Query(2026, ge=0, le=2026, description="End year"),
        time_range_mode: str = Query('overlapping',
                                     description="Whether the entities timeframe must be fully contained in the selected timeframe or only overlapping"),
        building_types: Optional[List[str]] = Query(None, description="Comma-separated list of building types"),
        event_types: Optional[List[str]] = Query(None, description="Comma-separated list of event types"),
        place_types: Optional[List[str]] = Query(None, description="Comma-separated list of place types"),
        only_historical: bool = Query(False, description="Only show demolished/no longer existing buildings"),
        has_artists: bool = Query(False, description="Only entities with known architects/artists"),
        related_to: bool = Query(False, description="Only entities with famous inhabitants or related people"),
        named_after: bool = Query(False, description="Only entities named after a person"),
        has_events: bool = Query(False, description="Only entities with related historical events"),
        only_monuments: bool = Query(False,
                                     description="Only officially protected monuments (HERIS/Cultural Heritage DB)")
) -> dict:
    """
    Get entities (buildings, events, places) within a spatial-temporal range

    **Spatial Filter**: Within radius of the specified coordinates
    **Temporal Filter**: Existed at any point during [from_year, to_year]

    Example: `/buildings?lat=48.2082&lng=16.3738&radius=500&from_year=1800&to_year=1900`
    """

    # Validate time range
    if from_year > to_year:
        raise HTTPException(status_code=400, detail="from_year must be <= to_year")

    # Parse building types filter
    building_types_list = building_types
    # if building_types:
    # building_types_list = [t.strip() for t in building_types]

    # Parse event types filter
    event_types_list = event_types
    # if building_types:
    # event_types_list = [t.strip() for t in event_types]

    # Parse place types filter
    place_types_list = place_types
    # if place_types:
    # place_types_list = [t.strip() for t in place_types]

    if not building_types_list and not event_types_list and not place_types_list:
        return {
            "count": 0,
            "query_params": {
                "center": {"lat": lat, "lng": lng},
                "radius": radius,
                "time_range": {"from": from_year, "to": to_year}
            },
            "entities": []
        }

    # Generate query
    query = SparqlQueries.get_entities_in_area(
        lat=lat,
        lng=lng,
        radius=radius,
        from_year=from_year,
        to_year=to_year,
        time_range_mode=time_range_mode,
        building_types=building_types_list,
        event_types=event_types_list,
        place_types=place_types_list,
        only_historical=only_historical,
        has_artists=has_artists,
        related_to=related_to,
        named_after=named_after,
        has_events=has_events,
        only_monuments=only_monuments,
    )

    results = execute_sparql(query)

    # Parse results
    entities = []
    for res in results["results"]["bindings"]:
        # Extract coordinates
        wkt = res.get("wkt", {}).get("value")
        if wkt:
            lat_val, lng_val = wkt_to_latlng(wkt)
        else:
            continue  # Skip entities without coordinates

        entity = {
            "uri": res["sub"]["value"],
            "type": res.get("type", {}).get("value"),
            "label": res.get("label", {}).get("value", "Unknown"),
            "lat": lat_val,
            "lng": lng_val,
        }

        # Optional fields
        if "start" in res:
            entity["startDate"] = res["start"]["value"]
        if "end" in res:
            entity["endDate"] = res["end"]["value"]
        if "historical" in res:
            entity["historical"] = res["historical"]["value"] == "true"

        entities.append(entity)

    return {
        "count": len(entities),
        "query_params": {
            "center": {"lat": lat, "lng": lng},
            "radius": radius,
            "time_range": {"from": from_year, "to": to_year}
        },
        "entities": entities
    }


@app.get("/entity-geo")
def get_geo_entity(uri: str = Query(...)) -> dict:
    """
    Get detailed information about an entity.
    """

    query = SparqlQueries.get_geo_entity_details(uri)
    results = execute_sparql(query)

    if not results["results"]["bindings"]:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Parse first result
    res = results["results"]["bindings"][0]

    details = {
        "uri": uri,
        "label": res.get("label", {}).get("value"),
        "buildingType": res.get("buildingType", {}).get("value"),
        "eventType": res.get("eventType", {}).get("value"),
        "placeType": res.get("placeType", {}).get("value"),
        "wikiPage": res.get("wikiPage", {}).get("value"),
    }

    # Temporal info
    if "startDate" in res:
        details["startDate"] = res["startDate"]["value"]
    if "endDate" in res:
        details["endDate"] = res["endDate"]["value"]
    if "historical" in res:
        details["historical"] = res["historical"]["value"] == "true"

    # Location
    if "wkt" in res:
        lat, lng = wkt_to_latlng(res["wkt"]["value"])
        details["coordinates"] = {"lat": lat, "lng": lng}
    if "address" in res:
        details["address"] = res["address"]["value"]
    if "districtName" in res:
        details["district"] = res["districtName"]["value"]

    # Monument protection database IDs
    if "herisId" in res:
        details["herisId"] = res["herisId"]["value"]
    if "cultId" in res:
        details["cultId"] = res["cultId"]["value"]

    # People
    architects = collect_values(results["results"]["bindings"], "architect")
    if architects:
        details["architects"] = architects

    named_after = collect_values(results["results"]["bindings"], "namedAfter")
    if named_after:
        details["namedAfter"] = named_after

    famous_inhabitant = collect_values(results["results"]["bindings"], "famousInhabitant")
    if famous_inhabitant:
        details["famousInhabitants"] = famous_inhabitant

    # Events
    events = collect_values(results["results"]["bindings"], "event")
    if events:
        details["events"] = events

    # Media
    if "image" in res:
        details["image"] = res["image"]["value"]

    return details


@app.get("/entity-details")
def get_info_entity(uri: str = Query(...)) -> dict:
    """
    Get detailed information about an entity.
    """

    query = SparqlQueries.get_info_entity_details(uri)
    results = execute_sparql(query)

    if not results["results"]["bindings"]:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Parse first result
    res = results["results"]["bindings"][0]

    details = {
        "uri": uri,
        "label": res.get("label", {}).get("value"),
        "wikiPage": res.get("wikiPage", {}).get("value"),
    }

    if "birthDate" in res:
        details["birthDate"] = res["birthDate"]["value"]
    if "deathDate" in res:
        details["deathDate"] = res["deathDate"]["value"]
    if "birthPlace" in res:
        details["birthPlace"] = res["birthPlace"]["value"]
    if "deathPlace" in res:
        details["deathPlace"] = res["deathPlace"]["value"]
    if "gender" in res:
        details["gender"] = res["gender"]["value"]
    if "image" in res:
        details["image"] = res["image"]["value"]

    resident_of = collect_values(results["results"]["bindings"], "residentOf")
    if resident_of:
        details["residentOf"] = resident_of

    architect_of = collect_values(results["results"]["bindings"], "architectOf")
    if architect_of:
        details["architectOf"] = architect_of

    named_after = collect_values(results["results"]["bindings"], "namedAfter")
    if resident_of:
        details["namedAfter"] = named_after

    return details


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
