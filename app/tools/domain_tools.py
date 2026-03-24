import json
import re
from dataclasses import dataclass
from typing import Any

from app.services.request_analysis import build_output_guardrails, extract_request_constraints
from app.services.ollama_service import OllamaService


@dataclass(frozen=True)
class DomainToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


generate_mvp_plan_tool = DomainToolDefinition(
    name="generate_mvp_plan",
    description=(
        "Gera um plano de MVP focado apenas em produto, escopo e prioridades "
        "essenciais."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_brief": {
                "type": "string",
                "description": "Descrição principal do produto, problema e objetivo do MVP.",
            },
            "target_users": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Perfis de utilizadores principais do MVP.",
            },
            "core_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Funcionalidades essenciais que precisam entrar nesta primeira versão.",
            },
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrições técnicas, operacionais ou de prazo relevantes.",
            },
        },
        "required": ["project_brief"],
        "additionalProperties": False,
    },
    output_schema={
        "type": "object",
        "properties": {
            "project_summary": {"type": "string"},
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "mvp_plan_markdown": {"type": "string"},
        },
        "required": ["project_summary", "assumptions", "mvp_plan_markdown"],
        "additionalProperties": False,
    },
)

generate_entities_tool = DomainToolDefinition(
    name="generate_entities",
    description=(
        "Modela entidades de domínio, relações e campos principais sem gerar SQL, "
        "focando a estrutura conceptual do produto."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_brief": {
                "type": "string",
                "description": "Descrição principal do produto e do problema a modelar.",
            },
            "target_users": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Perfis de utilizadores principais do domínio.",
            },
            "core_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Funcionalidades principais que influenciam o modelo conceptual.",
            },
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrições de negócio ou técnicas relevantes para a modelação.",
            },
        },
        "required": ["project_brief"],
        "additionalProperties": False,
    },
    output_schema={
        "type": "object",
        "properties": {
            "domain_summary": {"type": "string"},
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "entities_markdown": {"type": "string"},
        },
        "required": ["domain_summary", "assumptions", "entities_markdown"],
        "additionalProperties": False,
    },
)

generate_sql_schema_tool = DomainToolDefinition(
    name="generate_sql_schema",
    description=(
        "Gera um esquema SQL inicial para o MVP com tabelas, relações, chaves e índices "
        "essenciais."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_brief": {
                "type": "string",
                "description": "Descrição principal do produto e do problema a modelar.",
            },
            "entities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Entidades de domínio que devem aparecer no esquema SQL inicial.",
            },
            "core_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Funcionalidades centrais que influenciam o modelo de dados.",
            },
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrições técnicas ou de negócio relevantes para o esquema SQL.",
            },
            "database_engine": {
                "type": "string",
                "description": "Motor de base de dados preferido, como postgresql, mysql ou sqlite.",
            },
        },
        "required": ["project_brief"],
        "additionalProperties": False,
    },
    output_schema={
        "type": "object",
        "properties": {
            "schema_summary": {"type": "string"},
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "sql": {"type": "string"},
            "suggested_file_name": {"type": "string"},
        },
        "required": ["schema_summary", "assumptions", "sql"],
        "additionalProperties": False,
    },
)

suggest_api_endpoints_tool = DomainToolDefinition(
    name="suggest_api_endpoints",
    description=(
        "Sugere endpoints API iniciais para o MVP com métodos, paths, objetivo e contratos "
        "básicos de request e response."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_brief": {
                "type": "string",
                "description": "Descrição principal do produto e do problema a servir pela API.",
            },
            "core_entities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Entidades principais que a API deve expor ou manipular.",
            },
            "core_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Funcionalidades principais que influenciam os endpoints do MVP.",
            },
            "auth_style": {
                "type": "string",
                "description": "Estilo de autenticação esperado, como bearer, session ou public.",
            },
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrições técnicas ou de negócio relevantes para a API.",
            },
        },
        "required": ["project_brief"],
        "additionalProperties": False,
    },
    output_schema={
        "type": "object",
        "properties": {
            "api_summary": {"type": "string"},
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "endpoints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "path": {"type": "string"},
                        "purpose": {"type": "string"},
                        "request": {"type": "string"},
                        "response": {"type": "string"},
                    },
                    "required": ["method", "path", "purpose"],
                    "additionalProperties": False,
                },
            },
            "suggested_base_path": {"type": "string"},
        },
        "required": ["api_summary", "assumptions", "endpoints"],
        "additionalProperties": False,
    },
)


