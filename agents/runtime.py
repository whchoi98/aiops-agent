"""AgentCore 통합 Runtime 엔트리포인트

18개 로컬 도구 + 모든 외부 MCP 서버를 포함하는 통합 런타임.
도메인별 특화 런타임은 agents/{monitoring,cost,security,resource}/ 참조.

실행: python -m agents.runtime
"""
from __future__ import annotations

from agents.aiops_agent import SYSTEM_PROMPT, TOOLS
from agents.runtime_base import create_app

app = create_app(tools=TOOLS, system_prompt=SYSTEM_PROMPT)

if __name__ == "__main__":
    app.run()
