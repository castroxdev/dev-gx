from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5-coder:7b", alias="OLLAMA_MODEL")
    ollama_timeout: float = Field(default=120.0, alias="OLLAMA_TIMEOUT")
    ollama_status_timeout: float = Field(default=10.0, alias="OLLAMA_STATUS_TIMEOUT")
    ollama_chat_path: str = Field(default="/api/chat", alias="OLLAMA_CHAT_PATH")
    ollama_generate_path: str = Field(default="/api/generate", alias="OLLAMA_GENERATE_PATH")
    max_history_messages: int = Field(default=6, alias="MAX_HISTORY_MESSAGES")
    max_input_chars: int = Field(default=1800, alias="MAX_INPUT_CHARS")
    max_output_tokens: int = Field(default=700, alias="MAX_OUTPUT_TOKENS")

    mcp_server_enabled: bool = Field(default=True, alias="MCP_SERVER_ENABLED")
    mcp_server_base_url: str = Field(default="http://127.0.0.1:8765", alias="MCP_SERVER_BASE_URL")
    mcp_server_timeout: float = Field(default=15.0, alias="MCP_SERVER_TIMEOUT")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
