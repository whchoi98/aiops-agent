"""AWS 리소스 모니터링 에이전트 구현"""

from strands import Agent, tool
from typing import Any

from .tools import (
    get_cloudwatch_metrics,
    get_cloudwatch_alarms,
    query_cloudwatch_logs,
    describe_ec2_instances,
)


class MonitoringAgent(Agent):
    """AWS 리소스 모니터링을 담당하는 AI 에이전트

    CloudWatch 메트릭, 로그, 알람을 분석하여 인프라 상태를 모니터링하고
    이상 징후를 감지합니다.
    """

    def __init__(self, region: str = "ap-northeast-2") -> None:
        """모니터링 에이전트 초기화

        Args:
            region: AWS 리전 (기본값: ap-northeast-2)
        """
        self.region = region

        super().__init__(
            name="monitoring-agent",
            model="anthropic.claude-4-opus",
            system_prompt=self._get_system_prompt(),
            tools=[
                get_cloudwatch_metrics,
                get_cloudwatch_alarms,
                query_cloudwatch_logs,
                describe_ec2_instances,
            ],
        )

    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return """당신은 AWS 인프라 모니터링 전문가입니다.

주요 역할:
1. CloudWatch 메트릭을 분석하여 리소스 상태를 파악합니다
2. 알람 상태를 확인하고 문제를 식별합니다
3. 로그를 분석하여 에러 패턴을 찾습니다
4. 성능 이상 징후를 조기에 감지합니다

응답 시 다음을 포함하세요:
- 현재 상태 요약
- 발견된 문제점
- 권장 조치 사항
- 관련 메트릭 데이터

한국어로 응답하세요."""


def create_agent(region: str = "ap-northeast-2") -> MonitoringAgent:
    """모니터링 에이전트 팩토리 함수

    Args:
        region: AWS 리전

    Returns:
        MonitoringAgent 인스턴스
    """
    return MonitoringAgent(region=region)
