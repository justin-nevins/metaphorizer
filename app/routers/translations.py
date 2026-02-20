import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.paper import Paper, PaperSection
from app.services import translator

router = APIRouter()


@router.post("/api/paper/{paper_id}/translate/{lang}")
async def translate_paper_stream(paper_id: int, lang: str, db: AsyncSession = Depends(get_db)):
    async def event_gen():
        async for section_title, status in translator.translate_paper(db, paper_id, lang):
            data = json.dumps({"section": section_title, "status": status, "lang": lang})
            yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'status': 'done', 'lang': lang})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/translations", response_class=HTMLResponse)
async def translations_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Paper).order_by(Paper.id.desc()))
    papers = result.scalars().all()

    papers_data = []
    for p in papers:
        sections = await db.execute(
            select(PaperSection).where(PaperSection.paper_id == p.id).order_by(PaperSection.sort_order)
        )
        secs = sections.scalars().all()
        has_es = any(s.content_es for s in secs)
        has_zh = any(s.content_zh for s in secs)
        papers_data.append({"paper": p, "sections": secs, "has_es": has_es, "has_zh": has_zh})

    return request.app.state.templates.TemplateResponse(
        "translations.html", {"request": request, "papers_data": papers_data}
    )
