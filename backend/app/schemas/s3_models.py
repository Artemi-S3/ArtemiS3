from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class S3ObjectModel(BaseModel):
    key: str
    size: int
    last_modified: Optional[datetime] = None
    storage_class: Optional[str] = None
