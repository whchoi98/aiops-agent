#!/bin/bash
# AgentCore Runtime 배포 스크립트
# Usage:
#   bash scripts/deploy_runtime.sh all            # 전체 에이전트 배포
#   bash scripts/deploy_runtime.sh monitoring      # 개별 에이전트 배포
#   bash scripts/deploy_runtime.sh list            # 배포된 에이전트 목록
#   bash scripts/deploy_runtime.sh status          # 에이전트 상태 확인

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

AWS_REGION="${AWS_REGION:-ap-northeast-2}"

# Runtime 실행 역할 ARN 조회
get_runtime_role_arn() {
    local arn
    arn=$(aws ssm get-parameter \
        --name /app/aiops/agentcore/runtime_execution_role_arn \
        --query 'Parameter.Value' --output text 2>/dev/null) || {
        echo "ERROR: SSM 파라미터 /app/aiops/agentcore/runtime_execution_role_arn 을 찾을 수 없습니다."
        echo "Phase 2 인프라 배포(IAM 역할)가 완료되었는지 확인하세요."
        exit 1
    }
    echo "$arn"
}

# 에이전트 정의: name → entrypoint 매핑
declare -A AGENTS=(
    [monitoring]="src.agents.monitoring.agent:app"
    [cost]="src.agents.cost_optimizer.agent:app"
    [security]="src.agents.security.agent:app"
    [resource]="src.agents.resource_manager.agent:app"
    [inventory]="src.agents.inventory.agent:app"
    [incident]="src.agents.incident_response.agent:app"
)

usage() {
    echo "Usage: $0 {all|list|status|<agent-name>}"
    echo ""
    echo "Commands:"
    echo "  all       전체 에이전트 배포"
    echo "  list      배포된 에이전트 목록"
    echo "  status    에이전트 상태 및 최근 로그"
    echo ""
    echo "Agents:"
    for name in "${!AGENTS[@]}"; do
        echo "  ${name}"
    done | sort
    exit 1
}

deploy_agent() {
    local name=$1
    local entrypoint=${AGENTS[$name]}
    local agent_name="aiops-${name}-agent"

    echo "Deploying ${agent_name}..."
    echo "  Entrypoint: ${entrypoint}"

    agentcore launch \
        --name "${agent_name}" \
        --entrypoint "${entrypoint}" \
        --execution-role-arn "${RUNTIME_ROLE_ARN}" \
        --env "AWS_REGION=${AWS_REGION}"

    echo "  ✓ ${agent_name} 배포 완료"
    echo ""
}

deploy_all() {
    echo "=== 전체 에이전트 AgentCore Runtime 배포 ==="
    echo "Region: ${AWS_REGION}"
    echo "Role: ${RUNTIME_ROLE_ARN}"
    echo ""

    for name in $(echo "${!AGENTS[@]}" | tr ' ' '\n' | sort); do
        deploy_agent "$name"
    done

    echo "=== 전체 배포 완료 ==="
}

list_agents() {
    echo "=== 배포된 AIOps 에이전트 ==="
    agentcore list | grep -i aiops || echo "배포된 에이전트가 없습니다."
}

show_status() {
    echo "=== 에이전트 상태 ==="
    for name in $(echo "${!AGENTS[@]}" | tr ' ' '\n' | sort); do
        local agent_name="aiops-${name}-agent"
        echo "--- ${agent_name} ---"
        agentcore logs --name "${agent_name}" --tail 5 2>/dev/null || echo "  Not deployed"
        echo ""
    done
}

# 메인 실행
if [[ $# -eq 0 ]]; then
    usage
fi

case "${1}" in
    all)
        RUNTIME_ROLE_ARN=$(get_runtime_role_arn)
        deploy_all
        ;;
    list)
        list_agents
        ;;
    status)
        show_status
        ;;
    -h|--help)
        usage
        ;;
    *)
        if [[ -n "${AGENTS[$1]:-}" ]]; then
            RUNTIME_ROLE_ARN=$(get_runtime_role_arn)
            deploy_agent "$1"
        else
            echo "ERROR: 알 수 없는 에이전트: $1"
            echo ""
            usage
        fi
        ;;
esac
