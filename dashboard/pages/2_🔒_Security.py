"""보안 현황 페이지"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import plotly.express as px

from tools.security_tools import (
    get_guardduty_findings,
    get_iam_credential_report,
    get_security_findings,
)

st.set_page_config(page_title="보안 현황", page_icon="🔒", layout="wide")
st.title("🔒 보안 현황")

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]
COLOR_MAP = {
    "CRITICAL": "#d32f2f",
    "HIGH": "#f57c00",
    "MEDIUM": "#fbc02d",
    "LOW": "#388e3c",
    "INFORMATIONAL": "#1976d2",
}


@st.cache_data(ttl=300, show_spinner="Security Hub 조회 중…")
def _load_findings(severity: str | None) -> dict:
    return get_security_findings(severity=severity)


@st.cache_data(ttl=300, show_spinner="GuardDuty 조회 중…")
def _load_guardduty(severity: str | None) -> dict:
    return get_guardduty_findings(severity=severity)


@st.cache_data(ttl=600, show_spinner="IAM 자격 증명 보고서 조회 중…")
def _load_iam_report() -> dict:
    return get_iam_credential_report()


# ── 1) Security Hub ──
st.subheader("Security Hub 발견 사항")

sev_filter = st.selectbox("심각도 필터", ["전체", *SEVERITY_ORDER])
severity_arg = None if sev_filter == "전체" else sev_filter

findings = _load_findings(severity_arg)
if findings.get("error"):
    st.warning(findings["error"])
else:
    left, right = st.columns(2)
    with left:
        sev_counts = findings.get("severity_counts", {})
        if sev_counts:
            df_sev = pd.DataFrame(
                [{"severity": s, "count": sev_counts.get(s, 0)} for s in SEVERITY_ORDER if sev_counts.get(s, 0) > 0]
            )
            if not df_sev.empty:
                fig = px.bar(df_sev, x="severity", y="count", color="severity", color_discrete_map=COLOR_MAP)
                fig.update_layout(showlegend=False, margin=dict(t=20, b=20), height=300)
                st.plotly_chart(fig, use_container_width=True)
        st.metric("총 발견 사항", findings.get("total_count", 0))

    with right:
        finding_list = findings.get("findings", [])
        if finding_list:
            df_f = pd.DataFrame(finding_list)
            display_cols = [c for c in ["severity", "title", "resource_type", "resource_id", "compliance_status"] if c in df_f.columns]
            st.dataframe(df_f[display_cols], use_container_width=True, hide_index=True, height=340)
        else:
            st.success("발견 사항이 없습니다.")

st.divider()

# ── 2) GuardDuty ──
st.subheader("GuardDuty 위협 탐지")

gd = _load_guardduty(severity_arg)
if gd.get("error"):
    st.warning(gd["error"])
else:
    gd_findings = gd.get("findings", [])
    st.metric("탐지 건수", gd.get("total_count", 0))
    if gd_findings:
        df_gd = pd.DataFrame(gd_findings)
        if "created_at" in df_gd.columns:
            df_gd["created_at"] = pd.to_datetime(df_gd["created_at"], errors="coerce")
            df_gd_sorted = df_gd.sort_values("created_at", ascending=False)
            fig = px.scatter(
                df_gd_sorted,
                x="created_at",
                y="severity",
                color="severity",
                hover_data=["title", "type"],
                color_discrete_map=COLOR_MAP,
            )
            fig.update_layout(margin=dict(t=20, b=20), height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        display_cols = [c for c in ["severity", "type", "title", "resource_type", "resource_id", "created_at"] if c in df_gd.columns]
        st.dataframe(df_gd[display_cols], use_container_width=True, hide_index=True)
    else:
        st.success("GuardDuty 위협이 탐지되지 않았습니다.")

st.divider()

# ── 3) IAM 자격 증명 보고서 ──
st.subheader("IAM 자격 증명 상태")

iam = _load_iam_report()
if iam.get("error"):
    st.warning(iam["error"])
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("총 사용자", iam.get("total_users", 0))
    c2.metric("MFA 미설정 (콘솔)", iam.get("users_without_mfa", 0))
    c3.metric("보안 이슈", len(iam.get("issues", [])))

    issues = iam.get("issues", [])
    if issues:
        st.warning("보안 이슈 목록")
        st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)

    users = iam.get("users", [])
    if users:
        with st.expander("전체 사용자 자격 증명 현황"):
            df_users = pd.DataFrame(users)
            st.dataframe(df_users, use_container_width=True, hide_index=True)
