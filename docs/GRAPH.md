# Graph Database (Neo4j)

Optional Neo4j service for graph data. It runs only with the `graph` Compose
profile and the app starts normally when it is not running.

---

## Start Neo4j

```bash
cp .env.example .env            # if you have not already
docker compose --profile graph up -d neo4j
```

| Port | Purpose |
|---|---|
| 7474 | Neo4j Browser (HTTP) |
| 7687 | Bolt driver endpoint |

Connection settings come from `.env`:

| Variable | Default | Notes |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Bolt URL |
| `NEO4J_USER` | `neo4j` | Database user |
| `NEO4J_PASSWORD` | — | Placeholder in `.env.example`; change it |

The Compose service passes the credentials as `NEO4J_AUTH` and checks health
with `cypher-shell`. View status and logs with:

```bash
docker compose --profile graph ps neo4j
docker compose --profile graph logs neo4j
```

Open <http://localhost:7474> to use Neo4j Browser with the same credentials.

---

## Python driver

The `neo4j` driver is an optional extra, so install it only when graph support
is needed:

```bash
uv sync --extra graph
```

`Neo4jClient` creates its driver on first use. Importing the app never connects
to Neo4j, and `get_neo4j_client()` returns a process-wide singleton:

```python
from app.services.graph import get_neo4j_client

client = get_neo4j_client()
await client.connect()

try:
    rows = await client.run(
        "MERGE (p:Person {name: $name}) RETURN p.name AS name",
        {"name": "Ada"},
    )
    print(rows)  # [{"name": "Ada"}]
finally:
    await client.close()
```

`run(query, params)` accepts a Cypher string and an optional parameter
dictionary, and returns the records as a list of dictionaries. Call `connect()`
at startup when you want to fail fast if Neo4j is unreachable; otherwise the
first `run()` creates and uses the driver.

---

## Health

Neo4j is not part of `/api/health/ready` because it is optional. Check the
container directly:

```bash
docker compose --profile graph ps neo4j
docker compose --profile graph exec neo4j sh -c \
  'cypher-shell -u "${NEO4J_AUTH%%/*}" -p "${NEO4J_AUTH#*/}" "RETURN 1"'
```

Or call `client.connect()` from application code, which raises when the
database is unreachable.
