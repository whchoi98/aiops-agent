"""AgentCore Runtime 엔트리포인트 (E2E lab4 패턴)

MCP 연결 구조:
  1. AgentCore Gateway — 우리 커스텀 도구(18개)를 MCP 로 노출
  2. 외부 MCP 서버   — AWS 공식 MCP 서버 등을 설정 기반으로 연결
  3. 로컬 도구        — @tool 데코레이터로 정의된 함수들

설정: configs/mcp_servers.yaml
"""
from __future__ import annotations

from contextlib import ExitStack

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

from agents.aiops_agent import MODEL_ID, SYSTEM_PROMPT, TOOLS
from agents.mcp_manager import create_mcp_clients, load_mcp_config
from agents.memory import (
    ACTOR_ID,
    SESSION_ID,
    AIOpsMemoryHooks,
    memory_client,
)
from agents.utils import SSM_PREFIX, get_ssm_parameter

REGION = boto3.session.Session().region_name

model = BedrockModel(model_id=MODEL_ID)

# Memory 초기화
try:
    memory_id = get_ssm_parameter(f"{SSM_PREFIX}/memory_id")
    memory_hooks = AIOpsMemoryHooks(memory_id, memory_client, ACTOR_ID, SESSION_ID)
except Exception:
    memory_hooks = None  # type: ignore[assignment]

# MCP 설정 로드
mcp_config = load_mcp_config()

# AgentCore Runtime App
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload, context=None):
    """AgentCore Runtime 엔트리포인트"""
    user_input = payload.get("prompt", "")

    request_headers = (context.request_headers or {}) if context else {}
    auth_header = request_headers.get("Authorization", "")

    hooks = [memory_hooks] if memory_hooks else []
    all_tools = list(TOOLS)

    with ExitStack() as stack:
        # 1. AgentCore Gateway 연결 (선택적)
        if mcp_config.get("gateway", {}).get("enabled") and auth_header:
            try:
                gateway_id = get_ssm_parameter(f"{SSM_PREFIX}/gateway_id")
                from mcp.client.streamable_http import streamablehttp_client

                gw_api = boto3.client(
                    "bedrock-agentcore-control", region_name=REGION
                )
                gw_response = gw_api.get_gateway(gatewayIdentifier=gateway_id)
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

        # 2. 외부 MCP 서버 연결 (configs/mcp_servers.yaml)
        mcp_tools = create_mcp_clients(mcp_config, stack)
        all_tools.extend(mcp_tools)

        # 3. 에이전트 생성 및 실행
        agent = Agent(
            model=model,
            tools=all_tools,
            system_prompt=SYSTEM_PROMPT,
            hooks=hooks,
        )
        response = agent(user_input)
        return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
