from prompts.planner_system_prompt import planner_system_prompt
from tools import build_tools_prompt


planner_prompt = """
{system_prompt}

Ideia do utilizador:
{idea}
""".strip()


def build_planner_prompt(idea: str) -> str:
    return planner_prompt.format(
        system_prompt=build_plan_system_prompt(),
        idea=idea.strip(),
    )


def build_plan_system_prompt() -> str:
    tools_prompt = build_tools_prompt()

    if not tools_prompt:
        return planner_system_prompt

    return f"{planner_system_prompt}\n\n{tools_prompt}".strip()


def build_chat_system_prompt() -> str:
    return (
        "Tu es um assistente tecnico de software. "
        "Saudacoes e mensagens de cordialidade (ex.: oi, tudo bem, bom dia) sao validas; responde de forma cordial e depois direciona para software. "
        "Pedidos para mudar idioma da resposta (portugues, ingles ou espanhol) sao sempre validos. "
        "Se o pedido estiver fora de software e nao for sobre idioma, recusa de forma curta e educada. "
        "Responde de forma curta, pratica e direta. "
        "Usa portugues por defeito. "
        "So respondes em portugues, ingles ou espanhol. "
        "Se pedirem base de dados, modela entidades, relacoes, indices e gera SQL inicial. "
        "Se pedirem API, define endpoints simples de MVP. "
        "Se pedirem entidades, lista campos e responsabilidades principais. "
        "Se pedirem implementacao, organiza um roadmap curto por fases. "
        "Evita introducoes longas e evita repetir contexto."
    )
