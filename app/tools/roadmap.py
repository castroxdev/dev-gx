from app.tools.base import PlannerTool


roadmap_tool = PlannerTool(
    name="roadmap",
    purpose="Organizar a implementacao em fases, prioridades e entregas realistas de MVP.",
    guidance="""
Usa esta tool quando o pedido envolver passos de implementacao, backlog, prioridades ou fases.

Regras:
- Divide o trabalho em etapas pequenas e executaveis.
- Prioriza fundacao tecnica, funcionalidades criticas e depois refinamentos.
- Separa o que e MVP do que pode ficar para fase 2.
- Mantem a sequencia realista para uma equipa pequena ou um developer solo.
- Fecha com proximos passos concretos.
""".strip(),
)
