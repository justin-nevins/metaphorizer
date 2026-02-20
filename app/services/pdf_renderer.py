from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import HTML

from app.config import settings
from app.models.paper import Paper, PaperSection

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "pdf"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


LANG_CONTENT_FIELD = {
    "en": "content_en",
    "es": "content_es",
    "zh": "content_zh",
}

LANG_FONT = {
    "en": '"Liberation Serif", "Times New Roman", serif',
    "es": '"Liberation Serif", "Times New Roman", serif',
    "zh": '"Noto Serif CJK SC", "SimSun", serif',
}


async def render_pdf(db: AsyncSession, paper_id: int, lang: str = "en") -> bytes:
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise ValueError(f"Paper {paper_id} not found")

    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.sort_order)
    )
    sections = result.scalars().all()

    content_field = LANG_CONTENT_FIELD.get(lang, "content_en")
    font_family = LANG_FONT.get(lang, LANG_FONT["en"])

    sections_data = []
    for s in sections:
        content = getattr(s, content_field, "") or s.content_en
        if content:
            sections_data.append({
                "type": s.section_type,
                "title": s.title,
                "content": content,
            })

    template = env.get_template("paper.html")
    html_content = template.render(
        title=paper.title,
        author=paper.author,
        lang=lang,
        font_family=font_family,
        sections=sections_data,
    )

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
