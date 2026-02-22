from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), default="Metaphorical Architecture in The Great Gatsby")
    author = Column(String(200), default="")
    status = Column(String(50), default="draft")
    target_pages = Column(Integer, default=10)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sections = relationship("PaperSection", back_populates="paper", order_by="PaperSection.sort_order")


class PaperSection(Base):
    __tablename__ = "paper_sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    section_type = Column(String(50), nullable=False)
    topic_id = Column(Integer, nullable=True)
    title = Column(String(500), default="")
    content_en = Column(Text, default="")
    content_es = Column(Text, default="")
    content_zh = Column(Text, default="")
    target_words = Column(Integer, default=0)
    actual_words = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)

    paper = relationship("Paper", back_populates="sections")
