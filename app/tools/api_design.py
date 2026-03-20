from app.tools.base import PlannerTool


api_design_tool = PlannerTool(
    name="api_design",
    purpose="Desenhar endpoints, contratos de request/response e organizacao de API para MVP.",
    guidance="""
Usa esta tool quando o pedido envolver rotas, endpoints, CRUD, autenticacao ou integracao frontend-backend.

Regras:
- Prefere REST simples por defeito.
- Sugere apenas endpoints necessarios para o MVP.
- Indica metodo HTTP, rota e objetivo de cada endpoint.
- Resume payloads de request e response sem detalhar demais se nao for pedido.
- Considera autenticacao, autorizacao e validacoes basicas quando fizer sentido.
- Mantem nomes de recursos consistentes e previsiveis.
""".strip(),
)
