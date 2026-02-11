"""도구 단위 테스트 (moto 모킹)"""

import boto3
import pytest
from moto import mock_aws


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture
def ec2_client():
    with mock_aws():
        client = boto3.client("ec2", region_name="ap-northeast-2")
        yield client


@pytest.fixture
def ec2_instances(ec2_client):
    """테스트용 EC2 인스턴스 생성"""
    response = ec2_client.run_instances(
        ImageId="ami-12345678",
        InstanceType="t3.micro",
        MinCount=2,
        MaxCount=2,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": "test-instance"}],
            }
        ],
    )
    return [inst["InstanceId"] for inst in response["Instances"]]


# ---------------------------------------------------------------------------
# EC2 describe_ec2_instances Tests (moved from cloudwatch_tools to ec2_tools)
# ---------------------------------------------------------------------------

class TestDescribeEC2Instances:
    @mock_aws
    def test_describe_ec2_instances_empty(self):
        from tools.ec2_tools import describe_ec2_instances

        result = describe_ec2_instances()
        assert result["total_count"] == 0
        assert result["instances"] == []

    @mock_aws
    def test_describe_ec2_instances_with_data(self):
        from tools.ec2_tools import describe_ec2_instances

        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t3.micro",
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": "web-server"}],
                }
            ],
        )

        result = describe_ec2_instances()
        assert result["total_count"] == 1
        assert result["running_count"] == 1
        assert result["instances"][0]["name"] == "web-server"
        assert result["instances"][0]["type"] == "t3.micro"


# ---------------------------------------------------------------------------
# EC2 Tools Tests
# ---------------------------------------------------------------------------

class TestEC2Tools:
    @mock_aws
    def test_list_ec2_instances_empty(self):
        from tools.ec2_tools import list_ec2_instances

        result = list_ec2_instances()
        assert result["total_count"] == 0

    @mock_aws
    def test_list_ec2_instances_with_data(self):
        from tools.ec2_tools import list_ec2_instances

        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t3.micro",
            MinCount=3,
            MaxCount=3,
        )

        result = list_ec2_instances()
        assert result["total_count"] == 3
        assert result["running_count"] == 3

    @mock_aws
    def test_list_ec2_instances_filter_by_state(self):
        from tools.ec2_tools import list_ec2_instances

        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        resp = ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t3.micro",
            MinCount=2,
            MaxCount=2,
        )
        instance_id = resp["Instances"][0]["InstanceId"]
        ec2.stop_instances(InstanceIds=[instance_id])

        result = list_ec2_instances(state="running")
        assert result["total_count"] == 1

    @mock_aws
    def test_get_ebs_volumes_empty(self):
        from tools.ec2_tools import get_ebs_volumes

        result = get_ebs_volumes()
        assert result["total_count"] == 0
        assert result["total_size_gb"] == 0

    @mock_aws
    def test_get_ebs_volumes_with_data(self):
        from tools.ec2_tools import get_ebs_volumes

        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        ec2.create_volume(
            AvailabilityZone="ap-northeast-2a",
            Size=100,
            VolumeType="gp3",
        )

        result = get_ebs_volumes()
        assert result["total_count"] == 1
        assert result["volumes"][0]["size_gb"] == 100
        assert result["volumes"][0]["volume_type"] == "gp3"

    @mock_aws
    def test_get_instance_status(self):
        from tools.ec2_tools import get_instance_status

        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        resp = ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t3.micro",
            MinCount=1,
            MaxCount=1,
        )
        instance_id = resp["Instances"][0]["InstanceId"]

        result = get_instance_status(instance_ids=[instance_id])
        assert result["total_count"] == 1
        assert result["statuses"][0]["instance_id"] == instance_id


# ---------------------------------------------------------------------------
# VPC Tools Tests
# ---------------------------------------------------------------------------

class TestVPCTools:
    @mock_aws
    def test_describe_vpcs(self):
        from tools.vpc_tools import describe_vpcs

        result = describe_vpcs()
        # moto creates a default VPC
        assert result["total_count"] >= 1

    @mock_aws
    def test_describe_subnets(self):
        from tools.vpc_tools import describe_subnets

        result = describe_subnets()
        assert "total_count" in result
        assert "subnets" in result

    @mock_aws
    def test_describe_security_groups(self):
        from tools.vpc_tools import describe_security_groups

        result = describe_security_groups()
        # default SG always exists
        assert result["total_count"] >= 1

    @mock_aws
    def test_describe_route_tables(self):
        from tools.vpc_tools import describe_route_tables

        result = describe_route_tables()
        assert result["total_count"] >= 1

    @mock_aws
    def test_analyze_network_topology(self):
        from tools.vpc_tools import analyze_network_topology, describe_vpcs

        vpcs = describe_vpcs()
        if vpcs["vpcs"]:
            vpc_id = vpcs["vpcs"][0]["vpc_id"]
            result = analyze_network_topology(vpc_id=vpc_id)
            assert "vpc" in result
            assert "summary" in result
            assert "az_distribution" in result


# ---------------------------------------------------------------------------
# Resource Inventory Tests
# ---------------------------------------------------------------------------

class TestResourceInventory:
    @mock_aws
    def test_get_resource_summary(self):
        from tools.resource_inventory import get_resource_summary

        result = get_resource_summary()
        assert "summary" in result
        assert "total_resources" in result
        assert isinstance(result["summary"]["ec2_instances"], int)

    @mock_aws
    def test_list_resources_by_type_ec2(self):
        from tools.resource_inventory import list_resources_by_type

        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t3.micro",
            MinCount=1,
            MaxCount=1,
        )

        result = list_resources_by_type(resource_type="ec2")
        assert result["count"] == 1
        assert result["resource_type"] == "ec2"

    @mock_aws
    def test_list_resources_by_type_unknown(self):
        from tools.resource_inventory import list_resources_by_type

        result = list_resources_by_type(resource_type="unknown")
        assert "error" in result

    @mock_aws
    def test_list_resources_by_type_vpc(self):
        from tools.resource_inventory import list_resources_by_type

        result = list_resources_by_type(resource_type="vpc")
        assert result["resource_type"] == "vpc"
        assert result["count"] >= 1  # default VPC
