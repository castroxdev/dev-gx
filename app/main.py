from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routes import router as planner_router


app = FastAPI(
    title="Dev GX",
    description="API para transformar ideias de projetos em planos tecnicos com Ollama.",
    version="0.1.0",
)
ui_dir = Path(__file__).resolve().parent / "ui"

app.mount("/static", StaticFiles(directory=ui_dir), name="static")


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "Dev GX"}


app.include_router(planner_router)
