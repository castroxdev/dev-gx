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
        "Ferramentas MCP disponiveis:",
        "Usa apenas tools cujos nomes aparecam exatamente na lista abaixo.",
        "Nunca inventes nomes de tools, aliases ou nomes mais descritivos do que os fornecidos pelo servidor MCP.",
        "Se nao existir uma tool adequada na lista, nao devolvas tool_call inventado; responde normalmente com as limitacoes.",
        "Usa uma tool MCP quando o pedido exigir dados reais, verificacao, inspecao, listagem ou consulta que a tool possa fornecer.",
        "Se o pedido for claramente para gerar um plano de MVP de um produto, a tua primeira resposta deve ser um tool_call para generate_mvp_plan quando ela estiver disponivel.",
        "Se o utilizador pedir explicitamente para usar uma tool, a tua primeira resposta deve ser um tool_call valido sempre que exista uma tool adequada.",
        "Nao respondas com conhecimento geral nem inventes resultados se uma tool MCP puder obter a informacao pedida.",
        "Quando precisares de usar uma tool MCP, responde apenas com JSON puro neste formato:",
        '{"type":"tool_call","tool":"nome_da_tool","arguments":{"campo":"valor"}}',
        "Nao uses markdown nem texto extra quando fizeres tool_call.",
        "Escolhe argumentos simples, validos e alinhados com o input_schema da tool.",
        "Quando receberes TOOL_RESULT, usa o resultado para continuar ou faz novo tool_call se ainda faltar contexto.",
        "Se ja tiveres TOOL_RESULT suficiente, responde de forma final sem repetir o JSON de tool_call.",
    ]

    for tool in tools:
        name = str(tool.get("name", "")).strip()
        description = str(tool.get("description", "")).strip() or "Sem descricao."
        input_schema = tool.get("inputSchema")
        if name:
            sections.append(f"- {name}: {description}")
            if name == "generate_mvp_plan":
                sections.append(
                    "  usa_para: pedidos de plano MVP, fases de implementacao, escopo inicial, entidades, base de dados e API de um produto."
                )
            if name == "generate_sql_schema":
                sections.append(
                    "  usa_para: pedidos de schema SQL inicial, tabelas, relacoes, chaves, indices e estrutura de base de dados do MVP."
                )
            if name == "suggest_api_endpoints":
                sections.append(
                    "  usa_para: pedidos de endpoints API iniciais, rotas REST, contratos de request/response e estrutura base de backend."
                )
            if input_schema:
                sections.append(f"  input_schema: {json.dumps(input_schema, ensure_ascii=True)}")

    return "\n".join(sections).strip()
