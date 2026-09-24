"""Derive century labels from dates and architectural-style periods."""

import re
from collections import defaultdict
from typing import Dict, Iterable, Mapping, Optional, Set, Tuple

from rdflib import Graph, Literal, Namespace, URIRef
from SPARQLWrapper import JSON, POST, SPARQLWrapper

from elt.config import GRAPHDB_SPARQL
from elt.loaders.graphdb_loader import GraphDBLoader
from elt.utils.query_loader import load_query

VIENNA_DERIVED = Namespace("http://example.org/vienna/")
START_DATE_CENTURY = VIENNA_DERIVED.startDateCentury
END_DATE_CENTURY = VIENNA_DERIVED.endDateCentury
ACTIVE_DURING_CENTURY = VIENNA_DERIVED.activeDuringCentury
GENERATED_PREDICATES = (
    START_DATE_CENTURY,
    END_DATE_CENTURY,
    ACTIVE_DURING_CENTURY,
)

XSD_GYEAR = "http://www.w3.org/2001/XMLSchema#gYear"
XSD_DATE = "http://www.w3.org/2001/XMLSchema#date"

# These labels are deliberately aliases rather than URI assumptions: Wikidata
# style resources are linked by URI, but their labels are the stable input that
# identifies the small, manually curated set of important styles.
STYLE_PERIODS: Dict[str, Tuple[int, int]] = {
    # Renaissance
    "renaissance architecture": (15, 16),
    "renaissance architecure": (15, 16),
    "renaissance revival architecture": (19, 20),
    # Baroque
    "baroque architecture": (17, 18),
    "baroque": (17, 18),
    # Broad historical / regional styles
    "armenian architecture": (4, 21),
    "romanesque architecture": (11, 12),
    "gothic architecture": (12, 15),
    "byzantine revival architecture": (19, 20),
    "gothic revival": (18, 20),
    "moorish revival architecture": (19, 20),
    # Neoclassical and nineteenth-century historicist styles
    "neoclassical architecture": (18, 19),
    "neoclassicalism": (18, 19),
    "historicism": (19, 20),
    "historicist architecture": (19, 20),
    # Art Nouveau / twentieth-century styles
    "art nouveau architecture": (19, 20),
    "art noveau architecture": (19, 20),
    "art deco architecture": (20, 20),
    "new objectivity": (20, 20),
    "nachkriegsmoderne": (20, 20),
    "modern architecture": (20, 21),
    "postmodern architecture": (20, 21),
}

_GYEAR_PATTERN = re.compile(r"^([+-]?\d{4,})(?:Z|[+-]\d{2}:\d{2})?$")
_DATE_PATTERN = re.compile(r"^([+-]?\d{4,})-\d{2}-\d{2}(?:Z|[+-]\d{2}:\d{2})?$")


def normalize_label(value: str) -> str:
    """Normalize a style label for case-insensitive alias matching."""
    return " ".join(value.casefold().split())


