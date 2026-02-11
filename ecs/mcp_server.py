"""Steampipe MCP HTTP Server — ECS Fargate 배포용

AgentCore Gateway HTTP 타겟으로 사용되는 MCP 호환 서버.
컨테이너 내부 Steampipe 서비스(localhost:9193)에 psycopg2로 연결합니다.

실행: python ecs/mcp_server.py
"""
from __future__ import annotations

import datetime
import json
import os
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Steampipe PostgreSQL 연결
# ---------------------------------------------------------------------------

_STEAMPIPE_HOST = os.getenv("STEAMPIPE_HOST", "localhost")
_STEAMPIPE_PORT = int(os.getenv("STEAMPIPE_PORT", "9193"))
_STEAMPIPE_DB = os.getenv("STEAMPIPE_DB", "steampipe")
_STEAMPIPE_USER = os.getenv("STEAMPIPE_USER", "steampipe")
_STEAMPIPE_PASSWORD = os.getenv("STEAMPIPE_PASSWORD", "steampipe_aiops")


def _serialize_value(val: Any) -> Any:
    if isinstance(val, datetime.datetime):
        return val.isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    if isinstance(val, Decimal):
        return int(val) if val == val.to_integral_value() else float(val)
    return val


def _query(sql: str) -> dict[str, Any]:
    """Steampipe PostgreSQL 쿼리 실행"""
    try:
        conn = psycopg2.connect(
            host=_STEAMPIPE_HOST,
            port=_STEAMPIPE_PORT,
            dbname=_STEAMPIPE_DB,
            user=_STEAMPIPE_USER,
            password=_STEAMPIPE_PASSWORD,
            connect_timeout=10,
        )
        conn.set_session(autocommit=True)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                if cur.description:
                    rows = [
                        {k: _serialize_value(v) for k, v in dict(row).items()}
                        for row in cur.fetchall()
                    ]
                    return {"success": True, "data": rows, "count": len(rows)}
                return {"success": True, "data": [], "count": 0}
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "error": str(e)}


