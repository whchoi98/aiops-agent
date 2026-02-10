"""AWS 리소스 관리 에이전트 - AgentCore Gateway 통합"""

from strands import Agent

from src.tools.network import (
    analyze_network_topology,
    describe_network_acls,
    describe_route_tables,
    describe_security_groups,
    describe_subnets,
    describe_vpcs,
)
from src.gateway import GatewayConfig, MCPToolClient


class ResourceManagerAgent(Agent):
    """AWS 리소스 및 네트워크 관리 AI 에이전트

    VPC, 서브넷, 보안 그룹 등 네트워크 리소스를 관리하고
    AgentCore Gateway를 통해 MCP 도구에 접근합니다.
    """

    def __init__(
        self,
        region: str = "ap-northeast-2",
        gateway_config: GatewayConfig | None = None,
    ) -> None:
        """리소스 관리 에이전트 초기화

        Args:
            region: AWS 리전 (기본값: ap-northeast-2)
            gateway_config: AgentCore Gateway 설정 (선택)
        """
        self.region = region
        self.gateway_config = gateway_config or GatewayConfig.from_mcp_json()

        super().__init__(
            name="resource-manager-agent",
            model="anthropic.claude-4-opus",
            system_prompt=self._get_system_prompt(),
            tools=[
                # 네트워크 도구
                describe_vpcs,
                describe_subnets,
                describe_security_groups,
                describe_route_tables,
                describe_network_acls,
                analyze_network_topology,
            ],
        )

    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return """당신은 AWS 인프라 및 네트워크 관리 전문가입니다.

주요 역할:
1. VPC, 서브넷, 보안 그룹 등 네트워크 리소스 관리
2. 네트워크 토폴로지 분석 및 최적화 권장
3. 보안 그룹 규칙 검토 및 보안 강화 제안
4. 리소스 관계 매핑 및 의존성 분석

네트워크 분석 시 확인할 사항:
- VPC CIDR 블록 충돌 여부
- 서브넷 가용 IP 주소 여부
- 보안 그룹의 과도한 개방 포트
- 라우팅 테이블의 올바른 구성
- 네트워크 ACL 규칙 검토

응답 시 다음을 포함하세요:
- 현재 네트워크 구성 요약
- 발견된 문제점 또는 개선점
- 구체적인 권장 조치
- 관련 리소스 ID 및 상세 정보

한국어로 응답하세요."""

    async def analyze_vpc_with_gateway(self, vpc_id: str) -> dict:
        """AgentCore Gateway를 통한 VPC 분석

        Args:
            vpc_id: 분석할 VPC ID

        Returns:
            VPC 분석 결과
        """
        async with MCPToolClient(self.gateway_config) as client:
            # Gateway를 통해 VPC 정보 조회
            vpc_info = await client.call_tool(
                server_name="aws-ccapi",
                tool_name="get_resource",
                arguments={
                    "resource_type": "AWS::EC2::VPC",
                    "identifier": vpc_id,
                },
            )

            # 서브넷 조회
            subnets = await client.call_tool(
                server_name="aws-ccapi",
                tool_name="list_resources",
                arguments={
                    "resource_type": "AWS::EC2::Subnet",
                },
            )

            return {
                "vpc": vpc_info,
                "subnets": subnets,
            }


def create_agent(
    region: str = "ap-northeast-2",
    gateway_config: GatewayConfig | None = None,
) -> ResourceManagerAgent:
    """리소스 관리 에이전트 팩토리 함수

    Args:
        region: AWS 리전
        gateway_config: AgentCore Gateway 설정

    Returns:
        ResourceManagerAgent 인스턴스
    """
    return ResourceManagerAgent(region=region, gateway_config=gateway_config)
