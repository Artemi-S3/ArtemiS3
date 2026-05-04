"""main.py

FastAPI application entrypoint for ArtemiS3 backend services."""

import asyncio
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import meilisearch
import psycopg
from app.api.s3_routes import s3_router
from app.s3.index_refresh import refresh_meili_index
from app.s3.utils import parse_s3_uri
from app.schemas.pg_models import MimeRecord

app = FastAPI(title="ArtemiS3 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

meilisearch_url = os.getenv("MEILISEARCH_URL")
meili_client = meilisearch.Client(meilisearch_url)

postgres_url = os.getenv("DATABASE_URL")

# routers for various API endpoint functionalities
app.include_router(s3_router)

# index refresh async block
REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", "3600"))
REFRESH_BUCKETS = os.getenv(
    "REFRESH_BUCKETS",
    # "s3://asc-astropedia"
    # "s3://asc-pds-services,"
    "s3://asc-pds-services/pigpen,s3://asc-astropedia/Mars"
)


def _parse_refresh_targets():
    """Parse configured refresh targets into a list of non-empty S3 URIs."""
    return [s.strip() for s in REFRESH_BUCKETS.split(",") if s.strip()]


async def _index_refresh_loop():
    """Continuously refresh configured S3 targets into Meilisearch indexes."""
    await asyncio.sleep(2)  # let app start
    print("Starting index refresh loop...")
    while True:
        for s3_uri in _parse_refresh_targets():
            print(f"Trying to reindex: {s3_uri}")
            try:
                bucket, prefix = parse_s3_uri(s3_uri)
                await asyncio.to_thread(refresh_meili_index, bucket, prefix, s3_uri=s3_uri)

            except Exception as e:
                print(f"Refresh failed: s3_uri={s3_uri}, error={str(e)}")
        print(f"Waiting {REFRESH_INTERVAL_SECONDS} seconds...")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


@app.on_event("startup")
async def start_refresh_scheduler():
    """Start the background refresh loop when the API boots."""
    asyncio.create_task(_index_refresh_loop())


@app.get("/api/health")
def health() -> dict:
    """Return a simple API health check payload."""
    return {"status": "ok"}


@app.get("/api/test")
def test(name: str = "world") -> dict:
    """Return a greeting payload used for connectivity testing."""
    return {"message": f"Hello, {name}!"}


@app.get("/api/meilisearch/test")
def test() -> dict:
    """Return Meilisearch health status as seen from the backend."""
    health = meili_client.health()
    return {"status": health}


@app.get("/api/postgres/test")
def test() -> dict:
    """Return simple database inspection data for troubleshooting."""
    with psycopg.connect(postgres_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'""")
            tables = [table for table in cur.fetchall()]
            cur.execute("""SELECT * FROM file_tags""")
            records = [record for record in cur.fetchall()]
            cur.execute("""SELECT * FROM custom_mime_types""")
            mime_types = [mime for mime in cur.fetchall()]
    return {"tables": tables, "records": records, "mime_types": mime_types}


@app.post("/api/postgres/mime")
def add_mime(data: MimeRecord):
    """Insert or update a custom file-extension to MIME-type mapping."""
    postgres_url = os.getenv("DATABASE_URL")
    try:
        with psycopg.connect(postgres_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO custom_mime_types (extension, mime_type) VALUES (%s, %s) 
                                ON CONFLICT (extension) DO UPDATE SET mime_type = EXCLUDED.mime_type""",
                            (data.extension, data.mime_type,))
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error encountered while storing mime type to database."
        )


@app.delete("/api/postgres/mime/{extension}")
def delete_mime(extension: str):
    """Delete a custom MIME mapping by extension."""
    postgres_url = os.getenv("DATABASE_URL")
    try:
        with psycopg.connect(postgres_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM custom_mime_types WHERE extension=%s""", (extension,))
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error encountered while deleting mime type from database."
        )