def century_number(year: int) -> Optional[int]:
    """Return the requested calendar century number for a positive year."""
    if year < 1:
        return None
    return ((year - 1) // 100) + 1


def century_label(number: int) -> str:
    """Format a century number as the project vocabulary requires."""
    return f"century{number}"


def extract_year(value: Optional[str], datatype: Optional[str] = None) -> Optional[int]:
    """Extract a positive year from an ``xsd:gYear`` or ``xsd:date`` value.

    GraphDB returns the lexical value and datatype separately.  The datatype
    check prevents accidentally treating unrelated literals as dates while the
    lexical fallback keeps this helper convenient for unit tests and hand-built
    result rows.
    """
    if not value:
        return None
    if datatype and datatype not in (XSD_GYEAR, XSD_DATE):
        return None

    lexical_value = value.strip()
    if datatype == XSD_GYEAR:
        match = _GYEAR_PATTERN.match(lexical_value)
    elif datatype == XSD_DATE:
        match = _DATE_PATTERN.match(lexical_value)
    else:
        # Used only when a caller supplies a lexical value without its
        # datatype; accept the two supported date shapes, in that order.
        match = _GYEAR_PATTERN.match(lexical_value) or _DATE_PATTERN.match(lexical_value)
    if not match:
        return None

    try:
        year = int(match.group(1))
    except ValueError:
        return None
    return year if year >= 1 else None


def _row_value(row: Mapping[str, Mapping[str, str]], name: str) -> Optional[str]:
    binding = row.get(name)
    return binding.get("value") if binding else None


def _row_datatype(row: Mapping[str, Mapping[str, str]], name: str) -> Optional[str]:
    binding = row.get(name)
    return binding.get("datatype") if binding else None


def _add_range(graph: Graph, subject: URIRef, start: int, end: int) -> int:
    """Add an inclusive active-century range and return its triple count."""
    if start > end:
        return 0

    before = len(graph)
    for number in range(start, end + 1):
        graph.add((subject, ACTIVE_DURING_CENTURY, Literal(century_label(number))))
    return len(graph) - before


def _add_date_annotations(
        graph: Graph,
        subject: URIRef,
        start_years: Iterable[int],
        end_years: Iterable[int],
) -> None:
    """Add date boundary and active-century annotations for one subject."""
    start_centuries = {century_number(year) for year in start_years}
    end_centuries = {century_number(year) for year in end_years}
    start_centuries.discard(None)
    end_centuries.discard(None)

    for number in start_centuries:
        graph.add((subject, START_DATE_CENTURY, Literal(century_label(number))))
    for number in end_centuries:
        graph.add((subject, END_DATE_CENTURY, Literal(century_label(number))))

    if start_centuries and end_centuries:
        for start in start_centuries:
            for end in end_centuries:
                _add_range(graph, subject, start, end)
    elif start_centuries:
        # A known start with no end is active through the current model
        # horizon, century21.
        for start in start_centuries:
            _add_range(graph, subject, start, 21)
    else:
        for end in end_centuries:
            _add_range(graph, subject, end, end)


def _add_artist_annotations(
        graph: Graph,
        artist: URIRef,
        birth_years: Iterable[int],
        death_years: Iterable[int],
) -> None:
    """Add at most two active centuries for an artist.

    A known death date shortens the interval.  When the death date is absent,
    the artist's birth century and the following century are used, with
    century21 as the upper bound.
    """
    births = [century_number(year) for year in birth_years]
    deaths = [century_number(year) for year in death_years]
    births = [number for number in births if number is not None]
    deaths = [number for number in deaths if number is not None]

    if not births:
        return

    start = min(births)
    if deaths:
        end = max(deaths)
        if end < start:
            return
    else:
        end = min(start + 1, 21)

    # The requested artist rule is deliberately capped at two centuries.
    end = min(end, start + 1, 21)
    _add_range(graph, artist, start, end)


def _add_style_annotations(graph: Graph, style: URIRef, label: str) -> None:
    period = STYLE_PERIODS.get(normalize_label(label))
    if period is None:
        return

    start, end = period
    graph.add((style, START_DATE_CENTURY, Literal(century_label(start))))
    graph.add((style, END_DATE_CENTURY, Literal(century_label(end))))
    _add_range(graph, style, start, end)


def build_derived_graph(rows: Iterable[Mapping[str, Mapping[str, str]]]) -> Tuple[Graph, Dict[str, int]]:
    """Build all derived triples from SPARQL JSON result bindings."""
    subject_dates = defaultdict(lambda: {"start": set(), "end": set()})
    artist_dates = defaultdict(lambda: {"birth": set(), "death": set()})
    styles: Dict[str, Set[str]] = defaultdict(set)

    for row in rows:
        subject = _row_value(row, "subject")
        start_year = extract_year(_row_value(row, "startDate"), _row_datatype(row, "startDate"))
        end_year = extract_year(_row_value(row, "endDate"), _row_datatype(row, "endDate"))
        if subject and (start_year is not None or end_year is not None):
            if start_year is not None:
                subject_dates[subject]["start"].add(start_year)
            if end_year is not None:
                subject_dates[subject]["end"].add(end_year)

        artist = _row_value(row, "artist")
        birth_year = extract_year(_row_value(row, "birthDate"), _row_datatype(row, "birthDate"))
        death_year = extract_year(_row_value(row, "deathDate"), _row_datatype(row, "deathDate"))
        if artist and (birth_year is not None or death_year is not None):
            if birth_year is not None:
                artist_dates[artist]["birth"].add(birth_year)
            if death_year is not None:
                artist_dates[artist]["death"].add(death_year)

        style = _row_value(row, "style")
        style_label = _row_value(row, "styleLabel")
        if style and style_label:
            styles[style].add(style_label)

    graph = Graph()
    for subject, dates in subject_dates.items():
        _add_date_annotations(
            graph,
            URIRef(subject),
            dates["start"],
            dates["end"],
        )

    for artist, dates in artist_dates.items():
        _add_artist_annotations(
            graph,
            URIRef(artist),
            dates["birth"],
            dates["death"],
        )

    for style, labels in styles.items():
        for label in labels:
            _add_style_annotations(graph, URIRef(style), label)

    stats = {
        "subjects": len(subject_dates),
        "artists": len(artist_dates),
        "styles": sum(
            1
            for style, labels in styles.items()
            if any(normalize_label(label) in STYLE_PERIODS for label in labels)
        ),
        "triples": len(graph),
    }
    return graph, stats


class CategoricalDateTransformer:
    """Execute the date/style query and persist its derived triples."""

    def __init__(self, loader: Optional[GraphDBLoader] = None):
        self.loader = loader or GraphDBLoader()
        self.graphdb_sparql = getattr(self.loader, "sparql_url", GRAPHDB_SPARQL)

    def _select_rows(self):
        sparql = SPARQLWrapper(self.graphdb_sparql)
        sparql.setReturnFormat(JSON)
        sparql.setMethod(POST)
        sparql.setQuery(load_query("insert_categorical_dates.sparql"))
        return sparql.query().convert()["results"]["bindings"]

    @staticmethod
    def _delete_generated_triples() -> str:
        predicate_values = "\n".join(
            f"                <{predicate}>" for predicate in GENERATED_PREDICATES
        )
        return f"""
            DELETE {{ ?subject ?predicate ?object }}
            WHERE {{
                ?subject ?predicate ?object .
                VALUES ?predicate {{
                    {predicate_values}
                }}
            }}
        """

    @staticmethod
    def _insert_graph(graph: Graph) -> str:
        ntriples = graph.serialize(format="nt")
        return f"INSERT DATA {{\n{ntriples}\n}}"

    def run(self) -> Dict[str, int]:
        rows = self._select_rows()
        graph, stats = build_derived_graph(rows)

        if not self.loader.execute_sparql_update(self._delete_generated_triples()):
            raise RuntimeError("Failed to clear previously generated categorical-date triples")

        if len(graph) and not self.loader.execute_sparql_update(self._insert_graph(graph)):
            raise RuntimeError("Failed to insert categorical-date triples")

        print(
            "Categorical dates complete: "
            f"{stats['subjects']} subjects, {stats['artists']} artists, "
            f"{stats['styles']} architectural styles, {stats['triples']} triples"
        )
        return stats


if __name__ == "__main__":
    CategoricalDateTransformer().run()
