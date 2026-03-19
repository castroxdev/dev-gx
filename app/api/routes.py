from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

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


@router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
)
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    conversation = [{"role": "system", "content": build_chat_system_prompt()}]
    conversation.extend(message.model_dump() for message in payload.messages)

    async def stream_generator():
        try:
            async for chunk in ollama_service.chat_stream(conversation):
                escaped_chunk = chunk.replace("\\", "\\\\").replace("\n", "\\n")
                yield f"data: {escaped_chunk}\n\n"
        except OllamaServiceError as exc:
            escaped_error = str(exc).replace("\\", "\\\\").replace("\n", "\\n")
            yield f"event: error\ndata: {escaped_error}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
