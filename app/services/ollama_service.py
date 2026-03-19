import httpx

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_PATH,
    OLLAMA_GENERATE_PATH,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
)
from prompts.planner_prompt import build_planner_prompt


class OllamaServiceError(Exception):
    pass


class OllamaService:
    def __init__(self) -> None:
        self.generate_url = f"{OLLAMA_BASE_URL}{OLLAMA_GENERATE_PATH}"
        self.chat_url = f"{OLLAMA_BASE_URL}{OLLAMA_CHAT_PATH}"
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT_SECONDS

    async def generate_plan(self, idea: str) -> str:
        prompt = build_planner_prompt(idea)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        data = await self._post_json(self.generate_url, payload)
        generated_text = data.get("response", "").strip()

        if not generated_text:
            raise OllamaServiceError("O Ollama nao devolveu conteudo para o plano.")

        return generated_text

    async def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        data = await self._post_json(self.chat_url, payload)
        message = data.get("message", {})
        content = message.get("content", "").strip()

        if not content:
            raise OllamaServiceError("O Ollama nao devolveu conteudo para a resposta.")

        return content

    async def _post_json(self, url: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.RequestError as exc:
            raise OllamaServiceError(
                "Nao foi possivel comunicar com o Ollama. Confirma se esta ativo em http://localhost:11434."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaServiceError(
                f"O Ollama devolveu erro HTTP {exc.response.status_code}."
            ) from exc

        return response.json()
