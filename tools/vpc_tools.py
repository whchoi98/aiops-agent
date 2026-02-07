"""VPC / 네트워크 분석 도구"""
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
def describe_vpcs(
    vpc_ids: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """VPC 목록을 조회합니다.

    Args:
        vpc_ids: 조회할 VPC ID 목록 (선택)
        filters: 필터 조건 (예: [{"Name": "state", "Values": ["available"]}])

    Returns:
        VPC 목록과 상세 정보
    """
    client = _get_ec2_client()

    params: dict[str, Any] = {}
    if vpc_ids:
        params["VpcIds"] = vpc_ids
    if filters:
        params["Filters"] = filters

    response = client.describe_vpcs(**params)

    vpcs = []
    for vpc in response.get("Vpcs", []):
        name_tag = next(
            (tag["Value"] for tag in vpc.get("Tags", []) if tag["Key"] == "Name"),
            "N/A",
        )
        vpcs.append({
            "vpc_id": vpc["VpcId"],
            "name": name_tag,
            "cidr_block": vpc["CidrBlock"],
            "state": vpc["State"],
            "is_default": vpc.get("IsDefault", False),
            "dhcp_options_id": vpc.get("DhcpOptionsId"),
            "instance_tenancy": vpc.get("InstanceTenancy"),
        })

    return {"total_count": len(vpcs), "vpcs": vpcs}


@tool
def describe_subnets(
    subnet_ids: list[str] | None = None,
    vpc_id: str | None = None,
    availability_zone: str | None = None,
) -> dict[str, Any]:
    """서브넷 목록을 조회합니다.

    Args:
        subnet_ids: 조회할 서브넷 ID 목록 (선택)
        vpc_id: 특정 VPC의 서브넷만 조회 (선택)
        availability_zone: 특정 AZ의 서브넷만 조회 (선택)

    Returns:
        서브넷 목록과 상세 정보
    """
    client = _get_ec2_client()

    params: dict[str, Any] = {}
    if subnet_ids:
        params["SubnetIds"] = subnet_ids

    filters: list[dict[str, Any]] = []
    if vpc_id:
        filters.append({"Name": "vpc-id", "Values": [vpc_id]})
    if availability_zone:
        filters.append({"Name": "availability-zone", "Values": [availability_zone]})
    if filters:
        params["Filters"] = filters

    response = client.describe_subnets(**params)

    subnets = []
    for subnet in response.get("Subnets", []):
        name_tag = next(
            (tag["Value"] for tag in subnet.get("Tags", []) if tag["Key"] == "Name"),
            "N/A",
        )
        subnets.append({
            "subnet_id": subnet["SubnetId"],
            "name": name_tag,
            "vpc_id": subnet["VpcId"],
            "cidr_block": subnet["CidrBlock"],
            "availability_zone": subnet["AvailabilityZone"],
            "state": subnet["State"],
            "available_ip_count": subnet["AvailableIpAddressCount"],
            "map_public_ip": subnet.get("MapPublicIpOnLaunch", False),
            "default_for_az": subnet.get("DefaultForAz", False),
        })

    return {"total_count": len(subnets), "subnets": subnets}


@tool
def describe_security_groups(
    group_ids: list[str] | None = None,
    vpc_id: str | None = None,
    group_name: str | None = None,
) -> dict[str, Any]:
    """보안 그룹 목록을 조회합니다.

    Args:
        group_ids: 조회할 보안 그룹 ID 목록 (선택)
        vpc_id: 특정 VPC의 보안 그룹만 조회 (선택)
        group_name: 보안 그룹 이름으로 필터링 (선택)

    Returns:
        보안 그룹 목록과 인바운드/아웃바운드 규칙
    """
    client = _get_ec2_client()

    params: dict[str, Any] = {}
    if group_ids:
        params["GroupIds"] = group_ids

    filters: list[dict[str, Any]] = []
    if vpc_id:
        filters.append({"Name": "vpc-id", "Values": [vpc_id]})
    if group_name:
        filters.append({"Name": "group-name", "Values": [f"*{group_name}*"]})
    if filters:
        params["Filters"] = filters

    response = client.describe_security_groups(**params)

    security_groups = []
    for sg in response.get("SecurityGroups", []):
        inbound_rules = []
        for rule in sg.get("IpPermissions", []):
            inbound_rules.append({
                "protocol": rule.get("IpProtocol", "all"),
                "from_port": rule.get("FromPort"),
                "to_port": rule.get("ToPort"),
                "sources": [
                    ip_range.get("CidrIp")
                    for ip_range in rule.get("IpRanges", [])
                ] + [
                    sg_pair.get("GroupId")
                    for sg_pair in rule.get("UserIdGroupPairs", [])
                ],
            })

        outbound_rules = []
        for rule in sg.get("IpPermissionsEgress", []):
            outbound_rules.append({
                "protocol": rule.get("IpProtocol", "all"),
                "from_port": rule.get("FromPort"),
                "to_port": rule.get("ToPort"),
                "destinations": [
                    ip_range.get("CidrIp")
                    for ip_range in rule.get("IpRanges", [])
                ],
            })

        security_groups.append({
            "group_id": sg["GroupId"],
            "group_name": sg["GroupName"],
            "description": sg.get("Description"),
            "vpc_id": sg.get("VpcId"),
            "inbound_rules_count": len(inbound_rules),
            "outbound_rules_count": len(outbound_rules),
            "inbound_rules": inbound_rules,
            "outbound_rules": outbound_rules,
        })

    return {"total_count": len(security_groups), "security_groups": security_groups}


@tool
def describe_route_tables(
    route_table_ids: list[str] | None = None,
    vpc_id: str | None = None,
) -> dict[str, Any]:
    """라우팅 테이블 목록을 조회합니다.

    Args:
        route_table_ids: 조회할 라우팅 테이블 ID 목록 (선택)
        vpc_id: 특정 VPC의 라우팅 테이블만 조회 (선택)

    Returns:
        라우팅 테이블 목록과 라우트 정보
    """
    client = _get_ec2_client()

    params: dict[str, Any] = {}
    if route_table_ids:
        params["RouteTableIds"] = route_table_ids

    filters: list[dict[str, Any]] = []
    if vpc_id:
        filters.append({"Name": "vpc-id", "Values": [vpc_id]})
    if filters:
        params["Filters"] = filters

    response = client.describe_route_tables(**params)

    route_tables = []
    for rt in response.get("RouteTables", []):
        name_tag = next(
            (tag["Value"] for tag in rt.get("Tags", []) if tag["Key"] == "Name"),
            "N/A",
        )

        routes = []
        for route in rt.get("Routes", []):
            routes.append({
                "destination": (
                    route.get("DestinationCidrBlock")
                    or route.get("DestinationIpv6CidrBlock")
                ),
                "target": (
                    route.get("GatewayId")
                    or route.get("NatGatewayId")
                    or route.get("NetworkInterfaceId")
                    or route.get("VpcPeeringConnectionId")
                    or route.get("TransitGatewayId")
                    or "local"
                ),
                "state": route.get("State"),
            })

        associations = [
            {
                "subnet_id": assoc.get("SubnetId"),
                "main": assoc.get("Main", False),
            }
            for assoc in rt.get("Associations", [])
        ]

        route_tables.append({
            "route_table_id": rt["RouteTableId"],
            "name": name_tag,
            "vpc_id": rt["VpcId"],
            "routes": routes,
            "associations": associations,
        })

    return {"total_count": len(route_tables), "route_tables": route_tables}


@tool
def analyze_network_topology(vpc_id: str) -> dict[str, Any]:
    """VPC의 전체 네트워크 토폴로지를 분석합니다.

    Args:
        vpc_id: 분석할 VPC ID

    Returns:
        VPC, 서브넷, 보안 그룹, 라우팅 테이블을 포함한 종합 분석
    """
    vpcs = describe_vpcs(vpc_ids=[vpc_id])
    subnets = describe_subnets(vpc_id=vpc_id)
    security_groups = describe_security_groups(vpc_id=vpc_id)
    route_tables = describe_route_tables(vpc_id=vpc_id)

    public_subnets = []
    private_subnets = []
    for subnet in subnets.get("subnets", []):
        if subnet.get("map_public_ip"):
            public_subnets.append(subnet)
        else:
            private_subnets.append(subnet)

    az_distribution: dict[str, dict[str, int]] = {}
    for subnet in subnets.get("subnets", []):
        az = subnet["availability_zone"]
        if az not in az_distribution:
            az_distribution[az] = {"public": 0, "private": 0}
        if subnet.get("map_public_ip"):
            az_distribution[az]["public"] += 1
        else:
            az_distribution[az]["private"] += 1

    return {
        "vpc": vpcs.get("vpcs", [{}])[0] if vpcs.get("vpcs") else {},
        "summary": {
            "total_subnets": subnets.get("total_count", 0),
            "public_subnets": len(public_subnets),
            "private_subnets": len(private_subnets),
            "security_groups": security_groups.get("total_count", 0),
            "route_tables": route_tables.get("total_count", 0),
            "availability_zones": len(az_distribution),
        },
        "az_distribution": az_distribution,
        "public_subnets": public_subnets,
        "private_subnets": private_subnets,
        "security_groups": security_groups.get("security_groups", []),
        "route_tables": route_tables.get("route_tables", []),
    }
