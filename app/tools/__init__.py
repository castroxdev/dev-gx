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
