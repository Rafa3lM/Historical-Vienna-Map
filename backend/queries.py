"""
Centralized SPARQL query management for Historical Vienna Map.
Supports parameterized queries with filtering.
"""
import datetime
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
            time_range_mode: str = 'overlap',
            building_types: Optional[List[str]] = None,
            event_types: Optional[List[str]] = None,
            place_types: Optional[List[str]] = None,
            only_historical: bool = False,
            has_artists: bool = False,
            related_to: bool = False,
            named_after: bool = False,
            only_monuments: bool = False,
            has_events: bool = False,
    ) -> str:
        """
        Main spatial-temporal query for buildings, events, and places

        Args:
            lat, lng: Center point coordinates
            radius: Search radius in meters
            from_year, to_year: Time range
            time_range_mode: overlap: entity existed at any point in time range, contained: entity existed only inside time range
            building_types: List of building types (Kirche, Palais, etc.)
            event_types: List of event types (Brand, Versammlung, etc.)
            place_types: List of place types (Markt, Grünfläche, etc.)
            only_historical: If True, only show demolished buildings
            has_artists: List only entities with linked artists
            related_to: List only entities with relatedTo attribute
            named_after: List only entities named after someone/something
            only_monuments: List only buildings with a monument protection database ID
            has_events: List only entities linked to events
        """

        # Build entity type filter
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

        # Subtype filter
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

        # Temporal filter
        time_range_filter = ""
        if time_range_mode == "overlap":
            time_range_filter = f"""
            # Temporal filter: Entity existed at some point in timeframe
            FILTER (
                (!BOUND(?startDate) || YEAR(?startDate) <= {to_year}) &&
                (!BOUND(?endDate) || YEAR(?endDate) >= {from_year})
            )
            """
        elif time_range_mode == "contained":
            time_range_filter = f"""
            # Temporal filter: Entity constructed after start date and demolished before end date
            FILTER (
                (BOUND(?startDate) && YEAR(?startDate) >= {from_year}) &&
                (BOUND(?endDate) && ({to_year == datetime.datetime.now().year} || YEAR(?endDate) <= {to_year}))
            )
            """

        # Historical filter
        historical_filter = ""
        if only_historical:
            historical_filter = "FILTER(?historical = true)"

        has_artists_filter = ""
        if has_artists:
            has_artists_filter = "?sub schema:artist ?artist ."

        related_to_filter = ""
        if related_to:
            related_to_filter = "?sub schema:relatedTo ?related ."

        named_after_filter = ""
        if named_after:
            named_after_filter = "?sub property:Benannt_nach ?named_after ."

        events_filter = ""
        if has_events:
            events_filter = ("?sub schema:relatedLink ?event ."
                             "?event property:Art_des_Ereignisses ?anyEventType .")

        monuments_filter = ""
        if only_monuments:
            monuments_filter = ("?sub property:WikidataHERISID ?herisId ;"
                                "property:WikidataCulturalHeritageID ?cultId .")

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
                 
            {has_artists_filter}
            {related_to_filter}
            {named_after_filter}
            {events_filter}
            {monuments_filter}
            
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
            
            {time_range_filter}
            
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
        LIMIT 10000
        """
        return query

    @staticmethod
    def get_geo_entity_details(entity_uri: str) -> str:
        """
        Get detailed information about a geo-locatable entity
        """

        query = f"""
        PREFIX property: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX swivt: <http://semantic-mediawiki.org/swivt/1.0#>

        SELECT DISTINCT
            ?label
            ?buildingType
            ?eventType
            ?placeType
            ?startDate
            ?endDate
            ?historical
            ?wkt
            ?address
            ?architect
            ?namedAfter
            ?famousInhabitant
            ?event
            ?wikiPage
            ?district
            ?districtName
            ?image
            ?herisId
            ?cultId
        WHERE {{
            BIND(<{entity_uri}> AS ?entity)

            # Basic info
            ?entity rdfs:label ?label .
            OPTIONAL {{ ?entity property:Art_des_Bauwerks ?buildingType }}.
            OPTIONAL {{ ?entity property:Art_des_Ereignisses ?eventType }}.
            OPTIONAL {{ ?entity property:Art_des_Objekts ?placeType }}.

            # Temporal
            OPTIONAL {{ ?entity schema:startDate ?startDate }}.
            OPTIONAL {{ ?entity schema:endDate ?endDate }}.
            OPTIONAL {{ ?entity property:Historisch ?historical }}.

            # Location
            OPTIONAL {{ ?entity geo:hasGeometry/geo:asWKT ?wkt }}.
            OPTIONAL {{ ?entity schema:address ?address }}.
            OPTIONAL {{ 
                ?entity schema:containedInPlace ?district .
                ?district rdfs:label ?districtName .
            }}.

            # People & Attribution
            OPTIONAL {{ ?entity schema:artist ?architect }}.
            OPTIONAL {{ ?entity property:Benannt_nach ?namedAfter }}.
            OPTIONAL {{ ?entity schema:relatedTo ?famousInhabitant }}.
            
            # Related Events
            OPTIONAL {{ 
                ?entity schema:relatedLink ?event .
                ?event property:Art_des_Ereignisses ?anyEventType .
            }}
            
            # Monument Protection
            OPTIONAL {{ ?entity property:WikidataCulturalHeritageID ?cultId . }}
            OPTIONAL {{ ?entity property:WikidataHERISID ?herisId . }}

            # Links
            OPTIONAL {{ ?entity swivt:page ?wikiPage }}.
            OPTIONAL {{ ?entity schema:image ?image }}.
        }}
        """
        return query

    @staticmethod
    def get_info_entity_details(entity_uri: str) -> str:
        """
        Get detailed information about an entity
        """

        query = f"""
        PREFIX property: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX swivt: <http://semantic-mediawiki.org/swivt/1.0#>
        PREFIX wiki: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/>
        
        SELECT DISTINCT 
            ?label
            ?wikiPage
            ?image
            ?birthDate
            ?birthPlace
            ?deathDate
            ?deathPlace
            ?residentOf
            ?architectOf
            ?namedAfter
            ?gender
        WHERE {{
            BIND(<{entity_uri}> AS ?entity)

            # Basic info
            OPTIONAL {{ ?entity rdfs:label ?label . }}
            OPTIONAL {{ ?entity swivt:page ?wikiPage . }}
            
            OPTIONAL {{ ?entity schema:image ?image . }}
            
            OPTIONAL {{ ?entity schema:birthData ?birthDate .
                        FILTER(DATATYPE(?birthDate) = xsd:date) }}
            OPTIONAL {{ ?entity wiki:Property-3AGND_Geburtsort ?birthPlace . }}
            
            OPTIONAL {{ ?entity schema:deathDate ?deathDate . 
                        FILTER(DATATYPE(?deathDate) = xsd:date) }}
            OPTIONAL {{ ?entity wiki:Property-3AGND_Sterbeort ?deathPlace . }}
            
            OPTIONAL {{ ?entity schema:relatedTo ?residentOf . }}
            OPTIONAL {{ ?architectOf schema:artist ?entity . }}
            OPTIONAL {{ ?entity property:Benannt_nach ?namedAfter . }}
            
            OPTIONAL {{ ?entity schema:gender ?gender . }}
        }}
        """

        return query
