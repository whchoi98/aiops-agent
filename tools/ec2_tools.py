"""EC2 인스턴스 관리 도구"""
from __future__ import annotations

import os
from typing import Any

import boto3
from strands import tool


def _get_ec2_client() -> Any:
    return boto3.client(
        "ec2",
        region_name=os.getenv("AWS_REGION", "ap-northeast-2"),
    )


@tool
def list_ec2_instances(
    state: str | None = None,
    instance_type: str | None = None,
) -> dict[str, Any]:
    """EC2 인스턴스 목록을 조회합니다.

    Args:
        state: 인스턴스 상태 필터 (running, stopped, terminated)
        instance_type: 인스턴스 유형 필터 (t3.micro, m5.large 등)

    Returns:
        EC2 인스턴스 목록
    """
    client = _get_ec2_client()

    filters: list[dict[str, Any]] = []
    if state:
        filters.append({"Name": "instance-state-name", "Values": [state]})
    if instance_type:
        filters.append({"Name": "instance-type", "Values": [instance_type]})

    params: dict[str, Any] = {}
    if filters:
        params["Filters"] = filters

    paginator = client.get_paginator("describe_instances")
    instances = []
    for page in paginator.paginate(**params):
        for reservation in page.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                name_tag = next(
                    (
                        tag["Value"]
                        for tag in inst.get("Tags", [])
                        if tag["Key"] == "Name"
                    ),
                    "N/A",
                )
                instances.append({
                    "instance_id": inst["InstanceId"],
                    "name": name_tag,
                    "type": inst["InstanceType"],
                    "state": inst["State"]["Name"],
                    "private_ip": inst.get("PrivateIpAddress"),
                    "public_ip": inst.get("PublicIpAddress"),
                    "vpc_id": inst.get("VpcId"),
                    "subnet_id": inst.get("SubnetId"),
                    "launch_time": (
                        inst["LaunchTime"].isoformat()
                        if inst.get("LaunchTime")
                        else None
                    ),
                    "platform": inst.get("PlatformDetails", "Linux/UNIX"),
                })

    return {
        "total_count": len(instances),
        "running_count": sum(1 for i in instances if i["state"] == "running"),
        "stopped_count": sum(1 for i in instances if i["state"] == "stopped"),
        "instances": instances,
    }


@tool
def get_instance_status(instance_ids: list[str]) -> dict[str, Any]:
    """EC2 인스턴스의 시스템 상태 및 인스턴스 상태 검사를 조회합니다.

    Args:
        instance_ids: 조회할 인스턴스 ID 목록

    Returns:
        인스턴스별 상태 검사 결과
    """
    client = _get_ec2_client()

    response = client.describe_instance_status(
        InstanceIds=instance_ids,
        IncludeAllInstances=True,
    )

    statuses = []
    for status in response.get("InstanceStatuses", []):
        statuses.append({
            "instance_id": status["InstanceId"],
            "instance_state": status["InstanceState"]["Name"],
            "system_status": status.get("SystemStatus", {}).get("Status", "N/A"),
            "instance_status": status.get("InstanceStatus", {}).get("Status", "N/A"),
            "availability_zone": status.get("AvailabilityZone"),
            "system_checks": [
                {
                    "name": detail.get("Name"),
                    "status": detail.get("Status"),
                }
                for detail in status.get("SystemStatus", {}).get("Details", [])
            ],
            "instance_checks": [
                {
                    "name": detail.get("Name"),
                    "status": detail.get("Status"),
                }
                for detail in status.get("InstanceStatus", {}).get("Details", [])
            ],
        })

    return {"total_count": len(statuses), "statuses": statuses}


@tool
def get_ebs_volumes(
    volume_ids: list[str] | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    """EBS 볼륨 정보를 조회합니다.

    Args:
        volume_ids: 조회할 볼륨 ID 목록 (선택)
        state: 볼륨 상태 필터 (available, in-use, creating, deleting)

    Returns:
        EBS 볼륨 목록과 상세 정보
    """
    client = _get_ec2_client()

    params: dict[str, Any] = {}
    if volume_ids:
        params["VolumeIds"] = volume_ids

    filters: list[dict[str, Any]] = []
    if state:
        filters.append({"Name": "status", "Values": [state]})
    if filters:
        params["Filters"] = filters

    paginator = client.get_paginator("describe_volumes")
    volumes = []
    for page in paginator.paginate(**params):
        for vol in page.get("Volumes", []):
            name_tag = next(
                (
                    tag["Value"]
                    for tag in vol.get("Tags", [])
                    if tag["Key"] == "Name"
                ),
                "N/A",
            )
            attachments = [
                {
                    "instance_id": att.get("InstanceId"),
                    "device": att.get("Device"),
                    "state": att.get("State"),
                }
                for att in vol.get("Attachments", [])
            ]
            volumes.append({
                "volume_id": vol["VolumeId"],
                "name": name_tag,
                "size_gb": vol["Size"],
                "volume_type": vol["VolumeType"],
                "state": vol["State"],
                "iops": vol.get("Iops"),
                "encrypted": vol.get("Encrypted", False),
                "availability_zone": vol["AvailabilityZone"],
                "attachments": attachments,
                "create_time": (
                    vol["CreateTime"].isoformat() if vol.get("CreateTime") else None
                ),
            })

    unattached = [v for v in volumes if v["state"] == "available"]
    return {
        "total_count": len(volumes),
        "unattached_count": len(unattached),
        "total_size_gb": sum(v["size_gb"] for v in volumes),
        "volumes": volumes,
    }
