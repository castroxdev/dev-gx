from pydantic import BaseModel, Field


class GeneratePlanResponse(BaseModel):
    plan: str = Field(..., description="Plano tecnico gerado pelo Ollama.")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Resposta gerada pelo assistente.")


class ChatMessageResponse(BaseModel):
    role: str = Field(..., description="Autor da mensagem na conversa.")
    content: str = Field(..., description="Conteudo textual da mensagem.")
    created_at: str | None = Field(default=None, description="Data de criacao da mensagem.")


class ConversationSummaryResponse(BaseModel):
    id: str = Field(..., description="Identificador unico da conversa.")
    title: str = Field(..., description="Titulo resumido da conversa.")
    created_at: str = Field(..., description="Data de criacao da conversa.")
    updated_at: str = Field(..., description="Data da ultima atualizacao da conversa.")
    last_message_preview: str = Field(default="", description="Trecho curto da ultima mensagem.")


class ConversationResponse(BaseModel):
    id: str = Field(..., description="Identificador unico da conversa.")
    title: str = Field(..., description="Titulo resumido da conversa.")
    created_at: str = Field(..., description="Data de criacao da conversa.")
    updated_at: str = Field(..., description="Data da ultima atualizacao da conversa.")
    messages: list[ChatMessageResponse] = Field(default_factory=list, description="Mensagens da conversa.")


class OllamaHealthResponse(BaseModel):
    status: str = Field(..., description="Estado atual do Ollama.")
    model: str = Field(..., description="Modelo configurado na aplicacao.")
    base_url: str = Field(..., description="URL base usada para comunicar com o Ollama.")
    detail: str = Field(..., description="Detalhe textual do estado.")
    model_available: bool = Field(..., description="Indica se o modelo configurado existe no Ollama.")


class McpHealthResponse(BaseModel):
    status: str = Field(..., description="Estado atual do servidor MCP.")
    base_url: str = Field(..., description="URL base usada para comunicar com o servidor MCP.")
    detail: str = Field(..., description="Detalhe textual do estado.")
    tools_available: int = Field(..., description="Numero de tools descobertas no servidor MCP.")


class GenerateSqlSchemaResponse(BaseModel):
    file_path: str = Field(..., description="Caminho absoluto do ficheiro SQL gerado.")
    file_name: str = Field(..., description="Nome do ficheiro SQL gerado.")
    sql: str = Field(..., description="Conteudo SQL salvo no ficheiro.")
