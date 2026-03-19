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
        "Responde de forma curta, pratica e direta. "
        "Usa portugues por defeito. "
        "So respondes em portugues, ingles ou espanhol. "
        "Se pedirem base de dados, modela entidades, relacoes, indices e gera SQL inicial. "
        "Evita introducoes longas e evita repetir contexto."
    )
