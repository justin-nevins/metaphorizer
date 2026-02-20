import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.metaphor import Metaphor, Topic, Subtopic
from app.schemas.metaphor import TopicCreate, TopicOut
from app.services import organizer

router = APIRouter()


@router.post("/api/organize/auto")
async def auto_organize(db: AsyncSession = Depends(get_db)):
    topics = await organizer.auto_organize(db)
    return {"status": "ok", "topics": [{"id": t.id, "name": t.name} for t in topics]}


@router.get("/api/topics")
async def list_topics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic).order_by(Topic.sort_order))
    topics = result.scalars().all()

    out = []
    for t in topics:
        count = await db.execute(
            select(func.count(Metaphor.id)).where(Metaphor.topic_id == t.id)
        )
        out.append(TopicOut(
            id=t.id, name=t.name, description=t.description,
            sort_order=t.sort_order, metaphor_count=count.scalar() or 0,
        ))
    return out


@router.post("/api/topics")
async def create_topic(data: TopicCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.max(Topic.sort_order)))
    max_order = result.scalar() or 0

    topic = Topic(name=data.name, description=data.description, sort_order=max_order + 1)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return {"status": "ok", "id": topic.id}


@router.patch("/api/topics/{topic_id}")
async def update_topic(topic_id: int, data: TopicCreate, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        return {"error": "Not found"}
    topic.name = data.name
    topic.description = data.description
    await db.commit()
    return {"status": "ok"}


@router.post("/api/topics/reorder")
async def reorder_topics(topic_ids: list[int], db: AsyncSession = Depends(get_db)):
    for i, tid in enumerate(topic_ids):
        topic = await db.get(Topic, tid)
        if topic:
            topic.sort_order = i
    await db.commit()
    return {"status": "ok"}


@router.post("/api/metaphors/{metaphor_id}/assign")
async def assign_metaphor(
    metaphor_id: int, topic_id: int, subtopic_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    m = await db.get(Metaphor, metaphor_id)
    if not m:
        return {"error": "Not found"}
    m.topic_id = topic_id
    m.subtopic_id = subtopic_id
    await db.commit()
    return {"status": "ok"}


@router.post("/api/paper/suggest-word-counts")
async def suggest_word_counts(target_pages: int = 10, db: AsyncSession = Depends(get_db)):
    result = await organizer.suggest_word_counts(db, target_pages)
    return result


@router.get("/topics", response_class=HTMLResponse)
async def topics_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic).order_by(Topic.sort_order))
    topics = result.scalars().all()

    topics_data = []
    for t in topics:
        metaphors_result = await db.execute(
            select(Metaphor).where(Metaphor.topic_id == t.id).order_by(Metaphor.id)
        )
        topics_data.append({
            "topic": t,
            "metaphors": metaphors_result.scalars().all(),
        })

    unassigned_result = await db.execute(
        select(Metaphor).where(Metaphor.topic_id == None, Metaphor.selected == True)
    )
    unassigned = unassigned_result.scalars().all()

    return request.app.state.templates.TemplateResponse(
        "topics.html",
        {"request": request, "topics_data": topics_data, "unassigned": unassigned},
    )
