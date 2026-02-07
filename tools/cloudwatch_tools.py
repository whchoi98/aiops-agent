"""CloudWatch 메트릭 / 알람 / 로그 도구"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from strands import tool


def _get_cloudwatch_client() -> Any:
    return boto3.client(
        "cloudwatch",
        region_name=os.getenv("AWS_REGION", "ap-northeast-2"),
    )


def _get_logs_client() -> Any:
    return boto3.client(
        "logs",
        region_name=os.getenv("AWS_REGION", "ap-northeast-2"),
    )


@tool
def get_cloudwatch_metrics(
    namespace: str,
    metric_name: str,
    dimensions: list[dict[str, str]] | None = None,
    period_hours: int = 1,
) -> dict[str, Any]:
    """CloudWatch 메트릭 데이터를 조회합니다.

    Args:
        namespace: AWS 서비스 네임스페이스 (예: AWS/EC2, AWS/Lambda)
        metric_name: 메트릭 이름 (예: CPUUtilization, Invocations)
        dimensions: 메트릭 차원 리스트 (예: [{"Name": "InstanceId", "Value": "i-xxx"}])
        period_hours: 조회할 기간 (시간 단위, 기본값: 1)

    Returns:
        메트릭 데이터와 통계 정보
    """
    client = _get_cloudwatch_client()

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=period_hours)

    params: dict[str, Any] = {
        "Namespace": namespace,
        "MetricName": metric_name,
        "StartTime": start_time,
        "EndTime": end_time,
        "Period": 300,
        "Statistics": ["Average", "Maximum", "Minimum"],
    }
    if dimensions:
        params["Dimensions"] = dimensions

    response = client.get_metric_statistics(**params)
    datapoints = sorted(response.get("Datapoints", []), key=lambda x: x["Timestamp"])

    return {
        "namespace": namespace,
        "metric_name": metric_name,
        "period_hours": period_hours,
        "datapoints": [
            {
                "timestamp": dp["Timestamp"].isoformat(),
                "average": dp.get("Average"),
                "maximum": dp.get("Maximum"),
                "minimum": dp.get("Minimum"),
            }
            for dp in datapoints
        ],
        "summary": {
            "count": len(datapoints),
            "latest_average": datapoints[-1].get("Average") if datapoints else None,
            "max_value": max(
                (dp.get("Maximum", 0) for dp in datapoints), default=0
            ),
        },
    }


@tool
def get_cloudwatch_alarms(
    alarm_name_prefix: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    """CloudWatch 알람 상태를 조회합니다.

    Args:
        alarm_name_prefix: 알람 이름 접두사로 필터링 (선택)
        state: 알람 상태로 필터링 (OK, ALARM, INSUFFICIENT_DATA)

    Returns:
        알람 목록과 상태 정보
    """
    client = _get_cloudwatch_client()

    params: dict[str, Any] = {}
    if alarm_name_prefix:
        params["AlarmNamePrefix"] = alarm_name_prefix
    if state:
        params["StateValue"] = state

    response = client.describe_alarms(**params)

    alarms = []
    for alarm in response.get("MetricAlarms", []):
        alarms.append({
            "name": alarm["AlarmName"],
            "state": alarm["StateValue"],
            "metric": alarm["MetricName"],
            "namespace": alarm["Namespace"],
            "threshold": alarm.get("Threshold"),
            "comparison": alarm.get("ComparisonOperator"),
            "state_reason": alarm.get("StateReason"),
            "updated_at": (
                alarm["StateUpdatedTimestamp"].isoformat()
                if alarm.get("StateUpdatedTimestamp")
                else None
            ),
        })

    return {
        "total_count": len(alarms),
        "alarm_count": sum(1 for a in alarms if a["state"] == "ALARM"),
        "ok_count": sum(1 for a in alarms if a["state"] == "OK"),
        "alarms": alarms,
    }


@tool
def query_cloudwatch_logs(
    log_group_name: str,
    query: str,
    hours: int = 1,
    limit: int = 100,
) -> dict[str, Any]:
    """CloudWatch Logs Insights 쿼리를 실행합니다.

    Args:
        log_group_name: 로그 그룹 이름
        query: Logs Insights 쿼리 문자열
        hours: 조회할 기간 (시간 단위, 기본값: 1)
        limit: 결과 최대 개수 (기본값: 100)

    Returns:
        쿼리 결과
    """
    client = _get_logs_client()

    end_time = int(datetime.now(timezone.utc).timestamp())
    start_time = end_time - (hours * 3600)

    response = client.start_query(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        queryString=query,
        limit=limit,
    )
    query_id = response["queryId"]

    result: dict[str, Any] = {}
    for _ in range(30):
        result = client.get_query_results(queryId=query_id)
        if result["status"] == "Complete":
            break
        time.sleep(1)

    results = [
        {field["field"]: field["value"] for field in row}
        for row in result.get("results", [])
    ]

    return {
        "log_group": log_group_name,
        "query": query,
        "hours": hours,
        "result_count": len(results),
        "results": results,
    }


@tool
def describe_ec2_instances(
    instance_ids: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """EC2 인스턴스 정보를 조회합니다.

    Args:
        instance_ids: 조회할 인스턴스 ID 목록 (선택)
        filters: 필터 조건 (예: [{"Name": "instance-state-name", "Values": ["running"]}])

    Returns:
        EC2 인스턴스 목록과 상태 정보
    """
    client = boto3.client(
        "ec2", region_name=os.getenv("AWS_REGION", "ap-northeast-2")
    )

    params: dict[str, Any] = {}
    if instance_ids:
        params["InstanceIds"] = instance_ids
    if filters:
        params["Filters"] = filters

    response = client.describe_instances(**params)

    instances = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            name_tag = next(
                (
                    tag["Value"]
                    for tag in instance.get("Tags", [])
                    if tag["Key"] == "Name"
                ),
                "N/A",
            )
            instances.append({
                "instance_id": instance["InstanceId"],
                "name": name_tag,
                "type": instance["InstanceType"],
                "state": instance["State"]["Name"],
                "private_ip": instance.get("PrivateIpAddress"),
                "public_ip": instance.get("PublicIpAddress"),
                "launch_time": (
                    instance["LaunchTime"].isoformat()
                    if instance.get("LaunchTime")
                    else None
                ),
            })

    return {
        "total_count": len(instances),
        "running_count": sum(1 for i in instances if i["state"] == "running"),
        "stopped_count": sum(1 for i in instances if i["state"] == "stopped"),
        "instances": instances,
    }
