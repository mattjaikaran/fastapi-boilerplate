# Vector Store (pgvector)

Optional pgvector service for storing embeddings next to the rest of the stack.
It is off by default and only starts under the `vector` compose profile.

---

## Enable it

```bash
docker compose --profile vector up -d
```

The service runs `pgvector/pgvector:pg17` with its own `pgvector_data` volume,
reachable on host port `5433` (override with `VECTOR_POSTGRES_PORT`). Inside the
compose network the hostname is `pgvector` and the port is `5432`.

Without the profile the service is not created:

```bash
docker compose config --services   # no pgvector
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `VECTOR_POSTGRES_PORT` | `5433` | Host port published by the `pgvector` service |
| `VECTOR_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/app_db` | SQLAlchemy URL for the vector database |
| `EMBEDDING_DIMENSIONS` | `1536` | Width of the embedding vectors; match your model and column |

`EMBEDDING_DIMENSIONS` must match the model that produces the embeddings
(1536 for OpenAI `text-embedding-3-small`) and the `vector(n)` column you
create.

## The extension

Migration `0004_enable_pgvector` runs `CREATE EXTENSION IF NOT EXISTS vector`,
guarded by `pg_available_extensions`. On the default `postgres:17-alpine`
image the extension is unavailable and the migration is a no-op. On the
`pgvector/pgvector` image it enables the extension when you run migrations
against that database.

```bash
alembic upgrade head   # against the vector database
```

## One-table example

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id bigserial PRIMARY KEY,
    content text NOT NULL,
    embedding vector(1536) NOT NULL
);

CREATE INDEX documents_embedding_idx
    ON documents USING hnsw (embedding vector_cosine_ops);
```

Query the closest documents (the `<=>` operator is cosine distance, so a
smaller value is a better match):

```python
from pgvector.asyncpg import register_vector

await conn.execute(register_vector)

rows = await conn.fetch(
    """
    SELECT id, content, embedding <=> $1 AS distance
    FROM documents
    ORDER BY embedding <=> $1
    LIMIT 5
    """,
    query_embedding,
)
```

## Client package

The `pgvector` Python package lives in the `vector` extra:

```bash
uv sync --extra vector
```

It provides the `vector` SQLAlchemy type and the asyncpg codec registration
used above. Embedding generation and retrieval endpoints are out of scope for
this service.
