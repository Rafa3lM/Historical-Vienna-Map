from SPARQLWrapper import SPARQLWrapper

GRAPHDB_UPDATE = "http://localhost:7200/repositories/vienna/statements"

def run_update():
    sparql = SPARQLWrapper(GRAPHDB_UPDATE)
    with open("../queries/insert_geo.sparql", "r", encoding="utf-8") as f:
        query = f.read()

    sparql.setQuery(query)
    sparql.method = "POST"
    sparql.query()

    print("Geo Data inserted")

if __name__ == "__main__":
    run_update()