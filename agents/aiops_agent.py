"""AIOps 에이전트 정의 — 도구 + 시스템 프롬프트 (E2E lab1 패턴)"""
from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from tools.cloudwatch_tools import (
    describe_ec2_instances,
    get_cloudwatch_alarms,
    get_cloudwatch_metrics,
    query_cloudwatch_logs,
)
from tools.cost_explorer_tools import (
    get_cost_and_usage,
    get_cost_by_service,
    get_cost_forecast,
    get_rightsizing_recommendations,
)
from tools.ec2_tools import get_ebs_volumes, get_instance_status, list_ec2_instances
from tools.resource_inventory import get_resource_summary, list_resources_by_type
from tools.security_tools import (
    get_guardduty_findings,
    get_iam_credential_report,
    get_security_findings,
)
from tools.vpc_tools import (
    analyze_network_topology,
    describe_route_tables,
    describe_security_groups,
    describe_subnets,
    describe_vpcs,
)

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

SYSTEM_PROMPT = """당신은 AWS 인프라 운영 전문 AI 어시스턴트(AIOps Agent)입니다.

## 역할
- AWS 리소스 모니터링 및 상태 분석
- CloudWatch 메트릭/로그 기반 이상 탐지
- 비용 최적화 분석 및 권장 사항 제공
- 보안 취약점 탐지 및 조치 가이드
- VPC 네트워크 토폴로지 분석
- 리소스 인벤토리 관리

## 도구 사용 원칙
- 항상 도구를 사용하여 정확한 데이터를 기반으로 분석하세요.
- 추측하지 말고 실제 데이터를 조회한 후 답변하세요.
- 여러 도구를 조합하여 종합적인 분석을 제공하세요.

## 사용 가능한 도구
1. **모니터링**: get_cloudwatch_metrics, get_cloudwatch_alarms,
   query_cloudwatch_logs, describe_ec2_instances
2. **비용 분석**: get_cost_and_usage, get_cost_forecast,
   get_rightsizing_recommendations, get_cost_by_service
3. **보안 점검**: get_security_findings, get_guardduty_findings,
   get_iam_credential_report
4. **EC2 관리**: list_ec2_instances, get_instance_status, get_ebs_volumes
5. **네트워크**: describe_vpcs, describe_subnets,
   describe_security_groups, describe_route_tables, analyze_network_topology
6. **인벤토리**: get_resource_summary, list_resources_by_type

## 응답 형식
- 데이터 기반의 명확한 분석 결과를 제공하세요.
- 문제가 발견되면 심각도와 권장 조치를 포함하세요.
- 비용 관련 분석은 금액과 절감 가능 금액을 명시하세요.
- 보안 이슈는 즉시 주의가 필요한 항목을 우선 보고하세요.
"""

# 도구 목록 — runtime.py 에서 재사용
TOOLS = [
    # 모니터링
    get_cloudwatch_metrics,
    get_cloudwatch_alarms,
    query_cloudwatch_logs,
    describe_ec2_instances,
    # 비용
    get_cost_and_usage,
    get_cost_forecast,
    get_rightsizing_recommendations,
    get_cost_by_service,
    # 보안
    get_security_findings,
    get_guardduty_findings,
    get_iam_credential_report,
    # EC2
    list_ec2_instances,
    get_instance_status,
    get_ebs_volumes,
    # 네트워크
    describe_vpcs,
    describe_subnets,
    describe_security_groups,
    describe_route_tables,
    analyze_network_topology,
    # 인벤토리
    get_resource_summary,
    list_resources_by_type,
]


def create_agent(hooks: list | None = None) -> Agent:
    """AIOps 에이전트를 생성합니다.

    Args:
        hooks: Strands HookProvider 목록 (예: memory hooks)

    Returns:
        구성된 Agent 인스턴스
    """
    model = BedrockModel(model_id=MODEL_ID)
    return Agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        hooks=hooks or [],
    )
