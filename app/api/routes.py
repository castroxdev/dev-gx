from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import re
import unicodedata

from prompts.planner_prompt import build_chat_system_prompt
from schemas.request import ChatRequest, GeneratePlanRequest
from schemas.response import ChatResponse, GeneratePlanResponse, OllamaHealthResponse
from services.ollama_service import OllamaService, OllamaServiceError


router = APIRouter(prefix="/api", tags=["planner"])
ollama_service = OllamaService()

IN_SCOPE_TERMS = (
    "software",
    "app",
    "aplicativo",
    "aplicacao",
    "sistema",
    "site",
    "website",
    "web",
    "mvp",
    "produto digital",
    "arquitetura",
    "api",
    "backend",
    "frontend",
    "banco de dados",
    "base de dados",
    "sql",
    "schema",
    "tabela",
    "entidade",
    "relacao",
    "indice",
    "crud",
    "autenticacao",
    "login",
    "deploy",
    "docker",
    "microservico",
    "fastapi",
    "python",
    "javascript",
    "typescript",
    "react",
    "node",
    "llm",
    "prompt",
    "chatbot",
    "api design",
    "database",
    "application",
    "system design",
    "architecture",
    "endpoint",
    "framework",
    "bug",
    "debug",
    "repository",
    "repo",
    "codigo",
    "programacion",
    "programacao",
    "api rest",
    "servicio",
    "microservicio",
    "base de datos",
    "tabla",
    "entidades",
    "relaciones",
    "autenticacion",
    "autenticacion",
    "despliegue",
    "frontend",
    "backend",
    "fullstack",
)

LANGUAGE_CONTROL_TERMS = (
    "responde em",
    "responder em",
    "fale em",
    "fala em",
    "em portugues",
    "em ingles",
    "em espanhol",
    "portugues",
    "ingles",
    "espanhol",
    "respond in",
    "reply in",
    "speak in",
    "english",
    "spanish",
    "portuguese",
    "responde en",
    "responder en",
    "en espanol",
    "en ingles",
    "idioma",
    "language",
)

GREETING_TERMS = (
    "oi",
    "ola",
    "olaa",
    "oi tudo bem",
    "ola tudo bem",
    "tudo bem",
    "bom dia",
    "boa manha",
    "boa tarde",
    "boa noite",
    "e ai",
    "fala",
    "hey",
    "hello",
    "hi",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "hola",
    "hola que tal",
    "que tal",
    "buen dia",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
)



def _normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_for_match(text: str) -> str:
    normalized = _normalize_text(text)
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return " ".join(normalized.split())


def _is_in_scope(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False

    return any(term in normalized for term in IN_SCOPE_TERMS)


def _is_language_control(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False

    return any(term in normalized for term in LANGUAGE_CONTROL_TERMS)


def _is_cordial_greeting(text: str) -> bool:
    normalized = _normalize_for_match(text)
    if not normalized:
        return False

    return any(
        re.search(rf"(?:^|\s){re.escape(greeting)}(?:$|\s)", normalized) is not None
        for greeting in GREETING_TERMS
    )


def _conversation_is_in_scope(payload: ChatRequest) -> bool:
    user_messages = [msg.content for msg in payload.messages if msg.role == "user"]
    if not user_messages:
        return False

    latest_user = user_messages[-1]

    if _is_cordial_greeting(latest_user):
        return True

    if _is_language_control(latest_user):
        return True

    if _is_in_scope(latest_user):
        return True

    return any(_is_in_scope(message) for message in user_messages[:-1])


def _latest_user_message(payload: ChatRequest) -> str:
    user_messages = [msg.content for msg in payload.messages if msg.role == "user"]
    if not user_messages:
        return ""
    return user_messages[-1].strip()


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
