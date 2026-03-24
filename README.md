# Dev GX

Dev GX is a local AI software planning assistant built with FastAPI and Ollama. It helps transform product ideas into practical technical outputs such as MVP planning, entity modeling, API endpoint suggestions, and starter SQL schemas.

![Dev GX Home](docs/dev-gx-home.png)

## Overview

Dev GX was designed to support early software planning workflows with a local-first approach. Instead of acting as a generic chatbot, it focuses on turning product ideas into structured technical outputs that are useful during project definition and prototyping.

The application provides a web interface where the user can describe a product idea and receive targeted outputs such as:

- MVP planning
- Entity modeling
- API endpoint suggestions
- Initial SQL schemas

It also includes conversation persistence with SQLite and optional MCP server integration for external tools.

## Main Features

- Local AI-powered software planning assistant
- Web interface built for practical planning workflows
- MVP planning generation
- Entity and domain modeling support
- REST API endpoint suggestions
- Starter SQL schema generation
- SQL export support
- Conversation history persisted with SQLite
- Optional MCP server integration

## Stack

- Python
- FastAPI
- Uvicorn
- Ollama
- Pydantic
- HTML, CSS, and JavaScript
- SQLite

## Screenshots

### Home

![Dev GX Home](docs/dev-gx-home.png)

### Chat Experience

![Dev GX Chat](docs/dev-gx-chat.png)

### Request Processing

![Dev GX Loading](docs/dev-gx-loading.png)

### Entity Modeling

![Dev GX Entity Model](docs/dev-gx-entity-model.png)

### SQL Schema Generation

![Dev GX SQL Schema](docs/dev-gx-sql-schema.png)

### API Endpoint Suggestions

![Dev GX API Suggestions](docs/dev-gx-api-suggestions.png)

## Official Project Structure

```text
dev-gx/
|-- app/
|   |-- api/
|   |-- prompts/
|   |-- schemas/
|   |-- services/
|   |-- static/
|   |-- templates/
|   |-- tools/
|   |-- web/
|   |-- __init__.py
|   |-- config.py
|   `-- main.py
|-- docs/
|-- .env.example
|-- .gitignore
|-- LICENSE
|-- README.md
`-- requirements.txt
