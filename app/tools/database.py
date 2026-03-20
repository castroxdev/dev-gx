from app.tools.base import PlannerTool


database_tool = PlannerTool(
    name="database",
    purpose="Modelar dados e gerar um esquema SQL inicial de MVP.",
    guidance="""
Usa esta tool quando o pedido envolver dados, SQL, schema ou tabelas.

Regras:
- Assume SQL relacional por defeito.
- Prefere PostgreSQL para MVP geral e SQLite apenas para prototipos locais.
- Entrega tabelas, relacoes, chaves, indices essenciais e um bloco ```sql``` inicial.
- Usa snake_case e nomes simples.
- Faz suposicoes razoaveis se o pedido ja tiver contexto suficiente.
- Evita complexidade desnecessaria.
""".strip(),
)
