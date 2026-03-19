# Dev GX

Projeto em Python com FastAPI e uma interface simples de chat para conversar com um modelo local no Ollama.

## Estrutura

```text
app/
|-- api/
|   |-- __init__.py
|   `-- routes.py
|-- prompts/
|   |-- __init__.py
|   |-- planner_prompt.py
|   `-- planner_system_prompt.py
|-- schemas/
|   |-- __init__.py
|   |-- request.py
|   `-- response.py
|-- services/
|   |-- __init__.py
|   `-- ollama_service.py
|-- ui/
|   `-- index.html
|-- tools/
|   |-- api_design.py
|   |-- database.py
|   |-- entities.py
|   `-- roadmap.py
|-- config.py
|-- main.py
`-- requirements.txt
```

## Instalar dependencias

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Interface de chat

Garante primeiro que o Ollama esta ativo e que o modelo `qwen2.5-coder:7b` esta disponivel.

```bash
uvicorn main:app --reload
```

A interface web fica disponivel em [http://localhost:8000](http://localhost:8000).

## Correr o servidor

O servidor tambem continua a expor a API para gerar planos tecnicos e conversar com o modelo:

```bash
uvicorn main:app --reload
```

## Endpoints

`GET /`

Abre a interface web do chat.

`GET /health`

Healthcheck simples da aplicacao.

`POST /generate-plan`

Exemplo de payload:

```json
{
  "idea": "Plataforma para gerir tarefas de equipas remotas com relatorios semanais."
}
```

Exemplo de resposta:

```json
{
  "plan": "..."
}
```

`POST /chat`

Exemplo de payload:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Quero um MVP para gerir tarefas de equipas remotas."
    }
  ]
}
```

Exemplo de resposta:

```json
{
  "reply": "# 1. Resumo da solucao\n..."
}
```
