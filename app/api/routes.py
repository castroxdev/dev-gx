import asyncio

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from prompts.policy import detect_response_language, refusal_message
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
    McpHealthResponse,
    OllamaHealthResponse,
)
from services.conversation_store import ConversationStore
from services.mcp_service import McpService, McpServiceError
from services.ollama_service import OllamaService, OllamaServiceError
from services.tool_runtime import format_tool_result, parse_tool_call_response
from tools import build_tools_prompt_from_mcp


router = APIRouter(prefix="/api", tags=["planner"])
ollama_service = OllamaService()
conversation_store = ConversationStore()
mcp_service = McpService()


async def load_mcp_tools_prompt() -> str:
    try:
        mcp_tools = await mcp_service.list_tools()
    except McpServiceError:
        return ""

    return build_tools_prompt_from_mcp(mcp_tools)


async def execute_chat_with_mcp_tools(messages: list[dict[str, str]]) -> str:
    mcp_tools = []
    try:
        mcp_tools = await mcp_service.list_tools()
    except McpServiceError:
        mcp_tools = []

    tools_prompt = build_tools_prompt_from_mcp(mcp_tools)
    allowed_tools = {str(tool.get("name", "")).strip() for tool in mcp_tools if tool.get("name")}

    conversation = [{"role": "system", "content": ollama_service.build_chat_system_message(tools_prompt)}]
    conversation.extend(messages)

    max_tool_rounds = 4
    for _ in range(max_tool_rounds):
        reply = await ollama_service.chat(conversation)
        tool_call = parse_tool_call_response(reply, allowed_tools)

        if tool_call is None:
            return reply

        conversation.append({"role": "assistant", "content": reply})

        try:
            tool_result = await mcp_service.call_tool(tool_call["tool"], tool_call["arguments"])
            tool_result_message = format_tool_result(tool_call["tool"], tool_result)
        except McpServiceError as exc:
            tool_result_message = format_tool_result(
                tool_call["tool"],
                {"error": str(exc)},
            )

        conversation.append({"role": "system", "content": tool_result_message})

    return "Nao foi possivel concluir o pedido com as tools disponiveis dentro do limite de iteracoes."


async def execute_plan_with_mcp_tools(idea: str) -> str:
    tools_prompt = await load_mcp_tools_prompt()
    allowed_tools: set[str] = set()
    try:
        mcp_tools = await mcp_service.list_tools()
        allowed_tools = {str(tool.get("name", "")).strip() for tool in mcp_tools if tool.get("name")}
    except McpServiceError:
        allowed_tools = set()

    prompt = await ollama_service.generate_plan(idea, tools_prompt)
    tool_call = parse_tool_call_response(prompt, allowed_tools)
    if tool_call is None:
        return prompt

    conversation = [
        {"role": "system", "content": ollama_service.build_plan_system_message(tools_prompt)},
        {"role": "user", "content": idea},
        {"role": "assistant", "content": prompt},
    ]

    max_tool_rounds = 4
    for _ in range(max_tool_rounds):
        latest_assistant = conversation[-1]["content"]
        tool_call = parse_tool_call_response(latest_assistant, allowed_tools)
        if tool_call is None:
            return latest_assistant

        try:
            tool_result = await mcp_service.call_tool(tool_call["tool"], tool_call["arguments"])
            tool_result_message = format_tool_result(tool_call["tool"], tool_result)
        except McpServiceError as exc:
            tool_result_message = format_tool_result(tool_call["tool"], {"error": str(exc)})

        conversation.append({"role": "system", "content": tool_result_message})
        next_reply = await ollama_service.chat(conversation)
        conversation.append({"role": "assistant", "content": next_reply})

    return conversation[-1]["content"]


@router.get(
    "/health/ollama",
    response_model=OllamaHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def ollama_healthcheck() -> OllamaHealthResponse:
    status_payload = await ollama_service.get_status()
    return OllamaHealthResponse(**status_payload)


@router.get(
    "/health/mcp",
    response_model=McpHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def mcp_healthcheck() -> McpHealthResponse:
    status_payload = await mcp_service.get_status()
    return McpHealthResponse(**status_payload)


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
        return GeneratePlanResponse(
            plan=refusal_message(detect_response_language(payload.idea, scope["language"]))
        )

    try:
        plan = await execute_plan_with_mcp_tools(payload.idea)
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
        language = detect_response_language(payload.idea, scope["language"])
        return GenerateSqlSchemaResponse(
            file_path="",
            file_name="",
            sql=refusal_message(language),
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
        language = detect_response_language(last_user_message, scope["language"])
        return ChatResponse(reply=refusal_message(language))

    try:
        reply = await execute_chat_with_mcp_tools(
            [message.model_dump() for message in payload.messages]
        )
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
        language = detect_response_language(last_user_message, scope["language"])
        async def refusal_stream():
            escaped_chunk = refusal_message(language).replace("\\", "\\\\").replace("\n", "\\n")
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

    async def stream_generator():
        try:
            reply = await execute_chat_with_mcp_tools(
                [message.model_dump() for message in payload.messages]
            )
            escaped_chunk = reply.replace("\\", "\\\\").replace("\n", "\\n")
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
