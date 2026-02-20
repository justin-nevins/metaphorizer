import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metaphor import Metaphor, Topic
from app.models.paper import Paper, PaperSection
from app.schemas.llm import LLMRequest
from app.services.llm_provider import get_provider

SYSTEM = """You are an academic writer producing a scholarly paper analyzing metaphor in \
F. Scott Fitzgerald's The Great Gatsby. Write in formal academic register with precise \
literary analysis. Reference specific passages. Connect literary analysis to broader \
cultural significance in 1920s America. Use MLA citation style for references to the novel."""


async def generate_paper(db: AsyncSession, title: str, author: str, target_pages: int = 10):
    paper = Paper(title=title, author=author, status="generating", target_pages=target_pages)
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    topics_result = await db.execute(select(Topic).order_by(Topic.sort_order))
    topics = list(topics_result.scalars().all())
    topic_names = [t.name for t in topics]

    yield paper.id, "exec_summary", "generating"
    await _generate_exec_summary(db, paper, topics)
    yield paper.id, "exec_summary", "complete"

    yield paper.id, "introduction", "generating"
    await _generate_introduction(db, paper, topics)
    yield paper.id, "introduction", "complete"

    for i, topic in enumerate(topics):
        yield paper.id, topic.name, "generating"
        prev_topic = topics[i - 1].name if i > 0 else None
        next_topic = topics[i + 1].name if i < len(topics) - 1 else None
        await _generate_body_section(db, paper, topic, i + 2, prev_topic, next_topic)
        yield paper.id, topic.name, "complete"

    yield paper.id, "conclusion", "generating"
    await _generate_conclusion(db, paper, topics)
    yield paper.id, "conclusion", "complete"

    yield paper.id, "index", "generating"
    await _generate_index(db, paper)
    yield paper.id, "index", "complete"

    paper.status = "complete"
    await db.commit()


async def _generate_exec_summary(db: AsyncSession, paper: Paper, topics: list[Topic]):
    topic_desc = "\n".join(f"- {t.name}: {t.description}" for t in topics)
    prompt = f"""Write a 200-word executive summary of an academic paper titled "{paper.title}".

The paper analyzes these metaphor systems in The Great Gatsby:
{topic_desc}

Requirements:
- Exactly 200 words (±5)
- One or two paragraphs, no headers
- State the thesis first, then key metaphor systems and their significance
- End with why this analysis matters"""

    provider = get_provider()
    resp = await provider.complete(LLMRequest(system=SYSTEM, prompt=prompt, max_tokens=1024))

    section = PaperSection(
        paper_id=paper.id, section_type="exec_summary", title="Executive Summary",
        content_en=resp.content, target_words=200,
        actual_words=len(resp.content.split()), sort_order=0,
    )
    db.add(section)
    await db.commit()


async def _generate_introduction(db: AsyncSession, paper: Paper, topics: list[Topic]):
    topic_names = ", ".join(t.name for t in topics)
    target = 300

    prompt = f"""Write the introduction (~{target} words) for an academic paper titled "{paper.title}".

The paper will analyze these metaphor systems: {topic_names}

Requirements:
- State the thesis clearly
- Preview the metaphor systems to be analyzed
- Establish why metaphors matter in Gatsby
- Set an academic tone
- Approximately {target} words"""

    provider = get_provider()
    resp = await provider.complete(LLMRequest(system=SYSTEM, prompt=prompt, max_tokens=2048))

    section = PaperSection(
        paper_id=paper.id, section_type="introduction", title="Introduction",
        content_en=resp.content, target_words=target,
        actual_words=len(resp.content.split()), sort_order=1,
    )
    db.add(section)
    await db.commit()


async def _generate_body_section(
    db: AsyncSession, paper: Paper, topic: Topic,
    sort_order: int, prev_topic: str | None, next_topic: str | None,
):
    result = await db.execute(
        select(Metaphor).where(Metaphor.topic_id == topic.id, Metaphor.selected == True)
    )
    metaphors = result.scalars().all()

    metaphor_list = "\n".join(
        f'  - Quote: "{m.exact_quote}" (Chapter {m.chapter_id})\n    Meaning: {m.meaning}'
        + (f"\n    Notes: {m.user_notes}" if m.user_notes else "")
        for m in metaphors
    )

    # ~250 words per page, distribute across topics proportionally
    target = max(200, 1700 // max(1, sort_order))

    transitions = ""
    if prev_topic:
        transitions += f"\n- Transition smoothly from the previous section on \"{prev_topic}\""
    if next_topic:
        transitions += f"\n- End with a transition toward \"{next_topic}\""

    prompt = f"""Write the "{topic.name}" section (~{target} words) of the paper "{paper.title}".

Topic description: {topic.description}

Metaphors to analyze in this section:
{metaphor_list}

Requirements:
- Reference each metaphor by quoting it directly
- Analyze the metaphorical significance in 1920s American context
- Connect to Fitzgerald's broader critique of the American Dream
- Use MLA citation format (chapter references)
- Approximately {target} words{transitions}"""

    provider = get_provider()
    resp = await provider.complete(LLMRequest(system=SYSTEM, prompt=prompt, max_tokens=4096))

    section = PaperSection(
        paper_id=paper.id, section_type="body", topic_id=topic.id,
        title=topic.name, content_en=resp.content, target_words=target,
        actual_words=len(resp.content.split()), sort_order=sort_order,
    )
    db.add(section)
    await db.commit()


async def _generate_conclusion(db: AsyncSession, paper: Paper, topics: list[Topic]):
    topic_names = ", ".join(t.name for t in topics)
    target = 300

    prompt = f"""Write the conclusion (~{target} words) for the paper "{paper.title}".

Topics analyzed: {topic_names}

Requirements:
- Synthesize insights (don't just repeat)
- Address Fitzgerald's craft with metaphor
- Connect metaphors to the novel's lasting cultural impact
- End with genuine insight, not mere summary
- Approximately {target} words"""

    provider = get_provider()
    resp = await provider.complete(LLMRequest(system=SYSTEM, prompt=prompt, max_tokens=2048))

    section = PaperSection(
        paper_id=paper.id, section_type="conclusion", title="Conclusion",
        content_en=resp.content, target_words=target,
        actual_words=len(resp.content.split()), sort_order=99,
    )
    db.add(section)
    await db.commit()


async def _generate_index(db: AsyncSession, paper: Paper):
    result = await db.execute(
        select(Metaphor).where(Metaphor.selected == True).order_by(Metaphor.exact_quote)
    )
    metaphors = result.scalars().all()

    lines = []
    for m in metaphors:
        lines.append(f'"{m.exact_quote}" — Chapter {m.chapter_id}: {m.meaning[:80]}')

    content = "## Index of Metaphors\n\n" + "\n\n".join(lines)

    section = PaperSection(
        paper_id=paper.id, section_type="index", title="Index of Metaphors",
        content_en=content, target_words=0,
        actual_words=len(content.split()), sort_order=100,
    )
    db.add(section)
    await db.commit()
