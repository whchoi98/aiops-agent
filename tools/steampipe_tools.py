"""Steampipe 기반 AWS + Kubernetes 자산 인벤토리 도구

Steampipe aws / kubernetes 플러그인을 사용하여 SQL 기반으로 리소스를 조회합니다.

연결 방식:
  1. PostgreSQL 서비스 모드 (기본) — AgentCore Runtime 호환
     EC2에서 steampipe service 실행 → psycopg2로 연결
     환경변수: STEAMPIPE_HOST (기본: localhost), STEAMPIPE_PORT (기본: 9193),
               STEAMPIPE_PASSWORD (기본: steampipe_aiops)
  2. subprocess fallback — psycopg2 미설치 또는 서비스 미실행 시
     로컬 steampipe CLI 직접 호출

사전 요건:
  steampipe plugin install aws
  steampipe plugin install kubernetes
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
from decimal import Decimal
from typing import Any

from strands import tool

# ---------------------------------------------------------------------------
# PostgreSQL 연결 설정
# ---------------------------------------------------------------------------

try:
    import psycopg2
    import psycopg2.extras

    _HAS_PSYCOPG2 = True
except ImportError:
    _HAS_PSYCOPG2 = False

_STEAMPIPE_HOST = os.getenv("STEAMPIPE_HOST", "localhost")
_STEAMPIPE_PORT = int(os.getenv("STEAMPIPE_PORT", "9193"))
_STEAMPIPE_DB = os.getenv("STEAMPIPE_DB", "steampipe")
_STEAMPIPE_USER = os.getenv("STEAMPIPE_USER", "steampipe")
_STEAMPIPE_PASSWORD = os.getenv("STEAMPIPE_PASSWORD", "steampipe_aiops")


def _serialize_value(val: Any) -> Any:
    """psycopg2 반환 값을 JSON 직렬화 가능한 타입으로 변환"""
    if isinstance(val, datetime.datetime):
        return val.isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    if isinstance(val, Decimal):
        return int(val) if val == val.to_integral_value() else float(val)
    return val


def _serialize_row(row: dict) -> dict:
    return {k: _serialize_value(v) for k, v in row.items()}


# ---------------------------------------------------------------------------
# 쿼리 실행 엔진
# ---------------------------------------------------------------------------


def _run_steampipe_query_pg(query: str) -> dict[str, Any]:
    """PostgreSQL 프로토콜로 Steampipe 서비스에 쿼리 (AgentCore Runtime 호환)"""
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
                cur.execute(query)
                if cur.description:
                    rows = [_serialize_row(dict(row)) for row in cur.fetchall()]
                    return {
                        "success": True,
                        "data": rows,
                        "count": len(rows),
                        "query": query,
                    }
                return {"success": True, "data": [], "count": 0, "query": query}
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "error": str(e), "query": query}


def _run_steampipe_query_subprocess(
    query: str, output_format: str = "json",
) -> dict[str, Any]:
    """subprocess로 Steampipe CLI 직접 호출 (로컬 fallback)"""
    try:
        result = subprocess.run(
            ["steampipe", "query", query, "--output", output_format],
            capture_output=True,
            text=True,
            timeout=120,
            env={
                **os.environ,
                "AWS_PROFILE": os.getenv("AWS_PROFILE", "default"),
                "AWS_REGION": os.getenv("AWS_REGION", "ap-northeast-2"),
            },
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr, "query": query}

        if output_format == "json":
            data = json.loads(result.stdout) if result.stdout.strip() else []
            return {
                "success": True,
                "data": data,
                "count": len(data) if isinstance(data, list) else 1,
                "query": query,
            }

        return {"success": True, "data": result.stdout, "query": query}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Query timeout (120s exceeded)", "query": query}
    except FileNotFoundError:
        return {
            "success": False,
            "error": (
                "Steampipe not installed. Run: "
                "sudo /bin/sh -c \"$(curl -fsSL https://steampipe.io/install/steampipe.sh)\" && "
                "steampipe plugin install aws kubernetes"
            ),
            "query": query,
        }
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {e}", "query": query}


def _run_steampipe_query(query: str, output_format: str = "json") -> dict[str, Any]:
    """Steampipe 쿼리 실행 — PostgreSQL 서비스 우선, subprocess fallback"""
    if _HAS_PSYCOPG2:
        result = _run_steampipe_query_pg(query)
        if result.get("success"):
            return result
        # PG 연결 실패 시 subprocess fallback (로컬 환경)
        err = str(result.get("error", "")).lower()
        if "could not connect" in err or "connection refused" in err:
            return _run_steampipe_query_subprocess(query, output_format)
        return result
    return _run_steampipe_query_subprocess(query, output_format)


# ---------------------------------------------------------------------------
# 범용 쿼리 도구
# ---------------------------------------------------------------------------

@tool
def run_steampipe_query(query: str) -> dict[str, Any]:
    """Steampipe SQL 쿼리를 실행하여 AWS 또는 Kubernetes 자산을 조회합니다.

    Args:
        query: Steampipe SQL 쿼리
               AWS 예시: SELECT * FROM aws_ec2_instance LIMIT 10
               K8s 예시: SELECT * FROM kubernetes_pod WHERE namespace = 'default'

    Returns:
        쿼리 결과
    """
    return _run_steampipe_query(query)


@tool
def query_inventory(
    resource_type: str,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """AWS 또는 Kubernetes 자산 인벤토리를 유형별로 조회합니다.

    Args:
        resource_type: 리소스 유형
                       AWS: ec2, s3, rds, lambda, iam_user, vpc, security_group,
                            ebs, eks, ecs, dynamodb, sqs, sns 등
                       K8s: pod, deployment, service, namespace, node,
                            configmap, secret, ingress, daemonset, statefulset,
                            job, cronjob, pv, pvc, serviceaccount 등
        filters: 필터 조건 (예: {"instance_state": "running"}, {"namespace": "default"})
        limit: 결과 최대 개수

    Returns:
        자산 목록
    """
    table_mapping = {
        # ── AWS ──
        "ec2": "aws_ec2_instance",
        "s3": "aws_s3_bucket",
        "rds": "aws_rds_db_instance",
        "lambda": "aws_lambda_function",
        "iam_user": "aws_iam_user",
        "iam_role": "aws_iam_role",
        "vpc": "aws_vpc",
        "subnet": "aws_vpc_subnet",
        "security_group": "aws_vpc_security_group",
        "ebs": "aws_ebs_volume",
        "elb": "aws_ec2_load_balancer_listener",
        "alb": "aws_ec2_application_load_balancer",
        "eks": "aws_eks_cluster",
        "ecs": "aws_ecs_cluster",
        "cloudfront": "aws_cloudfront_distribution",
        "route53": "aws_route53_zone",
        "dynamodb": "aws_dynamodb_table",
        "sqs": "aws_sqs_queue",
        "sns": "aws_sns_topic",
        "kms": "aws_kms_key",
        "secretsmanager": "aws_secretsmanager_secret",
        # ── Kubernetes ──
        "pod": "kubernetes_pod",
        "deployment": "kubernetes_deployment",
        "service": "kubernetes_service",
        "namespace": "kubernetes_namespace",
        "node": "kubernetes_node",
        "configmap": "kubernetes_config_map",
        "secret": "kubernetes_secret",
        "ingress": "kubernetes_ingress",
        "daemonset": "kubernetes_daemonset",
        "statefulset": "kubernetes_stateful_set",
        "replicaset": "kubernetes_replicaset",
        "job": "kubernetes_job",
        "cronjob": "kubernetes_cronjob",
        "pv": "kubernetes_persistent_volume",
        "pvc": "kubernetes_persistent_volume_claim",
        "serviceaccount": "kubernetes_service_account",
        "networkpolicy": "kubernetes_network_policy",
        "role": "kubernetes_role",
        "clusterrole": "kubernetes_cluster_role",
        "hpa": "kubernetes_horizontal_pod_autoscaler",
    }

    table = table_mapping.get(resource_type.lower())
    if not table:
        return {
            "success": False,
            "error": (
                f"Unknown resource type: {resource_type}. "
                f"Available: {list(table_mapping.keys())}"
            ),
        }

    where_clauses = []
    if filters:
        for key, value in filters.items():
            if isinstance(value, str):
                where_clauses.append(f"{key} = '{value}'")
            elif isinstance(value, bool):
                where_clauses.append(f"{key} = {str(value).lower()}")
            elif isinstance(value, (int, float)):
                where_clauses.append(f"{key} = {value}")
            elif isinstance(value, list):
                values = ", ".join(f"'{v}'" for v in value)
                where_clauses.append(f"{key} IN ({values})")

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT {limit}"

    return _run_steampipe_query(query)


@tool
def get_asset_summary() -> dict[str, Any]:
    """전체 AWS + Kubernetes 자산 요약을 Steampipe로 조회합니다.

    Returns:
        리소스 유형별 개수 및 요약 정보 (AWS 12종 + K8s 6종)
    """
    queries = {
        # ── AWS ──
        "ec2_instances": "SELECT COUNT(*) as count FROM aws_ec2_instance",
        "ec2_running": (
            "SELECT COUNT(*) as count FROM aws_ec2_instance "
            "WHERE instance_state = 'running'"
        ),
        "s3_buckets": "SELECT COUNT(*) as count FROM aws_s3_bucket",
        "rds_instances": "SELECT COUNT(*) as count FROM aws_rds_db_instance",
        "lambda_functions": "SELECT COUNT(*) as count FROM aws_lambda_function",
        "vpcs": "SELECT COUNT(*) as count FROM aws_vpc",
        "security_groups": "SELECT COUNT(*) as count FROM aws_vpc_security_group",
        "iam_users": "SELECT COUNT(*) as count FROM aws_iam_user",
        "iam_roles": "SELECT COUNT(*) as count FROM aws_iam_role",
        "eks_clusters": "SELECT COUNT(*) as count FROM aws_eks_cluster",
        "ecs_clusters": "SELECT COUNT(*) as count FROM aws_ecs_cluster",
        "ebs_volumes": "SELECT COUNT(*) as count FROM aws_ebs_volume",
        # ── Kubernetes ──
        "k8s_namespaces": "SELECT COUNT(*) as count FROM kubernetes_namespace",
        "k8s_nodes": "SELECT COUNT(*) as count FROM kubernetes_node",
        "k8s_pods": "SELECT COUNT(*) as count FROM kubernetes_pod",
        "k8s_deployments": "SELECT COUNT(*) as count FROM kubernetes_deployment",
        "k8s_services": "SELECT COUNT(*) as count FROM kubernetes_service",
        "k8s_daemonsets": "SELECT COUNT(*) as count FROM kubernetes_daemonset",
    }

    summary: dict[str, Any] = {}
    errors = []

    for resource, query in queries.items():
        result = _run_steampipe_query(query)
        if result.get("success"):
            data = result.get("data", [])
            summary[resource] = data[0].get("count", 0) if data else 0
        else:
            errors.append(f"{resource}: {result.get('error')}")
            summary[resource] = "error"

    return {
        "success": len(errors) == 0,
        "summary": summary,
        "total_resources": sum(v for v in summary.values() if isinstance(v, int)),
        "errors": errors if errors else None,
    }


# ---------------------------------------------------------------------------
# 리소스별 조회 도구
# ---------------------------------------------------------------------------

@tool
def list_ec2_instances_steampipe(
    state: str | None = None,
    instance_type: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """EC2 인스턴스 목록을 Steampipe SQL로 조회합니다.

    Args:
        state: 인스턴스 상태 필터 (running, stopped, terminated)
        instance_type: 인스턴스 유형 필터 (t3.micro, m5.large 등)
        region: 리전 필터

    Returns:
        EC2 인스턴스 목록
    """
    conditions = []
    if state:
        conditions.append(f"instance_state = '{state}'")
    if instance_type:
        conditions.append(f"instance_type = '{instance_type}'")
    if region:
        conditions.append(f"region = '{region}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT instance_id, title, instance_type, instance_state,
           public_ip_address, private_ip_address, vpc_id, subnet_id,
           launch_time, region, tags
    FROM aws_ec2_instance
    WHERE {where_clause}
    ORDER BY launch_time DESC
    """
    return _run_steampipe_query(query)


