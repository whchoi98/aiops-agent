"""모니터링 도구 단위 테스트"""

import pytest
from moto import mock_aws

from src.agents.monitoring.tools import (
    describe_ec2_instances,
    get_cloudwatch_alarms,
    get_cloudwatch_metrics,
)


@pytest.fixture
def aws_credentials(monkeypatch):
    """AWS 자격증명 모킹"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")


@mock_aws
def test_describe_ec2_instances_empty(aws_credentials):
    """EC2 인스턴스가 없을 때 빈 결과 반환"""
    result = describe_ec2_instances()

    assert result["total_count"] == 0
    assert result["running_count"] == 0
    assert result["instances"] == []


@mock_aws
def test_get_cloudwatch_alarms_empty(aws_credentials):
    """알람이 없을 때 빈 결과 반환"""
    result = get_cloudwatch_alarms()

    assert result["total_count"] == 0
    assert result["alarm_count"] == 0
    assert result["alarms"] == []


@mock_aws
def test_get_cloudwatch_metrics(aws_credentials):
    """CloudWatch 메트릭 조회 테스트"""
    result = get_cloudwatch_metrics(
        namespace="AWS/EC2",
        metric_name="CPUUtilization",
        period_hours=1,
    )

    assert "namespace" in result
    assert result["namespace"] == "AWS/EC2"
    assert result["metric_name"] == "CPUUtilization"
    assert "datapoints" in result
    assert "summary" in result
