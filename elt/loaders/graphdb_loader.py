import requests
from pathlib import Path
import time

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import GRAPHDB_UPDATE, GRAPHDB_SPARQL


class GraphDBLoader:
    """Automated loader for GraphDB"""

    def __init__(self, repository_url=GRAPHDB_UPDATE):
        self.repository_url = repository_url
        self.sparql_url = GRAPHDB_SPARQL

    def load_file(self, filepath: str, context: str = None) -> bool:
        """Load RDF file into GraphDB"""
        print(f"Loading {filepath}...")

        # Detect format from extension
        format_map = {
            '.ttl': 'text/turtle',
            '.rdf': 'application/rdf+xml',
            '.xml': 'application/rdf+xml',
            '.nt': 'application/n-triples',
            '.jsonld': 'application/ld+json'
        }

        ext = Path(filepath).suffix.lower()
        content_type = format_map.get(ext, 'application/rdf+xml')

        try:
            with open(filepath, 'rb') as f:
                data = f.read()
        except Exception as e:
            print(f"Error reading file {filepath}: {str(e)}")
            return False

        headers = {'Content-Type': content_type}
        params = {}

        if context:
            params['context'] = f'<{context}>'

        try:
            response = requests.post(
                self.repository_url,
                data=data,
                headers=headers,
                params=params,
                timeout=60
            )

            if response.status_code in [200, 201, 204]:
                print(f"Successfully loaded {Path(filepath).name}")
                return True
            else:
                print(f"Failed to load {filepath}: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"Error loading {filepath}: {str(e)}")
            return False

    def load_directory(self, directory: str, pattern: str = "**/*.rdf") -> int:
        """Load all matching files from directory"""
        files = list(Path(directory).glob(pattern))
        print(f"\nFound {len(files)} files matching '{pattern}' in {directory}")

        if len(files) == 0:
            print(f"No files found matching pattern '{pattern}'")
            return 0

        success_count = 0
        failed_files = []

        for i, filepath in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] ", end="")
            if self.load_file(str(filepath)):
                success_count += 1
            else:
                failed_files.append(filepath)

            # Rate limiting - be nice to GraphDB
            if i < len(files):
                time.sleep(0.5)

        print(f"\n{'=' * 60}")
        print(f"Loaded {success_count}/{len(files)} files successfully")

        if failed_files:
            print(f"\nFailed files:")
            for f in failed_files:
                print(f"  - {f}")

        return success_count

    def execute_sparql_update(self, query: str) -> bool:
        """Execute SPARQL UPDATE query"""
        headers = {
            'Content-Type': 'application/sparql-update',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.repository_url,
                data=query.encode('utf-8'),
                headers=headers,
                timeout=120
            )

            if response.status_code in [200, 201, 204]:
                print("SPARQL update executed successfully")
                return True
            else:
                print(f"SPARQL update failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False

        except Exception as e:
            print(f"Error executing SPARQL update: {str(e)}")
            return False

    def execute_sparql_file(self, filepath: str) -> bool:
        """Execute SPARQL UPDATE from file"""
        print(f"Executing SPARQL from {filepath}...")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                query = f.read()
        except Exception as e:
            print(f"Error reading SPARQL file: {str(e)}")
            return False

        return self.execute_sparql_update(query)

    def clear_repository(self, confirm=False) -> bool:
        """Clear all data from repository (use with caution!)"""
        if not confirm:
            print("Repository clear requires confirmation. Set confirm=True")
            return False

        query = "CLEAR ALL"
        print("Clearing repository...")
        result = self.execute_sparql_update(query)

        if result:
            print("Repository cleared")

        return result

    def get_triple_count(self) -> int:
        """Get total number of triples in repository"""
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"

        headers = {'Accept': 'application/sparql-results+json'}
        params = {'query': query}

        try:
            response = requests.get(
                self.sparql_url,
                params=params,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                count = int(results['results']['bindings'][0]['count']['value'])
                return count
            else:
                print(f"Error getting triple count: {response.status_code}")
                return -1

        except Exception as e:
            print(f"Error getting triple count: {e}")
            return -1

    def test_connection(self) -> bool:
        """Test connection to GraphDB"""
        try:
            response = requests.get(self.sparql_url, timeout=5)
            if response.status_code == 200:
                print("GraphDB connection successful")
                return True
            else:
                print(f"GraphDB returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"Cannot connect to GraphDB: {e}")
            print(f"Make sure GraphDB is running at {self.sparql_url}")
            return False


# Test when run directly
if __name__ == "__main__":
    loader = GraphDBLoader()

    print("Testing GraphDB connection...")
    if loader.test_connection():
        count = loader.get_triple_count()
        print(f"Current triples in database: {count:,}")
