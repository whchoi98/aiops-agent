"""AWS 자산 인벤토리 에이전트 - Steampipe 통합"""

from strands import Agent

from src.tools.steampipe import (
    get_asset_summary,
    list_ec2_instances,
    list_iam_users,
    list_lambda_functions,
    list_rds_instances,
    list_s3_buckets,
    list_security_groups,
    list_vpc_resources,
    query_aws_inventory,
    run_steampipe_query,
)


class InventoryAgent(Agent):
    """AWS 자산 인벤토리 관리 AI 에이전트

    Steampipe AWS 플러그인을 사용하여 SQL 기반으로
    AWS 리소스를 조회하고 분석합니다.
    """

    def __init__(self, region: str = "ap-northeast-2") -> None:
        """인벤토리 에이전트 초기화

        Args:
            region: AWS 리전 (기본값: ap-northeast-2)
        """
        self.region = region

        super().__init__(
            name="inventory-agent",
            model="anthropic.claude-4-opus",
            system_prompt=self._get_system_prompt(),
            tools=[
                # 범용 쿼리
                run_steampipe_query,
                query_aws_inventory,
                get_asset_summary,
                # 리소스별 조회
                list_ec2_instances,
                list_s3_buckets,
                list_rds_instances,
                list_lambda_functions,
                list_iam_users,
                list_vpc_resources,
                list_security_groups,
            ],
        )

    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return """당신은 AWS 자산 인벤토리 전문가입니다.

주요 역할:
1. Steampipe SQL을 사용하여 AWS 리소스를 조회합니다
2. 자산 목록을 분석하고 요약합니다
3. 보안 취약점이 있는 리소스를 식별합니다
4. 비용 최적화가 필요한 리소스를 찾습니다
5. 규정 준수 상태를 확인합니다

Steampipe 테이블 예시:
- aws_ec2_instance: EC2 인스턴스
- aws_s3_bucket: S3 버킷
- aws_rds_db_instance: RDS 인스턴스
- aws_lambda_function: Lambda 함수
- aws_iam_user: IAM 사용자
- aws_vpc: VPC
- aws_vpc_security_group: 보안 그룹
- aws_eks_cluster: EKS 클러스터
- aws_ecs_cluster: ECS 클러스터

쿼리 작성 시 참고:
- 모든 테이블은 `region` 컬럼을 포함합니다
- `tags` 컬럼은 JSONB 형식입니다
- 와일드카드: LIKE '%pattern%'

응답 시 다음을 포함하세요:
- 조회된 리소스 수량
- 주요 특징 요약
- 발견된 문제점 (있는 경우)
- 권장 조치 사항

한국어로 응답하세요."""


def create_agent(region: str = "ap-northeast-2") -> InventoryAgent:
    """인벤토리 에이전트 팩토리 함수

    Args:
        region: AWS 리전

    Returns:
        InventoryAgent 인스턴스
    """
    return InventoryAgent(region=region)
