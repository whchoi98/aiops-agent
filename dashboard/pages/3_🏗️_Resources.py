"""리소스 관리 페이지"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import plotly.express as px

from tools.ec2_tools import describe_ec2_instances, get_ebs_volumes
from tools.vpc_tools import describe_subnets, describe_vpcs
from tools.resource_inventory import list_resources_by_type

st.set_page_config(page_title="리소스 관리", page_icon="🏗️", layout="wide")
st.title("🏗️ 리소스 관리")

STATE_COLORS = {
    "running": "🟢",
    "stopped": "🔴",
    "terminated": "⚫",
    "pending": "🟡",
    "shutting-down": "🟠",
    "stopping": "🟠",
}


@st.cache_data(ttl=300, show_spinner="EC2 인스턴스 조회 중…")
def _load_ec2() -> dict:
    return describe_ec2_instances()


@st.cache_data(ttl=300, show_spinner="VPC 조회 중…")
def _load_vpcs() -> dict:
    return describe_vpcs()


@st.cache_data(ttl=300, show_spinner="서브넷 조회 중…")
def _load_subnets() -> dict:
    return describe_subnets()


@st.cache_data(ttl=300, show_spinner="EBS 볼륨 조회 중…")
def _load_ebs() -> dict:
    return get_ebs_volumes()


@st.cache_data(ttl=300, show_spinner="리소스 조회 중…")
def _load_resources(rtype: str) -> dict:
    return list_resources_by_type(resource_type=rtype)


# ── 1) EC2 인스턴스 ──
st.subheader("EC2 인스턴스 현황")
ec2 = _load_ec2()
instances = ec2.get("instances", [])

c1, c2, c3 = st.columns(3)
c1.metric("전체", ec2.get("total_count", 0))
c2.metric("실행 중", ec2.get("running_count", 0))
c3.metric("중지됨", ec2.get("stopped_count", 0))

if instances:
    df_ec2 = pd.DataFrame(instances)
    df_ec2["status"] = df_ec2["state"].map(lambda s: f"{STATE_COLORS.get(s, '⚪')} {s}")
    display_cols = [c for c in ["instance_id", "name", "type", "status", "private_ip", "public_ip", "vpc_id"] if c in df_ec2.columns]
    st.dataframe(df_ec2[display_cols], use_container_width=True, hide_index=True)
else:
    st.info("EC2 인스턴스가 없습니다.")

st.divider()

# ── 2) 네트워크 개요 ──
st.subheader("네트워크 토폴로지 개요")

left, right = st.columns(2)

with left:
    st.markdown("**VPC 목록**")
    vpcs = _load_vpcs()
    vpc_list = vpcs.get("vpcs", [])
    if vpc_list:
        st.dataframe(pd.DataFrame(vpc_list), use_container_width=True, hide_index=True)
    else:
        st.info("VPC가 없습니다.")

with right:
    st.markdown("**서브넷 목록**")
    subnets = _load_subnets()
    subnet_list = subnets.get("subnets", [])
    if subnet_list:
        df_sub = pd.DataFrame(subnet_list)
        display_cols = [c for c in ["subnet_id", "name", "vpc_id", "cidr_block", "availability_zone", "available_ip_count", "map_public_ip"] if c in df_sub.columns]
        st.dataframe(df_sub[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("서브넷이 없습니다.")

st.divider()

# ── 3) EBS 볼륨 ──
st.subheader("EBS 볼륨")
ebs = _load_ebs()
volumes = ebs.get("volumes", [])

c1, c2, c3 = st.columns(3)
c1.metric("전체 볼륨", ebs.get("total_count", 0))
c2.metric("미연결 볼륨", ebs.get("unattached_count", 0))
c3.metric("총 용량 (GB)", ebs.get("total_size_gb", 0))

if volumes:
    df_ebs = pd.DataFrame(volumes)
    display_cols = [c for c in ["volume_id", "name", "size_gb", "volume_type", "state", "encrypted", "availability_zone"] if c in df_ebs.columns]
    st.dataframe(df_ebs[display_cols], use_container_width=True, hide_index=True)

st.divider()

# ── 4) 리소스 유형별 조회 ──
st.subheader("리소스 유형별 조회")
resource_types = ["ec2", "s3", "rds", "lambda", "vpc", "security_group", "ebs"]
selected = st.selectbox("리소스 유형 선택", resource_types)

if selected:
    data = _load_resources(selected)
    if data.get("error"):
        st.warning(data["error"])
    else:
        st.metric(f"{selected} 리소스 수", data.get("count", 0))
        resources = data.get("resources", [])
        if resources:
            st.dataframe(pd.DataFrame(resources), use_container_width=True, hide_index=True)
