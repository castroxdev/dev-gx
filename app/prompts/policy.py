import json
import re


SCOPE_CLASSIFIER_PROMPT = """
Classifica o pedido do utilizador para um assistente de software.

Regras:
- O ambito valido inclui software, programacao, arquitetura, bases de dados, APIs, frontend, backend, DevOps e planeamento tecnico de produtos digitais.
- Saudacoes simples sao validas.
- Pedidos para mudar idioma entre portugues, ingles e espanhol sao validos.
- Tudo o resto deve ser recusado.

Responde apenas com JSON valido, sem markdown, sem explicacoes, com este formato exato:
{{"decision":"allow|refuse","category":"software|greeting|language|non_software","reason":"texto curto"}}

Pedido do utilizador:
{user_input}
""".strip()


def build_scope_classifier_prompt(user_input: str) -> str:
    escaped_input = user_input.strip()
    return SCOPE_CLASSIFIER_PROMPT.format(user_input=escaped_input)


def parse_scope_classifier_response(raw_text: str) -> dict[str, str] | None:
    text = raw_text.strip()
    if not text:
        return None

    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    decision = str(parsed.get("decision", "")).strip().lower()
    category = str(parsed.get("category", "")).strip().lower()
    reason = str(parsed.get("reason", "")).strip()

    if decision not in {"allow", "refuse"}:
        return None
    if category not in {"software", "greeting", "language", "non_software"}:
        return None

    return {
        "decision": decision,
        "category": category,
        "reason": reason,
    }


def refusal_message() -> str:
    return "Posso ajudar com software, programacao, bases de dados, APIs e arquitetura. Se quiseres, reformula o pedido nesse contexto."