@tool
def list_s3_buckets_steampipe(
    public_access: bool | None = None,
) -> dict[str, Any]:
    """S3 버킷 목록을 Steampipe SQL로 조회합니다.

    Args:
        public_access: 퍼블릭 액세스 여부 필터

    Returns:
        S3 버킷 목록과 보안 상태
    """
    query = """
    SELECT name, region, creation_date, bucket_policy_is_public,
           block_public_acls, block_public_policy, versioning_enabled,
           server_side_encryption_configuration, tags
    FROM aws_s3_bucket
    ORDER BY creation_date DESC
    """
    result = _run_steampipe_query(query)

    if result.get("success") and public_access is not None:
        result["data"] = [
            b for b in result.get("data", [])
            if b.get("bucket_policy_is_public") == public_access
        ]
        result["count"] = len(result["data"])

    return result


@tool
def list_rds_instances_steampipe(
    engine: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """RDS 인스턴스 목록을 Steampipe SQL로 조회합니다.

    Args:
        engine: 데이터베이스 엔진 필터 (mysql, postgres, aurora 등)
        status: 상태 필터 (available, stopped 등)

    Returns:
        RDS 인스턴스 목록
    """
    conditions = []
    if engine:
        conditions.append(f"engine LIKE '%{engine}%'")
    if status:
        conditions.append(f"status = '{status}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT db_instance_identifier, db_instance_class, engine, engine_version,
           status, endpoint_address, endpoint_port, multi_az,
           storage_encrypted, publicly_accessible, vpc_id, region, tags
    FROM aws_rds_db_instance
    WHERE {where_clause}
    ORDER BY create_time DESC
    """
    return _run_steampipe_query(query)


@tool
def list_lambda_functions_steampipe(
    runtime: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Lambda 함수 목록을 Steampipe SQL로 조회합니다.

    Args:
        runtime: 런타임 필터 (python3.11, nodejs18.x 등)
        region: 리전 필터

    Returns:
        Lambda 함수 목록
    """
    conditions = []
    if runtime:
        conditions.append(f"runtime LIKE '%{runtime}%'")
    if region:
        conditions.append(f"region = '{region}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT name, runtime, handler, memory_size, timeout,
           last_modified, code_size, vpc_id, region, tags
    FROM aws_lambda_function
    WHERE {where_clause}
    ORDER BY last_modified DESC
    """
    return _run_steampipe_query(query)


@tool
def list_iam_users_steampipe(
    mfa_enabled: bool | None = None,
) -> dict[str, Any]:
    """IAM 사용자 목록을 Steampipe SQL로 조회합니다.

    Args:
        mfa_enabled: MFA 활성화 여부 필터

    Returns:
        IAM 사용자 목록과 보안 상태
    """
    conditions = []
    if mfa_enabled is not None:
        conditions.append(f"mfa_enabled = {str(mfa_enabled).lower()}")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT name, user_id, arn, create_date,
           password_last_used, mfa_enabled, tags
    FROM aws_iam_user
    WHERE {where_clause}
    ORDER BY create_date DESC
    """
    return _run_steampipe_query(query)


@tool
def list_vpc_resources_steampipe(vpc_id: str | None = None) -> dict[str, Any]:
    """VPC 및 관련 리소스를 Steampipe SQL로 조회합니다.

    Args:
        vpc_id: 특정 VPC ID로 필터링

    Returns:
        VPC, 서브넷 정보
    """
    vpc_condition = f"vpc_id = '{vpc_id}'" if vpc_id else "1=1"

    vpc_query = f"""
    SELECT vpc_id, title, cidr_block, state, is_default, region, tags
    FROM aws_vpc
    WHERE {vpc_condition if vpc_id else '1=1'}
    """

    subnet_query = f"""
    SELECT subnet_id, title, vpc_id, cidr_block, availability_zone,
           available_ip_address_count, map_public_ip_on_launch, state
    FROM aws_vpc_subnet
    WHERE {vpc_condition}
    """

    vpcs = _run_steampipe_query(vpc_query)
    subnets = _run_steampipe_query(subnet_query)

    return {
        "success": vpcs.get("success") and subnets.get("success"),
        "vpcs": vpcs.get("data", []),
        "subnets": subnets.get("data", []),
        "vpc_count": vpcs.get("count", 0),
        "subnet_count": subnets.get("count", 0),
    }


@tool
def list_security_groups_steampipe(
    vpc_id: str | None = None,
    open_to_internet: bool | None = None,
) -> dict[str, Any]:
    """보안 그룹 목록을 Steampipe SQL로 조회합니다.

    Args:
        vpc_id: VPC ID로 필터링
        open_to_internet: 인터넷에 개방된 그룹만 조회

    Returns:
        보안 그룹 목록과 규칙 정보
    """
    conditions = []
    if vpc_id:
        conditions.append(f"vpc_id = '{vpc_id}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT group_id, group_name, description, vpc_id,
           ip_permissions, ip_permissions_egress, region, tags
    FROM aws_vpc_security_group
    WHERE {where_clause}
    """
    result = _run_steampipe_query(query)

    if result.get("success") and open_to_internet is not None:
        filtered = []
        for sg in result.get("data", []):
            has_open_rule = False
            for rule in sg.get("ip_permissions", []) or []:
                for ip_range in rule.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        has_open_rule = True
                        break
            if has_open_rule == open_to_internet:
                filtered.append(sg)
        result["data"] = filtered
        result["count"] = len(filtered)

    return result


# ---------------------------------------------------------------------------
# Kubernetes 리소스 조회 도구
# ---------------------------------------------------------------------------

@tool
def list_k8s_pods(
    namespace: str | None = None,
    status_phase: str | None = None,
) -> dict[str, Any]:
    """Kubernetes Pod 목록을 Steampipe SQL로 조회합니다.

    Args:
        namespace: 네임스페이스 필터 (default, kube-system 등)
        status_phase: Pod 상태 필터 (Running, Pending, Failed, Succeeded)

    Returns:
        Pod 목록
    """
    conditions = []
    if namespace:
        conditions.append(f"namespace = '{namespace}'")
    if status_phase:
        conditions.append(f"phase = '{status_phase}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT name, namespace, phase, pod_ip, node_name,
           creation_timestamp, restart_count, labels
    FROM kubernetes_pod
    WHERE {where_clause}
    ORDER BY creation_timestamp DESC
    """
    return _run_steampipe_query(query)


@tool
def list_k8s_deployments(
    namespace: str | None = None,
) -> dict[str, Any]:
    """Kubernetes Deployment 목록을 Steampipe SQL로 조회합니다.

    Args:
        namespace: 네임스페이스 필터

    Returns:
        Deployment 목록 (레플리카 상태 포함)
    """
    conditions = []
    if namespace:
        conditions.append(f"namespace = '{namespace}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT name, namespace, replicas, ready_replicas,
           available_replicas, unavailable_replicas,
           creation_timestamp, labels
    FROM kubernetes_deployment
    WHERE {where_clause}
    ORDER BY creation_timestamp DESC
    """
    return _run_steampipe_query(query)


@tool
def list_k8s_services(
    namespace: str | None = None,
    service_type: str | None = None,
) -> dict[str, Any]:
    """Kubernetes Service 목록을 Steampipe SQL로 조회합니다.

    Args:
        namespace: 네임스페이스 필터
        service_type: 서비스 유형 필터 (ClusterIP, NodePort, LoadBalancer)

    Returns:
        Service 목록
    """
    conditions = []
    if namespace:
        conditions.append(f"namespace = '{namespace}'")
    if service_type:
        conditions.append(f"type = '{service_type}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT name, namespace, type, cluster_ip,
           external_ips, ports, selector, creation_timestamp
    FROM kubernetes_service
    WHERE {where_clause}
    ORDER BY creation_timestamp DESC
    """
    return _run_steampipe_query(query)


@tool
def list_k8s_nodes() -> dict[str, Any]:
    """Kubernetes 노드 목록을 Steampipe SQL로 조회합니다.

    Returns:
        노드 목록 (상태, 용량 정보 포함)
    """
    query = """
    SELECT name, uid, pod_cidr, provider_id,
           allocatable, capacity, conditions,
           creation_timestamp, labels
    FROM kubernetes_node
    ORDER BY creation_timestamp DESC
    """
    return _run_steampipe_query(query)


@tool
def get_k8s_cluster_summary() -> dict[str, Any]:
    """Kubernetes 클러스터 자산 요약을 조회합니다.

    Returns:
        네임스페이스, 노드, Pod, Deployment, Service, DaemonSet 개수 요약
    """
    queries = {
        "namespaces": "SELECT COUNT(*) as count FROM kubernetes_namespace",
        "nodes": "SELECT COUNT(*) as count FROM kubernetes_node",
        "pods_total": "SELECT COUNT(*) as count FROM kubernetes_pod",
        "pods_running": (
            "SELECT COUNT(*) as count FROM kubernetes_pod "
            "WHERE phase = 'Running'"
        ),
        "deployments": "SELECT COUNT(*) as count FROM kubernetes_deployment",
        "services": "SELECT COUNT(*) as count FROM kubernetes_service",
        "daemonsets": "SELECT COUNT(*) as count FROM kubernetes_daemonset",
        "statefulsets": "SELECT COUNT(*) as count FROM kubernetes_stateful_set",
        "jobs": "SELECT COUNT(*) as count FROM kubernetes_job",
        "cronjobs": "SELECT COUNT(*) as count FROM kubernetes_cronjob",
    }

    summary: dict[str, Any] = {}
    errors = []

    for resource, query in queries.items():
        result = _run_steampipe_query(query)
        if result.get("success"):
            data = result.get("data", [])
            summary[resource] = data[0].get("count", 0) if data else 0
        else:
            errors.append(f"{resource}: {result.get('error')}")
            summary[resource] = "error"

    return {
        "success": len(errors) == 0,
        "summary": summary,
        "total_resources": sum(v for v in summary.values() if isinstance(v, int)),
        "errors": errors if errors else None,
    }
