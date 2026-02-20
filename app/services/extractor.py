from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metaphor import Chapter, Metaphor
from app.schemas.llm import LLMRequest
from app.services.llm_provider import get_provider
from app.services.prompt_guard import sanitize_book_text

SYSTEM_PROMPT = """You are a literary scholar specializing in American modernist literature \
and F. Scott Fitzgerald. You identify metaphors with academic precision, considering the \
historical context of 1920s America, the Jazz Age, and the novel's themes of the American \
Dream, class, and moral decay."""

EXTRACTION_PROMPT = """Analyze Chapter {number} of The Great Gatsby below. Extract every metaphor, including:
- Similes, extended metaphors, implied metaphors, symbolic imagery
- Both obvious and subtle figurative language
- Personification, metonymy, synecdoche where they function metaphorically

For each metaphor found, record it using the tool provided.

Known metaphor systems (use as guidance, not constraint — identify new systems too):
- Light/Darkness: Green light, starlight, illumination imagery
- Water/Drowning: Boats against the current, swimming, drowning, flow
- Vision/Surveillance: Eckleburg's eyes, watching, seeing without acting
- Time: Past/future tension, clocks, seasons, repetition
- Money as Substance: "voice full of money", material wealth as intrinsic quality
- Nature Perverted: Valley of Ashes, corrupted natural imagery

Be thorough. Include every instance even if the same metaphor system appears multiple times.
Academic rigor matters — quote the exact text.

Chapter {number} text:
---
{text}
---"""

TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "metaphors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "exact_quote": {
                        "type": "string",
                        "description": "The verbatim text from the passage",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Why this is a metaphor and what figurative device is used",
                    },
                    "meaning": {
                        "type": "string",
                        "description": "What it means in 1920s American context and the novel's themes",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score 0.0-1.0",
                    },
                    "suggested_topic": {
                        "type": "string",
                        "description": "Suggested topic category",
                    },
                },
                "required": ["exact_quote", "explanation", "meaning", "confidence", "suggested_topic"],
            },
        }
    },
    "required": ["metaphors"],
}


async def extract_chapter(db: AsyncSession, chapter: Chapter) -> list[Metaphor]:
    sanitized_text = sanitize_book_text(chapter.text)
    prompt = EXTRACTION_PROMPT.format(number=chapter.number, text=sanitized_text)

    provider = get_provider()
    result = await provider.complete_structured(
        LLMRequest(system=SYSTEM_PROMPT, prompt=prompt, max_tokens=8192, temperature=0.2),
        tool_name="record_metaphors",
        tool_schema=TOOL_SCHEMA,
    )

    metaphors = []
    for item in result.get("metaphors", []):
        m = Metaphor(
            chapter_id=chapter.id,
            exact_quote=item["exact_quote"],
            explanation=item["explanation"],
            meaning=item["meaning"],
            confidence=item.get("confidence", 0.0),
            suggested_topic=item.get("suggested_topic", ""),
            selected=True,
        )
        db.add(m)
        metaphors.append(m)

    chapter.processed = True
    await db.commit()

    return metaphors


async def extract_all(db: AsyncSession):
    chapters = await db.execute(
        select(Chapter).where(Chapter.processed == False).order_by(Chapter.id)
    )
    for chapter in chapters.scalars().all():
        yield chapter.number, "processing"
        await extract_chapter(db, chapter)
        yield chapter.number, "complete"


async def get_extraction_stats(db: AsyncSession) -> dict:
    total_chapters = await db.execute(select(func.count(Chapter.id)))
    processed = await db.execute(
        select(func.count(Chapter.id)).where(Chapter.processed == True)
    )
    total_metaphors = await db.execute(select(func.count(Metaphor.id)))

    return {
        "total_chapters": total_chapters.scalar() or 0,
        "processed_chapters": processed.scalar() or 0,
        "total_metaphors": total_metaphors.scalar() or 0,
    }
