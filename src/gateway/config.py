"""AgentCore Gateway 설정"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """개별 MCP 서버 설정"""

    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class GatewayConfig(BaseModel):
    """AgentCore Gateway 설정"""

    # AgentCore Gateway 엔드포인트
    gateway_endpoint: str | None = None
    gateway_api_key: str | None = None

    # MCP 서버 설정
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    # 네트워크 관련 도구 그룹
    network_tools: list[str] = Field(
        default_factory=lambda: [
            "aws-network",  # VPC, TGW, Cloud WAN, Network Firewall 분석
            "aws-ccapi",    # VPC, Subnet, Security Group 등 관리
            "aws-cfn",      # CloudFormation 네트워크 스택
        ]
    )

    # 모니터링 도구 그룹
    monitoring_tools: list[str] = Field(
        default_factory=lambda: [
            "aws-cloudwatch",
            "aws-cost-explorer",
        ]
    )

    # 보안 도구 그룹
    security_tools: list[str] = Field(
        default_factory=lambda: [
            "aws-iam",
            "aws-network",  # Network Firewall, Security Group 분석
        ]
    )

    # 컴퓨팅 도구 그룹 (컨테이너)
    compute_tools: list[str] = Field(
        default_factory=lambda: [
            "aws-eks",  # Kubernetes 클러스터 관리
            "aws-ecs",  # ECS 클러스터/서비스 관리
            "aws-ccapi",
        ]
    )

    # 컨테이너 오케스트레이션 도구 그룹
    container_tools: list[str] = Field(
        default_factory=lambda: [
            "aws-eks",  # EKS 클러스터, K8s 리소스
            "aws-ecs",  # ECS 클러스터, 서비스, 태스크
        ]
    )

    # 자산 인벤토리 도구 그룹 (Steampipe)
    inventory_tools: list[str] = Field(
        default_factory=lambda: [
            "steampipe",  # SQL 기반 AWS 자산 조회
        ]
    )

    @classmethod
    def from_mcp_json(cls, mcp_json_path: str | Path | None = None) -> "GatewayConfig":
        """MCP JSON 파일에서 설정 로드

        Args:
            mcp_json_path: .mcp.json 파일 경로 (기본값: 프로젝트 루트)

        Returns:
            GatewayConfig 인스턴스
        """
        if mcp_json_path is None:
            # 프로젝트 루트에서 .mcp.json 찾기
            current = Path.cwd()
            while current != current.parent:
                mcp_file = current / ".mcp.json"
                if mcp_file.exists():
                    mcp_json_path = mcp_file
                    break
                current = current.parent

        if mcp_json_path is None or not Path(mcp_json_path).exists():
            return cls()

        with open(mcp_json_path) as f:
            data = json.load(f)

        mcp_servers = {}
        for name, config in data.get("mcpServers", {}).items():
            mcp_servers[name] = MCPServerConfig(**config)

        return cls(
            gateway_endpoint=os.getenv("AGENTCORE_GATEWAY_ENDPOINT"),
            gateway_api_key=os.getenv("AGENTCORE_GATEWAY_API_KEY"),
            mcp_servers=mcp_servers,
        )

    def get_tools_for_agent(self, agent_type: str) -> list[str]:
        """에이전트 유형에 따른 도구 목록 반환

        Args:
            agent_type: 에이전트 유형 (monitoring, security, network, compute)

        Returns:
            MCP 서버 이름 목록
        """
        tool_mapping = {
            "monitoring": self.monitoring_tools,
            "security": self.security_tools,
            "network": self.network_tools,
            "compute": self.compute_tools,
            "container": self.container_tools,
            "inventory": self.inventory_tools,
            "cost_optimizer": ["aws-cost-explorer", "aws-ccapi"],
            "incident_response": self.monitoring_tools + self.compute_tools + ["aws-network"],
            "resource_manager": self.network_tools + self.compute_tools + self.inventory_tools,
            "asset_manager": self.inventory_tools + ["aws-ccapi"],
            "eks": ["aws-eks"],
            "ecs": ["aws-ecs"],
        }

        return tool_mapping.get(agent_type, list(self.mcp_servers.keys()))

    def get_enabled_servers(self) -> dict[str, MCPServerConfig]:
        """활성화된 MCP 서버만 반환"""
        return {
            name: config
            for name, config in self.mcp_servers.items()
            if config.enabled
        }


@lru_cache
def get_gateway_config() -> GatewayConfig:
    """Gateway 설정 싱글톤 반환"""
    return GatewayConfig.from_mcp_json()
