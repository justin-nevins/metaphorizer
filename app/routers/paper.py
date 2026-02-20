import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.paper import Paper, PaperSection
from app.schemas.paper import PaperConfig
from app.services import writer
from app.services.pdf_renderer import render_pdf

router = APIRouter()


@router.post("/api/paper/generate")
async def generate_paper_stream(config: PaperConfig, db: AsyncSession = Depends(get_db)):
    async def event_gen():
        async for paper_id, section_name, status in writer.generate_paper(
            db, config.title, config.author, config.target_pages
        ):
            data = json.dumps({"paper_id": paper_id, "section": section_name, "status": status})
            yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'status': 'done'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/api/paper/{paper_id}")
async def get_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        return {"error": "Not found"}

    result = await db.execute(
        select(PaperSection).where(PaperSection.paper_id == paper_id).order_by(PaperSection.sort_order)
    )
    sections = result.scalars().all()

    return {
        "id": paper.id,
        "title": paper.title,
        "author": paper.author,
        "status": paper.status,
        "sections": [
            {
                "id": s.id, "type": s.section_type, "title": s.title,
                "content_en": s.content_en, "content_es": s.content_es,
                "content_zh": s.content_zh, "target_words": s.target_words,
                "actual_words": s.actual_words,
            }
            for s in sections
        ],
    }


@router.get("/api/paper/{paper_id}/pdf/{lang}")
async def download_pdf(paper_id: int, lang: str = "en", db: AsyncSession = Depends(get_db)):
    pdf_bytes = await render_pdf(db, paper_id, lang)
    filename = f"gatsby_analysis_{lang}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/paper/{paper_id}/pdf")
async def download_pdf_en(paper_id: int, db: AsyncSession = Depends(get_db)):
    return await download_pdf(paper_id, "en", db)


@router.get("/paper/config", response_class=HTMLResponse)
async def paper_config_page(request: Request, db: AsyncSession = Depends(get_db)):
    from app.models.metaphor import Topic
    result = await db.execute(select(Topic).order_by(Topic.sort_order))
    topics = result.scalars().all()

    result = await db.execute(select(Paper).order_by(Paper.id.desc()))
    papers = result.scalars().all()

    return request.app.state.templates.TemplateResponse(
        "paper_config.html", {"request": request, "topics": topics, "papers": papers}
    )


@router.get("/paper/preview/{paper_id}", response_class=HTMLResponse)
async def paper_preview_page(request: Request, paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    result = await db.execute(
        select(PaperSection).where(PaperSection.paper_id == paper_id).order_by(PaperSection.sort_order)
    )
    sections = result.scalars().all()

    return request.app.state.templates.TemplateResponse(
        "paper_preview.html", {"request": request, "paper": paper, "sections": sections}
    )
