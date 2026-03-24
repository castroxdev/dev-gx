from typing import Any

from app.services.request_analysis import extract_request_constraints, normalize_prompt_text


MVP_TOOL = "generate_mvp_plan"
ENTITIES_TOOL = "generate_entities"
SQL_TOOL = "generate_sql_schema"
API_TOOL = "suggest_api_endpoints"

EXPLICIT_REQUEST_VERBS = (
    "usa",
    "usar",
    "executa",
    "executar",
    "chama",
    "chamar",
    "utiliza",
    "utilizar",
)

MVP_DIRECT_PHRASES = (
    "plano mvp",
    "roadmap",
    "objetivo do produto",
    "objetivo do projeto",
    "publico alvo",
    "publico-alvo",
    "funcionalidades principais",
    "funcionalidades core",
    "principais funcionalidades",
    "escopo do mvp",
    "escopo inicial",
    "plano curto",
    "fases do mvp",
    "fases de implementacao",
    "passos de implementacao",
)
MVP_SUPPORT_PHRASES = (
    "mvp",
    "fases",
    "backlog",
    "prioridades",
    "entregas",
    "scope",
    "target users",
    "target audience",
)

ENTITY_DIRECT_PHRASES = (
    "entidades",
    "modela as entidades",
    "modelar entidades",
    "modelo de dominio",
    "modelacao de dominio",
    "modelagem de dominio",
    "domain model",
    "tabelas conceptuais",
    "tabelas conceituais",
    "campos principais",
    "campos essenciais",
    "atributos principais",
    "relacoes principais",
    "relacionamentos principais",
    "modelo conceptual",
    "modelo conceitual",
)
ENTITY_SUPPORT_PHRASES = (
    "entidade",
    "dominio",
    "modela",
    "modelar",
    "modelacao",
    "modelagem",
    "conceptual",
    "conceitual",
    "relacoes",
    "relacionamentos",
    "atributos",
    "campos",
)

API_DIRECT_PHRASES = (
    "endpoint",
    "endpoints",
    "api",
    "rotas",
    "rota",
    "controllers",
    "controller",
    "rest",
    "backend http",
    "http api",
)
API_SUPPORT_PHRASES = (
    "crud",
    "request",
    "response",
    "autenticacao",
    "authentication",
)

SQL_EXPLICIT_PHRASES = (
    "schema sql",
    "esquema sql",
    "script sql",
    "sql ddl",
    "create table",
    "alter table",
    "foreign key",
    "primary key",
    "base de dados relacional",
    "banco de dados relacional",
    "database relacional",
    "postgres",
    "postgresql",
    "mysql",
    "sqlite",
    "sql",
)
SQL_DATABASE_NOUNS = (
    "base de dados",
    "banco de dados",
    "database",
    "bd",
)
SQL_TECHNICAL_NOUNS = (
    "schema",
    "esquema",
    "tabela",
    "tabelas",
    "relacional",
    "create table",
    "migration",
    "migracao",
    "ddl",
    "indice",
    "indices",
    "index",
    "indexes",
)
SQL_ACTION_VERBS = (
    "cria",
    "criar",
    "gera",
    "gerar",
    "desenha",
    "desenhar",
    "monta",
    "montar",
)
SQL_NEGATION_PHRASES = (
    "sem sql",
    "nao sql",
    "nao quero sql",
    "nao gerar sql",
    "sem esquema sql",
    "sem schema sql",
)


def select_tool_from_prompt(
    last_user_message: str,
    available_tools: list[dict[str, Any]],
) -> dict[str, dict[str, object]] | None:
    text = last_user_message.strip()
    if not text:
        return None

    available_tool_names = {
        str(tool.get("name", "")).strip()
        for tool in available_tools
        if str(tool.get("name", "")).strip()
    }
    if not available_tool_names:
        return None

    explicit_request = extract_explicit_tool_request(text, available_tool_names)
    if explicit_request is not None:
        return explicit_request

    normalized_text = normalize_prompt_text(text)
    constraints = extract_request_constraints(text)

    if constraints.sql_only and not constraints.forbid_sql and SQL_TOOL in available_tool_names:
        return {
            "tool": SQL_TOOL,
            "arguments": build_tool_arguments(SQL_TOOL, text, normalized_text),
        }

    scores: dict[str, int] = {}

    if MVP_TOOL in available_tool_names:
        scores[MVP_TOOL] = score_mvp_intent(normalized_text)
    if ENTITIES_TOOL in available_tool_names:
        scores[ENTITIES_TOOL] = score_entities_intent(normalized_text)
    if SQL_TOOL in available_tool_names:
        scores[SQL_TOOL] = score_sql_intent(normalized_text, constraints=constraints)
    if API_TOOL in available_tool_names:
        scores[API_TOOL] = score_api_intent(normalized_text, constraints=constraints)

    positive_scores = [(tool_name, score) for tool_name, score in scores.items() if score > 0]
    if not positive_scores:
        return None

    ranked_scores = sorted(positive_scores, key=lambda item: item[1], reverse=True)
    top_tool_name, top_score = ranked_scores[0]
    if len(ranked_scores) > 1 and ranked_scores[1][1] == top_score:
        return None

    return {
        "tool": top_tool_name,
        "arguments": build_tool_arguments(top_tool_name, text, normalized_text),
    }


