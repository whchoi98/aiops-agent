"""인벤토리 Runtime 엔트리포인트

Steampipe 기반 AWS 자산 인벤토리 분석 특화 런타임.

실행: python -m agents.inventory.runtime
"""
from __future__ import annotations

import os

from agents.inventory.agent import SYSTEM_PROMPT, TOOLS
from agents.runtime_base import create_app

MCP_CONFIG = os.path.join(
    os.path.dirname(__file__), "..", "..", "configs", "inventory.yaml"
)

app = create_app(tools=TOOLS, system_prompt=SYSTEM_PROMPT, mcp_config_path=MCP_CONFIG)

if __name__ == "__main__":
    app.run()
