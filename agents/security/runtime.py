"""보안 Runtime 엔트리포인트

Security Hub / GuardDuty / IAM 도구를 포함하는 특화 런타임.

실행: python -m agents.security.runtime
"""
from __future__ import annotations

import os

from agents.runtime_base import create_app
from agents.security.agent import SYSTEM_PROMPT, TOOLS

MCP_CONFIG = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "security.yaml")

app = create_app(tools=TOOLS, system_prompt=SYSTEM_PROMPT, mcp_config_path=MCP_CONFIG)

if __name__ == "__main__":
    app.run()
