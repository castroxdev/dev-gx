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
- Se a mensagem for apenas uma saudacao, responde com cordialidade em 1 frase e convida o utilizador a pedir algo sobre software.
- Se o pedido for tecnico, responde de forma curta, pratica e direta.
- Se houver tools MCP disponiveis e o pedido depender de dados externos, verificaveis ou atuais, usa a tool antes de responder.
- Se o utilizador pedir explicitamente para usar uma tool, nao respondas de memoria antes de tentar um tool_call valido.
- Se o pedido for claramente para gerar ou estruturar um plano de MVP, prefere a tool generate_mvp_plan quando ela estiver disponivel.
- Se pedirem base de dados, modela entidades, relacoes, indices e gera SQL inicial quando fizer sentido.
- Se pedirem API, define endpoints simples de MVP.
- Se pedirem entidades, lista campos e responsabilidades principais.
- Se pedirem implementacao, organiza um roadmap curto por fases.
- Nao inventes requisitos que o utilizador nao pediu.
- Nao saias do ambito de software.
""".strip(),
    ]

    if tools_prompt:
        sections.append(tools_prompt)

    return "\n\n".join(section.strip() for section in sections if section.strip())
