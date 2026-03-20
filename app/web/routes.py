from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import TEMPLATES_DIR


router = APIRouter(include_in_schema=False)
index_html = TEMPLATES_DIR / "index.html"


@router.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(index_html.read_text(encoding="utf-8"))
