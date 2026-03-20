import json

from tools.api_design import api_design_tool
from tools.base import PlannerTool
from tools.database import database_tool
from tools.entities import entities_tool
from tools.roadmap import roadmap_tool


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
        "Quando precisares de usar uma tool MCP, responde apenas com JSON puro neste formato:",
        '{"type":"tool_call","tool":"nome_da_tool","arguments":{"campo":"valor"}}',
        "Nao uses markdown nem texto extra quando fizeres tool_call.",
        "Quando receberes TOOL_RESULT, usa o resultado para continuar ou faz novo tool_call se ainda faltar contexto.",
    ]

    for tool in tools:
        name = str(tool.get("name", "")).strip()
        description = str(tool.get("description", "")).strip() or "Sem descricao."
        input_schema = tool.get("inputSchema")
        if name:
            sections.append(f"- {name}: {description}")
            if input_schema:
                sections.append(f"  input_schema: {json.dumps(input_schema, ensure_ascii=True)}")

    return "\n".join(sections).strip()
