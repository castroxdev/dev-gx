# Dev GX

Planner tecnico com FastAPI, interface web mais completa, integracao local com Ollama e descoberta de tools via MCP.

O projeto usa uma arquitetura simples por camadas:
- `web/` para a interface
- `api/` para os endpoints JSON
- `services/` para integracao com o Ollama
- `prompts/` para orientar o comportamento do planner
- `services/mcp_service.py` para descobrir tools num servidor MCP real

## Funcionalidades

- Chat tecnico via browser
- Planeamento de MVP
- Descoberta de tools via servidor MCP
- Geracao e gravacao automatica de schema SQL em ficheiro `.sql`
- Healthcheck da aplicacao e do Ollama
- Healthcheck do servidor MCP
- Interface web com prompts rapidos e estado do modelo

## Estrutura

```text
app/
|-- api/
|   `-- routes.py
|-- prompts/
|   |-- planner_prompt.py
|   |-- planner_system_prompt.py
|   `-- sql_prompt.py
|-- schemas/
|   |-- request.py
|   `-- response.py
|-- services/
|   |-- mcp_service.py
|   `-- ollama_service.py
|-- static/
|   |-- app.css
|   |-- app.js
|   `-- icone.png
|-- templates/
|   `-- index.html
|-- tools/
|   |-- base.py
|   |-- database.py
|   |-- entities.py
|   |-- api_design.py
|   `-- roadmap.py
|-- web/
|   `-- routes.py
|-- generated/
|   `-- sql/
|-- config.py
|-- main.py
`-- requirements.txt
```

## Como correr

Garante primeiro que:
- o Ollama esta ativo
- o modelo `qwen2.5-coder:7b` existe localmente
- o servidor MCP esta ativo em `http://127.0.0.1:8765` ou ajusta `MCP_SERVER_BASE_URL` em `config.py`

Depois:

```bash
uvicorn main:app --reload
```

Interface web:
- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Endpoints

- `GET /`
- `GET /health`
- `GET /api/health/ollama`
- `GET /api/health/mcp`
- `POST /api/chat`
- `POST /api/chat/stream`
- `POST /api/sql-schema`
- `POST /api/generate-plan`

### Exemplo de `POST /api/chat`

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Cria a base de dados SQL para um sistema de tarefas com utilizadores, projetos e tarefas."
    }
  ]
}
```

### Exemplo de `POST /api/sql-schema`

```json
{
  "idea": "Cria a base de dados para um sistema de tarefas com utilizadores, projetos, tarefas e comentarios.",
  "file_name": "task_system_schema"
}
```

O ficheiro sera salvo em `generated/sql/`.

### Exemplo de `POST /api/generate-plan`

```json
{
  "idea": "Plataforma para gerir tarefas de equipas remotas com relatorios semanais."
}
```
