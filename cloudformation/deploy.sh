#!/bin/bash
# =============================================================================
# AIOps Platform - Unified Deployment Script
#
# Usage:
#   ./deploy.sh phase1          # Phase 1: VPC + CloudFront + ALB + EC2
#   ./deploy.sh phase2          # Phase 2: AgentCore IAM + Lambda
#   ./deploy.sh all             # Phase 1 -> Phase 2 sequential deploy
#   ./deploy.sh status          # Show both stack statuses
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE1_STACK="${PHASE1_STACK_NAME:-aiops-phase1}"
PHASE2_STACK="${PHASE2_STACK_NAME:-aiops-phase2}"

# Region
if [ -z "${AWS_REGION:-}" ]; then
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-2")
    export AWS_REGION
fi
echo "Region: ${AWS_REGION}"

# Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "None" ]; then
    echo "ERROR: Failed to get AWS Account ID. Check your credentials."
    exit 1
fi
echo "Account: ${ACCOUNT_ID}"

# =============================================================================
# Phase 1: Base Infrastructure (VPC + CF + ALB + EC2)
# =============================================================================
deploy_phase1() {
    echo ""
    echo "============================================="
    echo " Phase 1: Base Infrastructure"
    echo " Stack: ${PHASE1_STACK}"
    echo "============================================="

    # CloudFront Prefix List auto-discovery
    echo "Looking up CloudFront origin-facing prefix list..."
    PREFIX_LIST_ID=$(aws ec2 describe-managed-prefix-lists \
        --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
        --query 'PrefixLists[0].PrefixListId' --output text --region "${AWS_REGION}")

    if [ -z "$PREFIX_LIST_ID" ] || [ "$PREFIX_LIST_ID" = "None" ]; then
        echo "ERROR: Could not find CloudFront origin-facing prefix list."
        echo "       Make sure you are in a region that supports CloudFront prefix lists."
        exit 1
    fi
    echo "CloudFront Prefix List: ${PREFIX_LIST_ID}"

    # VSCode password prompt
    read -sp "VSCode Password (min 8 chars): " VSCODE_PW
    echo ""
    if [ ${#VSCODE_PW} -lt 8 ]; then
        echo "ERROR: Password must be at least 8 characters."
        exit 1
    fi

    # Validate template
    echo "Validating Phase 1 template..."
    aws cloudformation validate-template \
        --template-body "file://${SCRIPT_DIR}/phase1-base-infra.yaml" \
        --region "${AWS_REGION}" > /dev/null

    # Deploy
    echo "Deploying Phase 1 stack: ${PHASE1_STACK}..."
    output=$(aws cloudformation deploy \
        --stack-name "${PHASE1_STACK}" \
        --template-file "${SCRIPT_DIR}/phase1-base-infra.yaml" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameter-overrides \
            "CloudFrontPrefixListId=${PREFIX_LIST_ID}" \
            "VSCodePassword=${VSCODE_PW}" \
        --region "${AWS_REGION}" 2>&1) || {
        if echo "$output" | grep -qi "No changes to deploy"; then
            echo "No updates needed for stack ${PHASE1_STACK}."
        else
            echo "Error deploying Phase 1:"
            echo "$output"
            exit 1
        fi
    }

    echo ""
    echo "Phase 1 deployed successfully."
    aws cloudformation describe-stacks \
        --stack-name "${PHASE1_STACK}" \
        --query 'Stacks[0].Outputs' \
        --output table \
        --region "${AWS_REGION}"
}

# =============================================================================
# Lambda Packaging (reused from prerequisite/deploy.sh pattern)
# =============================================================================
package_lambda() {
    LAMBDA_S3_BUCKET="aiops-agent-artifacts-${ACCOUNT_ID}-${AWS_REGION}"
    LAMBDA_S3_KEY="aiops-gateway/lambda.zip"
    LAMBDA_ZIP="/tmp/aiops-gateway-lambda.zip"

    echo ""
    echo "=== Lambda Packaging ==="

    # S3 bucket (create if missing)
    if ! aws s3 ls "s3://${LAMBDA_S3_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
        echo "Creating S3 bucket: ${LAMBDA_S3_BUCKET}"
        if [ "${AWS_REGION}" = "us-east-1" ]; then
            aws s3 mb "s3://${LAMBDA_S3_BUCKET}" --region "${AWS_REGION}"
        else
            aws s3 mb "s3://${LAMBDA_S3_BUCKET}" --region "${AWS_REGION}" \
                --create-bucket-configuration LocationConstraint="${AWS_REGION}"
        fi
    fi

    # Build zip
    echo "Packaging Lambda code..."
    rm -f "${LAMBDA_ZIP}"

    PACKAGE_DIR=$(mktemp -d)
    # Bundle strands-agents (boto3 is included in Lambda runtime)
    pip install strands-agents -t "${PACKAGE_DIR}" --quiet 2>/dev/null || true

    # Source directories are relative to the repo root (one level up from cloudformation/)
    REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
    if [ -d "${REPO_ROOT}/gateway" ]; then
        cp -r "${REPO_ROOT}/gateway/" "${PACKAGE_DIR}/gateway/"
    else
        echo "WARNING: ${REPO_ROOT}/gateway/ not found. Lambda zip may be incomplete."
    fi
    if [ -d "${REPO_ROOT}/tools" ]; then
        cp -r "${REPO_ROOT}/tools/" "${PACKAGE_DIR}/tools/"
    else
        echo "WARNING: ${REPO_ROOT}/tools/ not found. Lambda zip may be incomplete."
    fi

    (cd "${PACKAGE_DIR}" && zip -r "${LAMBDA_ZIP}" . -x "__pycache__/*" "*.pyc") > /dev/null
    rm -rf "${PACKAGE_DIR}"

    echo "Uploading to s3://${LAMBDA_S3_BUCKET}/${LAMBDA_S3_KEY}"
    aws s3 cp "${LAMBDA_ZIP}" "s3://${LAMBDA_S3_BUCKET}/${LAMBDA_S3_KEY}" \
        --region "${AWS_REGION}" > /dev/null
    rm -f "${LAMBDA_ZIP}"
    echo "Lambda package uploaded."
}

# =============================================================================
# Phase 2: AgentCore Prerequisites (IAM + Lambda + EC2 policy)
# =============================================================================
deploy_phase2() {
    echo ""
    echo "============================================="
    echo " Phase 2: AgentCore Prerequisites"
    echo " Stack: ${PHASE2_STACK}"
    echo " Phase1 ref: ${PHASE1_STACK}"
    echo "============================================="

    # Verify Phase 1 exists
    if ! aws cloudformation describe-stacks --stack-name "${PHASE1_STACK}" \
        --region "${AWS_REGION}" > /dev/null 2>&1; then
        echo "ERROR: Phase 1 stack '${PHASE1_STACK}' not found."
        echo "       Deploy Phase 1 first:  ./deploy.sh phase1"
        exit 1
    fi
    echo "Phase 1 stack found: ${PHASE1_STACK}"

    # Package Lambda
    package_lambda

    # Validate template
    echo "Validating Phase 2 template..."
    aws cloudformation validate-template \
        --template-body "file://${SCRIPT_DIR}/phase2-agentcore-prereq.yaml" \
        --region "${AWS_REGION}" > /dev/null

    # Deploy
    echo "Deploying Phase 2 stack: ${PHASE2_STACK}..."
    output=$(aws cloudformation deploy \
        --stack-name "${PHASE2_STACK}" \
        --template-file "${SCRIPT_DIR}/phase2-agentcore-prereq.yaml" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameter-overrides \
            "Phase1StackName=${PHASE1_STACK}" \
            "LambdaS3Bucket=${LAMBDA_S3_BUCKET}" \
            "LambdaS3Key=${LAMBDA_S3_KEY}" \
        --region "${AWS_REGION}" 2>&1) || {
        if echo "$output" | grep -qi "No changes to deploy"; then
            echo "No updates needed for stack ${PHASE2_STACK}."
        else
            echo "Error deploying Phase 2:"
            echo "$output"
            exit 1
        fi
    }

    echo ""
    echo "Phase 2 deployed successfully."
    aws cloudformation describe-stacks \
        --stack-name "${PHASE2_STACK}" \
        --query 'Stacks[0].Outputs' \
        --output table \
        --region "${AWS_REGION}"

    echo ""
    echo "Next step: python -m gateway.setup_gateway  (Cognito + AgentCore Gateway)"
}

# =============================================================================
# Status: Show both stack statuses
# =============================================================================
show_status() {
    echo ""
    echo "============================================="
    echo " Stack Status"
    echo "============================================="

    for STACK in "${PHASE1_STACK}" "${PHASE2_STACK}"; do
        echo ""
        echo "--- ${STACK} ---"
        if aws cloudformation describe-stacks --stack-name "${STACK}" \
            --region "${AWS_REGION}" > /dev/null 2>&1; then
            STATUS=$(aws cloudformation describe-stacks --stack-name "${STACK}" \
                --query 'Stacks[0].StackStatus' --output text --region "${AWS_REGION}")
            echo "Status: ${STATUS}"
            aws cloudformation describe-stacks --stack-name "${STACK}" \
                --query 'Stacks[0].Outputs' --output table --region "${AWS_REGION}" 2>/dev/null || true
        else
            echo "Status: NOT DEPLOYED"
        fi
    done
}

# =============================================================================
# Main
# =============================================================================
usage() {
    echo "Usage: $0 {phase1|phase2|all|status}"
    echo ""
    echo "Commands:"
    echo "  phase1   Deploy Phase 1 (VPC + CloudFront + ALB + EC2)"
    echo "  phase2   Deploy Phase 2 (AgentCore IAM + Lambda + EC2 policy)"
    echo "  all      Deploy Phase 1 then Phase 2"
    echo "  status   Show both stack statuses"
    echo ""
    echo "Environment variables:"
    echo "  PHASE1_STACK_NAME  Phase 1 stack name (default: aiops-phase1)"
    echo "  PHASE2_STACK_NAME  Phase 2 stack name (default: aiops-phase2)"
    echo "  AWS_REGION         AWS region (default: ap-northeast-2)"
}

case "${1:-}" in
    phase1)
        deploy_phase1
        ;;
    phase2)
        deploy_phase2
        ;;
    all)
        deploy_phase1
        deploy_phase2
        ;;
    status)
        show_status
        ;;
    *)
        usage
        exit 1
        ;;
esac
