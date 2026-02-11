"""AgentCore Gateway 생성 및 설정 스크립트 (E2E lab-03 패턴)

Usage:
    python -m gateway.setup_gateway          # 생성
    python -m gateway.setup_gateway --delete  # 삭제
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import boto3

# 프로젝트 루트에서 실행되는 것을 가정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.utils import (
    SSM_PREFIX,
    delete_ssm_parameter,
    get_aws_region,
    get_ssm_parameter,
    put_ssm_parameter,
)

GATEWAY_NAME = "aiops-gateway"
TARGET_NAME = "aiops-tools"
API_SPEC_PATH = os.path.join(os.path.dirname(__file__), "api_spec.json")


def _load_api_spec() -> list[dict]:
    with open(API_SPEC_PATH, encoding="utf-8") as f:
        return json.load(f)


def _get_gateway_client():
    return boto3.client("bedrock-agentcore-control", region_name=get_aws_region())


def _get_cognito_client():
    return boto3.client("cognito-idp", region_name=get_aws_region())


# ---------------------------------------------------------------------------
# Cognito User Pool (인증용)
# ---------------------------------------------------------------------------

def _ensure_cognito_pool() -> tuple[str, str, str]:
    """Cognito User Pool/App Client 를 생성·조회합니다.

    Returns:
        (pool_id, client_id, issuer_url)
    """
    cognito = _get_cognito_client()
    region = get_aws_region()
    pool_name = "aiops-gateway-pool"

    # 기존 풀 검색
    existing_pools = cognito.list_user_pools(MaxResults=60)
    for pool in existing_pools.get("UserPools", []):
        if pool["Name"] == pool_name:
            pool_id = pool["Id"]
            break
    else:
        # 풀 생성
        result = cognito.create_user_pool(
            PoolName=pool_name,
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": True,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": False,
                }
            },
            AutoVerifiedAttributes=["email"],
        )
        pool_id = result["UserPool"]["Id"]
        print(f"Created Cognito User Pool: {pool_id}")

    # App Client 확인/생성
    clients = cognito.list_user_pool_clients(UserPoolId=pool_id, MaxResults=60)
    app_client_name = "aiops-gateway-client"
    client_id = None
    for c in clients.get("UserPoolClients", []):
        if c["ClientName"] == app_client_name:
            client_id = c["ClientId"]
            break

    if not client_id:
        client_result = cognito.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=app_client_name,
            ExplicitAuthFlows=[
                "ALLOW_USER_PASSWORD_AUTH",
                "ALLOW_REFRESH_TOKEN_AUTH",
            ],
            GenerateSecret=False,
        )
        client_id = client_result["UserPoolClient"]["ClientId"]
        print(f"Created Cognito App Client: {client_id}")

    issuer_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
    return pool_id, client_id, issuer_url


# ---------------------------------------------------------------------------
# Gateway 생성/삭제
# ---------------------------------------------------------------------------

def create_gateway() -> None:
    """AgentCore Gateway 를 생성하고 Lambda 타겟을 등록합니다."""
    client = _get_gateway_client()

    # 1. Cognito 설정
    pool_id, cognito_client_id, issuer_url = _ensure_cognito_pool()
    print(f"Cognito Issuer URL: {issuer_url}")

    # 2. Lambda ARN 조회 (CloudFormation 이 생성한 SSM 파라미터)
    lambda_arn = get_ssm_parameter(f"{SSM_PREFIX}/gateway_lambda_arn")
    print(f"Lambda ARN: {lambda_arn}")

    # 3. Gateway Role ARN 조회
    gateway_role_arn = get_ssm_parameter(f"{SSM_PREFIX}/gateway_role_arn")
    print(f"Gateway Role ARN: {gateway_role_arn}")

    # 4. Gateway 생성
    print("Creating AgentCore Gateway...")
    gw_response = client.create_gateway(
        name=GATEWAY_NAME,
        protocolType="MCP",
        roleArn=gateway_role_arn,
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration={
            "customJWTAuthorizer": {
                "discoveryUrl": f"{issuer_url}/.well-known/openid-configuration",
                "allowedAudience": [cognito_client_id],
                "allowedClients": [cognito_client_id],
            }
        },
    )
    gateway_id = gw_response["gatewayId"]
    print(f"Gateway created: {gateway_id}")

    # Gateway 가 ACTIVE 상태가 될 때까지 대기
    print("Waiting for gateway to become ACTIVE...")
    for _ in range(60):
        status = client.get_gateway(gatewayIdentifier=gateway_id)
        if status.get("status") == "READY":
            break
        time.sleep(5)
    else:
        print("WARNING: Gateway did not reach READY state within timeout")

    # 5. Lambda 타겟 생성
    print("Creating Gateway Target...")
    api_spec = _load_api_spec()
    target_response = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=TARGET_NAME,
        targetConfiguration={
            "mcp": {
                "lambda": {
                    "functionArn": lambda_arn,
                    "toolSchema": {
                        "inlinePayload": api_spec,
                    },
                }
            }
        },
        credentialProviderConfigurations=[
            {
                "credentialProviderType": "GATEWAY_IAM_ROLE",
                "credentialProvider": {
                    "roleArn": gateway_role_arn,
                },
            }
        ],
    )
    target_id = target_response["gatewayTargetId"]
    print(f"Gateway Target created: {target_id}")

    # Target 이 ACTIVE 상태가 될 때까지 대기
    print("Waiting for target to become ACTIVE...")
    for _ in range(60):
        t_status = client.get_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target_id
        )
        if t_status.get("status") == "READY":
            break
        time.sleep(5)
    else:
        print("WARNING: Target did not reach READY state within timeout")

    # 6. SSM 에 저장
    put_ssm_parameter(f"{SSM_PREFIX}/gateway_id", gateway_id)
    put_ssm_parameter(f"{SSM_PREFIX}/gateway_target_id", target_id)
    put_ssm_parameter(f"{SSM_PREFIX}/cognito_pool_id", pool_id)
    put_ssm_parameter(f"{SSM_PREFIX}/cognito_client_id", cognito_client_id)
    print("SSM parameters saved.")

    # 결과 출력
    gateway_url = client.get_gateway(gatewayIdentifier=gateway_id).get("gatewayUrl", "")
    print("\n=== Gateway Setup Complete ===")
    print(f"  Gateway ID:     {gateway_id}")
    print(f"  Gateway URL:    {gateway_url}")
    print(f"  Target ID:      {target_id}")
    print(f"  Cognito Pool:   {pool_id}")
    print(f"  Cognito Client: {cognito_client_id}")
    print(f"  Tools:          {len(api_spec)}")


def delete_gateway() -> None:
    """AgentCore Gateway 와 관련 리소스를 삭제합니다."""
    client = _get_gateway_client()

    # SSM 에서 ID 조회
    try:
        gateway_id = get_ssm_parameter(f"{SSM_PREFIX}/gateway_id")
    except Exception:
        print("No gateway_id found in SSM. Nothing to delete.")
        return

    # 타겟 삭제
    try:
        target_id = get_ssm_parameter(f"{SSM_PREFIX}/gateway_target_id")
        print(f"Deleting Gateway Target: {target_id}")
        client.delete_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target_id
        )
        # 타겟 삭제 완료 대기
        for _ in range(30):
            try:
                client.get_gateway_target(
                    gatewayIdentifier=gateway_id, targetId=target_id
                )
                time.sleep(5)
            except Exception:
                break
        print("Target deleted.")
    except Exception as e:
        print(f"Target deletion skipped: {e}")

    # Gateway 삭제
    try:
        print(f"Deleting Gateway: {gateway_id}")
        client.delete_gateway(gatewayIdentifier=gateway_id)
        for _ in range(30):
            try:
                client.get_gateway(gatewayIdentifier=gateway_id)
                time.sleep(5)
            except Exception:
                break
        print("Gateway deleted.")
    except Exception as e:
        print(f"Gateway deletion error: {e}")

    # Cognito Pool 삭제
    try:
        pool_id = get_ssm_parameter(f"{SSM_PREFIX}/cognito_pool_id")
        cognito = _get_cognito_client()
        # App Client 먼저 삭제
        clients = cognito.list_user_pool_clients(UserPoolId=pool_id, MaxResults=60)
        for c in clients.get("UserPoolClients", []):
            cognito.delete_user_pool_client(
                UserPoolId=pool_id, ClientId=c["ClientId"]
            )
        cognito.delete_user_pool(UserPoolId=pool_id)
        print(f"Cognito Pool deleted: {pool_id}")
    except Exception as e:
        print(f"Cognito cleanup skipped: {e}")

    # SSM 파라미터 정리
    for key in ["gateway_id", "gateway_target_id", "cognito_pool_id", "cognito_client_id"]:
        delete_ssm_parameter(f"{SSM_PREFIX}/{key}")
    print("SSM parameters cleaned up.")

    print("\n=== Gateway Cleanup Complete ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AgentCore Gateway 관리")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Gateway 및 관련 리소스 삭제",
    )
    args = parser.parse_args()

    if args.delete:
        delete_gateway()
    else:
        create_gateway()


if __name__ == "__main__":
    main()
