from pydantic import BaseModel


class MetaphorExtracted(BaseModel):
    exact_quote: str
    explanation: str
    meaning: str
    confidence: float = 0.0
    suggested_topic: str = ""


class MetaphorExtractionResult(BaseModel):
    metaphors: list[MetaphorExtracted]


class MetaphorOut(BaseModel):
    id: int
    chapter_id: int
    chapter_number: str = ""
    exact_quote: str
    explanation: str
    meaning: str
    suggested_topic: str
    topic_id: int | None = None
    topic_name: str | None = None
    subtopic_id: int | None = None
    selected: bool
    user_notes: str | None = None
    confidence: float

    class Config:
        from_attributes = True


class MetaphorUpdate(BaseModel):
    explanation: str | None = None
    meaning: str | None = None
    selected: bool | None = None
    user_notes: str | None = None
    topic_id: int | None = None
    subtopic_id: int | None = None


class ChapterOut(BaseModel):
    id: int
    number: str
    title: str
    word_count: int
    processed: bool
    metaphor_count: int = 0

    class Config:
        from_attributes = True


class TopicOut(BaseModel):
    id: int
    name: str
    description: str
    sort_order: int
    metaphor_count: int = 0

    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    name: str
    description: str = ""
