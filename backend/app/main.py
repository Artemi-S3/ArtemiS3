from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

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

class FilterRequest(BaseModel):
    selected_types: List[str]
    date: Optional[str] = None
    condition: Optional[str] = None

@app.post("/api/filter")
def receive_filter(filter_request: FilterRequest):
    print("Received filter request:")
    print("Selected types:", filter_request.selected_types)
    print("Date:", filter_request.date)
    print("Condition:", filter_request.condition)
    # You can add logic here to actually filter your data
    return {"status": "ok", "received": filter_request.dict()}