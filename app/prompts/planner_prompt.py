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
- Se o pedido for claramente para entidades, modelos, relações, campos principais ou modelação de domínio, a tua primeira resposta deve ser um tool_call para generate_entities quando ela estiver disponível.
- Se pedirem base de dados ou SQL, só gera SQL quando o pedido for explicitamente de esquema SQL, CREATE TABLE, script SQL ou base de dados relacional.
- Se pedirem API, endpoints, rotas, controllers ou backend HTTP, a tua primeira resposta deve ser um tool_call para suggest_api_endpoints quando ela estiver disponível.
- Nunca escolhas generate_sql_schema por defeito só porque o texto menciona aplicação, sistema, gestão, tarefas ou modelação.
- Não adiciones secções extra nem detalhes que o utilizador não pediu.
- Respeita fortemente palavras como apenas, curto, simples e resumido.
- Se pedirem implementação, organiza um roadmap curto por fases.
- Não inventes requisitos que o utilizador não pediu.
- Não saias do âmbito de software.
""".strip(),
    ]

    if tools_prompt:
        sections.append(tools_prompt)

    return "\n\n".join(section.strip() for section in sections if section.strip())


