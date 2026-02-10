"""MCP Tool Client - AgentCore Gateway를 통한 MCP 도구 호출"""

import asyncio
import json
import subprocess
from typing import Any

import httpx
import structlog

from .config import GatewayConfig, MCPServerConfig, get_gateway_config

logger = structlog.get_logger(__name__)


class MCPToolClient:
    """MCP 도구 클라이언트

    AgentCore Gateway 또는 로컬 MCP 서버를 통해 도구를 호출합니다.
    """

    def __init__(self, config: GatewayConfig | None = None) -> None:
        """MCP Tool Client 초기화

        Args:
            config: Gateway 설정 (기본값: 자동 로드)
        """
        self.config = config or get_gateway_config()
        self._http_client: httpx.AsyncClient | None = None
        self._local_processes: dict[str, subprocess.Popen] = {}

    async def __aenter__(self) -> "MCPToolClient":
        """비동기 컨텍스트 매니저 진입"""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """비동기 컨텍스트 매니저 종료"""
        if self._http_client:
            await self._http_client.aclose()

        # 로컬 프로세스 종료
        for process in self._local_processes.values():
            process.terminate()

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """MCP 도구 호출

        Args:
            server_name: MCP 서버 이름 (예: aws-ccapi)
            tool_name: 도구 이름 (예: list_resources)
            arguments: 도구 인자

        Returns:
            도구 실행 결과
        """
        # AgentCore Gateway가 설정된 경우 Gateway를 통해 호출
        if self.config.gateway_endpoint:
            return await self._call_via_gateway(server_name, tool_name, arguments)

        # 로컬 MCP 서버를 통해 호출
        return await self._call_local(server_name, tool_name, arguments)

    async def _call_via_gateway(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """AgentCore Gateway를 통한 도구 호출"""
        if not self._http_client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        headers = {}
        if self.config.gateway_api_key:
            headers["Authorization"] = f"Bearer {self.config.gateway_api_key}"

        payload = {
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
        }

        response = await self._http_client.post(
            f"{self.config.gateway_endpoint}/tools/call",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        return response.json()

    async def _call_local(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """로컬 MCP 서버를 통한 도구 호출"""
        server_config = self.config.mcp_servers.get(server_name)
        if not server_config:
            raise ValueError(f"Unknown MCP server: {server_name}")

        # MCP JSON-RPC 요청 생성
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        # 서버 프로세스 시작 또는 재사용
        process = await self._get_or_start_server(server_name, server_config)

        # 요청 전송 및 응답 수신
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()

        response_line = process.stdout.readline()
        response = json.loads(response_line)

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get("result", {})

    async def _get_or_start_server(
        self,
        server_name: str,
        config: MCPServerConfig,
    ) -> subprocess.Popen:
        """MCP 서버 프로세스 가져오기 또는 시작"""
        if server_name in self._local_processes:
            process = self._local_processes[server_name]
            if process.poll() is None:  # 아직 실행 중
                return process

        # 새 프로세스 시작
        env = {**dict(config.env)}
        cmd = [config.command] + config.args

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )

        self._local_processes[server_name] = process

        logger.info("Started MCP server", server=server_name, pid=process.pid)

        return process

    def get_available_tools(self, server_name: str | None = None) -> list[str]:
        """사용 가능한 도구 목록 반환

        Args:
            server_name: 특정 서버의 도구만 반환 (선택)

        Returns:
            도구 이름 목록
        """
        # 실제 구현에서는 MCP 서버에 tools/list 요청
        # 여기서는 알려진 도구 목록 반환
        known_tools = {
            "aws-ccapi": [
                "list_resources",
                "get_resource",
                "create_resource",
                "update_resource",
                "delete_resource",
                "get_resource_schema_information",
            ],
            "aws-cloudwatch": [
                "describe_log_groups",
                "execute_log_insights_query",
                "get_metric_data",
                "get_active_alarms",
            ],
            "aws-cost-explorer": [
                "get_cost_and_usage",
                "get_cost_forecast",
                "get_dimension_values",
            ],
            "aws-iam": [
                "list_users",
                "list_roles",
                "list_policies",
                "simulate_principal_policy",
            ],
            "aws-eks": [
                "manage_eks_stacks",
                "list_k8s_resources",
                "manage_k8s_resource",
                "apply_yaml",
                "generate_app_manifest",
                "get_pod_logs",
                "get_k8s_events",
                "get_cloudwatch_logs",
                "get_cloudwatch_metrics",
                "search_eks_troubleshoot_guide",
                "get_policies_for_role",
                "add_inline_policy",
            ],
            "aws-ecs": [
                "containerize_app",
                "build_and_push_image_to_ecr",
                "validate_ecs_express_mode_prerequisites",
                "wait_for_service_ready",
                "delete_app",
                "ecs_troubleshooting_tool",
                "ecs_resource_management",
            ],
            "aws-network": [
                "get_path_trace_methodology",
                "find_ip_address",
                "list_core_networks",
                "get_cloudwan_routes",
                "detect_cloudwan_inspection",
                "list_transit_gateways",
                "get_tgw_routes",
                "get_tgw_flow_logs",
                "list_vpcs",
                "get_vpc_network_details",
                "get_vpc_flow_logs",
                "list_network_firewalls",
                "get_firewall_rules",
                "list_vpn_connections",
            ],
            "aws-cfn": [
                "list_resources",
                "get_resource",
                "create_template",
            ],
            "steampipe": [
                "run_steampipe_query",
                "query_aws_inventory",
                "list_ec2_instances",
                "list_s3_buckets",
                "list_rds_instances",
                "list_lambda_functions",
                "list_iam_users",
                "list_vpc_resources",
                "list_security_groups",
                "get_asset_summary",
            ],
        }

        if server_name:
            return known_tools.get(server_name, [])

        all_tools = []
        for tools in known_tools.values():
            all_tools.extend(tools)
        return all_tools


class NetworkToolsMixin:
    """네트워크 관련 MCP 도구 믹스인"""

    async def list_vpcs(self, client: MCPToolClient) -> dict[str, Any]:
        """VPC 목록 조회"""
        return await client.call_tool(
            server_name="aws-ccapi",
            tool_name="list_resources",
            arguments={"resource_type": "AWS::EC2::VPC"},
        )

    async def list_subnets(
        self,
        client: MCPToolClient,
        vpc_id: str | None = None,
    ) -> dict[str, Any]:
        """서브넷 목록 조회"""
        args: dict[str, Any] = {"resource_type": "AWS::EC2::Subnet"}
        if vpc_id:
            args["resource_model"] = {"VpcId": vpc_id}

        return await client.call_tool(
            server_name="aws-ccapi",
            tool_name="list_resources",
            arguments=args,
        )

    async def list_security_groups(
        self,
        client: MCPToolClient,
        vpc_id: str | None = None,
    ) -> dict[str, Any]:
        """보안 그룹 목록 조회"""
        args: dict[str, Any] = {"resource_type": "AWS::EC2::SecurityGroup"}
        if vpc_id:
            args["resource_model"] = {"VpcId": vpc_id}

        return await client.call_tool(
            server_name="aws-ccapi",
            tool_name="list_resources",
            arguments=args,
        )

    async def get_vpc_details(
        self,
        client: MCPToolClient,
        vpc_id: str,
    ) -> dict[str, Any]:
        """VPC 상세 정보 조회"""
        return await client.call_tool(
            server_name="aws-ccapi",
            tool_name="get_resource",
            arguments={
                "resource_type": "AWS::EC2::VPC",
                "identifier": vpc_id,
            },
        )

    async def describe_network_topology(
        self,
        client: MCPToolClient,
        vpc_id: str,
    ) -> dict[str, Any]:
        """VPC 네트워크 토폴로지 조회"""
        vpc = await self.get_vpc_details(client, vpc_id)
        subnets = await self.list_subnets(client, vpc_id)
        security_groups = await self.list_security_groups(client, vpc_id)

        return {
            "vpc": vpc,
            "subnets": subnets,
            "security_groups": security_groups,
        }
