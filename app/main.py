from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_router
from web.routes import router as web_router


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dev GX",
        description="Planner tecnico com FastAPI, interface web e Ollama local.",
        version="0.2.0",
    )

    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "Dev GX"}

    app.include_router(api_router)
    app.include_router(web_router)

    return app


app = create_app()
