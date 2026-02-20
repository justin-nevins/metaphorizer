import json

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metaphor import Metaphor, Topic, Subtopic
from app.schemas.llm import LLMRequest
from app.services.llm_provider import get_provider
from app.services.prompt_guard import sanitize_user_input

ORGANIZE_SYSTEM = """You are a literary scholar organizing metaphors from The Great Gatsby \
into coherent thematic groups for an academic paper. Create clear, analytically useful \
topic categories that support sustained academic argument."""

ORGANIZE_PROMPT = """Organize the following metaphors into topics and subtopics for a \
10-page academic paper. Each topic should be a major thematic thread that can sustain \
1-2 pages of analysis.

Metaphors to organize:
{metaphors_json}

Return your organization using the tool provided. Create 4-7 topics, each with optional subtopics.
Assign every metaphor to a topic by its ID."""

ORGANIZE_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "subtopics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "metaphor_ids": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                },
                            },
                            "required": ["name", "metaphor_ids"],
                        },
                    },
                    "metaphor_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Metaphors that belong to this topic but no specific subtopic",
                    },
                },
                "required": ["name", "description", "metaphor_ids"],
            },
        }
    },
    "required": ["topics"],
}

WORD_COUNT_PROMPT = """Given a {target_pages}-page academic paper with the following topic structure, \
suggest word counts for each section. Total should be approximately {total_words} words.

Topics:
{topics_json}

Return word counts using the tool provided."""

WORD_COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "introduction": {"type": "integer"},
        "executive_summary": {"type": "integer", "description": "Must be exactly 200"},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic_id": {"type": "integer"},
                    "target_words": {"type": "integer"},
                },
                "required": ["topic_id", "target_words"],
            },
        },
        "conclusion": {"type": "integer"},
    },
    "required": ["introduction", "executive_summary", "topics", "conclusion"],
}


async def auto_organize(db: AsyncSession) -> list[Topic]:
    result = await db.execute(select(Metaphor).where(Metaphor.selected == True))
    metaphors = result.scalars().all()

    metaphors_data = [
        {"id": m.id, "quote": m.exact_quote[:100], "meaning": m.meaning[:100], "suggested": m.suggested_topic}
        for m in metaphors
    ]

    provider = get_provider()
    organized = await provider.complete_structured(
        LLMRequest(
            system=ORGANIZE_SYSTEM,
            prompt=ORGANIZE_PROMPT.format(metaphors_json=json.dumps(metaphors_data)),
            max_tokens=4096,
            temperature=0.2,
        ),
        tool_name="organize_metaphors",
        tool_schema=ORGANIZE_SCHEMA,
    )

    # Clear existing topics
    old_topics = await db.execute(select(Topic))
    for t in old_topics.scalars().all():
        await db.delete(t)
    old_subtopics = await db.execute(select(Subtopic))
    for s in old_subtopics.scalars().all():
        await db.delete(s)
    await db.flush()

    topics = []
    for i, topic_data in enumerate(organized.get("topics", [])):
        topic = Topic(
            name=topic_data["name"],
            description=topic_data.get("description", ""),
            sort_order=i,
        )
        db.add(topic)
        await db.flush()

        # Assign direct metaphors
        for mid in topic_data.get("metaphor_ids", []):
            m = await db.get(Metaphor, mid)
            if m:
                m.topic_id = topic.id

        # Handle subtopics
        for j, sub_data in enumerate(topic_data.get("subtopics", [])):
            subtopic = Subtopic(
                topic_id=topic.id,
                name=sub_data["name"],
                description=sub_data.get("description", ""),
                sort_order=j,
            )
            db.add(subtopic)
            await db.flush()

            for mid in sub_data.get("metaphor_ids", []):
                m = await db.get(Metaphor, mid)
                if m:
                    m.topic_id = topic.id
                    m.subtopic_id = subtopic.id

        topics.append(topic)

    await db.commit()
    return topics


async def suggest_word_counts(db: AsyncSession, target_pages: int = 10) -> dict:
    total_words = target_pages * 250  # ~250 words per double-spaced page
    result = await db.execute(select(Topic).order_by(Topic.sort_order))
    topics = result.scalars().all()

    topics_data = []
    for t in topics:
        count = await db.execute(
            select(func.count(Metaphor.id)).where(Metaphor.topic_id == t.id, Metaphor.selected == True)
        )
        topics_data.append({"id": t.id, "name": t.name, "metaphor_count": count.scalar() or 0})

    provider = get_provider()
    return await provider.complete_structured(
        LLMRequest(
            system="You are an academic writing planner.",
            prompt=WORD_COUNT_PROMPT.format(
                target_pages=target_pages,
                total_words=total_words,
                topics_json=json.dumps(topics_data),
            ),
            max_tokens=2048,
            temperature=0.1,
        ),
        tool_name="suggest_word_counts",
        tool_schema=WORD_COUNT_SCHEMA,
    )
