from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services import gutenberg

router = APIRouter()


@router.post("/api/ingest")
async def ingest_text(db: AsyncSession = Depends(get_db)):
    chapters = await gutenberg.ingest(db)
    return {
        "status": "ok",
        "chapters": [
            {"id": c.id, "number": c.number, "title": c.title, "word_count": c.word_count}
            for c in chapters
        ],
    }


@router.get("/ingest", response_class=HTMLResponse)
async def ingest_page(request: Request, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.metaphor import Chapter

    result = await db.execute(select(Chapter).order_by(Chapter.id))
    chapters = result.scalars().all()

    return request.app.state.templates.TemplateResponse(
        "ingest.html", {"request": request, "chapters": chapters}
    )
