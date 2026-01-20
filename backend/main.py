from fastapi import FastAPI, Query, HTTPException
from SPARQLWrapper import SPARQLWrapper, JSON
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from backend.queries import SparqlQueries

app = FastAPI(title="Vienna Historical Map API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite / Vue
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GRAPDB_URL = "http://localhost:7200/repositories/vienna"


def execute_sparql(query: str) -> dict:
    """Execute SPARQL query and return results"""
    sparql = SPARQLWrapper(GRAPDB_URL)
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
        building_types: Optional[List[str]] = Query(None, description="Comma-separated list of building types"),
        event_types: Optional[List[str]] = Query(None, description="Comma-separated list of event types"),
        place_types: Optional[List[str]] = Query(None, description="Comma-separated list of place types"),
        only_historical: bool = False,
        has_artists: bool = Query(False),
        related_to: bool = Query(False),
        named_after: bool = Query(False),
        has_events: bool = Query(False),
        only_monuments: bool = Query(False)
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

    print(query)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
