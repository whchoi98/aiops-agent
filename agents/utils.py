"""AIOps 에이전트 유틸리티 — SSM, IAM, 설정 관리"""
from __future__ import annotations

import json
import os
from typing import Any

import boto3
import yaml
from boto3.session import Session


# ---------------------------------------------------------------------------
# AWS 컨텍스트
# ---------------------------------------------------------------------------

def get_aws_region() -> str:
    """현재 AWS 리전을 반환합니다."""
    session = Session()
    return session.region_name or os.getenv("AWS_REGION", "ap-northeast-2")


def get_aws_account_id() -> str:
    """현재 AWS 계정 ID를 반환합니다."""
    sts = boto3.client("sts")
    return sts.get_caller_identity()["Account"]


# ---------------------------------------------------------------------------
# SSM Parameter Store
# ---------------------------------------------------------------------------

SSM_PREFIX = "/app/aiops/agentcore"


def get_ssm_parameter(name: str, with_decryption: bool = True) -> str:
    """SSM Parameter Store에서 값을 조회합니다.

    Args:
        name: 파라미터 이름 (절대 경로 또는 SSM_PREFIX 기준 상대 경로)
        with_decryption: SecureString 복호화 여부

    Returns:
        파라미터 값
    """
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
    return response["Parameter"]["Value"]


def put_ssm_parameter(
    name: str,
    value: str,
    parameter_type: str = "String",
    with_encryption: bool = False,
) -> None:
    """SSM Parameter Store에 값을 저장합니다.

    Args:
        name: 파라미터 이름
        value: 파라미터 값
        parameter_type: 파라미터 타입 (String, StringList, SecureString)
        with_encryption: SecureString으로 저장할지 여부
    """
    ssm = boto3.client("ssm")
    put_params: dict[str, Any] = {
        "Name": name,
        "Value": value,
        "Type": parameter_type,
        "Overwrite": True,
    }
    if with_encryption:
        put_params["Type"] = "SecureString"
    ssm.put_parameter(**put_params)


def delete_ssm_parameter(name: str) -> None:
    """SSM Parameter Store에서 파라미터를 삭제합니다."""
    ssm = boto3.client("ssm")
    try:
        ssm.delete_parameter(Name=name)
    except ssm.exceptions.ParameterNotFound:
        pass


# ---------------------------------------------------------------------------
# IAM Role 관리
# ---------------------------------------------------------------------------

ROLE_NAME_TEMPLATE = "AIOpsBedrockAgentCoreRole-{region}"
POLICY_NAME_TEMPLATE = "AIOpsBedrockAgentCorePolicy-{region}"


def create_agentcore_runtime_execution_role() -> str | None:
    """AgentCore Runtime 실행 역할을 생성하고 ARN을 반환합니다."""
    iam = boto3.client("iam")
    region = get_aws_region()
    account_id = get_aws_account_id()
    role_name = ROLE_NAME_TEMPLATE.format(region=region)
    policy_name = POLICY_NAME_TEMPLATE.format(region=region)

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    },
                },
            }
        ],
    }

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECRImageAccess",
                "Effect": "Allow",
                "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                "Resource": [f"arn:aws:ecr:{region}:{account_id}:repository/*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:DescribeLogGroups"],
                "Resource": [f"arn:aws:logs:{region}:{account_id}:log-group:*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ],
            },
            {
                "Sid": "ECRTokenAccess",
                "Effect": "Allow",
                "Action": ["ecr:GetAuthorizationToken"],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                "Resource": ["*"],
            },
            {
                "Effect": "Allow",
                "Resource": "*",
                "Action": "cloudwatch:PutMetricData",
                "Condition": {
                    "StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}
                },
            },
            {
                "Sid": "BedrockModelInvocation",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ApplyGuardrail",
                    "bedrock:Retrieve",
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account_id}:*",
                ],
            },
            {
                "Sid": "AllowAgentToUseMemory",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:GetMemoryRecord",
                    "bedrock-agentcore:GetMemory",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords",
                ],
                "Resource": [f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"],
            },
            {
                "Sid": "SSMParameterAccess",
                "Effect": "Allow",
                "Action": ["ssm:GetParameter"],
                "Resource": [f"arn:aws:ssm:{region}:{account_id}:parameter/app/aiops/*"],
            },
            {
                "Sid": "GatewayAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetGateway",
                    "bedrock-agentcore:InvokeGateway",
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/*"
                ],
            },
            {
                "Sid": "AIOpsReadOnlyAccess",
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:DescribeAlarms",
                    "cloudwatch:ListMetrics",
                    "logs:StartQuery",
                    "logs:GetQueryResults",
                    "logs:DescribeLogGroups",
                    "ec2:DescribeInstances",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeVpcs",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeRouteTables",
                    "ec2:DescribeNetworkAcls",
                    "ce:GetCostAndUsage",
                    "ce:GetCostForecast",
                    "ce:GetRightsizingRecommendation",
                    "securityhub:GetFindings",
                    "guardduty:ListDetectors",
                    "guardduty:ListFindings",
                    "guardduty:GetFindings",
                    "iam:GenerateCredentialReport",
                    "iam:GetCredentialReport",
                    "s3:ListAllMyBuckets",
                    "lambda:ListFunctions",
                    "rds:DescribeDBInstances",
                ],
                "Resource": ["*"],
            },
        ],
    }

    try:
        try:
            existing_role = iam.get_role(RoleName=role_name)
            return existing_role["Role"]["Arn"]
        except iam.exceptions.NoSuchEntityException:
            pass

        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for AIOps Bedrock AgentCore Runtime",
        )

        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        try:
            iam.get_policy(PolicyArn=policy_arn)
        except iam.exceptions.NoSuchEntityException:
            policy_response = iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
                Description="Policy for AIOps Bedrock AgentCore permissions",
            )
            policy_arn = policy_response["Policy"]["Arn"]

        iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        put_ssm_parameter(
            f"{SSM_PREFIX}/runtime_execution_role_arn",
            role_response["Role"]["Arn"],
        )
        return role_response["Role"]["Arn"]

    except Exception as e:
        print(f"Error creating IAM role: {e}")
        return None


# ---------------------------------------------------------------------------
# 설정 파일 로딩
# ---------------------------------------------------------------------------

def read_config(file_path: str) -> dict[str, Any]:
    """JSON 또는 YAML 설정 파일을 로드합니다.

    Args:
        file_path: 설정 파일 경로

    Returns:
        설정 딕셔너리

    Raises:
        FileNotFoundError: 파일이 존재하지 않는 경우
        ValueError: 지원하지 않는 형식이거나 파싱 오류
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    _, ext = os.path.splitext(file_path.lower())

    with open(file_path, "r", encoding="utf-8") as f:
        if ext == ".json":
            return json.load(f)
        elif ext in (".yaml", ".yml"):
            return yaml.safe_load(f)
        else:
            content = f.read()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return yaml.safe_load(content)
