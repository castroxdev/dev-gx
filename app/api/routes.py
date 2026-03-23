import asyncio
import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.logging_utils import format_log_event
from app.prompts.policy import detect_response_language, refusal_message
from app.schemas.request import (
    ChatRequest,
    ConversationSyncRequest,
    GeneratePlanRequest,
    GenerateSqlSchemaRequest,
)
from app.schemas.response import (
    ChatResponse,
    ConversationResponse,
    ConversationSummaryResponse,
    GeneratePlanResponse,
    GenerateSqlSchemaResponse,
    McpHealthResponse,
    OllamaHealthResponse,
)
from app.services.conversation_store import ConversationStore
from app.services.mcp_service import McpService, McpServiceError
from app.services.ollama_service import OllamaService, OllamaServiceError
from app.services.tool_runtime import (
    extract_tool_call_response,
    format_tool_result,
    parse_tool_call_response,
)
from app.trace_store import trace_store
from app.tools import build_tools_prompt_from_mcp


router = APIRouter(prefix="/api", tags=["planner"])
ollama_service = OllamaService()
conversation_store = ConversationStore()
mcp_service = McpService()
logger = logging.getLogger("devgx.api.chat")


async def load_mcp_tools() -> list[dict]:
    try:
        return await mcp_service.list_tools()
    except McpServiceError:
        return []


def build_chat_log_context(payload: ChatRequest) -> dict[str, str | int | None]:
    return {
        "request_id": None,
        "endpoint": None,
        "conversation_id": payload.conversation_id or "none",
        "message_count": len(payload.messages),
    }


def generate_request_id() -> str:
    return f"req-{uuid4().hex[:8]}"


def add_user_message_trace(request_id: str, user_message: str) -> None:
    trace_store.add_step(
        request_id,
        stage="user_message_captured",
        status="completed",
        user_message=user_message,
    )


def add_final_response_trace(request_id: str, reply: str) -> None:
    trace_store.add_step(
        request_id,
        stage="final_response_captured",
        status="completed",
        final_response=reply,
        reply_chars=len(reply),
    )


def add_tool_call_trace(
    request_id: str,
    *,
    tool_name: str,
    status: str,
    tool_input: dict | None = None,
    tool_result: object | None = None,
    error_detail: str | None = None,
) -> None:
    trace_store.add_step(
        request_id,
        stage="tool_call",
        status=status,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_result=tool_result,
        error_detail=error_detail,
    )


def build_tool_result_fallback(tool_name: str, tool_result: object) -> str:
    if isinstance(tool_result, str):
        rendered_result = tool_result.strip() or "<sem conteudo>"
    else:
        rendered_result = json.dumps(tool_result, ensure_ascii=False, indent=2)

    return f"Resultado da tool '{tool_name}':\n{rendered_result}"


def build_invalid_tool_call_fallback(tool_name: str) -> str:
    return (
        f"O modelo tentou chamar a tool '{tool_name}', "
        "mas essa tool nao esta disponivel ou o payload nao e executavel neste momento."
    )


