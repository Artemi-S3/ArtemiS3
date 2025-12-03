from pydantic import BaseModel
from typing import List, Optional

# NOTE: if you change the model, you must delete all of the indexes and reindex everything for the changes to be present
class MeiliDocumentModel(BaseModel):
    ID: str
    Key: str
    Size: int
    LastModified: str
    ContentType: str
    StorageClass: str
    Keywords: List[str]
    Tags: List[str]
    Prefix: Optional[str] = None

