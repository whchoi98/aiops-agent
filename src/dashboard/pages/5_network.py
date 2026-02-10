"""VPC / 서브넷 조회 페이지"""

import pandas as pd
import streamlit as st

from src.tools.steampipe.inventory import list_vpc_resources

st.header("네트워크 (VPC / 서브넷)")

vpc_filter = st.sidebar.text_input("VPC ID 필터 (비우면 전체)")


@st.cache_data(ttl=300)
def fetch_vpc(vpc_id: str | None = None) -> dict:
    return list_vpc_resources(vpc_id=vpc_id)


result = fetch_vpc(vpc_id=vpc_filter or None)

if not result.get("success"):
    st.error("VPC 리소스 조회 실패")
else:
    # ── VPC 목록 ─────────────────────────────────────
    vpcs = result.get("vpcs", [])
    st.subheader(f"VPC ({len(vpcs)}개)")
    if vpcs:
        df_vpcs = pd.DataFrame(vpcs)
        display_cols = [
            c
            for c in ["vpc_id", "title", "cidr_block", "state", "is_default", "region"]
            if c in df_vpcs.columns
        ]
        st.dataframe(df_vpcs[display_cols], use_container_width=True)
    else:
        st.info("VPC가 없습니다.")

    st.divider()

    # ── 서브넷 목록 ───────────────────────────────────
    subnets = result.get("subnets", [])
    st.subheader(f"서브넷 ({len(subnets)}개)")
    if subnets:
        df_sub = pd.DataFrame(subnets)
        display_cols = [
            c
            for c in [
                "subnet_id",
                "title",
                "vpc_id",
                "cidr_block",
                "availability_zone",
                "available_ip_address_count",
                "map_public_ip_on_launch",
                "state",
            ]
            if c in df_sub.columns
        ]
        st.dataframe(df_sub[display_cols], use_container_width=True)
    else:
        st.info("서브넷이 없습니다.")
