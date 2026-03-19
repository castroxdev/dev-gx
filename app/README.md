# Dev GX

Planner tecnico com FastAPI, interface web mais completa e integracao local com Ollama.

O projeto usa uma arquitetura simples por camadas:
- `web/` para a interface
- `api/` para os endpoints JSON
- `services/` para integracao com o Ollama
- `prompts/` e `tools/` para orientar o comportamento do planner

## Funcionalidades

- Chat tecnico via browser
- Planeamento de MVP
- Tool interna `database` para modelacao e esquema SQL inicial
- Healthcheck da aplicacao e do Ollama
- Interface web com prompts rapidos e estado do modelo

## Estrutura

```text
app/
|-- api/
|   `-- routes.py
|-- prompts/
|   |-- planner_prompt.py
|   `-- planner_system_prompt.py
|-- schemas/
|   |-- request.py
|   `-- response.py
|-- services/
|   `-- ollama_service.py
|-- static/
|   |-- app.css
|   `-- app.js
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
|-- config.py
|-- main.py
`-- requirements.txt
```

## Como correr

Garante primeiro que:
- o Ollama esta ativo
- o modelo `qwen2.5-coder:7b` existe localmente

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
- `POST /api/chat`
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

### Exemplo de `POST /api/generate-plan`

```json
{
  "idea": "Plataforma para gerir tarefas de equipas remotas com relatorios semanais."
}
```