async def execute_chat_with_mcp_tools(
    messages: list[dict[str, str]],
    mcp_tools: list[dict] | None = None,
    log_context: dict[str, str | int | None] | None = None,
) -> str:
    mcp_tools = mcp_tools or await load_mcp_tools()
    tools_prompt = build_tools_prompt_from_mcp(mcp_tools)
    allowed_tools = {str(tool.get("name", "")).strip() for tool in mcp_tools if tool.get("name")}

    conversation = [{"role": "system", "content": ollama_service.build_chat_system_message(tools_prompt)}]
    conversation.extend(messages)
    last_successful_tool_result: tuple[str, object] | None = None

    for _ in range(settings.max_tool_rounds):
        try:
            reply = await ollama_service.chat(conversation, log_context=log_context)
        except OllamaServiceError as exc:
            if (
                last_successful_tool_result is not None
                and "nao devolveu conteudo para a resposta" in str(exc).lower()
            ):
                tool_name, tool_result = last_successful_tool_result
                return build_tool_result_fallback(tool_name, tool_result)
            raise
        raw_tool_call = extract_tool_call_response(reply)
        tool_call = parse_tool_call_response(reply, allowed_tools)

        if tool_call is None:
            if raw_tool_call is not None:
                request_id = (
                    str(log_context["request_id"])
                    if log_context and log_context.get("request_id")
                    else None
                )
                if request_id is not None:
                    add_tool_call_trace(
                        request_id,
                        tool_name=raw_tool_call["tool"],
                        tool_input=raw_tool_call["arguments"],
                        status="error",
                        error_detail="tool_call_not_executable",
                    )
                return build_invalid_tool_call_fallback(raw_tool_call["tool"])
            return reply

        request_id = str(log_context["request_id"]) if log_context and log_context.get("request_id") else None
        if request_id is not None:
            add_tool_call_trace(
                request_id,
                tool_name=tool_call["tool"],
                tool_input=tool_call["arguments"],
                status="started",
            )

        conversation.append({"role": "assistant", "content": reply})

        try:
            tool_result = await mcp_service.call_tool(tool_call["tool"], tool_call["arguments"])
            last_successful_tool_result = (tool_call["tool"], tool_result)
            if request_id is not None:
                add_tool_call_trace(
                    request_id,
                    tool_name=tool_call["tool"],
                    tool_input=tool_call["arguments"],
                    tool_result=tool_result,
                    status="completed",
                )
            tool_result_message = format_tool_result(tool_call["tool"], tool_result)
        except McpServiceError as exc:
            if request_id is not None:
                add_tool_call_trace(
                    request_id,
                    tool_name=tool_call["tool"],
                    tool_input=tool_call["arguments"],
                    tool_result={"error": str(exc)},
                    error_detail=str(exc),
                    status="error",
                )
            tool_result_message = format_tool_result(
                tool_call["tool"],
                {"error": str(exc)},
            )

        conversation.append({"role": "system", "content": tool_result_message})

    return "Nao foi possivel concluir o pedido com as tools disponiveis dentro do limite de iteracoes."


async def execute_plan_with_mcp_tools(idea: str) -> str:
    mcp_tools = await load_mcp_tools()
    tools_prompt = build_tools_prompt_from_mcp(mcp_tools)
    allowed_tools = {str(tool.get("name", "")).strip() for tool in mcp_tools if tool.get("name")}

    prompt = await ollama_service.generate_plan(idea, tools_prompt)
    tool_call = parse_tool_call_response(prompt, allowed_tools)
    if tool_call is None:
        return prompt

    conversation = [
        {"role": "system", "content": ollama_service.build_plan_system_message(tools_prompt)},
        {"role": "user", "content": idea},
        {"role": "assistant", "content": prompt},
    ]

    for _ in range(settings.max_tool_rounds):
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
    "/debug/traces",
    status_code=status.HTTP_200_OK,
)
async def list_debug_traces(limit: int = 20) -> list[dict]:
    return trace_store.list_traces(limit=limit)


