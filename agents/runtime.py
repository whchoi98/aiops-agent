"""AgentCore Runtime 엔트리포인트 (E2E lab4 패턴)"""
from __future__ import annotations

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

from agents.aiops_agent import MODEL_ID, SYSTEM_PROMPT, TOOLS
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

# AgentCore Runtime App
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload, context=None):
    """AgentCore Runtime 엔트리포인트"""
    user_input = payload.get("prompt", "")

    request_headers = (context.request_headers or {}) if context else {}
    auth_header = request_headers.get("Authorization", "")

    # Gateway 연결 (선택적)
    gateway_id = None
    try:
        gateway_id = get_ssm_parameter(f"{SSM_PREFIX}/gateway_id")
    except Exception:
        pass

    hooks = [memory_hooks] if memory_hooks else []

    if gateway_id and auth_header:
        try:
            from mcp.client.streamable_http import streamablehttp_client

            gateway_client = boto3.client(
                "bedrock-agentcore-control", region_name=REGION
            )
            gateway_response = gateway_client.get_gateway(
                gatewayIdentifier=gateway_id
            )
            gateway_url = gateway_response["gatewayUrl"]

            mcp_client = MCPClient(
                lambda: streamablehttp_client(
                    url=gateway_url, headers={"Authorization": auth_header}
                )
            )

            with mcp_client:
                all_tools = TOOLS + mcp_client.list_tools_sync()
                agent = Agent(
                    model=model,
                    tools=all_tools,
                    system_prompt=SYSTEM_PROMPT,
                    hooks=hooks,
                )
                response = agent(user_input)
                return response.message["content"][0]["text"]
        except Exception as e:
            print(f"MCP client error: {e}")
            return f"Error: {e}"
    else:
        # 로컬 도구만 사용
        agent = Agent(
            model=model,
            tools=TOOLS,
            system_prompt=SYSTEM_PROMPT,
            hooks=hooks,
        )
        response = agent(user_input)
        return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
