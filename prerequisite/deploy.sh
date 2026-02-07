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