def _to_json(result: dict) -> str:
    return json.dumps(result, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 테이블 매핑
# ---------------------------------------------------------------------------

TABLE_MAP = {
    # AWS
    "ec2": "aws_ec2_instance", "s3": "aws_s3_bucket",
    "rds": "aws_rds_db_instance", "lambda": "aws_lambda_function",
    "iam_user": "aws_iam_user", "iam_role": "aws_iam_role",
    "vpc": "aws_vpc", "subnet": "aws_vpc_subnet",
    "security_group": "aws_vpc_security_group", "ebs": "aws_ebs_volume",
    "eks": "aws_eks_cluster", "ecs": "aws_ecs_cluster",
    "dynamodb": "aws_dynamodb_table", "sqs": "aws_sqs_queue",
    "sns": "aws_sns_topic",
    # Kubernetes
    "pod": "kubernetes_pod", "deployment": "kubernetes_deployment",
    "service": "kubernetes_service", "namespace": "kubernetes_namespace",
    "node": "kubernetes_node", "configmap": "kubernetes_config_map",
    "daemonset": "kubernetes_daemonset", "statefulset": "kubernetes_stateful_set",
    "job": "kubernetes_job", "cronjob": "kubernetes_cronjob",
    "pv": "kubernetes_persistent_volume", "pvc": "kubernetes_persistent_volume_claim",
}

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("aiops-steampipe-tools")


@mcp.tool()
def run_steampipe_query(query: str) -> str:
    """Steampipe SQL 쿼리를 실행하여 AWS 또는 Kubernetes 자산을 조회합니다.

    Args:
        query: Steampipe SQL 쿼리 (예: SELECT * FROM aws_ec2_instance LIMIT 10)
    """
    return _to_json(_query(query))


@mcp.tool()
def query_inventory(resource_type: str, limit: int = 100) -> str:
    """AWS 또는 Kubernetes 자산 인벤토리를 유형별로 조회합니다.

    Args:
        resource_type: 리소스 유형 (ec2, s3, rds, lambda, vpc, pod, deployment 등)
        limit: 최대 결과 수
    """
    table = TABLE_MAP.get(resource_type.lower())
    if not table:
        return _to_json({"success": False, "error": f"Unknown type: {resource_type}"})
    return _to_json(_query(f"SELECT * FROM {table} LIMIT {limit}"))


@mcp.tool()
def get_asset_summary() -> str:
    """전체 AWS + Kubernetes 자산 요약 (리소스 유형별 개수)"""
    queries = {
        "ec2_instances": "SELECT COUNT(*) as count FROM aws_ec2_instance",
        "ec2_running": "SELECT COUNT(*) as count FROM aws_ec2_instance WHERE instance_state = 'running'",
        "s3_buckets": "SELECT COUNT(*) as count FROM aws_s3_bucket",
        "rds_instances": "SELECT COUNT(*) as count FROM aws_rds_db_instance",
        "lambda_functions": "SELECT COUNT(*) as count FROM aws_lambda_function",
        "vpcs": "SELECT COUNT(*) as count FROM aws_vpc",
        "security_groups": "SELECT COUNT(*) as count FROM aws_vpc_security_group",
        "iam_users": "SELECT COUNT(*) as count FROM aws_iam_user",
        "ebs_volumes": "SELECT COUNT(*) as count FROM aws_ebs_volume",
        "k8s_pods": "SELECT COUNT(*) as count FROM kubernetes_pod",
        "k8s_deployments": "SELECT COUNT(*) as count FROM kubernetes_deployment",
        "k8s_services": "SELECT COUNT(*) as count FROM kubernetes_service",
    }
    summary = {}
    for key, sql in queries.items():
        r = _query(sql)
        summary[key] = r["data"][0]["count"] if r.get("success") and r.get("data") else "error"
    total = sum(v for v in summary.values() if isinstance(v, int))
    return _to_json({"summary": summary, "total_resources": total})


@mcp.tool()
def list_ec2_instances_steampipe(
    state: str = "", instance_type: str = "", region: str = "",
) -> str:
    """EC2 인스턴스 목록을 Steampipe SQL로 조회합니다.

    Args:
        state: 인스턴스 상태 필터 (running, stopped, terminated)
        instance_type: 인스턴스 유형 필터
        region: 리전 필터
    """
    conds = []
    if state:
        conds.append(f"instance_state = '{state}'")
    if instance_type:
        conds.append(f"instance_type = '{instance_type}'")
    if region:
        conds.append(f"region = '{region}'")
    where = " AND ".join(conds) if conds else "1=1"
    sql = f"""SELECT instance_id, title, instance_type, instance_state,
           public_ip_address, private_ip_address, vpc_id, launch_time, region, tags
    FROM aws_ec2_instance WHERE {where} ORDER BY launch_time DESC"""
    return _to_json(_query(sql))


@mcp.tool()
def list_s3_buckets_steampipe() -> str:
    """S3 버킷 목록과 보안 상태를 조회합니다."""
    sql = """SELECT name, region, creation_date, bucket_policy_is_public,
           block_public_acls, versioning_enabled, tags
    FROM aws_s3_bucket ORDER BY creation_date DESC"""
    return _to_json(_query(sql))


@mcp.tool()
def list_rds_instances_steampipe(engine: str = "", status: str = "") -> str:
    """RDS 인스턴스 목록을 조회합니다.

    Args:
        engine: 엔진 필터 (mysql, postgres, aurora 등)
        status: 상태 필터 (available, stopped 등)
    """
    conds = []
    if engine:
        conds.append(f"engine LIKE '%{engine}%'")
    if status:
        conds.append(f"status = '{status}'")
    where = " AND ".join(conds) if conds else "1=1"
    sql = f"""SELECT db_instance_identifier, db_instance_class, engine, engine_version,
           status, endpoint_address, multi_az, storage_encrypted, region, tags
    FROM aws_rds_db_instance WHERE {where}"""
    return _to_json(_query(sql))


@mcp.tool()
def list_lambda_functions_steampipe(runtime: str = "", region: str = "") -> str:
    """Lambda 함수 목록을 조회합니다.

    Args:
        runtime: 런타임 필터 (python3.12, nodejs20.x 등)
        region: 리전 필터
    """
    conds = []
    if runtime:
        conds.append(f"runtime LIKE '%{runtime}%'")
    if region:
        conds.append(f"region = '{region}'")
    where = " AND ".join(conds) if conds else "1=1"
    sql = f"""SELECT name, runtime, handler, memory_size, timeout,
           last_modified, code_size, region, tags
    FROM aws_lambda_function WHERE {where}"""
    return _to_json(_query(sql))


@mcp.tool()
def list_iam_users_steampipe(mfa_enabled: str = "") -> str:
    """IAM 사용자 목록과 보안 상태를 조회합니다.

    Args:
        mfa_enabled: MFA 필터 (true, false)
    """
    conds = []
    if mfa_enabled:
        conds.append(f"mfa_enabled = {mfa_enabled.lower()}")
    where = " AND ".join(conds) if conds else "1=1"
    sql = f"""SELECT name, user_id, arn, create_date,
           password_last_used, mfa_enabled, tags
    FROM aws_iam_user WHERE {where}"""
    return _to_json(_query(sql))


@mcp.tool()
def list_vpc_resources_steampipe(vpc_id: str = "") -> str:
    """VPC 및 서브넷 정보를 조회합니다.

    Args:
        vpc_id: 특정 VPC ID로 필터링
    """
    cond = f"vpc_id = '{vpc_id}'" if vpc_id else "1=1"
    vpcs = _query(f"SELECT vpc_id, title, cidr_block, state, is_default, region, tags FROM aws_vpc WHERE {cond}")
    subnets = _query(f"SELECT subnet_id, vpc_id, cidr_block, availability_zone, state FROM aws_vpc_subnet WHERE {cond}")
    return _to_json({"vpcs": vpcs.get("data", []), "subnets": subnets.get("data", [])})


@mcp.tool()
def list_security_groups_steampipe(vpc_id: str = "") -> str:
    """보안 그룹 목록을 조회합니다.

    Args:
        vpc_id: VPC ID로 필터링
    """
    cond = f"vpc_id = '{vpc_id}'" if vpc_id else "1=1"
    sql = f"""SELECT group_id, group_name, description, vpc_id,
           ip_permissions, ip_permissions_egress, region, tags
    FROM aws_vpc_security_group WHERE {cond}"""
    return _to_json(_query(sql))


@mcp.tool()
def list_k8s_pods(namespace: str = "", status_phase: str = "") -> str:
    """Kubernetes Pod 목록을 조회합니다.

    Args:
        namespace: 네임스페이스 필터
        status_phase: Pod 상태 필터 (Running, Pending, Failed)
    """
    conds = []
    if namespace:
        conds.append(f"namespace = '{namespace}'")
    if status_phase:
        conds.append(f"phase = '{status_phase}'")
    where = " AND ".join(conds) if conds else "1=1"
    sql = f"""SELECT name, namespace, phase, pod_ip, node_name,
           creation_timestamp, labels
    FROM kubernetes_pod WHERE {where}"""
    return _to_json(_query(sql))


@mcp.tool()
def list_k8s_deployments(namespace: str = "") -> str:
    """Kubernetes Deployment 목록을 조회합니다.

    Args:
        namespace: 네임스페이스 필터
    """
    cond = f"namespace = '{namespace}'" if namespace else "1=1"
    sql = f"""SELECT name, namespace, replicas, ready_replicas,
           available_replicas, creation_timestamp, labels
    FROM kubernetes_deployment WHERE {cond}"""
    return _to_json(_query(sql))


@mcp.tool()
def list_k8s_services(namespace: str = "", service_type: str = "") -> str:
    """Kubernetes Service 목록을 조회합니다.

    Args:
        namespace: 네임스페이스 필터
        service_type: 서비스 유형 필터 (ClusterIP, NodePort, LoadBalancer)
    """
    conds = []
    if namespace:
        conds.append(f"namespace = '{namespace}'")
    if service_type:
        conds.append(f"type = '{service_type}'")
    where = " AND ".join(conds) if conds else "1=1"
    sql = f"""SELECT name, namespace, type, cluster_ip, ports, selector, creation_timestamp
    FROM kubernetes_service WHERE {where}"""
    return _to_json(_query(sql))


@mcp.tool()
def list_k8s_nodes() -> str:
    """Kubernetes 노드 목록 (상태, 용량 정보)을 조회합니다."""
    sql = """SELECT name, pod_cidr, provider_id,
           allocatable, capacity, conditions, creation_timestamp, labels
    FROM kubernetes_node"""
    return _to_json(_query(sql))


@mcp.tool()
def get_k8s_cluster_summary() -> str:
    """Kubernetes 클러스터 자산 요약을 조회합니다."""
    queries = {
        "namespaces": "SELECT COUNT(*) as count FROM kubernetes_namespace",
        "nodes": "SELECT COUNT(*) as count FROM kubernetes_node",
        "pods_total": "SELECT COUNT(*) as count FROM kubernetes_pod",
        "pods_running": "SELECT COUNT(*) as count FROM kubernetes_pod WHERE phase = 'Running'",
        "deployments": "SELECT COUNT(*) as count FROM kubernetes_deployment",
        "services": "SELECT COUNT(*) as count FROM kubernetes_service",
        "daemonsets": "SELECT COUNT(*) as count FROM kubernetes_daemonset",
    }
    summary = {}
    for key, sql in queries.items():
        r = _query(sql)
        summary[key] = r["data"][0]["count"] if r.get("success") and r.get("data") else "error"
    total = sum(v for v in summary.values() if isinstance(v, int))
    return _to_json({"summary": summary, "total_resources": total})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
