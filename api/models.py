from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Scenario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sim_type: str
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"
    execution_time: Optional[float] = None