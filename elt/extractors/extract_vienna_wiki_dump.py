"""Streaming extractor for a full Vienna History Wiki RDF dump.

The dump is a gzipped RDF/XML document containing every ``swivt:Subject`` /
``owl:Class`` block of the wiki in one file (uncompressed size is roughly 1 GB).
We therefore never decompress it to disk and never load the whole document into
memory.  Instead we stream the gzip file twice:

1. an indexing pass that maps category pages to their member "type" URIs and
   records which main-namespace pages carry each ``rdf:type``;
2. a slicing pass that copies the selected ``swivt:Subject`` clusters (the main
   page plus its ``swivt:masterPage`` subobjects/queries) into the same batched
   files that the live :class:`ViennaHistoryWikiExtractor` produces.

The selection logic deliberately mirrors ``extract_entities_from_category``:
only main-namespace pages (``swivt:wikiNamespace`` = 0) with an
``rdfs:isDefinedBy`` are eligible, and membership is decided by the category's
export type (either the ``Category-3A...`` URI or the imported ``schema.org``
type).
"""

import gzip
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from rdflib import Graph, Namespace
from rdflib.namespace import RDFS

from elt.config import CATEGORIES, RAW_BASE, RAW_RELATED, resolve_dump_path

SCHEMA = Namespace("https://schema.org/")
PROPERTY = Namespace("http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A")
URI_RESOLVER = "http://www.geschichtewiki.wien.gv.at/Special:URIResolver/"

# Namespaces declared on the <rdf:RDF> root of the dump.  The individual block
# text is copied verbatim, so only these root-level declarations must be
# reproduced in the batched output files.
RDF_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE rdf:RDF[
\t<!ENTITY rdf 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
\t<!ENTITY rdfs 'http://www.w3.org/2000/01/rdf-schema#'>
\t<!ENTITY owl 'http://www.w3.org/2002/07/owl#'>
\t<!ENTITY swivt 'http://semantic-mediawiki.org/swivt/1.0#'>
\t<!ENTITY wiki 'http://www.geschichtewiki.wien.gv.at/Special:URIResolver/'>
\t<!ENTITY category 'http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Category-3A'>
\t<!ENTITY property 'http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A'>
\t<!ENTITY wikiurl 'https://www.geschichtewiki.wien.gv.at/'>
]>

<rdf:RDF
\txmlns:rdf="&rdf;"
\txmlns:rdfs="&rdfs;"
\txmlns:owl ="&owl;"
\txmlns:swivt="&swivt;"
\txmlns:wiki="&wiki;"
\txmlns:category="&category;"
\txmlns:property="&property;"
\txmlns:skos="http://www.w3.org/2004/02/skos/core#"
\txmlns:schema="https://schema.org/">

\t<owl:Ontology>
\t\t<owl:imports rdf:resource="http://semantic-mediawiki.org/swivt/1.0"/>
\t</owl:Ontology>
"""

RDF_FOOTER = "</rdf:RDF>\n"

_BLOCK_START_RE = re.compile(r"^\s*<(swivt:Subject|owl:Class)\b")
_BLOCK_END_RE = re.compile(r"^\s*</(swivt:Subject|owl:Class)>\s*$")
_ABOUT_RE = re.compile(r"<(?:swivt:Subject|owl:Class)\b[^>]*\brdf:about=\"([^\"]*)\"")
_DEFINED_BY_RE = re.compile(r"<rdfs:isDefinedBy\s+[^>]*rdf:resource=\"([^\"]*)\"")
_NAMESPACE_RE = re.compile(r"<swivt:wikiNamespace[^>]*>([^<]*)</swivt:wikiNamespace>")
_TYPE_RE = re.compile(r"<rdf:type\s+[^>]*rdf:resource=\"([^\"]*)\"")
_MASTER_RE = re.compile(r"<swivt:masterPage\s+[^>]*rdf:resource=\"([^\"]*)\"")

_CATEGORY_EXPORT_MARKER = "/Special:ExportRDF/Kategorie-3A"

_ENTITY_URIS = {
    "wiki": URI_RESOLVER,
    "category": URI_RESOLVER + "Category-3A",
    "property": URI_RESOLVER + "Property-3A",
}


@dataclass
class _BlockMeta:
    about: Optional[str] = None
    defined_by: Optional[str] = None
    namespace: Optional[str] = None
    types: Tuple[str, ...] = ()
    master_page: Optional[str] = None


def _expand_entity_refs(value: Optional[str]) -> Optional[str]:
    """Expand SMW's internal XML entity references (``&wiki;`` etc.)."""
    if not value:
        return value
    for name, uri in _ENTITY_URIS.items():
        ref = f"&{name};"
        if value.startswith(ref):
            return uri + value[len(ref):]
    return value


