"""보안 도구 — Security Hub / GuardDuty / IAM"""
from __future__ import annotations

import os
from typing import Any

import boto3
from strands import tool


def _get_region() -> str:
    return os.getenv("AWS_REGION", "ap-northeast-2")


@tool
def get_security_findings(
    severity: str | None = None,
    status: str = "ACTIVE",
    max_results: int = 50,
) -> dict[str, Any]:
    """AWS Security Hub 보안 발견 사항을 조회합니다.

    Args:
        severity: 심각도 필터 (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL)
        status: 상태 필터 (ACTIVE, ARCHIVED, RESOLVED, 기본값: ACTIVE)
        max_results: 최대 결과 수 (기본값: 50)

    Returns:
        보안 발견 사항 목록
    """
    client = boto3.client("securityhub", region_name=_get_region())

    filters: dict[str, Any] = {
        "WorkflowStatus": [{"Value": status, "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
    }
    if severity:
        filters["SeverityLabel"] = [
            {"Value": severity.upper(), "Comparison": "EQUALS"}
        ]

    try:
        response = client.get_findings(
            Filters=filters,
            MaxResults=min(max_results, 100),
            SortCriteria=[
                {"Field": "SeverityLabel", "SortOrder": "desc"},
            ],
        )

        findings = []
        for f in response.get("Findings", []):
            findings.append({
                "id": f.get("Id"),
                "title": f.get("Title"),
                "description": f.get("Description", "")[:200],
                "severity": f.get("Severity", {}).get("Label"),
                "status": f.get("Workflow", {}).get("Status"),
                "resource_type": (
                    f["Resources"][0].get("Type") if f.get("Resources") else None
                ),
                "resource_id": (
                    f["Resources"][0].get("Id") if f.get("Resources") else None
                ),
                "compliance_status": f.get("Compliance", {}).get("Status"),
                "created_at": f.get("CreatedAt"),
                "updated_at": f.get("UpdatedAt"),
            })

        severity_counts: dict[str, int] = {}
        for finding in findings:
            sev = finding.get("severity", "UNKNOWN")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "total_count": len(findings),
            "severity_counts": severity_counts,
            "findings": findings,
        }
    except client.exceptions.InvalidAccessException:
        return {"error": "Security Hub is not enabled in this region"}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_guardduty_findings(
    severity: str | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """AWS GuardDuty 위협 탐지 결과를 조회합니다.

    Args:
        severity: 심각도 필터 (HIGH, MEDIUM, LOW)
        max_results: 최대 결과 수 (기본값: 50)

    Returns:
        GuardDuty 발견 사항 목록
    """
    region = _get_region()
    client = boto3.client("guardduty", region_name=region)

    try:
        detectors = client.list_detectors()
        detector_ids = detectors.get("DetectorIds", [])
        if not detector_ids:
            return {"error": "No GuardDuty detector found in this region"}

        detector_id = detector_ids[0]

        finding_criteria: dict[str, Any] = {}
        if severity:
            severity_map = {"LOW": (1.0, 3.9), "MEDIUM": (4.0, 6.9), "HIGH": (7.0, 10.0)}
            sev_range = severity_map.get(severity.upper())
            if sev_range:
                finding_criteria["Criterion"] = {
                    "severity": {
                        "Gte": sev_range[0],
                        "Lte": sev_range[1],
                    }
                }

        list_params: dict[str, Any] = {
            "DetectorId": detector_id,
            "MaxResults": min(max_results, 50),
            "SortCriteria": {"AttributeName": "severity", "OrderBy": "DESC"},
        }
        if finding_criteria:
            list_params["FindingCriteria"] = finding_criteria

        response = client.list_findings(**list_params)
        finding_ids = response.get("FindingIds", [])

        if not finding_ids:
            return {"total_count": 0, "findings": []}

        detail_response = client.get_findings(
            DetectorId=detector_id,
            FindingIds=finding_ids,
        )

        findings = []
        for f in detail_response.get("Findings", []):
            resource = f.get("Resource", {})
            findings.append({
                "id": f.get("Id"),
                "type": f.get("Type"),
                "title": f.get("Title"),
                "description": f.get("Description", "")[:200],
                "severity": f.get("Severity", {}).get("Label"),
                "severity_score": f.get("Severity", {}).get("Normalized"),
                "resource_type": resource.get("ResourceType"),
                "resource_id": (
                    resource.get("InstanceDetails", {}).get("InstanceId")
                    or resource.get("AccessKeyDetails", {}).get("AccessKeyId")
                ),
                "region": f.get("Region"),
                "created_at": f.get("CreatedAt"),
                "updated_at": f.get("UpdatedAt"),
            })

        return {"total_count": len(findings), "findings": findings}

    except client.exceptions.BadRequestException:
        return {"error": "GuardDuty is not enabled in this region"}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_iam_credential_report() -> dict[str, Any]:
    """IAM 자격 증명 보고서를 생성하고 분석합니다.

    Returns:
        사용자별 자격 증명 상태 분석 결과
    """
    import csv
    import io
    import time

    client = boto3.client("iam")

    try:
        client.generate_credential_report()
        for _ in range(10):
            try:
                response = client.get_credential_report()
                break
            except client.exceptions.CredentialReportNotReadyException:
                time.sleep(2)
        else:
            return {"error": "Credential report generation timed out"}

        content = response["Content"].decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        users = []
        issues = []
        for row in reader:
            user_name = row.get("user", "")
            if user_name == "<root_account>":
                user_name = "root"

            mfa_active = row.get("mfa_active", "false") == "true"
            password_enabled = row.get("password_enabled", "false") == "true"
            ak1_active = row.get("access_key_1_active", "false") == "true"
            ak2_active = row.get("access_key_2_active", "false") == "true"

            user_info = {
                "user": user_name,
                "mfa_active": mfa_active,
                "password_enabled": password_enabled,
                "password_last_used": row.get("password_last_used"),
                "access_key_1_active": ak1_active,
                "access_key_1_last_used": row.get("access_key_1_last_used_date"),
                "access_key_2_active": ak2_active,
                "access_key_2_last_used": row.get("access_key_2_last_used_date"),
            }
            users.append(user_info)

            if password_enabled and not mfa_active:
                issues.append({
                    "user": user_name,
                    "issue": "MFA not enabled for console user",
                    "severity": "HIGH",
                })
            if ak1_active and row.get("access_key_1_last_rotated", "N/A") == "N/A":
                issues.append({
                    "user": user_name,
                    "issue": "Access key 1 never rotated",
                    "severity": "MEDIUM",
                })

        return {
            "total_users": len(users),
            "users_without_mfa": sum(
                1
                for u in users
                if u["password_enabled"] and not u["mfa_active"]
            ),
            "issues": issues,
            "users": users,
        }
    except Exception as e:
        return {"error": str(e)}
