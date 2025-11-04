from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ArtemiS3 API")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/api/test")
def test(name: str = "world") -> dict:
    return {"message": f"Hello, {name}!"}
