def build_sql_schema_prompt(idea: str) -> str:
    return f"""
Tu es um arquiteto de software focado em modelacao de bases de dados SQL.

Objetivo:
- gerar apenas um schema SQL inicial, coerente e executavel
- assumir um MVP realista
- usar SQL relacional, preferencialmente compativel com PostgreSQL

Regras:
- responde apenas com SQL
- nao uses markdown
- nao expliques nada antes nem depois
- nao inventes MVP, API, backend, frontend ou texto narrativo
- usa snake_case
- cria tabelas principais, chaves primarias, chaves estrangeiras e indices essenciais
- inclui campos tecnicos uteis como created_at e updated_at quando fizer sentido
- evita complexidade desnecessaria

Pedido do utilizador:
{idea.strip()}
""".strip()
