#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------
# AgentCore Observability 래퍼 스크립트
#
# opentelemetry-instrument 를 통해 에이전트를 실행합니다.
# Strands 에이전트의 트레이스/메트릭/로그가 CloudWatch GenAI Observability로 전송됩니다.
#
# 사용법:
#   bash scripts/run_with_otel.sh                          # 통합 런타임
#   bash scripts/run_with_otel.sh agents.monitoring.runtime # 모니터링 런타임
#   bash scripts/run_with_otel.sh agents.cost.runtime       # 비용 런타임
#   bash scripts/run_with_otel.sh agents.security.runtime   # 보안 런타임
#   bash scripts/run_with_otel.sh agents.resource.runtime   # 리소스 런타임
#
# 환경 변수:
#   OTEL_SERVICE_NAME  — 서비스 이름 (기본: aiops-agent-strands)
#   OTEL_LOG_GROUP     — CloudWatch 로그 그룹 (기본: agents/aiops-agent-logs)
#   OTEL_LOG_STREAM    — CloudWatch 로그 스트림 (기본: default)
# -----------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

cd "${PROJECT_DIR}"

# 가상환경 활성화
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# AWS 리전 확인
REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || echo 'ap-northeast-2')}"
export AWS_REGION="${REGION}"
export AWS_DEFAULT_REGION="${REGION}"

# AWS 계정 ID
ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'unknown')}"
export AWS_ACCOUNT_ID="${ACCOUNT_ID}"

# OTEL 환경 변수 설정
SERVICE_NAME="${OTEL_SERVICE_NAME:-aiops-agent-strands}"
LOG_GROUP="${OTEL_LOG_GROUP:-agents/aiops-agent-logs}"
LOG_STREAM="${OTEL_LOG_STREAM:-default}"

export OTEL_PYTHON_DISTRO="aws_distro"
export OTEL_PYTHON_CONFIGURATOR="aws_configurator"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="x-aws-log-group=${LOG_GROUP},x-aws-log-stream=${LOG_STREAM},x-aws-metric-namespace=agents"
export OTEL_RESOURCE_ATTRIBUTES="service.name=${SERVICE_NAME}"
export AGENT_OBSERVABILITY_ENABLED="true"

# 실행할 모듈 (기본: 통합 런타임)
MODULE="${1:-agents.runtime}"

echo "=== AgentCore Observability ==="
echo "Module:    ${MODULE}"
echo "Service:   ${SERVICE_NAME}"
echo "Region:    ${REGION}"
echo "Log Group: ${LOG_GROUP}"
echo "==============================="

# CloudWatch 로그 그룹/스트림 생성 (없으면 생성)
python3 -c "
from agents.observability import ensure_log_group
ensure_log_group('${LOG_GROUP}', '${LOG_STREAM}')
print('Log group ready: ${LOG_GROUP}')
" 2>/dev/null || echo "Warning: Could not ensure log group (will be created on first write)"

# opentelemetry-instrument 로 실행
exec opentelemetry-instrument python -m "${MODULE}"
