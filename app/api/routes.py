import asyncio

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from prompts.policy import refusal_message
from prompts.planner_prompt import build_chat_system_prompt
from schemas.request import (
    ChatRequest,
    ConversationSyncRequest,
    GeneratePlanRequest,
    GenerateSqlSchemaRequest,
)
from schemas.response import (
    ChatResponse,
    ConversationResponse,
    ConversationSummaryResponse,
    GeneratePlanResponse,
    GenerateSqlSchemaResponse,
    OllamaHealthResponse,
)
from services.conversation_store import ConversationStore
from services.ollama_service import OllamaService, OllamaServiceError


router = APIRouter(prefix="/api", tags=["planner"])
ollama_service = OllamaService()
conversation_store = ConversationStore()


@router.get(
    "/health/ollama",
    response_model=OllamaHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def ollama_healthcheck() -> OllamaHealthResponse:
    status_payload = await ollama_service.get_status()
    return OllamaHealthResponse(**status_payload)


@router.get(
    "/conversations",
    response_model=list[ConversationSummaryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_conversations() -> list[ConversationSummaryResponse]:
    items = await asyncio.to_thread(conversation_store.list_conversations)
    return [ConversationSummaryResponse(**item) for item in items]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation() -> ConversationResponse:
    conversation = await asyncio.to_thread(conversation_store.create_conversation)
    return ConversationResponse(**conversation)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_conversation(conversation_id: str) -> ConversationResponse:
    conversation = await asyncio.to_thread(conversation_store.get_conversation, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa nao encontrada.",
        )
    return ConversationResponse(**conversation)


@router.put(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
async def sync_conversation(
    conversation_id: str,
    payload: ConversationSyncRequest,
) -> ConversationResponse:
    conversation = await asyncio.to_thread(
        conversation_store.replace_messages,
        conversation_id,
        [message.model_dump() for message in payload.messages],
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa nao encontrada.",
        )
    return ConversationResponse(**conversation)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(conversation_id: str) -> Response:
    deleted = await asyncio.to_thread(conversation_store.delete_conversation, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa nao encontrada.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/generate-plan",
    response_model=GeneratePlanResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_plan(payload: GeneratePlanRequest) -> GeneratePlanResponse:
    scope = await ollama_service.classify_request_scope(payload.idea)
    if scope["decision"] == "refuse":
        return GeneratePlanResponse(plan=refusal_message())

    try:
        plan = await ollama_service.generate_plan(payload.idea)
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return GeneratePlanResponse(plan=plan)


@router.post(
    "/sql-schema",
    response_model=GenerateSqlSchemaResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_sql_schema(payload: GenerateSqlSchemaRequest) -> GenerateSqlSchemaResponse:
    scope = await ollama_service.classify_request_scope(payload.idea)
    if scope["decision"] == "refuse":
        return GenerateSqlSchemaResponse(
            file_path="",
            file_name="",
            sql=refusal_message(),
        )

    try:
        sql = await ollama_service.generate_sql_schema(payload.idea)
        file_path, file_name = ollama_service.save_sql_schema(sql, payload.file_name)
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return GenerateSqlSchemaResponse(
        file_path=file_path,
        file_name=file_name,
        sql=sql,
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(payload: ChatRequest) -> ChatResponse:
    last_user_message = payload.messages[-1].content
    scope = await ollama_service.classify_request_scope(last_user_message)
    if scope["decision"] == "refuse":
        return ChatResponse(reply=refusal_message())

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
    last_user_message = payload.messages[-1].content
    scope = await ollama_service.classify_request_scope(last_user_message)
    if scope["decision"] == "refuse":
        async def refusal_stream():
            escaped_chunk = refusal_message().replace("\\", "\\\\").replace("\n", "\\n")
            yield f"data: {escaped_chunk}\n\n"
            yield "event: done\ndata: [DONE]\n\n"

        return StreamingResponse(
            refusal_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

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
