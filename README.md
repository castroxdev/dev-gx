# Dev GX

AI software planning assistant built with Python, FastAPI and Ollama. Dev GX helps turn project ideas into technical outputs such as MVP scope, entities, API structure and initial SQL schema.

![Dev GX Home](docs/dev-gx-home.png)

## Overview

Dev GX is a local AI assistant for software planning. It was built to help transform simple product ideas into more structured technical artifacts that can be used as a starting point for development.

With a prompt-based interface, the application can help with:
- MVP planning
- entity modeling
- API and backend suggestions
- initial SQL schema generation

The project uses a local Ollama model, making it useful for experimentation with private, local-first AI workflows.

## Features

- Local AI-powered software planning
- MVP scope suggestions from project ideas
- Entity modeling for applications and systems
- REST API endpoint suggestions
- Initial SQL schema generation
- Chat history persistence with SQLite
- Simple dark UI for technical prompting

## Screenshots

### Home
![Dev GX Home](docs/dev-gx-home.png)

### MVP planning
![Dev GX MVP Planning](docs/dev-gx-mvp-planning.png)

### API design
![Dev GX API Design](docs/dev-gx-api-design.png)

## Tech Stack

- Python
- FastAPI
- Ollama
- Jinja2
- HTML / CSS / JavaScript
- SQLite

## Project Structure

```text
app/
├── api/
├── schemas/
├── services/
├── static/
├── templates/
├── tools/
└── main.py
