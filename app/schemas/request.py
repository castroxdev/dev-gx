from typing import Literal

from pydantic import BaseModel, Field


class GeneratePlanRequest(BaseModel):
    idea: str = Field(..., min_length=5, description="Descricao do projeto a planear.")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(
        ...,
        description="Autor da mensagem na conversa.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Conteudo textual da mensagem.",
    )


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        description="Historico atual da conversa.",
    )


class GenerateSqlSchemaRequest(BaseModel):
    idea: str = Field(
        ...,
        min_length=5,
        description="Descricao do sistema para gerar o schema SQL.",
    )
    file_name: str | None = Field(
        default=None,
        description="Nome opcional do ficheiro SQL a gerar.",
    )
