#!/bin/bash
set -euo pipefail

STACK_NAME=${1:-AIOpsAgentInfra}

REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-2")
export AWS_REGION="${REGION}"

echo "=== AIOps Agent Cleanup ==="
echo "Region: ${AWS_REGION}"

# Confirm
read -p "Delete stack '${STACK_NAME}' and clean up SSM parameters? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Delete CloudFormation stack
echo "Deleting stack: ${STACK_NAME}..."
aws cloudformation delete-stack --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
echo "Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
echo "Stack deleted."

# Clean up SSM parameters not managed by stack
echo "Cleaning up SSM parameters..."
for param in memory_id gateway_id; do
    aws ssm delete-parameter --name "/app/aiops/agentcore/${param}" --region "${AWS_REGION}" 2>/dev/null || true
done

echo "=== Cleanup Complete ==="