def extract_explicit_tool_request(
    text: str,
    available_tool_names: set[str],
) -> dict[str, dict[str, object]] | None:
    normalized_text = normalize_prompt_text(text)
    matched_tool_name = next(
        (
            tool_name
            for tool_name in available_tool_names
            if normalize_prompt_text(tool_name) in normalized_text
        ),
        None,
    )
    if matched_tool_name is None:
        return None

    if not any(verb in normalized_text for verb in EXPLICIT_REQUEST_VERBS):
        return None

    return {
        "tool": matched_tool_name,
        "arguments": build_tool_arguments(matched_tool_name, text, normalized_text),
    }


def build_tool_arguments(
    tool_name: str,
    original_text: str,
    normalized_text: str,
) -> dict[str, object]:
    arguments: dict[str, object] = {"project_brief": original_text}

    if tool_name == SQL_TOOL:
        database_engine = extract_database_engine(normalized_text)
        if database_engine:
            arguments["database_engine"] = database_engine

    if tool_name == API_TOOL:
        auth_style = extract_auth_style(normalized_text)
        if auth_style:
            arguments["auth_style"] = auth_style

    return arguments


def score_mvp_intent(text: str) -> int:
    score = 0

    direct_hits = count_phrase_hits(text, MVP_DIRECT_PHRASES)
    support_hits = count_phrase_hits(text, MVP_SUPPORT_PHRASES)
    if direct_hits:
        score += 4 + min(direct_hits, 3)
    if "mvp" in text:
        score += 2
    if support_hits:
        score += min(support_hits, 2)
    if any(word in text for word in ("plano", "roadmap", "fases", "escopo")):
        score += 1

    return score


def score_entities_intent(text: str) -> int:
    score = 0

    direct_hits = count_phrase_hits(text, ENTITY_DIRECT_PHRASES)
    support_hits = count_phrase_hits(text, ENTITY_SUPPORT_PHRASES)
    if direct_hits:
        score += 4 + min(direct_hits, 3)
    if support_hits:
        score += min(support_hits, 3)
    if any(word in text for word in ("modela", "modelar", "modelo")) and any(
        word in text for word in ("entidade", "entidades", "dominio")
    ):
        score += 2

    return score


def score_api_intent(text: str, *, constraints) -> int:
    if constraints.forbid_api:
        return 0

    score = 0

    direct_hits = count_phrase_hits(text, API_DIRECT_PHRASES)
    support_hits = count_phrase_hits(text, API_SUPPORT_PHRASES)
    if direct_hits:
        score += 4 + min(direct_hits, 3)
    if support_hits:
        score += min(support_hits, 2)

    return score


def score_sql_intent(text: str, *, constraints) -> int:
    if constraints.forbid_sql or constraints.forbid_database:
        return 0

    if constraints.sql_only:
        return 10

    if any(phrase in text for phrase in SQL_NEGATION_PHRASES):
        return 0

    explicit_hits = count_phrase_hits(text, SQL_EXPLICIT_PHRASES)
    has_database_request = any(noun in text for noun in SQL_DATABASE_NOUNS) and any(
        term in text for term in SQL_TECHNICAL_NOUNS + SQL_ACTION_VERBS
    )

    score = 0
    if explicit_hits:
        score += 6 + min(explicit_hits, 2)
    if has_database_request:
        score += 4

    return score


def extract_database_engine(text: str) -> str | None:
    if "postgresql" in text or "postgres" in text:
        return "postgresql"
    if "mysql" in text:
        return "mysql"
    if "sqlite" in text:
        return "sqlite"
    return None


def extract_auth_style(text: str) -> str | None:
    if "bearer" in text or "jwt" in text:
        return "bearer"
    if "session" in text:
        return "session"
    if "public" in text:
        return "public"
    return None


def count_phrase_hits(text: str, phrases: tuple[str, ...]) -> int:
    return sum(1 for phrase in phrases if phrase in text)
