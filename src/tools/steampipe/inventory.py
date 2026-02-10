"""Steampipe 기반 AWS 자산 인벤토리 도구"""

import json
import os
import subprocess
from typing import Any

from strands import tool


def _run_steampipe_query(query: str, output_format: str = "json") -> dict[str, Any]:
    """Steampipe 쿼리 실행

    Args:
        query: SQL 쿼리
        output_format: 출력 형식 (json, csv, table)

    Returns:
        쿼리 결과
    """
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
            return {
                "success": False,
                "error": result.stderr,
                "query": query,
            }

        if output_format == "json":
            data = json.loads(result.stdout) if result.stdout.strip() else []
            return {
                "success": True,
                "data": data,
                "count": len(data) if isinstance(data, list) else 1,
                "query": query,
            }

        return {
            "success": True,
            "data": result.stdout,
            "query": query,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Query timeout (120s exceeded)",
            "query": query,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "Steampipe not installed. Run: brew install turbot/tap/steampipe && steampipe plugin install aws",
            "query": query,
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON parse error: {e}",
            "query": query,
        }


@tool
def run_steampipe_query(query: str) -> dict[str, Any]:
    """Steampipe SQL 쿼리를 실행하여 AWS 자산을 조회합니다.

    Args:
        query: Steampipe SQL 쿼리 (예: SELECT * FROM aws_ec2_instance LIMIT 10)

    Returns:
        쿼리 결과

    Example queries:
        - SELECT * FROM aws_ec2_instance WHERE instance_state = 'running'
        - SELECT * FROM aws_s3_bucket
        - SELECT * FROM aws_iam_user WHERE mfa_enabled = false
    """
    return _run_steampipe_query(query)


@tool
def query_aws_inventory(
    resource_type: str,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """AWS 자산 인벤토리를 조회합니다.

    Args:
        resource_type: 리소스 유형 (ec2, s3, rds, lambda, iam_user, vpc, security_group)
        filters: 필터 조건 (예: {"instance_state": "running"})
        limit: 결과 최대 개수

    Returns:
        자산 목록
    """
    table_mapping = {
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
    }

    table = table_mapping.get(resource_type.lower())
    if not table:
        return {
            "success": False,
            "error": f"Unknown resource type: {resource_type}. Available: {list(table_mapping.keys())}",
        }

    # WHERE 절 구성
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
def list_ec2_instances(
    state: str | None = None,
    instance_type: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """EC2 인스턴스 목록을 조회합니다.

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
    SELECT
        instance_id,
        title,
        instance_type,
        instance_state,
        public_ip_address,
        private_ip_address,
        vpc_id,
        subnet_id,
        launch_time,
        region,
        tags
    FROM aws_ec2_instance
    WHERE {where_clause}
    ORDER BY launch_time DESC
    """

    return _run_steampipe_query(query)


@tool
def list_s3_buckets(
    public_access: bool | None = None,
    encryption: bool | None = None,
) -> dict[str, Any]:
    """S3 버킷 목록을 조회합니다.

    Args:
        public_access: 퍼블릭 액세스 여부 필터
        encryption: 암호화 활성화 여부 필터

    Returns:
        S3 버킷 목록과 보안 상태
    """
    query = """
    SELECT
        name,
        region,
        creation_date,
        bucket_policy_is_public,
        block_public_acls,
        block_public_policy,
        versioning_enabled,
        server_side_encryption_configuration,
        tags
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
def list_rds_instances(
    engine: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """RDS 인스턴스 목록을 조회합니다.

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
    SELECT
        db_instance_identifier,
        db_instance_class,
        engine,
        engine_version,
        status,
        endpoint_address,
        endpoint_port,
        multi_az,
        storage_encrypted,
        publicly_accessible,
        vpc_id,
        region,
        tags
    FROM aws_rds_db_instance
    WHERE {where_clause}
    ORDER BY create_time DESC
    """

    return _run_steampipe_query(query)


@tool
def list_lambda_functions(
    runtime: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Lambda 함수 목록을 조회합니다.

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
    SELECT
        name,
        runtime,
        handler,
        memory_size,
        timeout,
        last_modified,
        code_size,
        vpc_id,
        region,
        tags
    FROM aws_lambda_function
    WHERE {where_clause}
    ORDER BY last_modified DESC
    """

    return _run_steampipe_query(query)


@tool
def list_iam_users(
    mfa_enabled: bool | None = None,
    has_console_access: bool | None = None,
) -> dict[str, Any]:
    """IAM 사용자 목록을 조회합니다.

    Args:
        mfa_enabled: MFA 활성화 여부 필터
        has_console_access: 콘솔 액세스 여부 필터

    Returns:
        IAM 사용자 목록과 보안 상태
    """
    conditions = []
    if mfa_enabled is not None:
        conditions.append(f"mfa_enabled = {str(mfa_enabled).lower()}")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT
        name,
        user_id,
        arn,
        create_date,
        password_last_used,
        mfa_enabled,
        tags
    FROM aws_iam_user
    WHERE {where_clause}
    ORDER BY create_date DESC
    """

    return _run_steampipe_query(query)


@tool
def list_vpc_resources(vpc_id: str | None = None) -> dict[str, Any]:
    """VPC 및 관련 리소스를 조회합니다.

    Args:
        vpc_id: 특정 VPC ID로 필터링

    Returns:
        VPC, 서브넷, 라우트 테이블 정보
    """
    vpc_condition = f"vpc_id = '{vpc_id}'" if vpc_id else "1=1"

    vpc_query = f"""
    SELECT
        vpc_id,
        title,
        cidr_block,
        state,
        is_default,
        region,
        tags
    FROM aws_vpc
    WHERE {vpc_condition if vpc_id else '1=1'}
    """

    subnet_query = f"""
    SELECT
        subnet_id,
        title,
        vpc_id,
        cidr_block,
        availability_zone,
        available_ip_address_count,
        map_public_ip_on_launch,
        state
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
def list_security_groups(
    vpc_id: str | None = None,
    open_to_internet: bool | None = None,
) -> dict[str, Any]:
    """보안 그룹 목록을 조회합니다.

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
    SELECT
        group_id,
        group_name,
        description,
        vpc_id,
        ip_permissions,
        ip_permissions_egress,
        region,
        tags
    FROM aws_vpc_security_group
    WHERE {where_clause}
    """

    result = _run_steampipe_query(query)

    # 인터넷에 개방된 그룹 필터링
    if result.get("success") and open_to_internet is not None:
        filtered = []
        for sg in result.get("data", []):
            has_open_rule = False
            for rule in sg.get("ip_permissions", []) or []:
                ip_ranges = rule.get("IpRanges", [])
                for ip_range in ip_ranges:
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        has_open_rule = True
                        break

            if has_open_rule == open_to_internet:
                filtered.append(sg)

        result["data"] = filtered
        result["count"] = len(filtered)

    return result


@tool
def get_asset_summary() -> dict[str, Any]:
    """전체 AWS 자산 요약을 조회합니다.

    Returns:
        리소스 유형별 개수 및 요약 정보
    """
    queries = {
        "ec2_instances": "SELECT COUNT(*) as count FROM aws_ec2_instance",
        "ec2_running": "SELECT COUNT(*) as count FROM aws_ec2_instance WHERE instance_state = 'running'",
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
    }

    summary = {}
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
