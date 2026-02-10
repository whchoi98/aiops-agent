"""EC2 인스턴스 조회 페이지"""

import pandas as pd
import streamlit as st

from src.tools.steampipe.inventory import list_ec2_instances

st.header("EC2 인스턴스")

# 사이드바 필터
state = st.sidebar.selectbox("상태", ["all", "running", "stopped", "terminated"])
instance_type = st.sidebar.text_input("인스턴스 유형 (예: t3.micro)")
region = st.sidebar.text_input("리전 (예: ap-northeast-2)")


@st.cache_data(ttl=300)
def fetch_ec2(
    state: str | None = None,
    instance_type: str | None = None,
    region: str | None = None,
) -> dict:
    return list_ec2_instances(
        state=state,
        instance_type=instance_type or None,
        region=region or None,
    )


result = fetch_ec2(
    state=None if state == "all" else state,
    instance_type=instance_type or None,
    region=region or None,
)

if not result["success"]:
    st.error(result.get("error", "조회 실패"))
else:
    data = result.get("data", [])
    st.subheader(f"총 {len(data)}개 인스턴스")
    if data:
        df = pd.DataFrame(data)
        display_cols = [
            c
            for c in [
                "instance_id",
                "title",
                "instance_type",
                "instance_state",
                "public_ip_address",
                "private_ip_address",
                "vpc_id",
                "region",
                "launch_time",
            ]
            if c in df.columns
        ]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("조건에 맞는 인스턴스가 없습니다.")
