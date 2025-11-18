from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class S3ObjectModel(BaseModel):
    key: str
    size: int
    last_modified: Optional[str] = None
    storage_class: Optional[datetime] = None
