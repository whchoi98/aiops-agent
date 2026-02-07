"""Multi-MCP Client 관리자 — 설정 기반 MCP 서버 연결

configs/mcp_servers.yaml 에 정의된 MCP 서버들을 읽어
ExitStack 으로 일괄 연결하고 도구를 수집합니다.
"""
from __future__ import annotations

import os
import re
from contextlib import ExitStack
from typing import Any

import yaml
from strands.tools.mcp import MCPClient

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "configs", "mcp_servers.yaml"
)

_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


# ---------------------------------------------------------------------------
# 설정 로드
# ---------------------------------------------------------------------------

def load_mcp_config(config_path: str | None = None) -> dict[str, Any]:
    """MCP 서버 설정 파일을 로드합니다.

    Args:
        config_path: 설정 파일 경로 (미지정 시 configs/mcp_servers.yaml)

    Returns:
        설정 딕셔너리
    """
    path = config_path or CONFIG_PATH
    if not os.path.exists(path):
        return {"gateway": {"enabled": False}, "mcp_servers": []}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# MCP 클라이언트 생성
# ---------------------------------------------------------------------------

def create_mcp_clients(
    config: dict[str, Any],
    exit_stack: ExitStack,
) -> list:
    """설정에 따라 MCP 클라이언트를 생성하고 도구 목록을 반환합니다.

    Args:
        config: load_mcp_config() 로 로드한 설정
        exit_stack: context manager 를 등록할 ExitStack

    Returns:
        수집된 MCP 도구 리스트
    """
    tools: list = []

    for server in config.get("mcp_servers", []):
        if not server.get("enabled", False):
            continue

        name = server.get("name", "unknown")
        transport = server.get("transport")

        try:
            if transport == "stdio":
                mcp_client = _create_stdio_client(server)
            elif transport == "streamable_http":
                mcp_client = _create_http_client(server)
            else:
                print(f"MCP '{name}': unsupported transport '{transport}'")
                continue

            exit_stack.enter_context(mcp_client)
            server_tools = mcp_client.list_tools_sync()
            tools.extend(server_tools)
            print(f"MCP '{name}': {len(server_tools)} tools loaded")

        except Exception as e:
            print(f"MCP '{name}' connection failed: {e}")

    return tools


# ---------------------------------------------------------------------------
# Transport 별 클라이언트 팩토리
# ---------------------------------------------------------------------------

def _create_stdio_client(server: dict[str, Any]) -> MCPClient:
    """stdio transport MCP 클라이언트를 생성합니다."""
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client

    command = server["command"]
    args = server.get("args", [])
    env = _resolve_env(server.get("env", {}))

    return MCPClient(
        lambda cmd=command, a=args, e=env: stdio_client(
            server=StdioServerParameters(command=cmd, args=a, env=e)
        )
    )


def _create_http_client(server: dict[str, Any]) -> MCPClient:
    """streamable_http transport MCP 클라이언트를 생성합니다."""
    from mcp.client.streamable_http import streamablehttp_client

    url = server["url"]
    headers = _resolve_env(server.get("headers", {}))

    return MCPClient(
        lambda u=url, h=headers: streamablehttp_client(url=u, headers=h)
    )


# ---------------------------------------------------------------------------
# 환경 변수 해석
# ---------------------------------------------------------------------------

def _resolve_env(env: dict[str, str]) -> dict[str, str]:
    """환경 변수 참조(${VAR})를 실제 값으로 대체합니다."""
    resolved = {}
    for key, value in env.items():
        if isinstance(value, str):
            resolved[key] = _ENV_VAR_RE.sub(
                lambda m: os.getenv(m.group(1), m.group(0)),
                value,
            )
        else:
            resolved[key] = str(value)
    return resolved
