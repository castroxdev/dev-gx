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
        "Gera um plano de MVP orientado ao dominio do produto com escopo, entidades, "
        "base de dados, API e passos de implementacao."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_brief": {
                "type": "string",
                "description": "Descricao principal do produto, problema e objetivo do MVP.",
            },
            "target_users": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Perfis de utilizadores principais do MVP.",
            },
            "core_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Funcionalidades essenciais que precisam entrar nesta primeira versao.",
            },
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restricoes tecnicas, operacionais ou de prazo relevantes.",
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
        "Gera um esquema SQL inicial para o MVP com tabelas, relacoes, chaves e indices "
        "essenciais."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_brief": {
                "type": "string",
                "description": "Descricao principal do produto e do problema a modelar.",
            },
            "entities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Entidades de dominio que devem aparecer no schema inicial.",
            },
            "core_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Funcionalidades centrais que influenciam o modelo de dados.",
            },
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restricoes tecnicas ou de negocio relevantes para o schema.",
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


DOMAIN_TOOLS: tuple[DomainToolDefinition, ...] = (
    generate_mvp_plan_tool,
    generate_sql_schema_tool,
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

    raise ValueError(f"Tool de dominio desconhecida: {tool_name}")


async def _execute_generate_mvp_plan(
    arguments: dict[str, Any],
    ollama_service: OllamaService,
) -> dict[str, Any]:
    project_brief = str(arguments.get("project_brief", "")).strip()
    if len(project_brief) < 5:
        raise ValueError("A tool generate_mvp_plan exige um campo project_brief valido.")

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
        raise ValueError("A tool generate_sql_schema exige um campo project_brief valido.")

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
        sections.append("Restricoes:\n- " + "\n- ".join(constraints))

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
        sections.append("Restricoes:\n- " + "\n- ".join(constraints))
    if database_engine:
        sections.append(f"Motor de base de dados preferido:\n{database_engine}")

    return "\n\n".join(sections).strip()


def _build_mvp_assumptions(
    *,
    target_users: list[str],
    core_features: list[str],
    constraints: list[str],
) -> list[str]:
    assumptions: list[str] = []

    if not target_users:
        assumptions.append("Os utilizadores alvo serao assumidos a partir do briefing principal.")
    if not core_features:
        assumptions.append("O plano vai priorizar apenas o fluxo principal do MVP descrito no briefing.")
    if not constraints:
        assumptions.append("Sem restricoes explicitas, o plano assume um MVP web com stack simples e iteravel.")

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
        assumptions.append("As entidades principais serao inferidas a partir do briefing e das funcionalidades descritas.")
    if not core_features:
        assumptions.append("O schema vai cobrir apenas o fluxo principal do MVP descrito no briefing.")
    if not constraints:
        assumptions.append("Sem restricoes explicitas, o schema assume relacoes simples, chaves primarias e indices essenciais.")
    if not database_engine:
        assumptions.append("Sem motor indicado, o schema assume SQL relacional com sintaxe compativel com PostgreSQL.")

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