def _decode_wiki_page_name(encoded: str) -> str:
    """Decode an SMW export URL page name.

    ``Kategorie-3ABrücke`` -> ``Kategorie:Brücke`` and
    ``Griechisch-2Dorthodoxe_Kirche`` -> ``Griechisch-orthodoxe Kirche``.
    ``_`` encodes a space and ``-XX`` encodes the character with the given
    uppercase hex code point.
    """
    out: List[str] = []
    i = 0
    while i < len(encoded):
        ch = encoded[i]
        if ch == "_":
            out.append(" ")
            i += 1
        elif ch == "-" and i + 2 < len(encoded):
            hexpart = encoded[i + 1:i + 3]
            if all(c in "0123456789ABCDEF" for c in hexpart):
                out.append(chr(int(hexpart, 16)))
                i += 3
                continue
            out.append(ch)
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _parse_block(block_text: str) -> _BlockMeta:
    about_match = _ABOUT_RE.search(block_text)
    defined_match = _DEFINED_BY_RE.search(block_text)
    ns_match = _NAMESPACE_RE.search(block_text)
    master_match = _MASTER_RE.search(block_text)
    types = tuple(
        expanded
        for raw in _TYPE_RE.findall(block_text)
        if (expanded := _expand_entity_refs(raw))
    )
    return _BlockMeta(
        about=_expand_entity_refs(about_match.group(1)) if about_match else None,
        defined_by=_expand_entity_refs(defined_match.group(1)) if defined_match else None,
        namespace=ns_match.group(1) if ns_match else None,
        types=types,
        master_page=_expand_entity_refs(master_match.group(1)) if master_match else None,
    )


