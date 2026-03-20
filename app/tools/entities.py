from app.tools.base import PlannerTool


entities_tool = PlannerTool(
    name="entities",
    purpose="Definir entidades de dominio, campos, responsabilidades e relacoes principais.",
    guidance="""
Usa esta tool quando o pedido envolver modelacao de dominio, objetos principais ou estrutura de dados.

Regras:
- Identifica primeiro as entidades centrais do negocio.
- Para cada entidade, sugere responsabilidade, campos essenciais e relacoes.
- Evita entidades desnecessarias no MVP.
- Distingue entidades de negocio de tabelas tecnicas.
- Se fizer sentido, aponta enums ou estados importantes.
""".strip(),
)