DOMAIN_TOOLS: tuple[DomainToolDefinition, ...] = (
    generate_mvp_plan_tool,
    generate_entities_tool,
    generate_sql_schema_tool,
    suggest_api_endpoints_tool,
)
DOMAIN_TOOL_MAP = {tool.name: tool for tool in DOMAIN_TOOLS}


def list_domain_mcp_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema,
        }
        for tool in DOMAIN_TOOLS
    ]


def is_domain_tool(tool_name: str) -> bool:
    return tool_name in DOMAIN_TOOL_MAP


async def execute_domain_tool(
    tool_name: str,
    arguments: dict[str, Any],
    ollama_service: OllamaService,
) -> dict[str, Any]:
    if tool_name == generate_mvp_plan_tool.name:
        return await _execute_generate_mvp_plan(arguments, ollama_service)

    if tool_name == generate_entities_tool.name:
        return await _execute_generate_entities(arguments, ollama_service)

    if tool_name == generate_sql_schema_tool.name:
        return await _execute_generate_sql_schema(arguments, ollama_service)

    if tool_name == suggest_api_endpoints_tool.name:
        return await _execute_suggest_api_endpoints(arguments, ollama_service)

    raise ValueError(f"Tool de domínio desconhecida: {tool_name}")


async def _execute_generate_mvp_plan(
    arguments: dict[str, Any],
    ollama_service: OllamaService,
) -> dict[str, Any]:
    project_brief = str(arguments.get("project_brief", "")).strip()
    if len(project_brief) < 5:
        raise ValueError("A tool generate_mvp_plan exige um campo project_brief válido.")

    target_users = _normalize_string_list(arguments.get("target_users"))
    core_features = _normalize_string_list(arguments.get("core_features"))
    constraints = _normalize_string_list(arguments.get("constraints"))
    request_constraints = extract_request_constraints(project_brief)

    plan_prompt = _build_mvp_plan_prompt(
        project_brief=project_brief,
        target_users=target_users,
        core_features=core_features,
        constraints=constraints,
        request_constraints=request_constraints,
    )
    plan = await ollama_service.chat(plan_prompt)

    return {
        "project_summary": project_brief,
        "assumptions": _build_mvp_assumptions(
            target_users=target_users,
            core_features=core_features,
            constraints=constraints,
        ),
        "mvp_plan_markdown": plan.strip(),
        "rendered_text": plan.strip(),
    }


async def _execute_generate_sql_schema(
    arguments: dict[str, Any],
    ollama_service: OllamaService,
) -> dict[str, Any]:
    project_brief = str(arguments.get("project_brief", "")).strip()
    if len(project_brief) < 5:
        raise ValueError("A tool generate_sql_schema exige um campo project_brief válido.")

    entities = _normalize_string_list(arguments.get("entities"))
    core_features = _normalize_string_list(arguments.get("core_features"))
    constraints = _normalize_string_list(arguments.get("constraints"))
    database_engine = str(arguments.get("database_engine", "")).strip().lower()
    request_constraints = extract_request_constraints(project_brief)

    sql_prompt = _build_sql_schema_prompt(
        project_brief=project_brief,
        entities=entities,
        core_features=core_features,
        constraints=constraints,
        database_engine=database_engine,
        request_constraints=request_constraints,
    )
    sql = await ollama_service.generate_sql_schema(sql_prompt)

    response: dict[str, Any] = {
        "schema_summary": project_brief,
        "assumptions": _build_sql_assumptions(
            entities=entities,
            core_features=core_features,
            constraints=constraints,
            database_engine=database_engine,
        ),
        "sql": sql,
    }

    suggested_file_name = _build_suggested_sql_file_name(project_brief)
    if suggested_file_name:
        response["suggested_file_name"] = suggested_file_name

    response["rendered_text"] = sql.strip()
    return response


