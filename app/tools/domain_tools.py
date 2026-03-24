import json
import re
from dataclasses import dataclass
from typing import Any

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
        "Gera um plano de MVP orientado ao domínio do produto com escopo, entidades, "
        "base de dados, API e passos de implementação."
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

    plan_prompt = _build_plan_prompt(
        project_brief=project_brief,
        target_users=target_users,
        core_features=core_features,
        constraints=constraints,
    )
    plan = await ollama_service.generate_plan(plan_prompt)

    return {
        "project_summary": project_brief,
        "assumptions": _build_mvp_assumptions(
            target_users=target_users,
            core_features=core_features,
            constraints=constraints,
        ),
        "mvp_plan_markdown": plan,
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

    sql_prompt = _build_sql_schema_prompt(
        project_brief=project_brief,
        entities=entities,
        core_features=core_features,
        constraints=constraints,
        database_engine=database_engine,
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

    return response


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

    api_prompt = _build_api_endpoints_prompt(
        project_brief=project_brief,
        core_entities=core_entities,
        core_features=core_features,
        auth_style=auth_style,
        constraints=constraints,
    )
    raw_response = await ollama_service.chat(api_prompt)
    parsed = _parse_api_endpoints_response(raw_response)

    endpoints = _normalize_endpoints(parsed.get("endpoints"))
    if not endpoints:
        raise ValueError("A tool suggest_api_endpoints não conseguiu gerar endpoints válidos.")

    response: dict[str, Any] = {
        "api_summary": str(parsed.get("api_summary", "")).strip() or project_brief,
        "assumptions": _build_api_assumptions(
            core_entities=core_entities,
            core_features=core_features,
            auth_style=auth_style,
            constraints=constraints,
        ),
        "endpoints": endpoints,
    }

    suggested_base_path = str(parsed.get("suggested_base_path", "")).strip()
    if suggested_base_path:
        response["suggested_base_path"] = suggested_base_path

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


def _build_plan_prompt(
    *,
    project_brief: str,
    target_users: list[str],
    core_features: list[str],
    constraints: list[str],
) -> str:
    sections = [f"Projeto:\n{project_brief}"]

    if target_users:
        sections.append("Utilizadores alvo:\n- " + "\n- ".join(target_users))
    if core_features:
        sections.append("Funcionalidades core do MVP:\n- " + "\n- ".join(core_features))
    if constraints:
        sections.append("Restrições:\n- " + "\n- ".join(constraints))

    return "\n\n".join(sections).strip()


def _build_sql_schema_prompt(
    *,
    project_brief: str,
    entities: list[str],
    core_features: list[str],
    constraints: list[str],
    database_engine: str,
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

    return "\n\n".join(sections).strip()


def _build_api_endpoints_prompt(
    *,
    project_brief: str,
    core_entities: list[str],
    core_features: list[str],
    auth_style: str,
    constraints: list[str],
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

    instructions = """
Devolve apenas JSON válido com esta estrutura:
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
- Não uses markdown nem texto fora do JSON.
""".strip()

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


def _parse_api_endpoints_response(raw_response: str) -> dict[str, Any]:
    text = raw_response.strip()
    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("A tool suggest_api_endpoints recebeu JSON inválido do modelo.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("A tool suggest_api_endpoints recebeu um payload inválido do modelo.")

    return parsed


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

