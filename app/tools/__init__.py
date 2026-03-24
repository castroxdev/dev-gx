import json

from app.tools.api_design import api_design_tool
from app.tools.base import PlannerTool
from app.tools.database import database_tool
from app.tools.entities import entities_tool
from app.tools.roadmap import roadmap_tool


AVAILABLE_TOOLS: tuple[PlannerTool, ...] = (
    database_tool,
    entities_tool,
    api_design_tool,
    roadmap_tool,
)


def build_tools_prompt() -> str:
    if not AVAILABLE_TOOLS:
        return ""

    sections: list[str] = ["Ferramentas internas:"]

    for tool in AVAILABLE_TOOLS:
        sections.append(f"- {tool.name}: {tool.purpose}")
        sections.append(tool.guidance.strip())

    return "\n".join(sections).strip()


def build_tools_prompt_from_mcp(tools: list[dict]) -> str:
    if not tools:
        return ""

    sections: list[str] = [
        "Ferramentas MCP disponíveis:",
        "Se responderes em português, usa português natural, com acentuação correta e formulações simples.",
        "Usa apenas tools cujos nomes apareçam exatamente na lista abaixo.",
        "Nunca inventes nomes de tools, aliases ou nomes mais descritivos do que os fornecidos pelo servidor MCP.",
        "Se não existir uma tool adequada na lista, não devolvas tool_call inventado; responde normalmente com as limitações.",
        "Usa uma tool MCP quando o pedido exigir dados reais, verificação, inspeção, listagem ou consulta que a tool possa fornecer.",
        "Seleciona a tool pela intenção principal do pedido, não por palavras genéricas como aplicação, sistema, gestão ou tarefas.",
        "Se o pedido for claramente para gerar um plano de MVP, roadmap, fases, objetivo do produto, público-alvo ou funcionalidades principais, a tua primeira resposta deve ser um tool_call para generate_mvp_plan quando ela estiver disponível.",
        "Se o pedido for para entidades, modelos, tabelas conceptuais, relações, campos principais ou modelação de domínio, a tua primeira resposta deve ser um tool_call para generate_entities quando ela estiver disponível.",
        "Só usa generate_sql_schema quando o pedido for explicitamente SQL, esquema SQL, CREATE TABLE, script SQL, base de dados relacional ou estrutura técnica de base de dados.",
        "Se o pedido for para endpoints, rotas, controllers, API, backend HTTP ou sugestões REST, a tua primeira resposta deve ser um tool_call para suggest_api_endpoints quando ela estiver disponível.",
        "Não acrescentes secções extra nem expandas para temas adjacentes se o utilizador não os pediu.",
        "Se o pedido disser curto, simples, resumido ou apenas, responde com esse nível de concisão.",
        "Se o utilizador pedir explicitamente para usar uma tool, a tua primeira resposta deve ser um tool_call válido sempre que exista uma tool adequada.",
        "Não respondas com conhecimento geral nem inventes resultados se uma tool MCP puder obter a informação pedida.",
        "Quando precisares de usar uma tool MCP, responde apenas com JSON puro neste formato:",
        '{"type":"tool_call","tool":"nome_da_tool","arguments":{"campo":"valor"}}',
        "Não uses markdown nem texto extra quando fizeres tool_call.",
        "Escolhe argumentos simples, válidos e alinhados com o input_schema da tool.",
        "Quando receberes TOOL_RESULT, usa o resultado para continuar ou faz novo tool_call se ainda faltar contexto.",
        "Se já tiveres TOOL_RESULT suficiente, responde de forma final sem repetir o JSON de tool_call.",
    ]

    for tool in tools:
        name = str(tool.get("name", "")).strip()
        description = str(tool.get("description", "")).strip() or "Sem descrição."
        input_schema = tool.get("inputSchema")
        if name:
            sections.append(f"- {name}: {description}")
            if name == "generate_mvp_plan":
                sections.append(
                    "  usa_para: pedidos de plano MVP, roadmap, fases, objetivo do produto, público-alvo e funcionalidades principais."
                )
            if name == "generate_entities":
                sections.append(
                    "  usa_para: pedidos de entidades, modelos, tabelas conceptuais, relações, campos principais e modelação de domínio sem SQL."
                )
            if name == "generate_sql_schema":
                sections.append(
                    "  usa_para: pedidos explicitamente SQL, esquema SQL, CREATE TABLE, chaves, índices e estrutura técnica de base de dados."
                )
            if name == "suggest_api_endpoints":
                sections.append(
                    "  usa_para: pedidos de endpoints API iniciais, rotas REST, contratos de request/response e estrutura base de backend."
                )
            if input_schema:
                sections.append(f"  input_schema: {json.dumps(input_schema, ensure_ascii=True)}")

    return "\n".join(sections).strip()



