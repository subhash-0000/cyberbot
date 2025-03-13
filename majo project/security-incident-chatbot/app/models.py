from sqlalchemy import Column, Integer, String, DateTime, Text
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.database import Base

# SQLAlchemy Model
class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    jira_ticket_id = Column(String(50), nullable=True)

# Pydantic Models for API
class AlertBase(BaseModel):
    source: str
    message: str

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    severity: str
    created_at: datetime
    jira_ticket_id: Optional[str] = None
    
    class Config:
        orm_mode = True