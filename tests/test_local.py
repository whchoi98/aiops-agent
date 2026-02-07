"""로컬 에이전트 통합 테스트 — import 및 구조 검증"""

import importlib

import pytest


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


class TestAIOpsAgentStructure:
    """에이전트 모듈 import 및 구조 검증"""

    def test_import_aiops_agent(self):
        mod = importlib.import_module("agents.aiops_agent")
        assert hasattr(mod, "MODEL_ID")
        assert hasattr(mod, "SYSTEM_PROMPT")
        assert hasattr(mod, "TOOLS")
        assert hasattr(mod, "create_agent")

    def test_model_id_format(self):
        from agents.aiops_agent import MODEL_ID

        assert "anthropic" in MODEL_ID
        assert "claude" in MODEL_ID

    def test_system_prompt_content(self):
        from agents.aiops_agent import SYSTEM_PROMPT

        assert "AWS" in SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 100

    def test_tools_list_not_empty(self):
        from agents.aiops_agent import TOOLS

        assert len(TOOLS) >= 10
        # All items should be callable
        for t in TOOLS:
            assert callable(t)

    def test_tools_have_expected_items(self):
        from agents.aiops_agent import TOOLS

        tool_names = []
        for t in TOOLS:
            name = getattr(t, "__name__", None) or getattr(t, "name", None)
            if name:
                tool_names.append(name)

        expected = [
            "get_cloudwatch_metrics",
            "get_cloudwatch_alarms",
            "list_ec2_instances",
            "get_cost_and_usage",
            "describe_vpcs",
            "get_resource_summary",
        ]
        for expected_name in expected:
            assert expected_name in tool_names, f"Missing tool: {expected_name}"


class TestToolModuleImports:
    """각 도구 모듈 import 검증"""

    def test_import_cloudwatch_tools(self):
        mod = importlib.import_module("tools.cloudwatch_tools")
        assert hasattr(mod, "get_cloudwatch_metrics")
        assert hasattr(mod, "get_cloudwatch_alarms")
        assert hasattr(mod, "query_cloudwatch_logs")
        assert hasattr(mod, "describe_ec2_instances")

    def test_import_vpc_tools(self):
        mod = importlib.import_module("tools.vpc_tools")
        assert hasattr(mod, "describe_vpcs")
        assert hasattr(mod, "describe_subnets")
        assert hasattr(mod, "describe_security_groups")
        assert hasattr(mod, "analyze_network_topology")

    def test_import_ec2_tools(self):
        mod = importlib.import_module("tools.ec2_tools")
        assert hasattr(mod, "list_ec2_instances")
        assert hasattr(mod, "get_instance_status")
        assert hasattr(mod, "get_ebs_volumes")

    def test_import_cost_explorer_tools(self):
        mod = importlib.import_module("tools.cost_explorer_tools")
        assert hasattr(mod, "get_cost_and_usage")
        assert hasattr(mod, "get_cost_forecast")
        assert hasattr(mod, "get_rightsizing_recommendations")
        assert hasattr(mod, "get_cost_by_service")

    def test_import_security_tools(self):
        mod = importlib.import_module("tools.security_tools")
        assert hasattr(mod, "get_security_findings")
        assert hasattr(mod, "get_guardduty_findings")
        assert hasattr(mod, "get_iam_credential_report")

    def test_import_resource_inventory(self):
        mod = importlib.import_module("tools.resource_inventory")
        assert hasattr(mod, "get_resource_summary")
        assert hasattr(mod, "list_resources_by_type")


class TestUtilsModule:
    """유틸리티 모듈 검증"""

    def test_import_utils(self):
        mod = importlib.import_module("agents.utils")
        assert hasattr(mod, "get_aws_region")
        assert hasattr(mod, "get_aws_account_id")
        assert hasattr(mod, "get_ssm_parameter")
        assert hasattr(mod, "put_ssm_parameter")
        assert hasattr(mod, "read_config")
        assert hasattr(mod, "create_agentcore_runtime_execution_role")

    def test_read_config_json(self, tmp_path):
        from agents.utils import read_config

        config_file = tmp_path / "test.json"
        config_file.write_text('{"key": "value"}')
        result = read_config(str(config_file))
        assert result == {"key": "value"}

    def test_read_config_yaml(self, tmp_path):
        from agents.utils import read_config

        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value\nnested:\n  a: 1\n")
        result = read_config(str(config_file))
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_read_config_not_found(self):
        from agents.utils import read_config

        with pytest.raises(FileNotFoundError):
            read_config("/nonexistent/path.json")
