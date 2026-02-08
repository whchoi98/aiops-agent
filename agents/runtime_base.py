"""AgentCore Runtime 공유 팩토리

도메인별 Runtime이 공통으로 사용하는 초기화 로직:
  - BedrockModel 생성
  - AgentCore Memory 연결
  - AgentCore Observability (OTEL 세션 컨텍스트)
  - AgentCore Gateway 연결
  - 외부 MCP 서버 연결
  - Agent 생성 및 실행
"""
from __future__ import annotations

from contextlib import ExitStack
from typing import Any

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

from agents.mcp_manager import create_mcp_clients, load_mcp_config
from agents.memory import (
    ACTOR_ID,
    SESSION_ID,
    AIOpsMemoryHooks,
    memory_client,
)
from agents.observability import attach_session_context, detach_session_context
from agents.utils import SSM_PREFIX, get_ssm_parameter

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = boto3.session.Session().region_name


def _init_memory() -> AIOpsMemoryHooks | None:
    """AgentCore Memory 훅을 초기화합니다. 실패 시 None."""
    try:
        memory_id = get_ssm_parameter(f"{SSM_PREFIX}/memory_id")
        return AIOpsMemoryHooks(memory_id, memory_client, ACTOR_ID, SESSION_ID)
    except Exception:
        return None


def create_app(
    tools: list,
    system_prompt: str,
    mcp_config_path: str | None = None,
) -> BedrockAgentCoreApp:
    """도메인별 AgentCore Runtime App을 생성합니다.

    Args:
        tools: 로컬 @tool 함수 목록
        system_prompt: 에이전트 시스템 프롬프트
        mcp_config_path: MCP 설정 파일 경로 (미지정 시 기본 configs/mcp_servers.yaml)

    Returns:
        구성된 BedrockAgentCoreApp 인스턴스
    """
    model = BedrockModel(model_id=MODEL_ID)
    memory_hooks = _init_memory()
    mcp_config = load_mcp_config(mcp_config_path)

    app = BedrockAgentCoreApp()

    @app.entrypoint
    async def invoke(payload: dict[str, Any], context: Any = None) -> str:
        """AgentCore Runtime 엔트리포인트"""
        user_input = payload.get("prompt", "")

        request_headers = (context.request_headers or {}) if context else {}
        auth_header = request_headers.get("Authorization", "")

        # Observability: 세션 ID를 OTEL baggage에 첨부
        otel_token = attach_session_context(SESSION_ID)

        hooks = [memory_hooks] if memory_hooks else []
        all_tools = list(tools)

        try:
            with ExitStack() as stack:
                # 1. AgentCore Gateway 연결 (선택적)
                if mcp_config.get("gateway", {}).get("enabled") and auth_header:
                    try:
                        gateway_id = get_ssm_parameter(f"{SSM_PREFIX}/gateway_id")
                        from mcp.client.streamable_http import streamablehttp_client

                        gw_api = boto3.client(
                            "bedrock-agentcore-control", region_name=REGION
                        )
                        gw_response = gw_api.get_gateway(
                            gatewayIdentifier=gateway_id
                        )
                        gw_url = gw_response["gatewayUrl"]

                        gw_mcp = MCPClient(
                            lambda url=gw_url, hdr=auth_header: streamablehttp_client(
                                url=url, headers={"Authorization": hdr}
                            )
                        )
                        stack.enter_context(gw_mcp)
                        gw_tools = gw_mcp.list_tools_sync()
                        all_tools.extend(gw_tools)
                        print(f"Gateway: {len(gw_tools)} tools loaded")
                    except Exception as e:
                        print(f"Gateway connection failed: {e}")

                # 2. 외부 MCP 서버 연결 (설정 파일 기반)
                mcp_tools = create_mcp_clients(mcp_config, stack)
                all_tools.extend(mcp_tools)

                # 3. 에이전트 생성 및 실행
                agent = Agent(
                    model=model,
                    tools=all_tools,
                    system_prompt=system_prompt,
                    hooks=hooks,
                )
                response = agent(user_input)
                return response.message["content"][0]["text"]
        finally:
            # Observability: 세션 컨텍스트 해제
            detach_session_context(otel_token)

    return app
