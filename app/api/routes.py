from fastapi import APIRouter, HTTPException, status

from prompts.planner_prompt import build_chat_system_prompt
from schemas.request import ChatRequest, GeneratePlanRequest
from schemas.response import ChatResponse, GeneratePlanResponse, OllamaHealthResponse
from services.ollama_service import OllamaService, OllamaServiceError


router = APIRouter(prefix="/api", tags=["planner"])
ollama_service = OllamaService()


@router.get(
    "/health/ollama",
    response_model=OllamaHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def ollama_healthcheck() -> OllamaHealthResponse:
    status_payload = await ollama_service.get_status()
    return OllamaHealthResponse(**status_payload)


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
    conversation = [{"role": "system", "content": build_chat_system_prompt()}]
    conversation.extend(message.model_dump() for message in payload.messages)

    try:
        reply = await ollama_service.chat(conversation)
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ChatResponse(reply=reply)
