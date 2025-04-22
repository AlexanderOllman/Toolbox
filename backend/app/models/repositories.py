from pydantic import BaseModel
from typing import List, Optional

class RepositoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = []

class RepositoryCreate(RepositoryBase):
    repo_url: str

class Repository(RepositoryBase):
    id: int
    
    class Config:
        from_attributes = True

class RepositoryInDB(Repository):
    pass 