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

The project uses a local Ollama model, making it useful for experimentation with local-first AI workflows.

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

### MVP Planning
![Dev GX MVP Planning](docs/dev-gx-mvp-planning.png)

### API Design
![Dev GX API Design](docs/dev-gx-api-design.png)

## Tech Stack

- Python
- FastAPI
- Ollama
- Jinja2
- HTML
- CSS
- JavaScript
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
```

## How It Works

The user submits a software idea or technical request in the chat interface.

Dev GX then uses a local Ollama model to generate structured technical output, such as:
- a simple MVP plan
- core entities
- suggested API endpoints
- a starting SQL schema

The generated response is displayed in the interface and conversations can be stored locally.

## Example Prompts

- Create a simple MVP plan for a barbershop application with appointments, clients, barbers and haircut history.
- Suggest a simple REST API for a barbershop application with clients, barbers, haircuts and appointments.
- Create a simple SQL database for a task management system with users, projects, tasks and comments.

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/castroxdev/dev-gx.git
cd dev-gx
```

### 2. Create and activate a virtual environment

**Windows**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Ollama

Make sure Ollama is installed and running locally, and that the configured model is available.

Example:
```bash
ollama run qwen2.5-coder:7b
```

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

Then open the local address shown in the terminal.

## Configuration

The project can be configured with environment variables for items such as:
- Ollama base URL
- model name
- request timeout
- input and output limits
- app environment and debug mode

A `.env.example` file is recommended for local setup.

## Current Status

Dev GX is still in development, but the core idea and main workflow are already functional.

The current focus is on:
- improving configuration and project setup
- refining prompt flows
- polishing the UI
- making outputs more consistent and structured

## Future Improvements

- better response formatting
- export options for generated artifacts
- more specialized prompt modes
- improved validation of generated SQL and API suggestions
- cleaner configuration with environment variables
- stronger documentation and setup flow

## Author

**Lucas de Castro Silva**  
GPSI student and Gen AI intern at WIT Software.

GitHub: [castroxdev](https://github.com/castroxdev)

## License

This project is currently shared for portfolio and learning purposes.
