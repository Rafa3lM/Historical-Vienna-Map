"""
Centralized SPARQL query management for Historical Vienna Map.
Supports parameterized queries with filtering.
"""

from typing import List, Optional


class SparqlQueries:
    """Sparql query templates with parameter injection"""

    @staticmethod
    def get_entities_in_area(
            lat: float,
            lng: float,
            radius: float,
            from_year: int,
            to_year: int,
            building_types: Optional[List[str]] = None,
            event_types: Optional[List[str]] = None,
            place_types: Optional[List[str]] = None,
            only_historical: bool = False,
    ) -> str:
        """
        Main spatial-temporal query for buildings, events, and places

        Args:
            lat, lng: Center point coordinates
            radius: Search radius in meters
            from_year, to_year: Time range
            building_types: List of building types (Kirche, Palais, etc.)
            event_types: List of event types (Brand, Versammlung, etc.)
            place_types: List of place types (Markt, Grünfläche, etc.)
            only_historical: If True, only show demolished buildings
            include_buildings/events/places: What entity types to include
        """

        # Build entity type filter
        type_filters = []
        if building_types and len(building_types) > 0:
            type_filters.append('?sub property:Art_des_Bauwerks ?building_type')
        if event_types and len(event_types) > 0:
            type_filters.append('?sub property:Art_des_Ereignisses ?event_type')
        if place_types and len(place_types) > 0:
            type_filters.append('?sub property:Art_des_Objekts ?place_type')

        type_union = " UNION ".join([f"{{ {f} }}" for f in type_filters]) if type_filters else "{ ?sub a ?anyType }"

        # Build building type filter
        building_type_filter = ""
        if building_types and len(building_types) > 0:
            building_types_str = ", ".join([f'wiki:{t}' for t in building_types])
            building_type_filter = f"""
            # Filter by building category
            ?sub property:Art_des_Bauwerks ?typeLabel .
            FILTER(?typeLabel IN ({building_types_str}))
            """

        # Build event type filter
        event_type_filter = ""
        if event_types and len(event_types) > 0:
            event_types_string = ", ".join([f'wiki:{t}' for t in building_types])
            event_type_filter = f"""
                # Filter by event category
                ?sub property:Art_des_Ereignisses ?typeLabel .
                FILTER(STR(?typeLabel) IN ({event_types_string}))
                """

        # Build place type filter
        place_type_filter = ""
        if place_types and len(place_types) > 0:
            event_types_string = ", ".join([f'wiki:{t}' for t in building_types])
            place_type_filter = f"""
                # Filter by place category
                ?sub property:Art_des_Objekts ?typeLabel .
                FILTER(STR(?typeLabel) IN ({event_types_string}))
                """

        # Build specific entity type filter (Art_des_Bauwerks)

        # entity_type_filter = ""
        # if entity_types and len(entity_types) > 0:
        #     # Convert URIs to filter
        #     uris = ", ".join([f"<{t}>" for t in entity_types])
        #     entity_type_filter = f"FILTER(?type IN ({uris}))"

        # Historical filter
        historical_filter = ""
        if only_historical:
            historical_filter = "FILTER(?historical = true)"

        query = f"""
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX property: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A>
        PREFIX wiki: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/>
        
        SELECT DISTINCT 
            ?sub 
            ?type 
            ?label 
            (STR(?startDate) AS ?start)
            (STR(?endDate) AS ?end)
            ?historical 
            ?wkt
        WHERE {{
            # Entity type union (buildings, events, places)
            {type_union}
            
            # Required properties
            ?sub property:Art_des_Bauwerks ?type ;
                 rdfs:label ?label ;
                 geo:hasGeometry/geo:asWKT ?wkt .
            
            # Optional properties
            OPTIONAL {{ ?sub property:Historisch ?historical }}.
            OPTIONAL {{ ?sub schema:startDate ?startDate }}.
            OPTIONAL {{ ?sub schema:endDate ?endDate }}.
            
            {building_type_filter}
            {event_type_filter}
            {place_type_filter}
            {historical_filter}
            
            # Temporal filter: Entity existed at some point in timeframe
            FILTER (
                (!BOUND(?startDate) || xsd:integer(?startDate) <= {to_year}) &&
                (!BOUND(?endDate) || xsd:integer(?endDate) >= {from_year})
            )
            
            # Spatial filter: Within radius
            FILTER (
                geof:distance(
                    ?wkt,
                    "POINT({lng} {lat})"^^geo:wktLiteral,
                    <http://www.opengis.net/def/uom/OGC/1.0/metre>
                ) <= {radius}
            )
        }}
        ORDER BY ?label
        LIMIT 1000
        """
        return query
