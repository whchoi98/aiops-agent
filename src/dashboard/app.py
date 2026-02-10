"""AWS AIOps 인벤토리 대시보드 — Streamlit 멀티페이지 진입점"""

import streamlit as st

st.set_page_config(
    page_title="AIOps 인벤토리",
    page_icon="🏗️",
    layout="wide",
)

st.title("AWS AIOps 인벤토리 대시보드")
st.markdown("Steampipe 기반 AWS 자산 조회 · 사이드바에서 페이지를 선택하세요.")
