from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.database import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)
    number = Column(String(10), nullable=False)
    title = Column(String(200), default="")
    text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    processed = Column(Boolean, default=False)

    metaphors = relationship("Metaphor", back_populates="chapter")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)

    subtopics = relationship("Subtopic", back_populates="topic")
    metaphors = relationship("Metaphor", back_populates="topic")


class Subtopic(Base):
    __tablename__ = "subtopics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)

    topic = relationship("Topic", back_populates="subtopics")
    metaphors = relationship("Metaphor", back_populates="subtopic")


class Metaphor(Base):
    __tablename__ = "metaphors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    exact_quote = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    meaning = Column(Text, nullable=False)
    suggested_topic = Column(String(200), default="")
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)
    selected = Column(Boolean, default=True)
    user_notes = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)

    chapter = relationship("Chapter", back_populates="metaphors")
    topic = relationship("Topic", back_populates="metaphors")
    subtopic = relationship("Subtopic", back_populates="metaphors")
