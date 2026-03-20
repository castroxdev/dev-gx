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
        self.session_id: str | None = None

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

        return [tool for tool in normalized_tools if tool["name"]]

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
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as exc:
            raise McpServiceError(
                f"Nao foi possivel comunicar com o servidor MCP em {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise McpServiceError(
                f"O servidor MCP devolveu HTTP {exc.response.status_code}."
            ) from exc
        except ValueError as exc:
            raise McpServiceError("O servidor MCP respondeu com JSON invalido.") from exc

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