async def _execute_generate_entities(
    arguments: dict[str, Any],
    ollama_service: OllamaService,
) -> dict[str, Any]:
    project_brief = str(arguments.get("project_brief", "")).strip()
    if len(project_brief) < 5:
        raise ValueError("A tool generate_entities exige um campo project_brief válido.")

    target_users = _normalize_string_list(arguments.get("target_users"))
    core_features = _normalize_string_list(arguments.get("core_features"))
    constraints = _normalize_string_list(arguments.get("constraints"))
    request_constraints = extract_request_constraints(project_brief)

    entities_prompt = _build_entities_prompt(
        project_brief=project_brief,
        target_users=target_users,
        core_features=core_features,
        constraints=constraints,
        request_constraints=request_constraints,
    )
    entities_markdown = await ollama_service.chat(entities_prompt)

    return {
        "domain_summary": project_brief,
        "assumptions": _build_entities_assumptions(
            target_users=target_users,
            core_features=core_features,
            constraints=constraints,
        ),
        "entities_markdown": entities_markdown.strip(),
        "rendered_text": entities_markdown.strip(),
    }


async def _execute_suggest_api_endpoints(
    arguments: dict[str, Any],
    ollama_service: OllamaService,
) -> dict[str, Any]:
    project_brief = str(arguments.get("project_brief", "")).strip()
    if len(project_brief) < 5:
        raise ValueError("A tool suggest_api_endpoints exige um campo project_brief válido.")

    core_entities = _normalize_string_list(arguments.get("core_entities"))
    core_features = _normalize_string_list(arguments.get("core_features"))
    constraints = _normalize_string_list(arguments.get("constraints"))
    auth_style = str(arguments.get("auth_style", "")).strip().lower()
    request_constraints = extract_request_constraints(project_brief)

    api_prompt = _build_api_endpoints_prompt(
        project_brief=project_brief,
        core_entities=core_entities,
        core_features=core_features,
        auth_style=auth_style,
        constraints=constraints,
        request_constraints=request_constraints,
    )
    raw_response = await ollama_service.chat(api_prompt)
    parsed = _parse_api_endpoints_response(raw_response)
    endpoints = _normalize_endpoints(parsed.get("endpoints"))
    if not endpoints:
        endpoints = _extract_endpoints_from_text(raw_response)

    response: dict[str, Any] = {
        "api_summary": str(parsed.get("api_summary", "")).strip() or project_brief,
        "assumptions": _build_api_assumptions(
            core_entities=core_entities,
            core_features=core_features,
            auth_style=auth_style,
            constraints=constraints,
        ),
    }
    if endpoints:
        response["endpoints"] = endpoints

    suggested_base_path = str(parsed.get("suggested_base_path", "")).strip()
    if suggested_base_path:
        response["suggested_base_path"] = suggested_base_path

    if endpoints:
        response["rendered_text"] = _render_api_endpoints(endpoints)
    else:
        response["rendered_text"] = _build_api_text_fallback(raw_response)
    return response


