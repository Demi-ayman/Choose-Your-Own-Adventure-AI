from sqlalchemy import Column, Integer, String, DateTime 
from sqlalchemy.sql import func
from db.database import Base

class StoryJob(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    status = Column(String, default="pending")  # optional
    theme = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    session_id = Column(String, index=True)
    story_id = Column(Integer, index=True, nullable=True)  # match Story.id type
    error = Column(String, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)