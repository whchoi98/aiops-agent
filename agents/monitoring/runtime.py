"""모니터링 Runtime 엔트리포인트

CloudWatch MCP + EC2 상태 확인 도구를 포함하는 특화 런타임.

실행: python -m agents.monitoring.runtime
"""
from __future__ import annotations

import os

from agents.monitoring.agent import SYSTEM_PROMPT, TOOLS
from agents.runtime_base import create_app

MCP_CONFIG = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "monitoring.yaml")

app = create_app(tools=TOOLS, system_prompt=SYSTEM_PROMPT, mcp_config_path=MCP_CONFIG)

if __name__ == "__main__":
    app.run()
