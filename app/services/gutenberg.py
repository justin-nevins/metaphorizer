import re

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.metaphor import Chapter


# Match centered Roman numerals (chapter markers in Gutenberg text)
# The text has lines like "                                  I\r" (lots of leading spaces)
CHAPTER_PATTERN = re.compile(
    r"^\s{20,}(I{1,3}|IV|V|VI{1,3}|IX)\s*$",
    re.MULTILINE,
)

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9,
}


async def fetch_text() -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(settings.gutenberg_url, timeout=30)
        resp.raise_for_status()
    # Normalize line endings
    return resp.text.replace('\r\n', '\n').replace('\r', '\n')


def parse_chapters(text: str) -> list[dict]:
    # Strip Gutenberg header/footer
    start_markers = ["*** START OF THE PROJECT GUTENBERG EBOOK", "***START OF"]
    end_markers = ["*** END OF THE PROJECT GUTENBERG EBOOK", "***END OF"]

    body = text
    for marker in start_markers:
        if marker in body:
            body = body.split(marker, 1)[1]
            break
    for marker in end_markers:
        if marker in body:
            body = body.rsplit(marker, 1)[0]
            break

    splits = CHAPTER_PATTERN.split(body)
    chapters = []

    # splits alternates: [pre-text, "I", ch1_text, "II", ch2_text, ...]
    i = 1
    while i < len(splits) - 1:
        roman = splits[i].strip()
        chapter_text = splits[i + 1].strip()
        if roman in ROMAN_TO_INT and chapter_text:
            chapters.append({
                "id": ROMAN_TO_INT[roman],
                "number": roman,
                "title": f"Chapter {roman}",
                "text": chapter_text,
                "word_count": len(chapter_text.split()),
            })
        i += 2

    return chapters


async def ingest(db: AsyncSession) -> list[Chapter]:
    existing = await db.execute(select(Chapter))
    if existing.scalars().first():
        result = await db.execute(select(Chapter).order_by(Chapter.id))
        return list(result.scalars().all())

    raw_text = await fetch_text()
    parsed = parse_chapters(raw_text)
    chapters = []

    for ch in parsed:
        chapter = Chapter(**ch)
        db.add(chapter)
        chapters.append(chapter)

    await db.commit()
    for ch in chapters:
        await db.refresh(ch)

    return chapters
