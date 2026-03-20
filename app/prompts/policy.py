import json
import re


SCOPE_CLASSIFIER_PROMPT = """
Classifica o pedido do utilizador para um assistente de software.

Regras:
- O ambito valido inclui software, programacao, arquitetura, bases de dados, APIs, frontend, backend, DevOps e planeamento tecnico de produtos digitais.
- Saudacoes simples sao validas.
- Pedidos para mudar idioma entre portugues, ingles e espanhol sao validos.
- Deteta o idioma principal do pedido do utilizador entre portugues, ingles e espanhol. Se nao tiveres certeza, usa portugues.
- Tudo o resto deve ser recusado.

Responde apenas com JSON valido, sem markdown, sem explicacoes, com este formato exato:
{{"decision":"allow|refuse","category":"software|greeting|language|non_software","language":"pt|en|es","reason":"texto curto"}}

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
    language = str(parsed.get("language", "")).strip().lower()
    reason = str(parsed.get("reason", "")).strip()

    if decision not in {"allow", "refuse"}:
        return None
    if category not in {"software", "greeting", "language", "non_software"}:
        return None
    if language not in {"pt", "en", "es"}:
        return None

    return {
        "decision": decision,
        "category": category,
        "language": language,
        "reason": reason,
    }


def detect_response_language(user_input: str, classified_language: str = "pt") -> str:
    text = user_input.lower()

    english_markers = (
        " the ",
        " and ",
        " how ",
        " what ",
        " why ",
        " when ",
        " where ",
        "can you",
        "could you",
        "please",
        "help me",
        "tell me",
        "about ",
        "with ",
        "is it",
        "do you",
    )
    spanish_markers = (
        " el ",
        " la ",
        " los ",
        " las ",
        " como ",
        " que ",
        " por que ",
        "puedes",
        "podrias",
        "ayudame",
        "dime",
        "sobre ",
        " con ",
        "es ",
        "puedo",
    )

    english_score = sum(1 for marker in english_markers if marker in text)
    spanish_score = sum(1 for marker in spanish_markers if marker in text)

    if english_score > spanish_score and english_score > 0:
        return "en"
    if spanish_score > english_score and spanish_score > 0:
        return "es"
    if classified_language in {"pt", "en", "es"}:
        return classified_language
    return "pt"


def refusal_message(language: str = "pt") -> str:
    messages = {
        "pt": "Posso ajudar com software, programacao, bases de dados, APIs e arquitetura. Se quiseres, reformula o pedido nesse contexto.",
        "en": "I can help with software, programming, databases, APIs, and architecture. If you want, rephrase your request in that context.",
        "es": "Puedo ayudar con software, programacion, bases de datos, APIs y arquitectura. Si quieres, reformula tu pedido en ese contexto.",
    }
    return messages.get(language, messages["pt"])
