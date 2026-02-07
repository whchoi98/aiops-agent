#!/bin/bash
set -euo pipefail

STACK_NAME=${1:-AIOpsAgentInfra}

REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-2")
export AWS_REGION="${REGION}"

echo "=== AIOps Agent Cleanup ==="
echo "Region: ${AWS_REGION}"

# Confirm
read -p "Delete stack '${STACK_NAME}' and clean up all resources? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# -----------------------------------------------------------------------
# Gateway 정리 (setup_gateway.py 로 생성된 리소스)
# -----------------------------------------------------------------------
echo "--- Gateway Cleanup ---"
GATEWAY_ID=$(aws ssm get-parameter --name "/app/aiops/agentcore/gateway_id" \
    --query "Parameter.Value" --output text --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -n "$GATEWAY_ID" ] && [ "$GATEWAY_ID" != "None" ]; then
    echo "Found Gateway: ${GATEWAY_ID}"
    # python 스크립트로 Gateway 삭제 (Cognito 포함)
    if command -v python3 &>/dev/null; then
        python3 -m gateway.setup_gateway --delete 2>/dev/null || {
            echo "Python gateway cleanup failed, cleaning up SSM parameters manually."
            for param in gateway_id gateway_target_id cognito_pool_id cognito_client_id; do
                aws ssm delete-parameter --name "/app/aiops/agentcore/${param}" \
                    --region "${AWS_REGION}" 2>/dev/null || true
            done
        }
    else
        echo "python3 not found, cleaning up SSM parameters manually."
        for param in gateway_id gateway_target_id cognito_pool_id cognito_client_id; do
            aws ssm delete-parameter --name "/app/aiops/agentcore/${param}" \
                --region "${AWS_REGION}" 2>/dev/null || true
        done
    fi
else
    echo "No Gateway found in SSM. Skipping."
fi

# -----------------------------------------------------------------------
# Lambda 아티팩트 S3 버킷 정리
# -----------------------------------------------------------------------
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -n "$ACCOUNT_ID" ] && [ "$ACCOUNT_ID" != "None" ]; then
    LAMBDA_S3_BUCKET="aiops-agent-artifacts-${ACCOUNT_ID}-${AWS_REGION}"
    if aws s3 ls "s3://${LAMBDA_S3_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
        echo "Cleaning S3 bucket: ${LAMBDA_S3_BUCKET}"
        aws s3 rm "s3://${LAMBDA_S3_BUCKET}/aiops-gateway/" --recursive \
            --region "${AWS_REGION}" 2>/dev/null || true
    fi
fi

# -----------------------------------------------------------------------
# CloudFormation 스택 삭제
# -----------------------------------------------------------------------
echo "--- CloudFormation Cleanup ---"
echo "Deleting stack: ${STACK_NAME}..."
aws cloudformation delete-stack --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
echo "Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
echo "Stack deleted."

# Clean up SSM parameters not managed by stack
echo "Cleaning up remaining SSM parameters..."
for param in memory_id gateway_id gateway_target_id cognito_pool_id cognito_client_id; do
    aws ssm delete-parameter --name "/app/aiops/agentcore/${param}" \
        --region "${AWS_REGION}" 2>/dev/null || true
done

echo "=== Cleanup Complete ==="
