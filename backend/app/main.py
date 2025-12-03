import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from app.api.s3_routes import s3_router
import meilisearch

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

# routers for various API endpoint functionalities
app.include_router(s3_router)

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/api/test")
def test(name: str = "world") -> dict:
    return {"message": f"Hello, {name}!"}

@app.get("/api/meilisearch/test")
def test() -> dict:
    health = meili_client.health()
    return {"status": health}
