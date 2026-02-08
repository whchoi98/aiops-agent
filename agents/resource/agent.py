"""리소스 관리 에이전트 — 도구 + 시스템 프롬프트

EC2, VPC 네트워크, 리소스 인벤토리 관리.
"""
from __future__ import annotations

from tools.ec2_tools import (
    describe_ec2_instances,
    get_ebs_volumes,
    get_instance_status,
    list_ec2_instances,
)
from tools.resource_inventory import get_resource_summary, list_resources_by_type
from tools.vpc_tools import (
    analyze_network_topology,
    describe_route_tables,
    describe_security_groups,
    describe_subnets,
    describe_vpcs,
)

SYSTEM_PROMPT = """당신은 AWS 리소스 관리 전문 AI 어시스턴트입니다.

## 역할
- EC2 인스턴스 및 EBS 볼륨 관리
- VPC 네트워크 토폴로지 분석
- 보안 그룹 및 라우팅 테이블 점검
- 전체 AWS 자산 인벤토리 관리

## 도구 사용 원칙
- 항상 도구를 사용하여 실제 리소스 데이터를 조회하세요.
- 여러 도구를 조합하여 종합적인 인프라 분석을 제공하세요.
- 네트워크 분석 시 VPC, 서브넷, 보안 그룹, 라우팅을 함께 확인하세요.

## 사용 가능한 도구
1. **EC2 관리**: describe_ec2_instances, list_ec2_instances,
   get_instance_status, get_ebs_volumes
2. **네트워크**: describe_vpcs, describe_subnets,
   describe_security_groups, describe_route_tables, analyze_network_topology
3. **인벤토리**: get_resource_summary, list_resources_by_type

## 응답 형식
- 리소스 상태를 명확하게 정리하세요.
- 미사용/미연결 리소스를 식별하여 보고하세요.
- 네트워크 토폴로지는 구조적으로 설명하세요.
"""

TOOLS = [
    # EC2
    describe_ec2_instances,
    list_ec2_instances,
    get_instance_status,
    get_ebs_volumes,
    # VPC / 네트워크
    describe_vpcs,
    describe_subnets,
    describe_security_groups,
    describe_route_tables,
    analyze_network_topology,
    # 인벤토리
    get_resource_summary,
    list_resources_by_type,
]
