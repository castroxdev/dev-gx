from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import STATIC_DIR, settings
from app.logging_config import setup_logging
from app.web.routes import router as web_router


setup_logging()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dev GX",
        description="Planner tecnico com FastAPI, interface web e Ollama local.",
        version="0.2.0",
        debug=settings.debug,
    )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "Dev GX"}

    app.include_router(api_router)
    app.include_router(web_router)

    return app


app = create_app()
