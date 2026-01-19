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
        # TODO do not allow empty types?
        types_empty = (not building_types or len(building_types) == 0) and (
                not event_types or len(event_types) == 0) and (not place_types or len(place_types) == 0)
        type_filters = []
        if building_types and len(building_types) > 0 or types_empty:
            type_filters.append('?sub property:Art_des_Bauwerks ?type')
        if event_types and len(event_types) > 0 or types_empty:
            type_filters.append('?sub property:Art_des_Ereignisses ?type')
        if place_types and len(place_types) > 0 or types_empty:
            type_filters.append('?sub property:Art_des_Objekts ?type')

        type_union = " UNION ".join([f"{{ {f} }}" for f in type_filters]) if type_filters else "{ ?sub a ?anyType }"

        # Build type filter
        types = []
        if building_types:
            types.extend(building_types)
        if event_types:
            types.extend(event_types)
        if place_types:
            types.extend(place_types)

        type_filter = ""
        if types and len(types) > 0:
            types_string = ", ".join([f'wiki:{t}' for t in types])
            type_filter = f"""
            # Filter by type
            FILTER(?type IN ({types_string}))
            """

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
            ?label 
            ?type
            (STR(?startDate) AS ?start)
            (STR(?endDate) AS ?end)
            ?historical 
            ?wkt
        WHERE {{
            # Entity type union (buildings, events, places)
            {type_union}
            
            # Required properties
            ?sub rdfs:label ?label ;
                 geo:hasGeometry/geo:asWKT ?wkt .
            
            # Optional properties
            OPTIONAL {{ ?sub property:Historisch ?historical }}.
            OPTIONAL {{ ?sub schema:startDate ?startDate . 
        		FILTER (DATATYPE(?startDate) = xsd:gYear || 
        		DATATYPE(?startDate) = xsd:date ||
        		DATATYPE(?startDate) = xsd:gYearMonth)
        		}} .
            OPTIONAL {{ ?sub schema:endDate ?endDate .
   				FILTER (DATATYPE(?endDate) = xsd:gYear || 
        		DATATYPE(?endDate) = xsd:date || 
        		DATATYPE(?endDate) = xsd:gYearMonth)
        		}} .
            
            {type_filter}
            {historical_filter}
            
            # Temporal filter: Entity existed at some point in timeframe
            FILTER (
                (!BOUND(?startDate) || YEAR(?startDate) <= {to_year}) &&
                (!BOUND(?endDate) || YEAR(?endDate) >= {from_year})
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