@router.get(
    "/debug/traces/{request_id}",
    status_code=status.HTTP_200_OK,
)
async def get_debug_trace(request_id: str) -> dict:
    trace = trace_store.get_trace(request_id)
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace nao encontrado.",
        )
    return trace


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
    log_context = build_chat_log_context(payload)
    log_context["request_id"] = generate_request_id()
    log_context["endpoint"] = "/api/chat"
    trace_store.start_trace(
        request_id=str(log_context["request_id"]),
        endpoint=str(log_context["endpoint"]),
        conversation_id=str(log_context["conversation_id"]),
        model=ollama_service.model,
    )
    trace_store.add_step(
        str(log_context["request_id"]),
        stage="request_received",
        status="started",
        message_count=log_context["message_count"],
    )
    logger.info(
        format_log_event(
            request_id=log_context["request_id"],
            endpoint=log_context["endpoint"],
            conversation_id=log_context["conversation_id"],
            model=ollama_service.model,
            stage="request_received",
            status="started",
            message_count=log_context["message_count"],
        )
    )

    last_user_message = payload.messages[-1].content
    add_user_message_trace(str(log_context["request_id"]), last_user_message)
    started_at = perf_counter()
    scope = await ollama_service.classify_request_scope(last_user_message)
    if scope["decision"] == "refuse":
        language = detect_response_language(last_user_message, scope["language"])
        refusal_reply = refusal_message(language)
        add_final_response_trace(str(log_context["request_id"]), refusal_reply)
        total_ms = (perf_counter() - started_at) * 1000
        trace_store.add_step(
            str(log_context["request_id"]),
            stage="request_refused",
            status="completed",
            duration_ms=total_ms,
        )
        trace_store.finish_trace(
            str(log_context["request_id"]),
            status="success",
            total_duration_ms=total_ms,
        )
        logger.info(
            format_log_event(
                request_id=log_context["request_id"],
                endpoint=log_context["endpoint"],
                conversation_id=log_context["conversation_id"],
                model=ollama_service.model,
                stage="request_refused",
                duration_ms=total_ms,
                status="completed",
            )
        )
        return ChatResponse(reply=refusal_reply)

    try:
        trace_store.add_step(
            str(log_context["request_id"]),
            stage="processing_started",
            status="started",
        )
        logger.info(
            format_log_event(
                request_id=log_context["request_id"],
                endpoint=log_context["endpoint"],
                conversation_id=log_context["conversation_id"],
                model=ollama_service.model,
                stage="processing_started",
                status="started",
            )
        )
        reply = await execute_chat_with_mcp_tools(
            [message.model_dump() for message in payload.messages],
            log_context=log_context,
        )
    except OllamaServiceError as exc:
        total_ms = (perf_counter() - started_at) * 1000
        trace_store.add_step(
            str(log_context["request_id"]),
            stage="error",
            status="error",
            duration_ms=total_ms,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        trace_store.finish_trace(
            str(log_context["request_id"]),
            status="error",
            total_duration_ms=total_ms,
        )
        logger.exception(
            format_log_event(
                request_id=log_context["request_id"],
                endpoint=log_context["endpoint"],
                conversation_id=log_context["conversation_id"],
                model=ollama_service.model,
                stage="response_error",
                duration_ms=total_ms,
                status="error",
                error_type=type(exc).__name__,
            )
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    total_ms = (perf_counter() - started_at) * 1000
    add_final_response_trace(str(log_context["request_id"]), reply)
    trace_store.add_step(
        str(log_context["request_id"]),
        stage="response_sent",
        status="completed",
        duration_ms=total_ms,
        reply_chars=len(reply),
    )
    trace_store.finish_trace(
        str(log_context["request_id"]),
        status="success",
        total_duration_ms=total_ms,
    )
    logger.info(
        format_log_event(
            request_id=log_context["request_id"],
            endpoint=log_context["endpoint"],
            conversation_id=log_context["conversation_id"],
            model=ollama_service.model,
            stage="response_sent",
            duration_ms=total_ms,
            status="completed",
            reply_chars=len(reply),
        )
    )
    return ChatResponse(reply=reply)


@router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
)
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    log_context = build_chat_log_context(payload)
    log_context["request_id"] = generate_request_id()
    log_context["endpoint"] = "/api/chat/stream"
    trace_store.start_trace(
        request_id=str(log_context["request_id"]),
        endpoint=str(log_context["endpoint"]),
        conversation_id=str(log_context["conversation_id"]),
        model=ollama_service.model,
    )
    trace_store.add_step(
        str(log_context["request_id"]),
        stage="request_received",
        status="started",
        message_count=log_context["message_count"],
    )
    logger.info(
        format_log_event(
            request_id=log_context["request_id"],
            endpoint=log_context["endpoint"],
            conversation_id=log_context["conversation_id"],
            model=ollama_service.model,
            stage="request_received",
            status="started",
            message_count=log_context["message_count"],
        )
    )

    last_user_message = payload.messages[-1].content
    add_user_message_trace(str(log_context["request_id"]), last_user_message)
    started_at = perf_counter()
    scope = await ollama_service.classify_request_scope(last_user_message)
    if scope["decision"] == "refuse":
        language = detect_response_language(last_user_message, scope["language"])
        refusal_reply = refusal_message(language)
        add_final_response_trace(str(log_context["request_id"]), refusal_reply)
        total_ms = (perf_counter() - started_at) * 1000
        trace_store.add_step(
            str(log_context["request_id"]),
            stage="request_refused",
            status="completed",
            duration_ms=total_ms,
        )
        trace_store.finish_trace(
            str(log_context["request_id"]),
            status="success",
            total_duration_ms=total_ms,
        )
        logger.info(
            format_log_event(
                request_id=log_context["request_id"],
                endpoint=log_context["endpoint"],
                conversation_id=log_context["conversation_id"],
                model=ollama_service.model,
                stage="request_refused",
                duration_ms=total_ms,
                status="completed",
            )
        )

        async def refusal_stream():
            escaped_chunk = refusal_reply.replace("\\", "\\\\").replace("\n", "\\n")
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

    stream_log_context = dict(log_context)
    trace_store.add_step(
        str(stream_log_context["request_id"]),
        stage="processing_started",
        status="started",
    )
    logger.info(
        format_log_event(
            request_id=stream_log_context["request_id"],
            endpoint=stream_log_context["endpoint"],
            conversation_id=stream_log_context["conversation_id"],
            model=ollama_service.model,
            stage="processing_started",
            status="started",
        )
    )

    async def stream_generator():
        stream_failed = False
        streamed_chunks: list[str] = []
        final_reply: str | None = None
        try:
            raw_messages = [message.model_dump() for message in payload.messages]
            mcp_tools = await load_mcp_tools()

            if mcp_tools:
                reply = await execute_chat_with_mcp_tools(
                    raw_messages,
                    mcp_tools=mcp_tools,
                    log_context=stream_log_context,
                )
                final_reply = reply
                escaped_chunk = reply.replace("\\", "\\\\").replace("\n", "\\n")
                yield f"data: {escaped_chunk}\n\n"
            else:
                conversation = [
                    {"role": "system", "content": ollama_service.build_chat_system_message()},
                    *raw_messages,
                ]
                async for chunk in ollama_service.chat_stream(conversation, log_context=stream_log_context):
                    streamed_chunks.append(chunk)
                    escaped_chunk = chunk.replace("\\", "\\\\").replace("\n", "\\n")
                    yield f"data: {escaped_chunk}\n\n"
        except OllamaServiceError as exc:
            stream_failed = True
            total_ms = (perf_counter() - started_at) * 1000
            trace_store.add_step(
                str(stream_log_context["request_id"]),
                stage="error",
                status="error",
                duration_ms=total_ms,
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            trace_store.finish_trace(
                str(stream_log_context["request_id"]),
                status="error",
                total_duration_ms=total_ms,
            )
            logger.exception(
                format_log_event(
                    request_id=stream_log_context["request_id"],
                    endpoint=stream_log_context["endpoint"],
                    conversation_id=stream_log_context["conversation_id"],
                    model=ollama_service.model,
                    stage="response_error",
                    duration_ms=total_ms,
                    status="error",
                    error_type=type(exc).__name__,
                )
            )
            escaped_error = str(exc).replace("\\", "\\\\").replace("\n", "\\n")
            yield f"event: error\ndata: {escaped_error}\n\n"

        if stream_failed:
            yield "event: done\ndata: [DONE]\n\n"
            return

        total_ms = (perf_counter() - started_at) * 1000
        if final_reply is None:
            final_reply = "".join(streamed_chunks)
        add_final_response_trace(str(stream_log_context["request_id"]), final_reply)
        trace_store.add_step(
            str(stream_log_context["request_id"]),
            stage="response_sent",
            status="completed",
            duration_ms=total_ms,
            reply_chars=len(final_reply),
        )
        trace_store.finish_trace(
            str(stream_log_context["request_id"]),
            status="success",
            total_duration_ms=total_ms,
        )
        logger.info(
            format_log_event(
                request_id=stream_log_context["request_id"],
                endpoint=stream_log_context["endpoint"],
                conversation_id=stream_log_context["conversation_id"],
                model=ollama_service.model,
                stage="response_sent",
                duration_ms=total_ms,
                status="completed",
                reply_chars=len(final_reply),
            )
        )
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
