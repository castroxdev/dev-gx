# Dev GX

Projeto em Python com FastAPI e uma interface simples de chat para conversar com um modelo local no Ollama.

## Estrutura

```text
app/
|-- api/
|   |-- __init__.py
|   `-- routes.py
|-- chat_ui.py
|-- prompts/
|   |-- __init__.py
|   `-- planner_prompt.py
|-- schemas/
|   |-- __init__.py
|   |-- request.py
|   `-- response.py
|-- services/
|   |-- __init__.py
|   `-- ollama_service.py
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
python chat_ui.py
```

A interface abre uma janela simples com historico da conversa, campo de texto, botao de envio e opcao para iniciar uma nova conversa.

## Correr o servidor

Se quiseres manter a API existente para gerar planos tecnicos:

```bash
uvicorn main:app --reload
```

## Endpoint principal

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
