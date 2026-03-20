import json
import re

import httpx

from app.config import GENERATED_DIR, settings
from app.prompts.policy import build_scope_classifier_prompt, parse_scope_classifier_response
from app.prompts.planner_prompt import build_planner_prompt
from app.prompts.sql_prompt import build_sql_schema_prompt


class OllamaServiceError(Exception):
    pass


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.generate_url = f"{settings.ollama_base_url}{settings.ollama_generate_path}"
        self.chat_url = f"{settings.ollama_base_url}{settings.ollama_chat_path}"
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.status_timeout = settings.ollama_status_timeout
        self.max_history_messages = settings.max_history_messages
        self.max_message_chars = settings.max_input_chars
        self.num_predict = settings.max_output_tokens

    async def get_status(self) -> dict[str, str | bool]:
        tags_url = f"{self.base_url}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=self.status_timeout) as client:
                response = await client.get(tags_url)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError:
            return {
                "status": "offline",
                "model": self.model,
                "base_url": self.base_url,
                "detail": f"Nao foi possivel contactar o Ollama em {self.base_url}.",
                "model_available": False,
            }
        except httpx.HTTPStatusError as exc:
            return {
                "status": "offline",
                "model": self.model,
                "base_url": self.base_url,
                "detail": f"O endpoint de health do Ollama devolveu HTTP {exc.response.status_code}.",
                "model_available": False,
            }
        except ValueError:
            return {
                "status": "offline",
                "model": self.model,
                "base_url": self.base_url,
                "detail": "O Ollama respondeu, mas nao devolveu JSON valido no endpoint /api/tags.",
                "model_available": False,
            }

        models = data.get("models", [])
        available_names = {
            model.get("name", "")
            for model in models
            if isinstance(model, dict)
        }
        model_available = self.model in available_names

        if not model_available:
            available_text = ", ".join(sorted(name for name in available_names if name)) or "nenhum modelo"
            return {
                "status": "degraded",
                "model": self.model,
                "base_url": self.base_url,
                "detail": f"O Ollama esta online, mas o modelo configurado nao foi encontrado. Modelos disponiveis: {available_text}.",
                "model_available": False,
            }

        return {
            "status": "online",
            "model": self.model,
            "base_url": self.base_url,
            "detail": "O Ollama esta acessivel e o modelo configurado esta disponivel.",
            "model_available": True,
        }

    async def generate_plan(self, idea: str, tools_prompt: str = "") -> str:
        prompt = build_planner_prompt(idea, tools_prompt)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self.num_predict,
            },
        }

        data = await self._post_json(self.generate_url, payload)
        generated_text = data.get("response", "").strip()

        if not generated_text:
            raise OllamaServiceError("O Ollama nao devolveu conteudo para o plano.")

        return generated_text

    async def generate_sql_schema(self, idea: str) -> str:
        prompt = build_sql_schema_prompt(idea)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self.num_predict,
            },
        }

        data = await self._post_json(self.generate_url, payload)
        generated_text = data.get("response", "").strip()

        if not generated_text:
            raise OllamaServiceError("O Ollama nao devolveu conteudo para o schema SQL.")

        return self._extract_sql(generated_text)

    async def classify_request_scope(self, user_input: str) -> dict[str, str]:
        prompt = build_scope_classifier_prompt(user_input)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 120,
            },
        }

        data = await self._post_json(self.generate_url, payload)
        generated_text = data.get("response", "").strip()
        parsed = parse_scope_classifier_response(generated_text)

        if parsed is None:
            # Fail open to avoid blocking valid software requests if classification is malformed.
            return {
                "decision": "allow",
                "category": "software",
                "language": "pt",
                "reason": "classifier_fallback",
            }

        return parsed

    async def chat(self, messages: list[dict[str, str]]) -> str:
        trimmed_messages = self._trim_messages(messages)
        payload = {
            "model": self.model,
            "messages": trimmed_messages,
            "stream": False,
            "options": {
                "num_predict": self.num_predict,
            },
        }

        data = await self._post_json(self.chat_url, payload)
        message = data.get("message", {})
        content = message.get("content", "").strip()

        if not content:
            raise OllamaServiceError("O Ollama nao devolveu conteudo para a resposta.")

        return content

    async def chat_stream(self, messages: list[dict[str, str]]):
        trimmed_messages = self._trim_messages(messages)
        payload = {
            "model": self.model,
            "messages": trimmed_messages,
            "stream": True,
            "options": {
                "num_predict": self.num_predict,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", self.chat_url, json=payload) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise OllamaServiceError(
                                "O Ollama respondeu com um fragmento invalido durante o streaming."
                            ) from exc

                        message = data.get("message", {})
                        content = str(message.get("content", ""))
                        if content:
                            yield content
        except httpx.RequestError as exc:
            status = await self.get_status()
            raise OllamaServiceError(str(status["detail"])) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 404:
                raise OllamaServiceError(
                    f"O endpoint do Ollama nao foi encontrado em {self.chat_url}."
                ) from exc
            if status_code == 400:
                raise OllamaServiceError(
                    f"O Ollama rejeitou o pedido. Confirma se o modelo '{self.model}' existe e se o payload enviado e valido."
                ) from exc
            raise OllamaServiceError(
                f"O Ollama devolveu erro HTTP {status_code}."
            ) from exc

    def save_sql_schema(self, sql: str, file_name: str | None = None) -> tuple[str, str]:
        target_dir = GENERATED_DIR / "sql"
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._sanitize_file_name(file_name)
        file_path = target_dir / f"{safe_name}.sql"
        file_path.write_text(sql.strip() + "\n", encoding="utf-8")
        return str(file_path), file_path.name

    def _trim_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        if not messages:
            return []

        system_messages = [message for message in messages if message.get("role") == "system"][:1]
        non_system_messages = [message for message in messages if message.get("role") != "system"]
        recent_messages = non_system_messages[-self.max_history_messages :]

        normalized_recent_messages = []
        for message in recent_messages:
            content = str(message.get("content", "")).strip()
            if len(content) > self.max_message_chars:
                content = f"{content[: self.max_message_chars].rstrip()}..."

            normalized_recent_messages.append(
                {
                    "role": message.get("role", "user"),
                    "content": content,
                }
            )

        return system_messages + normalized_recent_messages

    def _sanitize_file_name(self, raw_name: str | None) -> str:
        if not raw_name:
            return "schema"

        normalized = raw_name.strip().lower()
        normalized = re.sub(r"\.sql$", "", normalized)
        normalized = re.sub(r"[^a-z0-9_-]+", "_", normalized)
        normalized = normalized.strip("_-")
        return normalized or "schema"

    def _extract_sql(self, text: str) -> str:
        fenced_match = re.search(r"```sql\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
        if fenced_match:
            return fenced_match.group(1).strip()
        return text.strip()

    async def _post_json(self, url: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            status = await self.get_status()
            raise OllamaServiceError(str(status["detail"])) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 404:
                raise OllamaServiceError(
                    f"O endpoint do Ollama nao foi encontrado em {url}."
                ) from exc
            if status_code == 400:
                raise OllamaServiceError(
                    f"O Ollama rejeitou o pedido. Confirma se o modelo '{self.model}' existe e se o payload enviado e valido."
                ) from exc
            raise OllamaServiceError(
                f"O Ollama devolveu erro HTTP {status_code}."
            ) from exc
        except ValueError as exc:
            raise OllamaServiceError(
                "O Ollama respondeu, mas nao devolveu JSON valido."
            ) from exc

    def build_chat_system_message(self, tools_prompt: str = "") -> str:
        from app.prompts.planner_prompt import build_chat_system_prompt

        return build_chat_system_prompt(tools_prompt)

    def build_plan_system_message(self, tools_prompt: str = "") -> str:
        from app.prompts.planner_prompt import build_plan_system_prompt

        return build_plan_system_prompt(tools_prompt)
