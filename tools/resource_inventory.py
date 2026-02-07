"""리소스 인벤토리 도구 — boto3 기반 AWS 자산 요약"""
from __future__ import annotations

import os
from typing import Any

import boto3
from strands import tool


def _get_region() -> str:
    return os.getenv("AWS_REGION", "ap-northeast-2")


def _safe_count(fn) -> int | str:
    """API 호출을 시도하고 리소스 개수를 반환합니다. 실패 시 'error'."""
    try:
        return fn()
    except Exception:
        return "error"


@tool
def get_resource_summary() -> dict[str, Any]:
    """전체 AWS 자산 요약을 조회합니다.

    Returns:
        리소스 유형별 개수 및 요약 정보
    """
    region = _get_region()

    ec2 = boto3.client("ec2", region_name=region)
    s3 = boto3.client("s3", region_name=region)
    rds = boto3.client("rds", region_name=region)
    lam = boto3.client("lambda", region_name=region)
    iam = boto3.client("iam")

    def count_ec2_all():
        count = 0
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for res in page.get("Reservations", []):
                count += len(res.get("Instances", []))
        return count

    def count_ec2_running():
        count = 0
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        ):
            for res in page.get("Reservations", []):
                count += len(res.get("Instances", []))
        return count

    def count_s3():
        return len(s3.list_buckets().get("Buckets", []))

    def count_rds():
        return len(rds.describe_db_instances().get("DBInstances", []))

    def count_lambda():
        count = 0
        paginator = lam.get_paginator("list_functions")
        for page in paginator.paginate():
            count += len(page.get("Functions", []))
        return count

    def count_vpcs():
        return len(ec2.describe_vpcs().get("Vpcs", []))

    def count_security_groups():
        return len(ec2.describe_security_groups().get("SecurityGroups", []))

    def count_ebs():
        count = 0
        paginator = ec2.get_paginator("describe_volumes")
        for page in paginator.paginate():
            count += len(page.get("Volumes", []))
        return count

    def count_iam_users():
        return len(iam.list_users().get("Users", []))

    def count_iam_roles():
        return len(iam.list_roles().get("Roles", []))

    summary = {
        "ec2_instances": _safe_count(count_ec2_all),
        "ec2_running": _safe_count(count_ec2_running),
        "s3_buckets": _safe_count(count_s3),
        "rds_instances": _safe_count(count_rds),
        "lambda_functions": _safe_count(count_lambda),
        "vpcs": _safe_count(count_vpcs),
        "security_groups": _safe_count(count_security_groups),
        "ebs_volumes": _safe_count(count_ebs),
        "iam_users": _safe_count(count_iam_users),
        "iam_roles": _safe_count(count_iam_roles),
    }

    total = sum(v for v in summary.values() if isinstance(v, int))
    errors = [k for k, v in summary.items() if v == "error"]

    return {
        "region": region,
        "summary": summary,
        "total_resources": total,
        "errors": errors if errors else None,
    }


@tool
def list_resources_by_type(
    resource_type: str,
    limit: int = 100,
) -> dict[str, Any]:
    """지정된 유형의 AWS 리소스 목록을 조회합니다.

    Args:
        resource_type: 리소스 유형 (ec2, s3, rds, lambda, vpc, security_group, ebs)
        limit: 최대 결과 수 (기본값: 100)

    Returns:
        리소스 목록
    """
    region = _get_region()

    try:
        if resource_type == "ec2":
            ec2 = boto3.client("ec2", region_name=region)
            instances = []
            paginator = ec2.get_paginator("describe_instances")
            for page in paginator.paginate():
                for res in page.get("Reservations", []):
                    for inst in res.get("Instances", []):
                        name = next(
                            (
                                t["Value"]
                                for t in inst.get("Tags", [])
                                if t["Key"] == "Name"
                            ),
                            "N/A",
                        )
                        instances.append({
                            "id": inst["InstanceId"],
                            "name": name,
                            "type": inst["InstanceType"],
                            "state": inst["State"]["Name"],
                        })
                        if len(instances) >= limit:
                            break
                    if len(instances) >= limit:
                        break
                if len(instances) >= limit:
                    break
            return {"resource_type": "ec2", "count": len(instances), "resources": instances}

        elif resource_type == "s3":
            s3 = boto3.client("s3", region_name=region)
            buckets = [
                {
                    "name": b["Name"],
                    "created": b["CreationDate"].isoformat() if b.get("CreationDate") else None,
                }
                for b in s3.list_buckets().get("Buckets", [])[:limit]
            ]
            return {"resource_type": "s3", "count": len(buckets), "resources": buckets}

        elif resource_type == "rds":
            rds = boto3.client("rds", region_name=region)
            dbs = [
                {
                    "id": db["DBInstanceIdentifier"],
                    "engine": db["Engine"],
                    "class": db["DBInstanceClass"],
                    "status": db["DBInstanceStatus"],
                }
                for db in rds.describe_db_instances().get("DBInstances", [])[:limit]
            ]
            return {"resource_type": "rds", "count": len(dbs), "resources": dbs}

        elif resource_type == "lambda":
            lam = boto3.client("lambda", region_name=region)
            functions = []
            paginator = lam.get_paginator("list_functions")
            for page in paginator.paginate():
                for fn in page.get("Functions", []):
                    functions.append({
                        "name": fn["FunctionName"],
                        "runtime": fn.get("Runtime"),
                        "memory": fn.get("MemorySize"),
                    })
                    if len(functions) >= limit:
                        break
                if len(functions) >= limit:
                    break
            return {"resource_type": "lambda", "count": len(functions), "resources": functions}

        elif resource_type == "vpc":
            ec2 = boto3.client("ec2", region_name=region)
            vpcs = [
                {
                    "id": v["VpcId"],
                    "cidr": v["CidrBlock"],
                    "state": v["State"],
                    "is_default": v.get("IsDefault", False),
                }
                for v in ec2.describe_vpcs().get("Vpcs", [])[:limit]
            ]
            return {"resource_type": "vpc", "count": len(vpcs), "resources": vpcs}

        elif resource_type == "security_group":
            ec2 = boto3.client("ec2", region_name=region)
            sgs = [
                {
                    "id": sg["GroupId"],
                    "name": sg["GroupName"],
                    "vpc_id": sg.get("VpcId"),
                }
                for sg in ec2.describe_security_groups().get("SecurityGroups", [])[:limit]
            ]
            return {"resource_type": "security_group", "count": len(sgs), "resources": sgs}

        elif resource_type == "ebs":
            ec2 = boto3.client("ec2", region_name=region)
            volumes = []
            paginator = ec2.get_paginator("describe_volumes")
            for page in paginator.paginate():
                for v in page.get("Volumes", []):
                    volumes.append({
                        "id": v["VolumeId"],
                        "size_gb": v["Size"],
                        "type": v["VolumeType"],
                        "state": v["State"],
                    })
                    if len(volumes) >= limit:
                        break
                if len(volumes) >= limit:
                    break
            return {"resource_type": "ebs", "count": len(volumes), "resources": volumes}

        else:
            return {
                "error": f"Unknown resource type: {resource_type}. "
                "Available: ec2, s3, rds, lambda, vpc, security_group, ebs"
            }

    except Exception as e:
        return {"resource_type": resource_type, "error": str(e)}
