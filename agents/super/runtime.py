"""Super Agent Runtime — 서브 에이전트 오케스트레이션 엔트리포인트

4개 도메인 전문 에이전트를 @tool로 래핑하여 단일 진입점에서 오케스트레이션.
전체 9개 MCP 서버에 연결하여 Super Agent가 직접 MCP 도구도 사용 가능.

실행: python -m agents.super.runtime
"""
from __future__ import annotations

import os

from agents.runtime_base import create_app
from agents.super.agent import SYSTEM_PROMPT, TOOLS

MCP_CONFIG = os.path.join(
    os.path.dirname(__file__), "..", "..", "configs", "super.yaml"
)

app = create_app(
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT,
    mcp_config_path=MCP_CONFIG,
)

if __name__ == "__main__":
    app.run()
