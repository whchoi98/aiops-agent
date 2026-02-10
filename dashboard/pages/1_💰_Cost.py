"""비용 분석 페이지"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from tools.cost_explorer_tools import (
    get_cost_and_usage,
    get_cost_by_service,
    get_cost_forecast,
    get_rightsizing_recommendations,
)

st.set_page_config(page_title="비용 분석", page_icon="💰", layout="wide")
st.title("💰 비용 분석")


# ── 캐싱 ──
@st.cache_data(ttl=300, show_spinner="비용 데이터 조회 중…")
def _load_daily_cost(days: int) -> dict:
    return get_cost_and_usage(days=days, granularity="DAILY")


@st.cache_data(ttl=300, show_spinner="서비스별 비용 조회 중…")
def _load_cost_by_service(days: int) -> dict:
    return get_cost_by_service(days=days)


@st.cache_data(ttl=300, show_spinner="비용 예측 조회 중…")
def _load_forecast(days: int) -> dict:
    return get_cost_forecast(days=days, granularity="DAILY")


@st.cache_data(ttl=600, show_spinner="라이트사이징 권장 조회 중…")
def _load_rightsizing() -> dict:
    return get_rightsizing_recommendations()


# ── 컨트롤 ──
period = st.selectbox("조회 기간", [7, 14, 30, 60, 90], index=2, format_func=lambda d: f"최근 {d}일")

# ── 1) 일별 비용 트렌드 ──
st.subheader("일별 비용 트렌드")
daily = _load_daily_cost(period)
results = daily.get("results", [])
if results:
    rows = [{"date": r["start"], "cost": r.get("total_cost", 0)} for r in results]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    fig = px.line(df, x="date", y="cost", markers=True)
    fig.update_layout(
        xaxis_title="날짜",
        yaxis_title="비용 (USD)",
        margin=dict(t=20, b=20),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.metric("기간 총 비용 (USD)", f"${daily.get('total_cost', 0):,.2f}")
else:
    st.info("비용 데이터가 없습니다.")

st.divider()

# ── 2) 서비스별 비용 ──
left, right = st.columns(2)

with left:
    st.subheader("서비스별 비용 분포")
    svc = _load_cost_by_service(period)
    services = svc.get("services", [])
    if services:
        df_svc = pd.DataFrame(services)
        fig = px.pie(df_svc, names="service", values="cost", hole=0.4)
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("서비스별 데이터가 없습니다.")

with right:
    st.subheader("서비스별 비용 테이블")
    if services:
        st.dataframe(
            pd.DataFrame(services).sort_values("cost", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

# ── 3) 비용 예측 ──
st.subheader("비용 예측 (향후 30일)")
fc = _load_forecast(30)
if fc.get("error"):
    st.warning(fc["error"])
else:
    forecasts = fc.get("forecasts", [])
    if forecasts:
        rows = []
        for f in forecasts:
            rows.append({"date": f["start"], "mean": f["mean"], "low": f["low"], "high": f["high"]})
        df_fc = pd.DataFrame(rows)
        df_fc["date"] = pd.to_datetime(df_fc["date"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_fc["date"], y=df_fc["high"], mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df_fc["date"], y=df_fc["low"], mode="lines", fill="tonexty", fillcolor="rgba(33,150,243,0.2)", line=dict(width=0), name="예측 범위"))
        fig.add_trace(go.Scatter(x=df_fc["date"], y=df_fc["mean"], mode="lines+markers", name="예측 평균", line=dict(color="#1976d2")))
        fig.update_layout(xaxis_title="날짜", yaxis_title="비용 (USD)", margin=dict(t=20, b=20), height=350)
        st.plotly_chart(fig, use_container_width=True)
        st.metric("예측 총 비용 (USD)", f"${fc.get('total_forecast', 0):,.2f}")
    else:
        st.info("예측 데이터가 없습니다.")

st.divider()

# ── 4) 라이트사이징 권장 ──
st.subheader("EC2 라이트사이징 권장")
rs = _load_rightsizing()
if rs.get("error"):
    st.warning(rs["error"])
else:
    recs = rs.get("recommendations", [])
    if recs:
        st.metric("예상 월간 절감 (USD)", f"${rs.get('total_estimated_monthly_savings', 0):,.2f}")
        df_rs = pd.DataFrame(recs)
        display_cols = [c for c in ["instance_id", "instance_type", "action", "recommended_type", "estimated_monthly_savings"] if c in df_rs.columns]
        st.dataframe(df_rs[display_cols], use_container_width=True, hide_index=True)
    else:
        st.success("라이트사이징 권장 사항이 없습니다.")
