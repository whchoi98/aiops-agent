"""비용 분석 도구 — AWS Cost Explorer"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from strands import tool


def _get_ce_client() -> Any:
    return boto3.client(
        "ce",
        region_name=os.getenv("AWS_REGION", "ap-northeast-2"),
    )


@tool
def get_cost_and_usage(
    days: int = 30,
    granularity: str = "MONTHLY",
    group_by: str | None = None,
) -> dict[str, Any]:
    """AWS 비용 및 사용량을 조회합니다.

    Args:
        days: 조회할 기간 (일 단위, 기본값: 30)
        granularity: 집계 단위 (DAILY, MONTHLY)
        group_by: 그룹 기준 (SERVICE, LINKED_ACCOUNT, REGION)

    Returns:
        기간별 비용 데이터
    """
    client = _get_ce_client()

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    params: dict[str, Any] = {
        "TimePeriod": {"Start": start_date, "End": end_date},
        "Granularity": granularity,
        "Metrics": ["UnblendedCost", "UsageQuantity"],
        "Filter": {
            "Not": {
                "Dimensions": {
                    "Key": "RECORD_TYPE",
                    "Values": ["Credit", "Refund"],
                }
            }
        },
    }
    if group_by:
        params["GroupBy"] = [{"Type": "DIMENSION", "Key": group_by}]

    response = client.get_cost_and_usage(**params)

    results = []
    for period in response.get("ResultsByTime", []):
        entry: dict[str, Any] = {
            "start": period["TimePeriod"]["Start"],
            "end": period["TimePeriod"]["End"],
        }
        if period.get("Groups"):
            entry["groups"] = [
                {
                    "key": g["Keys"][0],
                    "amount": float(g["Metrics"]["UnblendedCost"]["Amount"]),
                    "unit": g["Metrics"]["UnblendedCost"]["Unit"],
                }
                for g in period["Groups"]
            ]
        else:
            entry["total_cost"] = float(
                period["Total"]["UnblendedCost"]["Amount"]
            )
            entry["unit"] = period["Total"]["UnblendedCost"]["Unit"]
        results.append(entry)

    total = sum(
        r.get("total_cost", 0)
        or sum(g["amount"] for g in r.get("groups", []))
        for r in results
    )

    return {
        "period": {"start": start_date, "end": end_date},
        "granularity": granularity,
        "total_cost": round(total, 2),
        "results": results,
    }


@tool
def get_cost_forecast(
    days: int = 30,
    granularity: str = "MONTHLY",
) -> dict[str, Any]:
    """AWS 비용 예측을 조회합니다.

    Args:
        days: 예측 기간 (일 단위, 기본값: 30)
        granularity: 집계 단위 (DAILY, MONTHLY)

    Returns:
        비용 예측 데이터
    """
    client = _get_ce_client()

    start_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        response = client.get_cost_forecast(
            TimePeriod={"Start": start_date, "End": end_date},
            Metric="UNBLENDED_COST",
            Granularity=granularity,
        )

        forecasts = [
            {
                "start": f["TimePeriod"]["Start"],
                "end": f["TimePeriod"]["End"],
                "mean": float(f["MeanValue"]),
                "low": float(f["PredictionIntervalLowerBound"]),
                "high": float(f["PredictionIntervalUpperBound"]),
            }
            for f in response.get("ForecastResultsByTime", [])
        ]

        return {
            "period": {"start": start_date, "end": end_date},
            "total_forecast": float(response.get("Total", {}).get("Amount", 0)),
            "unit": response.get("Total", {}).get("Unit", "USD"),
            "forecasts": forecasts,
        }
    except client.exceptions.DataUnavailableException:
        return {
            "period": {"start": start_date, "end": end_date},
            "error": "Not enough historical data for forecast",
        }


@tool
def get_rightsizing_recommendations(
    service: str = "AmazonEC2",
) -> dict[str, Any]:
    """라이트사이징 권장 사항을 조회합니다.

    Args:
        service: 서비스 이름 (기본값: AmazonEC2)

    Returns:
        라이트사이징 권장 사항 목록
    """
    client = _get_ce_client()

    try:
        response = client.get_rightsizing_recommendation(
            Service=service,
            Configuration={
                "RecommendationTarget": "SAME_INSTANCE_FAMILY",
                "BenefitsConsidered": True,
            },
        )

        recommendations = []
        for rec in response.get("RightsizingRecommendations", []):
            current = rec.get("CurrentInstance", {})
            modify_rec = rec.get("ModifyRecommendationDetail", {})
            target_instances = modify_rec.get("TargetInstances", [])

            recommendation: dict[str, Any] = {
                "account_id": rec.get("AccountId"),
                "instance_id": current.get("ResourceId"),
                "instance_type": current.get("ResourceDetails", {})
                .get("EC2ResourceDetails", {})
                .get("InstanceType"),
                "action": rec.get("RightsizingType"),
                "estimated_monthly_savings": float(
                    current.get("MonthlyCost", "0")
                ) - float(
                    target_instances[0].get("EstimatedMonthlyCost", "0")
                    if target_instances
                    else "0"
                ),
            }
            if target_instances:
                target = target_instances[0]
                recommendation["recommended_type"] = (
                    target.get("ResourceDetails", {})
                    .get("EC2ResourceDetails", {})
                    .get("InstanceType")
                )
            recommendations.append(recommendation)

        total_savings = sum(r["estimated_monthly_savings"] for r in recommendations)

        return {
            "service": service,
            "total_recommendations": len(recommendations),
            "total_estimated_monthly_savings": round(total_savings, 2),
            "recommendations": recommendations,
        }
    except Exception as e:
        return {"service": service, "error": str(e)}


@tool
def get_cost_by_service(days: int = 30) -> dict[str, Any]:
    """서비스별 비용을 조회합니다.

    Args:
        days: 조회할 기간 (일 단위, 기본값: 30)

    Returns:
        서비스별 비용 정보 (내림차순 정렬)
    """
    result = get_cost_and_usage(days=days, granularity="MONTHLY", group_by="SERVICE")

    service_costs: dict[str, float] = {}
    for period in result.get("results", []):
        for group in period.get("groups", []):
            service = group["key"]
            amount = group["amount"]
            service_costs[service] = service_costs.get(service, 0) + amount

    sorted_services = sorted(
        service_costs.items(), key=lambda x: x[1], reverse=True
    )

    return {
        "period_days": days,
        "total_cost": round(sum(service_costs.values()), 2),
        "services": [
            {"service": name, "cost": round(cost, 2)}
            for name, cost in sorted_services
            if cost > 0.01
        ],
    }
