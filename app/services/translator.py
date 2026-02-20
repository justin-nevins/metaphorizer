from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper, PaperSection
from app.schemas.llm import LLMRequest
from app.services.llm_provider import get_provider

LANG_NAMES = {"es": "Spanish", "zh": "Simplified Mandarin Chinese"}

SYSTEM = """You are a professional academic translator specializing in literary analysis. \
Translate with precision, maintaining the academic register and formal tone of the original."""

TRANSLATE_PROMPT = """Translate the following academic paper section from English to {lang_name}.

Rules:
- Maintain academic register and formal tone
- For direct quotes from The Great Gatsby, provide your translation followed by the \
original English in brackets: "translation" ["original English"]
- Preserve all formatting (headings, paragraphs, block quotes)
- For literary terms with no direct equivalent, use the closest term and add a brief \
parenthetical explanation
{extra_rules}

Section title: {title}

Text to translate:
---
{text}
---"""


async def translate_paper(db: AsyncSession, paper_id: int, lang: str):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise ValueError(f"Paper {paper_id} not found")

    result = await db.execute(
        select(PaperSection).where(PaperSection.paper_id == paper_id).order_by(PaperSection.sort_order)
    )
    sections = result.scalars().all()

    lang_name = LANG_NAMES.get(lang, lang)
    extra_rules = ""
    if lang == "zh":
        extra_rules = "- Use Simplified Chinese characters throughout"

    provider = get_provider()

    for section in sections:
        if not section.content_en:
            continue

        yield section.title, "translating"

        prompt = TRANSLATE_PROMPT.format(
            lang_name=lang_name,
            extra_rules=extra_rules,
            title=section.title,
            text=section.content_en,
        )

        resp = await provider.complete(
            LLMRequest(system=SYSTEM, prompt=prompt, max_tokens=8192, temperature=0.2)
        )

        if lang == "es":
            section.content_es = resp.content
        elif lang == "zh":
            section.content_zh = resp.content

        await db.commit()
        yield section.title, "complete"