def _normalize_string_list(raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        return []

    normalized_items: list[str] = []
    for item in raw_value:
        text = str(item).strip()
        if text:
            normalized_items.append(text)
    return normalized_items


def _build_mvp_plan_prompt(
    *,
    project_brief: str,
    target_users: list[str],
    core_features: list[str],
    constraints: list[str],
    request_constraints,
) -> list[dict[str, str]]:
    sections = [f"Projeto:\n{project_brief}"]

    if target_users:
        sections.append("Utilizadores alvo:\n- " + "\n- ".join(target_users))
    if core_features:
        sections.append("Funcionalidades core do MVP:\n- " + "\n- ".join(core_features))
    if constraints:
        sections.append("Restrições:\n- " + "\n- ".join(constraints))

    guardrails = build_output_guardrails(
        request_constraints,
        allow_code=False,
        allow_sql=False,
        allow_database=False,
        allow_api=False,
        allow_backend=False,
        allow_frontend=False,
    )

    instructions = [
        "Tu geras apenas planeamento de produto para um MVP.",
        "Nunca incluas SQL, base de dados, API, endpoints, backend, frontend, código ou entidades técnicas.",
        "Foca apenas objetivo, público-alvo, funcionalidades essenciais, prioridade e próximos passos do produto.",
        "Não adiciones secções que o utilizador não pediu.",
        "Se o pedido for curto, simples, resumido ou apenas, responde de forma curta.",
        "Se não houver pedido de detalhe, usa no máximo 4 bullets curtos.",
    ]
    if request_constraints.forbid_explanations:
        instructions.append("Devolve apenas bullets diretos, sem introdução nem conclusão.")
    instructions.extend(guardrails)

    return [
        {"role": "system", "content": "\n".join(instructions)},
        {"role": "user", "content": "\n\n".join(sections).strip()},
    ]


def _build_sql_schema_prompt(
    *,
    project_brief: str,
    entities: list[str],
    core_features: list[str],
    constraints: list[str],
    database_engine: str,
    request_constraints,
) -> str:
    sections = [f"Projeto:\n{project_brief}"]

    if entities:
        sections.append("Entidades esperadas:\n- " + "\n- ".join(entities))
    if core_features:
        sections.append("Funcionalidades core:\n- " + "\n- ".join(core_features))
    if constraints:
        sections.append("Restrições:\n- " + "\n- ".join(constraints))
    if database_engine:
        sections.append(f"Motor de base de dados preferido:\n{database_engine}")

    guardrails = build_output_guardrails(
        request_constraints,
        allow_code=False,
        allow_sql=True,
        allow_database=True,
        allow_api=False,
        allow_backend=False,
        allow_frontend=False,
    )
    if guardrails:
        sections.append("Regras de output:\n- " + "\n- ".join(guardrails))

    return "\n\n".join(sections).strip()


def _build_entities_prompt(
    *,
    project_brief: str,
    target_users: list[str],
    core_features: list[str],
    constraints: list[str],
    request_constraints,
) -> list[dict[str, str]]:
    sections = [f"Projeto:\n{project_brief}"]

    if target_users:
        sections.append("Utilizadores alvo:\n- " + "\n- ".join(target_users))
    if core_features:
        sections.append("Funcionalidades core:\n- " + "\n- ".join(core_features))
    if constraints:
        sections.append("Restrições:\n- " + "\n- ".join(constraints))

    guardrails = build_output_guardrails(
        request_constraints,
        allow_code=False,
        allow_sql=False,
        allow_database=False,
        allow_api=False,
        allow_backend=False,
        allow_frontend=False,
    )

    instructions = [
        "Responde em Markdown e foca apenas a modelação conceptual do domínio.",
        "Devolve só entidades, campos principais e relações relevantes.",
        "Não geres SQL.",
        "Não cries CREATE TABLE.",
        "Não desenhes API nem endpoints.",
        "Não incluas backend, frontend nem código.",
        "Se o pedido falar em tabelas conceptuais, trata-as como entidades de domínio.",
        "Se não houver pedido de detalhe, limita-te a 3 a 5 entidades principais.",
        "Formato esperado:",
        "# 1. Entidades principais",
        "## Nome da entidade",
        "- Campos principais: ...",
        "- Relações: ...",
        "- Observações: ... (opcional)",
    ]
    if request_constraints.forbid_explanations:
        instructions.append("Não incluas resumo inicial nem secção final; vai direto às entidades.")
    instructions.extend(guardrails)

    return [
        {"role": "system", "content": "\n".join(instructions)},
        {"role": "user", "content": "\n\n".join(sections).strip()},
    ]


def _build_api_endpoints_prompt(
    *,
    project_brief: str,
    core_entities: list[str],
    core_features: list[str],
    auth_style: str,
    constraints: list[str],
    request_constraints,
) -> list[dict[str, str]]:
    sections = [f"Projeto:\n{project_brief}"]

    if core_entities:
        sections.append("Entidades principais:\n- " + "\n- ".join(core_entities))
    if core_features:
        sections.append("Funcionalidades core:\n- " + "\n- ".join(core_features))
    if auth_style:
        sections.append(f"Estilo de autenticação:\n{auth_style}")
    if constraints:
        sections.append("Restrições:\n- " + "\n- ".join(constraints))

    guardrails = build_output_guardrails(
        request_constraints,
        allow_code=False,
        allow_sql=False,
        allow_database=False,
        allow_api=True,
        allow_backend=False,
        allow_frontend=False,
    )

    instructions = """
Devolve JSON puro e válido com esta estrutura:
{
  "api_summary": "string",
  "suggested_base_path": "string opcional",
  "endpoints": [
    {
      "method": "GET|POST|PUT|PATCH|DELETE",
      "path": "/...",
      "purpose": "objetivo do endpoint",
      "request": "resumo curto do request quando fizer sentido",
      "response": "resumo curto do response quando fizer sentido"
    }
  ]
}

Regras:
- Sugere apenas endpoints essenciais para um MVP.
- Prefere REST simples.
- Usa paths consistentes e previsíveis.
- Inclui request e response quando fizer sentido.
- Não incluas SQL, entidades completas, frontend nem código longo.
- Se o pedido for curto ou simples, usa descrições curtas.
- A tua primeira opção deve ser sempre JSON válido e sem markdown.
- Se por algum motivo falhares no JSON, devolve apenas linhas no formato: `- METHOD /path: descrição curta`.
- Não uses markdown nem texto fora do JSON.
""".strip()

    if request_constraints.forbid_explanations:
        instructions = f"{instructions}\n- Não incluas texto introdutório nem comentários extra."
    if guardrails:
        instructions = f"{instructions}\n- " + "\n- ".join(guardrails)

    return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": "\n\n".join(sections).strip()},
    ]


