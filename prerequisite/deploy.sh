#!/bin/bash
set -euo pipefail

STACK_NAME=${1:-AIOpsAgentInfra}
TEMPLATE_FILE="prerequisite/infrastructure.yaml"

# Region
if [ -z "${AWS_REGION:-}" ]; then
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-2")
    export AWS_REGION
fi
echo "Region: ${AWS_REGION}"

# Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "None" ]; then
    echo "Failed to get AWS Account ID. Check your credentials."
    exit 1
fi
echo "Account ID: ${ACCOUNT_ID}"

# -----------------------------------------------------------------------
# Lambda 패키징 — gateway/ + tools/ 를 zip 으로 묶어 S3 업로드
# -----------------------------------------------------------------------
LAMBDA_S3_BUCKET="aiops-agent-artifacts-${ACCOUNT_ID}-${AWS_REGION}"
LAMBDA_S3_KEY="aiops-gateway/lambda.zip"
LAMBDA_ZIP="/tmp/aiops-gateway-lambda.zip"

echo "=== Lambda Packaging ==="

# S3 버킷 생성 (없으면)
if ! aws s3 ls "s3://${LAMBDA_S3_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
    echo "Creating S3 bucket: ${LAMBDA_S3_BUCKET}"
    if [ "${AWS_REGION}" = "us-east-1" ]; then
        aws s3 mb "s3://${LAMBDA_S3_BUCKET}" --region "${AWS_REGION}"
    else
        aws s3 mb "s3://${LAMBDA_S3_BUCKET}" --region "${AWS_REGION}" \
            --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    fi
fi

# zip 패키징 (gateway/, tools/, strands 런타임은 Lambda Layer 또는 번들)
echo "Packaging Lambda code..."
rm -f "${LAMBDA_ZIP}"

# pip install 로 의존성 번들 (boto3 는 Lambda 런타임에 포함이므로 제외)
PACKAGE_DIR=$(mktemp -d)
pip install strands-agents -t "${PACKAGE_DIR}" --quiet 2>/dev/null || true

# 소스 복사
cp -r gateway/ "${PACKAGE_DIR}/gateway/"
cp -r tools/ "${PACKAGE_DIR}/tools/"

# zip 생성
(cd "${PACKAGE_DIR}" && zip -r "${LAMBDA_ZIP}" . -x "__pycache__/*" "*.pyc") > /dev/null
rm -rf "${PACKAGE_DIR}"

echo "Uploading to s3://${LAMBDA_S3_BUCKET}/${LAMBDA_S3_KEY}"
aws s3 cp "${LAMBDA_ZIP}" "s3://${LAMBDA_S3_BUCKET}/${LAMBDA_S3_KEY}" \
    --region "${AWS_REGION}" > /dev/null
rm -f "${LAMBDA_ZIP}"
echo "Lambda package uploaded."

# -----------------------------------------------------------------------
# CloudFormation 배포
# -----------------------------------------------------------------------

# Validate template
echo "Validating CloudFormation template..."
aws cloudformation validate-template \
    --template-body "file://${TEMPLATE_FILE}" \
    --region "${AWS_REGION}" > /dev/null

# Deploy
echo "Deploying stack: ${STACK_NAME}..."
output=$(aws cloudformation deploy \
    --stack-name "${STACK_NAME}" \
    --template-file "${TEMPLATE_FILE}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        "LambdaS3Bucket=${LAMBDA_S3_BUCKET}" \
        "LambdaS3Key=${LAMBDA_S3_KEY}" \
    --region "${AWS_REGION}" 2>&1) || {
    if echo "$output" | grep -qi "No changes to deploy"; then
        echo "No updates needed for stack ${STACK_NAME}."
    else
        echo "Error deploying stack:"
        echo "$output"
        exit 1
    fi
}

echo "Stack ${STACK_NAME} deployed successfully."

# Show outputs
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query 'Stacks[0].Outputs' \
    --output table \
    --region "${AWS_REGION}"
