from pydantic import BaseModel


class SectionConfig(BaseModel):
    section_type: str
    topic_id: int | None = None
    title: str = ""
    target_words: int = 0


class PaperConfig(BaseModel):
    title: str = "Metaphorical Architecture in The Great Gatsby"
    author: str = ""
    target_pages: int = 10
    sections: list[SectionConfig] = []


class PaperSectionOut(BaseModel):
    id: int
    section_type: str
    topic_id: int | None
    title: str
    content_en: str
    content_es: str
    content_zh: str
    target_words: int
    actual_words: int
    sort_order: int

    class Config:
        from_attributes = True


class PaperOut(BaseModel):
    id: int
    title: str
    author: str
    status: str
    target_pages: int
    sections: list[PaperSectionOut] = []

    class Config:
        from_attributes = True