def _build_mvp_assumptions(
    *,
    target_users: list[str],
    core_features: list[str],
    constraints: list[str],
) -> list[str]:
    assumptions: list[str] = []

    if not target_users:
        assumptions.append("Os utilizadores-alvo serão assumidos a partir do briefing principal.")
    if not core_features:
        assumptions.append("O plano vai priorizar apenas o fluxo principal do MVP descrito no briefing.")
    if not constraints:
        assumptions.append("Sem restrições explícitas, o plano assume um MVP web com stack simples e iterável.")

    return assumptions


def _build_sql_assumptions(
    *,
    entities: list[str],
    core_features: list[str],
    constraints: list[str],
    database_engine: str,
) -> list[str]:
    assumptions: list[str] = []

    if not entities:
        assumptions.append("As entidades principais serão inferidas a partir do briefing e das funcionalidades descritas.")
    if not core_features:
        assumptions.append("O schema vai cobrir apenas o fluxo principal do MVP descrito no briefing.")
    if not constraints:
        assumptions.append("Sem restrições explícitas, o esquema assume relações simples, chaves primárias e índices essenciais.")
    if not database_engine:
        assumptions.append("Sem motor indicado, o esquema assume SQL relacional com sintaxe compatível com PostgreSQL.")

    return assumptions


def _build_entities_assumptions(
    *,
    target_users: list[str],
    core_features: list[str],
    constraints: list[str],
) -> list[str]:
    assumptions: list[str] = []

    if not target_users:
        assumptions.append("Os utilizadores-alvo serão inferidos a partir do briefing principal.")
    if not core_features:
        assumptions.append("A modelação vai focar apenas os fluxos essenciais do MVP descrito no briefing.")
    if not constraints:
        assumptions.append("Sem restrições explícitas, a proposta assume um domínio simples, com entidades e relações principais.")

    return assumptions


def _build_api_assumptions(
    *,
    core_entities: list[str],
    core_features: list[str],
    auth_style: str,
    constraints: list[str],
) -> list[str]:
    assumptions: list[str] = []

    if not core_entities:
        assumptions.append("As entidades principais da API serão inferidas a partir do briefing e das funcionalidades descritas.")
    if not core_features:
        assumptions.append("Os endpoints vão cobrir apenas os fluxos essenciais do MVP descrito no briefing.")
    if not auth_style:
        assumptions.append("Sem estilo de autenticação indicado, a sugestão assume autenticação bearer simples apenas quando fizer sentido.")
    if not constraints:
        assumptions.append("Sem restrições explícitas, a API assume REST simples com payloads curtos e validações básicas.")

    return assumptions


