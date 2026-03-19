from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(include_in_schema=False)
index_html = Path(__file__).resolve().parent.parent / "templates" / "index.html"


@router.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(index_html.read_text(encoding="utf-8"))
