"""AgentCore Gateway Lambda 핸들러 — MCP 도구 디스패치

E2E 튜토리얼 lab-03 패턴:
  tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
  tool_name = tool_name.split("___")[1]  # target___tool_name → tool_name
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Lambda 패키징 시 tools/ 가 함께 번들되므로 sys.path 에 추가
_LAMBDA_TASK_ROOT = os.getenv("LAMBDA_TASK_ROOT", "")
if _LAMBDA_TASK_ROOT and _LAMBDA_TASK_ROOT not in sys.path:
    sys.path.insert(0, _LAMBDA_TASK_ROOT)

# ---------------------------------------------------------------------------
# 도구 임포트 — @tool 데코레이터가 붙어 있지만 일반 호출도 가능
# CloudWatch 도구는 AWS 공식 CloudWatch MCP 서버로 대체
# ---------------------------------------------------------------------------
from tools.cost_explorer_tools import (  # noqa: E402
    get_cost_and_usage,
    get_cost_by_service,
    get_cost_forecast,
    get_rightsizing_recommendations,
)
from tools.ec2_tools import (  # noqa: E402
    describe_ec2_instances,
    get_ebs_volumes,
    get_instance_status,
    list_ec2_instances,
)
from tools.resource_inventory import (  # noqa: E402
    get_resource_summary,
    list_resources_by_type,
)
from tools.security_tools import (  # noqa: E402
    get_guardduty_findings,
    get_iam_credential_report,
    get_security_findings,
)
from tools.vpc_tools import (  # noqa: E402
    analyze_network_topology,
    describe_route_tables,
    describe_security_groups,
    describe_subnets,
    describe_vpcs,
)

# ---------------------------------------------------------------------------
# 도구 레지스트리 — {tool_name: callable}
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, Any] = {
    # EC2
    "describe_ec2_instances": describe_ec2_instances,
    # 비용
    "get_cost_and_usage": get_cost_and_usage,
    "get_cost_forecast": get_cost_forecast,
    "get_rightsizing_recommendations": get_rightsizing_recommendations,
    "get_cost_by_service": get_cost_by_service,
    # 보안
    "get_security_findings": get_security_findings,
    "get_guardduty_findings": get_guardduty_findings,
    "get_iam_credential_report": get_iam_credential_report,
    # EC2
    "list_ec2_instances": list_ec2_instances,
    "get_instance_status": get_instance_status,
    "get_ebs_volumes": get_ebs_volumes,
    # 네트워크
    "describe_vpcs": describe_vpcs,
    "describe_subnets": describe_subnets,
    "describe_security_groups": describe_security_groups,
    "describe_route_tables": describe_route_tables,
    "analyze_network_topology": analyze_network_topology,
    # 인벤토리
    "get_resource_summary": get_resource_summary,
    "list_resources_by_type": list_resources_by_type,
}


def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """AgentCore Gateway 로부터 도구 호출을 수신하여 디스패치합니다.

    Args:
        event: Gateway가 inputSchema에 맞춰 전달한 도구 파라미터
        context: Lambda 컨텍스트 (client_context.custom 에 도구 이름 포함)
    """
    # 도구 이름 추출: target___tool_name → tool_name
    try:
        raw_name = context.client_context.custom["bedrockAgentCoreToolName"]
    except (AttributeError, KeyError, TypeError):
        logger.error("bedrockAgentCoreToolName not found in client context")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing bedrockAgentCoreToolName"}),
        }

    tool_name = raw_name.split("___")[1] if "___" in raw_name else raw_name
    logger.info("Dispatching tool: %s (raw: %s)", tool_name, raw_name)

    handler = TOOL_REGISTRY.get(tool_name)
    if handler is None:
        logger.error("Unknown tool: %s", tool_name)
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"Unknown tool: {tool_name}"}),
        }

    try:
        params = event if isinstance(event, dict) else {}
        result = handler(**params)
        return {
            "statusCode": 200,
            "body": json.dumps(result, default=str),
        }
    except Exception:
        logger.exception("Tool execution failed: %s", tool_name)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Tool execution failed: {tool_name}"}),
        }
