"""Super Agent — 도메인별 서브 에이전트 오케스트레이션

사용자 쿼리를 분석하여 전문 에이전트(Monitoring, Cost, Security, Resource)에 위임하고,
여러 에이전트 결과를 종합하여 포괄적인 답변을 제공합니다.

참조: AgentCore Samples — multi-agent-runtime 패턴
"""
from __future__ import annotations

from strands import Agent, tool
from strands.models import BedrockModel

from agents.runtime_base import MODEL_ID

# 서브에이전트용 모델 (호출마다 새로 생성하지 않도록 모듈 레벨)
_sub_model = BedrockModel(model_id=MODEL_ID)


@tool
def ask_monitoring_agent(query: str) -> str:
    """AWS 모니터링 분석을 전문 에이전트에 위임합니다.
    CloudWatch 메트릭/알람/로그, EC2 인스턴스 상태 분석에 사용하세요.

    Args:
        query: 모니터링 관련 질문 또는 분석 요청
    """
    from agents.monitoring.agent import SYSTEM_PROMPT, TOOLS

    agent = Agent(model=_sub_model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
    response = agent(query)
    return response.message["content"][0]["text"]


@tool
def ask_cost_agent(query: str) -> str:
    """AWS 비용 분석을 전문 에이전트에 위임합니다.
    비용/사용량 조회, 예측, 라이트사이징 권장에 사용하세요.

    Args:
        query: 비용 관련 질문 또는 분석 요청
    """
    from agents.cost.agent import SYSTEM_PROMPT, TOOLS

    agent = Agent(model=_sub_model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
    response = agent(query)
    return response.message["content"][0]["text"]


@tool
def ask_security_agent(query: str) -> str:
    """AWS 보안 분석을 전문 에이전트에 위임합니다.
    Security Hub, GuardDuty 위협 탐지, IAM 자격 증명 점검에 사용하세요.

    Args:
        query: 보안 관련 질문 또는 분석 요청
    """
    from agents.security.agent import SYSTEM_PROMPT, TOOLS

    agent = Agent(model=_sub_model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
    response = agent(query)
    return response.message["content"][0]["text"]


@tool
def ask_resource_agent(query: str) -> str:
    """AWS 리소스 관리를 전문 에이전트에 위임합니다.
    EC2, VPC 네트워크, EBS, 리소스 인벤토리 분석에 사용하세요.

    Args:
        query: 리소스 관련 질문 또는 분석 요청
    """
    from agents.resource.agent import SYSTEM_PROMPT, TOOLS

    agent = Agent(model=_sub_model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
    response = agent(query)
    return response.message["content"][0]["text"]


SYSTEM_PROMPT = """당신은 AWS AIOps Super Agent입니다.

## 역할
사용자의 질문을 분석하여 적절한 전문 에이전트에 위임하고,
여러 에이전트의 결과를 종합하여 포괄적인 답변을 제공합니다.

## 전문 에이전트
1. **ask_monitoring_agent**: CloudWatch 메트릭/알람/로그, EC2 상태 분석
2. **ask_cost_agent**: 비용 분석, 예측, 라이트사이징 권장
3. **ask_security_agent**: Security Hub, GuardDuty, IAM 보안 점검
4. **ask_resource_agent**: EC2, VPC, EBS, 리소스 인벤토리 관리

## 오케스트레이션 원칙
- 단순 질문은 하나의 전문 에이전트에 위임
- 크로스 도메인 질문은 여러 에이전트를 순차 호출하여 종합
  예: "비용이 올랐는데 원인이 뭐야?" → ask_cost_agent + ask_resource_agent
- 전문 에이전트 결과를 종합하여 일관된 답변을 구성
- MCP 도구도 직접 사용 가능 (간단한 조회, CloudWatch/CloudTrail 등)

## 응답 형식
- 어떤 에이전트를 사용했는지 명시
- 크로스 도메인 분석은 도메인별로 구분하여 정리
- 종합 요약과 권장 조치를 마지막에 제공
"""

TOOLS = [
    ask_monitoring_agent,
    ask_cost_agent,
    ask_security_agent,
    ask_resource_agent,
]
