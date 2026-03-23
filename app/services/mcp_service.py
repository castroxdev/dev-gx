import asyncio
import json
import uuid
from typing import Any

import httpx

from app.config import settings


class McpServiceError(Exception):
    pass


class McpService:
    def __init__(self) -> None:
        self.enabled = settings.mcp_server_enabled
        self.base_url = settings.mcp_server_base_url.rstrip("/")
        self.timeout = settings.mcp_server_timeout
        self.tools_cache_ttl = settings.mcp_tools_cache_ttl
        self.session_id: str | None = None
        self._tools_cache: list[dict[str, Any]] | None = None
        self._tools_cache_expires_at: float = 0.0

    async def get_status(self) -> dict[str, str | bool | int]:
        if not self.enabled:
            return {
                "status": "disabled",
                "base_url": self.base_url,
                "detail": "A integracao MCP esta desativada na configuracao.",
                "tools_available": 0,
            }

        try:
            tools = await self.list_tools()
        except McpServiceError as exc:
            return {
                "status": "offline",
                "base_url": self.base_url,
                "detail": str(exc),
                "tools_available": 0,
            }

        return {
            "status": "online",
            "base_url": self.base_url,
            "detail": "Servidor MCP acessivel e lista de tools carregada.",
            "tools_available": len(tools),
        }

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        now = asyncio.get_running_loop().time()
        if self._tools_cache is not None and now < self._tools_cache_expires_at:
            return self._tools_cache

        await self._initialize()
        result = await self._rpc_call("tools/list", {})
        tools = result.get("tools", [])

        if not isinstance(tools, list):
            raise McpServiceError("O servidor MCP devolveu uma lista de tools invalida.")

        normalized_tools: list[dict[str, Any]] = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue

            normalized_tools.append(
                {
                    "name": str(tool.get("name", "")).strip(),
                    "description": str(tool.get("description", "")).strip() or "Sem descricao.",
                    "inputSchema": tool.get("inputSchema"),
                }
            )

        filtered_tools = [tool for tool in normalized_tools if tool["name"]]
        self._tools_cache = filtered_tools
        self._tools_cache_expires_at = now + max(self.tools_cache_ttl, 0.0)
        return filtered_tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not self.enabled:
            raise McpServiceError("A integracao MCP esta desativada na configuracao.")

        await self._initialize()
        result = await self._rpc_call(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )

        if "content" in result:
            return result["content"]
        if "structuredContent" in result:
            return result["structuredContent"]
        return result

    async def _initialize(self) -> None:
        if self.session_id is not None:
            return

        result = await self._rpc_call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "dev-gx",
                    "version": "0.3.0",
                },
                "capabilities": {},
            },
        )

        if self.session_id is not None:
            return

        session_id = result.get("sessionId")
        if isinstance(session_id, str) and session_id.strip():
            self.session_id = session_id.strip()

    async def _rpc_call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                response_session_id = response.headers.get("mcp-session-id")
                if isinstance(response_session_id, str) and response_session_id.strip():
                    self.session_id = response_session_id.strip()
                data = self._parse_response_data(response)
        except httpx.RequestError as exc:
            raise McpServiceError(
                f"Nao foi possivel comunicar com o servidor MCP em {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            content_type = exc.response.headers.get("Content-Type", "desconhecido")
            raw_preview = exc.response.text.strip().replace("\n", "\\n")[:240] or "<vazio>"
            raise McpServiceError(
                f"O servidor MCP devolveu HTTP {exc.response.status_code}. "
                f"method={method}. content_type={content_type}. body_preview={raw_preview}"
            ) from exc
        except ValueError as exc:
            content_type = response.headers.get("Content-Type", "desconhecido")
            raw_preview = response.text.strip().replace("\n", "\\n")[:240] or "<vazio>"
            raise McpServiceError(
                "O servidor MCP respondeu com formato invalido. "
                f"content_type={content_type}. body_preview={raw_preview}"
            ) from exc

        if not isinstance(data, dict):
            raise McpServiceError("O servidor MCP devolveu uma resposta invalida.")

        error = data.get("error")
        if isinstance(error, dict):
            message = str(error.get("message", "")).strip() or "Erro desconhecido no servidor MCP."
            raise McpServiceError(message)

        result = data.get("result")
        if not isinstance(result, dict):
            raise McpServiceError("O servidor MCP devolveu um resultado invalido.")

        return result

    def _parse_response_data(self, response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("Content-Type", "").lower()

        if "text/event-stream" in content_type:
            return self._parse_sse_response(response.text)

        return response.json()

    def _parse_sse_response(self, raw_text: str) -> dict[str, Any]:
        data_lines: list[str] = []

        for line in raw_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("data:"):
                data_lines.append(stripped[5:].strip())

        if not data_lines:
            raise ValueError("Resposta SSE sem bloco data.")

        payload = "\n".join(data_lines).strip()
        if not payload:
            raise ValueError("Resposta SSE com data vazia.")

        return json.loads(payload)
