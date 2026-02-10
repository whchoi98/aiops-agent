"""자산 인벤토리 페이지 — Steampipe (AWS + K8s)"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd

from tools.steampipe_tools import (
    get_asset_summary,
    get_k8s_cluster_summary,
    query_inventory,
    run_steampipe_query,
)

st.set_page_config(page_title="자산 인벤토리", page_icon="📋", layout="wide")
st.title("📋 자산 인벤토리")
st.caption("Steampipe 기반 AWS + Kubernetes 통합 자산 관리")

RESOURCE_TYPES = [
    "ec2", "s3", "rds", "lambda", "iam_user", "iam_role",
    "vpc", "subnet", "security_group", "ebs", "alb", "eks", "ecs",
    "cloudfront", "dynamodb", "sqs", "sns", "kms",
    "pod", "deployment", "service", "namespace", "node",
    "configmap", "daemonset", "statefulset", "job", "cronjob",
]


@st.cache_data(ttl=300, show_spinner="AWS 자산 요약 조회 중…")
def _load_asset_summary() -> dict:
    return get_asset_summary()


@st.cache_data(ttl=300, show_spinner="K8s 클러스터 요약 조회 중…")
def _load_k8s_summary() -> dict:
    return get_k8s_cluster_summary()


@st.cache_data(ttl=120, show_spinner="인벤토리 조회 중…")
def _query_inventory(rtype: str) -> dict:
    return query_inventory(resource_type=rtype)


@st.cache_data(ttl=120, show_spinner="Steampipe 쿼리 실행 중…")
def _run_query(q: str) -> dict:
    return run_steampipe_query(query=q)


# ── 1) AWS 자산 요약 ──
st.subheader("AWS 자산 요약")
asset = _load_asset_summary()
if not asset.get("success") and asset.get("errors"):
    st.warning(f"일부 조회 실패: {len(asset['errors'])}건")

summary = asset.get("summary", {})

aws_keys = [
    ("EC2", "ec2_instances"),
    ("EC2 Running", "ec2_running"),
    ("S3", "s3_buckets"),
    ("RDS", "rds_instances"),
    ("Lambda", "lambda_functions"),
    ("VPC", "vpcs"),
    ("SG", "security_groups"),
    ("IAM Users", "iam_users"),
    ("IAM Roles", "iam_roles"),
    ("EKS", "eks_clusters"),
    ("ECS", "ecs_clusters"),
    ("EBS", "ebs_volumes"),
]

cols = st.columns(6)
for i, (label, key) in enumerate(aws_keys):
    cols[i % 6].metric(label, summary.get(key, "–"))

st.metric("총 AWS 리소스", asset.get("total_resources", "–"))

st.divider()

# ── 2) K8s 클러스터 요약 ──
st.subheader("Kubernetes 클러스터 요약")
k8s = _load_k8s_summary()

k8s_summary = k8s.get("summary", {})
k8s_keys = [
    ("Namespaces", "namespaces"),
    ("Nodes", "nodes"),
    ("Pods (전체)", "pods_total"),
    ("Pods (Running)", "pods_running"),
    ("Deployments", "deployments"),
    ("Services", "services"),
    ("DaemonSets", "daemonsets"),
    ("StatefulSets", "statefulsets"),
    ("Jobs", "jobs"),
    ("CronJobs", "cronjobs"),
]
cols = st.columns(5)
for i, (label, key) in enumerate(k8s_keys):
    cols[i % 5].metric(label, k8s_summary.get(key, "–"))

if k8s.get("errors"):
    with st.expander("K8s 조회 오류"):
        for err in k8s["errors"]:
            st.text(err)

st.divider()

# ── 3) 리소스 유형별 조회 ──
st.subheader("리소스 유형별 조회")

selected = st.selectbox("리소스 유형", RESOURCE_TYPES)
if selected:
    data = _query_inventory(selected)
    if not data.get("success"):
        st.warning(data.get("error", "조회 실패"))
    else:
        items = data.get("data", [])
        st.metric(f"{selected} 리소스 수", data.get("count", 0))
        if items:
            st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)

st.divider()

# ── 4) 사용자 정의 SQL 쿼리 ──
st.subheader("Steampipe SQL 쿼리")
st.caption("AWS / Kubernetes 테이블에 대해 자유 SQL 쿼리를 실행합니다.")

default_query = "SELECT instance_id, title, instance_type, instance_state FROM aws_ec2_instance LIMIT 10"
user_query = st.text_area("SQL 쿼리", value=default_query, height=100)

if st.button("실행", type="primary"):
    result = _run_query(user_query)
    if not result.get("success"):
        st.error(result.get("error", "쿼리 실패"))
    else:
        items = result.get("data", [])
        if items and isinstance(items, list):
            st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
        else:
            st.info("결과가 없습니다.")
