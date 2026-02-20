import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.metaphor import Chapter, Metaphor, Topic
from app.schemas.metaphor import MetaphorOut, MetaphorUpdate
from app.services import extractor
from app.services.prompt_guard import sanitize_user_input

router = APIRouter()


@router.post("/api/extract/{chapter_id}")
async def extract_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        return {"error": "Chapter not found"}
    metaphors = await extractor.extract_chapter(db, chapter)
    return {"status": "ok", "count": len(metaphors)}


@router.get("/api/extract/stream")
async def extract_all_stream(db: AsyncSession = Depends(get_db)):
    async def event_gen():
        async for chapter_num, status in extractor.extract_all(db):
            data = json.dumps({"chapter": chapter_num, "status": status})
            yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'status': 'done'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/api/metaphors")
async def list_metaphors(
    chapter_id: int | None = None,
    topic_id: int | None = None,
    selected: bool | None = None,
    min_confidence: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Metaphor)
    if chapter_id is not None:
        query = query.where(Metaphor.chapter_id == chapter_id)
    if topic_id is not None:
        query = query.where(Metaphor.topic_id == topic_id)
    if selected is not None:
        query = query.where(Metaphor.selected == selected)
    if min_confidence is not None:
        query = query.where(Metaphor.confidence >= min_confidence)

    result = await db.execute(query.order_by(Metaphor.chapter_id, Metaphor.id))
    metaphors = result.scalars().all()

    out = []
    for m in metaphors:
        chapter = await db.get(Chapter, m.chapter_id)
        topic = await db.get(Topic, m.topic_id) if m.topic_id else None
        out.append(MetaphorOut(
            id=m.id, chapter_id=m.chapter_id,
            chapter_number=chapter.number if chapter else "",
            exact_quote=m.exact_quote, explanation=m.explanation,
            meaning=m.meaning, suggested_topic=m.suggested_topic,
            topic_id=m.topic_id, topic_name=topic.name if topic else None,
            subtopic_id=m.subtopic_id, selected=m.selected,
            user_notes=m.user_notes, confidence=m.confidence,
        ))
    return out


@router.patch("/api/metaphors/{metaphor_id}")
async def update_metaphor(
    metaphor_id: int,
    update: MetaphorUpdate,
    db: AsyncSession = Depends(get_db),
):
    m = await db.get(Metaphor, metaphor_id)
    if not m:
        return {"error": "Not found"}

    if update.explanation is not None:
        m.explanation = sanitize_user_input(update.explanation)
    if update.meaning is not None:
        m.meaning = sanitize_user_input(update.meaning)
    if update.selected is not None:
        m.selected = update.selected
    if update.user_notes is not None:
        m.user_notes = sanitize_user_input(update.user_notes)
    if update.topic_id is not None:
        m.topic_id = update.topic_id
    if update.subtopic_id is not None:
        m.subtopic_id = update.subtopic_id

    await db.commit()
    return {"status": "ok"}


@router.post("/api/metaphors/{metaphor_id}/toggle")
async def toggle_metaphor(metaphor_id: int, db: AsyncSession = Depends(get_db)):
    m = await db.get(Metaphor, metaphor_id)
    if not m:
        return {"error": "Not found"}
    m.selected = not m.selected
    await db.commit()
    return {"status": "ok", "selected": m.selected}


@router.get("/review", response_class=HTMLResponse)
async def review_page(request: Request, db: AsyncSession = Depends(get_db)):
    stats = await extractor.get_extraction_stats(db)

    result = await db.execute(select(Chapter).order_by(Chapter.id))
    chapters = result.scalars().all()

    result = await db.execute(select(Metaphor).order_by(Metaphor.chapter_id, Metaphor.id))
    metaphors = result.scalars().all()

    topics = set()
    for m in metaphors:
        if m.suggested_topic:
            topics.add(m.suggested_topic)

    return request.app.state.templates.TemplateResponse(
        "review.html",
        {"request": request, "chapters": chapters, "metaphors": metaphors,
         "stats": stats, "topics": sorted(topics)},
    )
