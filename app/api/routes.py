from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from prompts.planner_system_prompt import planner_system_prompt
from schemas.request import ChatRequest, GeneratePlanRequest
from schemas.response import ChatResponse, GeneratePlanResponse
from services.ollama_service import OllamaService, OllamaServiceError


router = APIRouter(tags=["planner"])
ollama_service = OllamaService()
index_html = Path(__file__).resolve().parent.parent / "ui" / "index.html"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def web_app() -> HTMLResponse:
    return HTMLResponse(index_html.read_text(encoding="utf-8"))


@router.post(
    "/generate-plan",
    response_model=GeneratePlanResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_plan(payload: GeneratePlanRequest) -> GeneratePlanResponse:
    try:
        plan = await ollama_service.generate_plan(payload.idea)
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return GeneratePlanResponse(plan=plan)


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(payload: ChatRequest) -> ChatResponse:
    conversation = [{"role": "system", "content": planner_system_prompt}]
    conversation.extend(message.model_dump() for message in payload.messages)

    try:
        reply = await ollama_service.chat(conversation)
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ChatResponse(reply=reply)
