from fastapi import FastAPI

from api.routes import router as planner_router


app = FastAPI(
    title="Dev GX",
    description="API para transformar ideias de projetos em planos tecnicos com Ollama.",
    version="0.1.0",
)


@app.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "Dev GX"}


app.include_router(planner_router)
