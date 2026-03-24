from app.prompts.planner_system_prompt import BASE_SYSTEM_RULES, planner_system_prompt


planner_prompt = """
{system_prompt}

Ideia do utilizador:
{idea}
""".strip()


def build_planner_prompt(idea: str, tools_prompt: str = "") -> str:
    return planner_prompt.format(
        system_prompt=build_plan_system_prompt(tools_prompt),
        idea=idea.strip(),
    )


def build_plan_system_prompt(tools_prompt: str = "") -> str:
    if not tools_prompt:
        return planner_system_prompt

    return f"{planner_system_prompt}\n\n{tools_prompt}".strip()


def build_chat_system_prompt(tools_prompt: str = "") -> str:
    sections = [
        BASE_SYSTEM_RULES,
        """
Modo de resposta para chat:
- Se a mensagem for apenas uma saudação, responde com cordialidade em 1 frase e convida o utilizador a pedir algo sobre software.
- Se o pedido for técnico, responde de forma curta, prática e direta.
- Se responderes em português, usa português natural, com acentuação correta e frases simples.
- Se houver tools MCP disponíveis e o pedido depender de dados externos, verificáveis ou atuais, usa a tool antes de responder.
- Se o utilizador pedir explicitamente para usar uma tool, não respondas de memória antes de tentar um tool_call válido.
- Se o pedido for claramente para gerar ou estruturar um plano de MVP, a tua primeira resposta deve ser um tool_call para generate_mvp_plan quando ela estiver disponível.
- Se pedirem base de dados, modela entidades, relações, índices e gera SQL inicial quando fizer sentido.
- Se pedirem API, define endpoints simples de MVP.
- Se pedirem entidades, lista campos e responsabilidades principais.
- Se pedirem implementação, organiza um roadmap curto por fases.
- Não inventes requisitos que o utilizador não pediu.
- Não saias do âmbito de software.
""".strip(),
    ]

    if tools_prompt:
        sections.append(tools_prompt)

    return "\n\n".join(section.strip() for section in sections if section.strip())


