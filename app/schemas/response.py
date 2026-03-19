from pydantic import BaseModel, Field


class GeneratePlanResponse(BaseModel):
    plan: str = Field(..., description="Plano tecnico gerado pelo Ollama.")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Resposta gerada pelo assistente.")
