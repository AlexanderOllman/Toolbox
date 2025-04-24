from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class RepositoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = []
    transport: str = "stdio"
    url: Optional[str] = ""
    read_timeout_seconds: Optional[int] = None
    read_transport_sse_timeout_seconds: int = 300
    headers: Optional[str] = "{}"
    api_key: Optional[str] = ""
    env: Optional[str] = "{}"
    roots_table: Optional[str] = ""

class RepositoryCreate(RepositoryBase):
    repo_url: str

class Repository(RepositoryBase):
    id: int
    
    class Config:
        from_attributes = True

class RepositoryInDB(Repository):
    pass

class ServerRoot(BaseModel):
    server_name: str
    uri: str
    name: Optional[str] = None
    server_uri_alias: Optional[str] = None 