class DumpWikiExtractor:
    """Extract base and related entities from a Vienna History Wiki dump."""

    def __init__(self, dump_path=None, batch_size: int = 100):
        self.dump_path = resolve_dump_path(dump_path)
        if self.dump_path is None:
            raise FileNotFoundError(
                "No Vienna History Wiki dump found. Place it at "
                "data/dump/ViennaHistoryWiki.rdf.gz or pass --dump-path."
            )
        self.batch_size = batch_size

    # ------------------------------------------------------------------ #
    # Streaming helpers
    # ------------------------------------------------------------------ #
    def _iter_blocks(self) -> Iterator[str]:
        """Yield the raw XML text of each top-level Subject/Class block."""
        with gzip.open(self.dump_path, "rt", encoding="utf-8") as handle:
            block_lines: List[str] = []
            in_block = False
            for line in handle:
                if not in_block:
                    if _BLOCK_START_RE.match(line) and "/>" not in line:
                        in_block = True
                        block_lines = [line]
                else:
                    block_lines.append(line)
                    if _BLOCK_END_RE.match(line):
                        in_block = False
                        yield "".join(block_lines)
                        block_lines = []

    def _index(self) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
        """First pass: category export types and rdf:type membership index."""
        category_types: Dict[str, str] = {}
        type_to_pages: Dict[str, Set[str]] = defaultdict(set)

        for block_text in self._iter_blocks():
            meta = _parse_block(block_text)

            if (
                meta.about
                and meta.defined_by
                and _CATEGORY_EXPORT_MARKER in meta.defined_by
            ):
                encoded = meta.defined_by.split(_CATEGORY_EXPORT_MARKER, 1)[1]
                name = "Kategorie:" + _decode_wiki_page_name(encoded)
                category_types[name] = meta.about

            if meta.namespace == "0" and meta.defined_by and meta.about:
                for type_uri in meta.types:
                    type_to_pages[type_uri].add(meta.about)

        return category_types, type_to_pages

    def _collect_clusters(
        self, page_to_group: Dict[str, str]
    ) -> Iterator[Tuple[str, List[str]]]:
        """Second pass: yield (group, [raw block texts]) for selected pages.

        Subobject/query blocks follow their main page in the dump and are
        attached to the current cluster via ``swivt:masterPage``.
        """
        current_page: Optional[str] = None
        current_group: Optional[str] = None
        current_blocks: List[str] = []

        for block_text in self._iter_blocks():
            meta = _parse_block(block_text)

            if meta.master_page is not None:
                if current_page is not None and meta.master_page == current_page:
                    current_blocks.append(block_text)
                continue

            # A new top-level page (main or category) ends the previous cluster.
            if current_page is not None and current_group is not None:
                yield current_group, current_blocks
            current_page = None
            current_group = None
            current_blocks = []

            if (
                meta.namespace == "0"
                and meta.defined_by
                and meta.about
                and meta.about in page_to_group
            ):
                current_page = meta.about
                current_group = page_to_group[meta.about]
                current_blocks = [block_text]

        if current_page is not None and current_group is not None:
            yield current_group, current_blocks

    @staticmethod
    def _clear_group_batches(group: str, output_dir: str) -> None:
        """Remove stale batch files for a group before writing new ones."""
        output = Path(output_dir)
        if not output.exists():
            return
        for path in output.glob(f"{group}_*.rdf"):
            try:
                path.unlink()
            except OSError:
                pass

    @staticmethod
    def _write_one_batch(
        group: str,
        start: int,
        end: int,
        clusters: List[List[str]],
        output_dir: str,
    ) -> None:
        filename = f"{group}_{start}_{end}.rdf"
        path = Path(output_dir) / filename
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(RDF_HEADER)
            for blocks in clusters:
                handle.write("".join(blocks))
            handle.write(RDF_FOOTER)
        print(f"Wrote {len(clusters)} entities to {filename}")

    def _route_and_write(
        self,
        cluster_iter: Iterator[Tuple[str, List[str]]],
        output_dir: str,
    ) -> Dict[str, int]:
        """Buffer clusters per group and write each group in batch_size chunks."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        pending: Dict[str, List[List[str]]] = defaultdict(list)
        start_index: Dict[str, int] = defaultdict(int)
        total: Dict[str, int] = defaultdict(int)

        for group, blocks in cluster_iter:
            pending[group].append(blocks)
            total[group] += 1
            if len(pending[group]) == self.batch_size:
                self._write_one_batch(
                    group, start_index[group], total[group] - 1, pending[group], output_dir
                )
                start_index[group] = total[group]
                pending[group] = []

        for group, blocks in pending.items():
            if blocks:
                self._write_one_batch(
                    group, start_index[group], total[group] - 1, blocks, output_dir
                )

        return dict(total)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def extract_base_entities(self, output_dir: str = RAW_BASE) -> Dict[str, int]:
        """Extract the same base entities as the live category extraction."""
        print(f"Indexing dump: {self.dump_path}")
        category_types, type_to_pages = self._index()

        page_to_group: Dict[str, str] = {}
        counts: Dict[str, int] = {}

        for group, category_names in CATEGORIES.items():
            target_types = {
                category_types[name]
                for name in category_names
                if name in category_types
            }
            missing = [name for name in category_names if name not in category_types]
            if missing:
                print(f"Warning: {group} categories not found in dump: {missing}")

            pages: Set[str] = set()
            for type_uri in target_types:
                pages.update(type_to_pages.get(type_uri, set()))

            for page in pages:
                page_to_group.setdefault(page, group)
            counts[group] = len(pages)
            print(f"{group}: {len(pages)} entities selected from dump")

        # Free the per-type index before the second full pass.
        del type_to_pages

        for group in CATEGORIES:
            self._clear_group_batches(group, output_dir)

        self._route_and_write(self._collect_clusters(page_to_group), output_dir)

        return counts

    def extract_related_from_dump(
        self,
        base_dir: str = RAW_BASE,
        output_dir: str = RAW_RELATED,
    ) -> Dict[str, int]:
        """Discover related entities from local base files and slice the dump.

        Mirrors ``extract_related_entities.sparql`` without requiring GraphDB:
        ``schema:artist`` (architects), ``schema:relatedTo`` (inhabitants) and
        ``property:Benannt_nach`` (named after) targets are selected when they
        are wiki URIResolver URIs and do not already have an ``rdfs:label`` in
        the base data.
        """
        related_groups = {
            "architects": SCHEMA.artist,
            "inhabitants": SCHEMA.relatedTo,
            "named_after": PROPERTY["Benannt_nach"],
        }

        labeled: Set[str] = set()
        related_pages: Dict[str, Set[str]] = {group: set() for group in related_groups}

        base_files = sorted(Path(base_dir).glob("**/*.rdf"))
        print(f"Scanning {len(base_files)} base files for related entities...")

        for file_path in base_files:
            graph = Graph()
            graph.parse(str(file_path), format="xml")

            for subject in graph.subjects(None, RDFS.label):
                labeled.add(str(subject))

            for group, predicate in related_groups.items():
                for obj in graph.objects(None, predicate):
                    uri = str(obj)
                    if uri.startswith(URI_RESOLVER):
                        related_pages[group].add(uri)

        page_to_group: Dict[str, str] = {}
        counts: Dict[str, int] = {}
        for group, pages in related_pages.items():
            # Only entities without their own data in the base export.
            filtered = {page for page in pages if page not in labeled}
            for page in filtered:
                page_to_group.setdefault(page, group)
            counts[group] = len(filtered)
            print(f"{group}: {len(filtered)} related entities discovered")
            self._clear_group_batches(group, output_dir)

        written = self._route_and_write(self._collect_clusters(page_to_group), output_dir)
        for group, discovered in counts.items():
            print(
                f"{group}: sliced {written.get(group, 0)} of {discovered} pages from dump"
            )

        return counts


if __name__ == "__main__":
    extractor = DumpWikiExtractor()
    extractor.extract_base_entities()