def _build_suggested_sql_file_name(project_brief: str) -> str:
    words = []
    for raw_part in project_brief.lower().split():
        normalized = "".join(char for char in raw_part if char.isalnum() or char == "_")
        if normalized:
            words.append(normalized)
        if len(words) == 4:
            break

    if not words:
        return "schema"

    return "_".join(words) + "_schema"


def _render_api_endpoints(endpoints: list[dict[str, str]]) -> str:
    rendered_lines: list[str] = []

    for endpoint in endpoints:
        method = str(endpoint.get("method", "")).strip().upper()
        path = str(endpoint.get("path", "")).strip()
        purpose = str(endpoint.get("purpose", "")).strip()
        if not method or not path or not purpose:
            continue

        rendered_lines.append(f"- {method} {path}: {purpose}")

        request_text = str(endpoint.get("request", "")).strip()
        response_text = str(endpoint.get("response", "")).strip()
        if request_text:
            rendered_lines.append(f"  request: {request_text}")
        if response_text:
            rendered_lines.append(f"  response: {response_text}")

    return "\n".join(rendered_lines).strip()


def _parse_api_endpoints_response(raw_response: str) -> dict[str, Any]:
    candidates = _build_api_parse_candidates(raw_response)

    for candidate in candidates:
        parsed = _try_parse_api_payload(candidate)
        if isinstance(parsed, dict):
            return parsed

    return {
        "api_summary": "",
        "endpoints": _extract_endpoints_from_text(raw_response),
    }


def _build_api_parse_candidates(raw_response: str) -> list[str]:
    text = raw_response.strip()
    candidates: list[str] = []

    if text:
        candidates.append(text)

    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fenced_match:
        fenced_text = fenced_match.group(1).strip()
        if fenced_text:
            candidates.append(fenced_text)

    json_object = _extract_first_json_object(text)
    if json_object:
        candidates.append(json_object)

    unique_candidates: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)

    return unique_candidates


def _try_parse_api_payload(text: str) -> dict[str, Any] | None:
    normalized = text.strip()
    if not normalized:
        return None

    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)

    for candidate in (normalized, normalized.replace("'", '"')):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    return None


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def _extract_endpoints_from_text(raw_response: str) -> list[dict[str, str]]:
    endpoints: list[dict[str, str]] = []

    for raw_line in raw_response.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^`|`$", "", line)

        match = re.match(
            r"^(GET|POST|PUT|PATCH|DELETE)\s+([^\s:]+)\s*(?:[:\-]\s*(.+))?$",
            line,
            re.IGNORECASE,
        )
        if not match:
            continue

        method = match.group(1).upper()
        path = match.group(2).strip()
        purpose = str(match.group(3) or "Endpoint essencial da API.").strip()

        endpoints.append(
            {
                "method": method,
                "path": path,
                "purpose": purpose,
            }
        )

    return endpoints


def _build_api_text_fallback(raw_response: str) -> str:
    endpoints = _extract_endpoints_from_text(raw_response)
    if endpoints:
        return _render_api_endpoints(endpoints)

    text = raw_response.strip()
    fenced_match = re.search(r"```(?:json|markdown)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "Nao foi possivel estruturar endpoints validos, mas a tool recebeu uma resposta vazia."

    return "\n".join(lines[:8])


def _normalize_endpoints(raw_value: Any) -> list[dict[str, str]]:
    if not isinstance(raw_value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue

        method = str(item.get("method", "")).strip().upper()
        path = str(item.get("path", "")).strip()
        purpose = str(item.get("purpose", "")).strip()
        if not method or not path or not purpose:
            continue

        endpoint = {
            "method": method,
            "path": path,
            "purpose": purpose,
        }

        request = str(item.get("request", "")).strip()
        response = str(item.get("response", "")).strip()
        if request:
            endpoint["request"] = request
        if response:
            endpoint["response"] = response

        normalized.append(endpoint)

    return normalized

