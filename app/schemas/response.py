from pydantic import BaseModel, Field


class GeneratePlanResponse(BaseModel):
    plan: str = Field(..., description="Plano tecnico gerado pelo Ollama.")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Resposta gerada pelo assistente.")


class OllamaHealthResponse(BaseModel):
    status: str = Field(..., description="Estado atual do Ollama.")
    model: str = Field(..., description="Modelo configurado na aplicacao.")
    base_url: str = Field(..., description="URL base usada para comunicar com o Ollama.")
    detail: str = Field(..., description="Detalhe textual do estado.")
    model_available: bool = Field(..., description="Indica se o modelo configurado existe no Ollama.")
