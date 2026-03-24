import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestConstraints:
    wants_brief_output: bool
    wants_simple_output: bool
    only_requested_scope: bool
    forbid_code: bool
    forbid_sql: bool
    forbid_database: bool
    forbid_api: bool
    forbid_explanations: bool
    forbid_backend: bool
    forbid_frontend: bool
    sql_only: bool


BRIEF_PHRASES = (
    "curto",
    "curta",
    "breve",
    "simples",
    "simplesmente",
    "resumido",
    "resumida",
    "sucinto",
    "sucinta",
)

ONLY_SCOPE_PHRASES = (
    "apenas",
    "so ",
    "somente",
    "apenas o resultado",
    "so o resultado",
    "somente o resultado",
    "apenas o output",
    "so o output",
    "somente o output",
)

FORBID_CODE_PHRASES = (
    "sem codigo",
    "nao incluas codigo",
    "nao incluir codigo",
    "nao quero codigo",
)

FORBID_SQL_PHRASES = (
    "sem sql",
    "nao incluas sql",
    "nao incluir sql",
    "nao gerar sql",
    "sem esquema sql",
    "sem schema sql",
)

FORBID_DATABASE_PHRASES = (
    "sem base de dados",
    "sem banco de dados",
    "nao incluas base de dados",
    "nao incluir base de dados",
    "sem base de dados relacional",
)

FORBID_API_PHRASES = (
    "sem api",
    "nem api",
    "nao incluas api",
    "nao incluir api",
    "nao quero api",
    "sem endpoint",
    "sem endpoints",
    "nao incluas endpoint",
    "nao incluas endpoints",
    "nao quero endpoint",
    "nao quero endpoints",
    "sem rota",
    "sem rotas",
    "nao quero rota",
    "nao quero rotas",
)

FORBID_EXPLANATIONS_PHRASES = (
    "sem explicacoes",
    "sem explicacao",
    "nao expliques",
    "nao quero explicacoes",
    "nao quero explicacao",
    "sem texto extra",
    "sem contexto",
    "sem resumo",
    "sem introducao",
    "sem conclusao",
    "apenas o resultado",
    "so o resultado",
    "somente o resultado",
    "apenas o output",
    "so o output",
    "somente o output",
)

SQL_ONLY_PHRASES = (
    "apenas sql",
    "so sql",
    "somente sql",
    "apenas o sql",
    "so o sql",
    "somente o sql",
)


def extract_request_constraints(user_input: str) -> RequestConstraints:
    text = normalize_prompt_text(user_input)

    return RequestConstraints(
        wants_brief_output=contains_any_phrase(text, BRIEF_PHRASES),
        wants_simple_output=contains_any_phrase(text, ("simples", "objetivo", "objetiva")),
        only_requested_scope=contains_any_phrase(text, ONLY_SCOPE_PHRASES),
        forbid_code=contains_any_phrase(text, FORBID_CODE_PHRASES),
        forbid_sql=contains_any_phrase(text, FORBID_SQL_PHRASES),
        forbid_database=contains_any_phrase(text, FORBID_DATABASE_PHRASES),
        forbid_api=contains_any_phrase(text, FORBID_API_PHRASES),
        forbid_explanations=contains_any_phrase(text, FORBID_EXPLANATIONS_PHRASES),
        forbid_backend=contains_any_phrase(
            text,
            ("sem backend", "nao incluas backend", "nao incluir backend"),
        ),
        forbid_frontend=contains_any_phrase(
            text,
            ("sem frontend", "nao incluas frontend", "nao incluir frontend"),
        ),
        sql_only=contains_any_phrase(text, SQL_ONLY_PHRASES),
    )


def build_output_guardrails(
    constraints: RequestConstraints,
    *,
    allow_code: bool,
    allow_sql: bool,
    allow_database: bool,
    allow_api: bool,
    allow_backend: bool,
    allow_frontend: bool,
) -> list[str]:
    rules: list[str] = []

    if constraints.only_requested_scope:
        rules.append("Responde apenas com o que foi pedido, sem seções extra.")
    if constraints.wants_brief_output:
        rules.append("Mantém a resposta curta e direta.")
    if constraints.wants_simple_output:
        rules.append("Usa linguagem simples e evita detalhes desnecessários.")
    if constraints.forbid_explanations:
        rules.append("Não incluas introdução, conclusão, resumo, contexto nem explicações.")
    if constraints.sql_only:
        rules.append("Devolve apenas SQL limpo.")
    if constraints.forbid_code or not allow_code:
        rules.append("Não incluas código.")
    if constraints.forbid_sql or not allow_sql:
        rules.append("Não incluas SQL nem CREATE TABLE.")
    if constraints.forbid_database or not allow_database:
        rules.append("Não incluas desenho de base de dados.")
    if constraints.forbid_api or not allow_api:
        rules.append("Não incluas API, endpoints nem rotas.")
    if constraints.forbid_backend or not allow_backend:
        rules.append("Não incluas backend.")
    if constraints.forbid_frontend or not allow_frontend:
        rules.append("Não incluas frontend.")

    return rules


def normalize_prompt_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return " ".join(normalized.split())


def contains_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)
