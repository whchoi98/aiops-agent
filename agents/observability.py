"""AgentCore Observability — OpenTelemetry 설정 및 세션 컨텍스트 관리

AWS OpenTelemetry Python Distro를 사용하여 Strands 에이전트의
트레이스/메트릭/로그를 CloudWatch GenAI Observability로 전송합니다.

사용법:
  1. configure_otel_env()로 환경 변수 설정
  2. opentelemetry-instrument python -m agents.<domain>.runtime 으로 실행
  3. CloudWatch > GenAI Observability > Bedrock AgentCore 에서 확인

참조: E2E 튜토리얼 Optional-lab-agentcore-observability.ipynb
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 기본 설정값
# ---------------------------------------------------------------------------

DEFAULT_LOG_GROUP = "agents/aiops-agent-logs"
DEFAULT_LOG_STREAM = "default"
DEFAULT_METRIC_NAMESPACE = "agents"
DEFAULT_SERVICE_NAME = "aiops-agent-strands"

# OTEL 환경 변수 매핑
OTEL_ENV_DEFAULTS: dict[str, str] = {
    "OTEL_PYTHON_DISTRO": "aws_distro",
    "OTEL_PYTHON_CONFIGURATOR": "aws_configurator",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
    "OTEL_TRACES_EXPORTER": "otlp",
    "AGENT_OBSERVABILITY_ENABLED": "true",
}


# ---------------------------------------------------------------------------
# 환경 변수 설정
# ---------------------------------------------------------------------------

def configure_otel_env(
    log_group: str = DEFAULT_LOG_GROUP,
    log_stream: str = DEFAULT_LOG_STREAM,
    metric_namespace: str = DEFAULT_METRIC_NAMESPACE,
    service_name: str = DEFAULT_SERVICE_NAME,
) -> dict[str, str]:
    """OTEL 환경 변수를 설정합니다.

    opentelemetry-instrument CLI에서 참조하는 환경 변수를 os.environ에 주입합니다.
    이미 설정된 변수는 덮어쓰지 않습니다.

    Args:
        log_group: CloudWatch 로그 그룹 이름
        log_stream: CloudWatch 로그 스트림 이름
        metric_namespace: CloudWatch 메트릭 네임스페이스
        service_name: 서비스 식별자 (OTEL_RESOURCE_ATTRIBUTES)

    Returns:
        설정된 환경 변수 딕셔너리
    """
    env_vars = {
        **OTEL_ENV_DEFAULTS,
        "OTEL_EXPORTER_OTLP_LOGS_HEADERS": (
            f"x-aws-log-group={log_group},"
            f"x-aws-log-stream={log_stream},"
            f"x-aws-metric-namespace={metric_namespace}"
        ),
        "OTEL_RESOURCE_ATTRIBUTES": f"service.name={service_name}",
    }

    configured = {}
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
        configured[key] = os.environ[key]

    logger.info("OTEL environment configured: %s", list(configured.keys()))
    return configured


def write_dotenv(
    output_path: str = ".env",
    log_group: str = DEFAULT_LOG_GROUP,
    log_stream: str = DEFAULT_LOG_STREAM,
    metric_namespace: str = DEFAULT_METRIC_NAMESPACE,
    service_name: str = DEFAULT_SERVICE_NAME,
) -> str:
    """OTEL 환경 변수를 .env 파일로 출력합니다.

    Args:
        output_path: 출력 파일 경로
        log_group: CloudWatch 로그 그룹 이름
        log_stream: CloudWatch 로그 스트림 이름
        metric_namespace: CloudWatch 메트릭 네임스페이스
        service_name: 서비스 식별자

    Returns:
        생성된 .env 파일 경로
    """
    from agents.utils import get_aws_region, get_aws_account_id

    region = get_aws_region()
    account_id = get_aws_account_id()

    lines = [
        f"AWS_REGION={region}",
        f"AWS_DEFAULT_REGION={region}",
        f"AWS_ACCOUNT_ID={account_id}",
        "",
        "# OpenTelemetry — AWS CloudWatch GenAI Observability",
        f"OTEL_PYTHON_DISTRO={OTEL_ENV_DEFAULTS['OTEL_PYTHON_DISTRO']}",
        f"OTEL_PYTHON_CONFIGURATOR={OTEL_ENV_DEFAULTS['OTEL_PYTHON_CONFIGURATOR']}",
        f"OTEL_EXPORTER_OTLP_PROTOCOL={OTEL_ENV_DEFAULTS['OTEL_EXPORTER_OTLP_PROTOCOL']}",
        f"OTEL_TRACES_EXPORTER={OTEL_ENV_DEFAULTS['OTEL_TRACES_EXPORTER']}",
        (
            f"OTEL_EXPORTER_OTLP_LOGS_HEADERS="
            f"x-aws-log-group={log_group},"
            f"x-aws-log-stream={log_stream},"
            f"x-aws-metric-namespace={metric_namespace}"
        ),
        f"OTEL_RESOURCE_ATTRIBUTES=service.name={service_name}",
        f"AGENT_OBSERVABILITY_ENABLED={OTEL_ENV_DEFAULTS['AGENT_OBSERVABILITY_ENABLED']}",
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    logger.info("Wrote OTEL .env to %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# 세션 컨텍스트 (OpenTelemetry Baggage)
# ---------------------------------------------------------------------------

def attach_session_context(session_id: str) -> object | None:
    """세션 ID를 OpenTelemetry baggage에 첨부합니다.

    트레이스와 세션을 연결하여 CloudWatch GenAI Observability에서
    세션별로 추적할 수 있습니다.

    Args:
        session_id: 세션 식별자

    Returns:
        context token (detach 시 사용), OTEL 미설치 시 None
    """
    try:
        from opentelemetry import baggage, context

        ctx = baggage.set_baggage("session.id", session_id)
        token = context.attach(ctx)
        logger.info("Session ID '%s' attached to telemetry context", session_id)
        return token
    except ImportError:
        logger.debug("opentelemetry not available, skipping session context")
        return None


def detach_session_context(token: object | None) -> None:
    """세션 컨텍스트를 해제합니다.

    Args:
        token: attach_session_context()에서 반환된 토큰
    """
    if token is None:
        return
    try:
        from opentelemetry import context

        context.detach(token)
        logger.info("Session context detached")
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# CloudWatch 로그 그룹 생성 유틸리티
# ---------------------------------------------------------------------------

def ensure_log_group(
    log_group: str = DEFAULT_LOG_GROUP,
    log_stream: str = DEFAULT_LOG_STREAM,
) -> None:
    """CloudWatch 로그 그룹/스트림이 존재하지 않으면 생성합니다.

    Args:
        log_group: 로그 그룹 이름
        log_stream: 로그 스트림 이름
    """
    import boto3

    logs_client = boto3.client("logs")

    try:
        logs_client.create_log_group(logGroupName=log_group)
        logger.info("Created log group: %s", log_group)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass

    try:
        logs_client.create_log_stream(
            logGroupName=log_group, logStreamName=log_stream
        )
        logger.info("Created log stream: %s", log_stream)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass
