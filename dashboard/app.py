"""AIOps Overview Dashboard — 메인 엔트리 포인트"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# aiops_agent 루트를 import 경로에 추가
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import plotly.express as px

from tools.resource_inventory import get_resource_summary
from tools.cost_explorer_tools import get_cost_by_service
from tools.security_tools import get_security_findings

# ── 페이지 설정 ──
st.set_page_config(
    page_title="AIOps Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("AWS AIOps Overview")
st.caption("리소스 현황 · 비용 분석 · 보안 요약")


# ── 캐싱 헬퍼 ──
@st.cache_data(ttl=300, show_spinner="리소스 요약 조회 중…")
def _load_resource_summary() -> dict:
    return get_resource_summary()


@st.cache_data(ttl=300, show_spinner="비용 데이터 조회 중…")
def _load_cost_by_service(days: int = 30) -> dict:
    return get_cost_by_service(days=days)


@st.cache_data(ttl=300, show_spinner="보안 발견 사항 조회 중…")
def _load_security_findings() -> dict:
    return get_security_findings()


# ── 1) 리소스 요약 ──
st.subheader("리소스 현황")

res = _load_resource_summary()
if res.get("errors"):
    st.warning(f"일부 리소스 조회 실패: {res['errors']}")

summary = res.get("summary", {})
cols = st.columns(5)
metric_map = [
    ("EC2 인스턴스", "ec2_instances", "ec2_running"),
    ("S3 버킷", "s3_buckets", None),
    ("RDS 인스턴스", "rds_instances", None),
    ("Lambda 함수", "lambda_functions", None),
    ("VPC", "vpcs", None),
]
for col, (label, key, sub_key) in zip(cols, metric_map):
    val = summary.get(key, "–")
    delta = None
    if sub_key:
        running = summary.get(sub_key, 0)
        if isinstance(running, int) and isinstance(val, int):
            delta = f"{running} running"
    col.metric(label, val, delta=delta)

cols2 = st.columns(5)
metric_map2 = [
    ("보안 그룹", "security_groups"),
    ("EBS 볼륨", "ebs_volumes"),
    ("IAM 사용자", "iam_users"),
    ("IAM 역할", "iam_roles"),
    ("총 리소스", None),
]
for col, (label, key) in zip(cols2, metric_map2):
    if key:
        col.metric(label, summary.get(key, "–"))
    else:
        col.metric(label, res.get("total_resources", "–"))

st.divider()

# ── 2) 비용 + 보안 (2컬럼) ──
left, right = st.columns(2)

with left:
    st.subheader("서비스별 비용 (최근 30일)")
    cost_data = _load_cost_by_service(30)
    if cost_data.get("services"):
        df_cost = pd.DataFrame(cost_data["services"])
        fig = px.pie(
            df_cost,
            names="service",
            values="cost",
            hole=0.4,
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
        st.plotly_chart(fig, use_container_width=True)
        st.metric("총 비용 (USD)", f"${cost_data.get('total_cost', 0):,.2f}")
    else:
        st.info("비용 데이터가 없습니다.")

with right:
    st.subheader("보안 발견 사항")
    sec_data = _load_security_findings()
    if sec_data.get("error"):
        st.warning(sec_data["error"])
    else:
        sev_counts = sec_data.get("severity_counts", {})
        if sev_counts:
            order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]
            df_sec = pd.DataFrame(
                [
                    {"severity": s, "count": sev_counts.get(s, 0)}
                    for s in order
                    if sev_counts.get(s, 0) > 0
                ]
            )
            if not df_sec.empty:
                color_map = {
                    "CRITICAL": "#d32f2f",
                    "HIGH": "#f57c00",
                    "MEDIUM": "#fbc02d",
                    "LOW": "#388e3c",
                    "INFORMATIONAL": "#1976d2",
                }
                fig = px.bar(
                    df_sec,
                    x="severity",
                    y="count",
                    color="severity",
                    color_discrete_map=color_map,
                )
                fig.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=350,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("보안 발견 사항이 없습니다.")
        st.metric("총 발견 사항", sec_data.get("total_count", 0))
