"""IAM 사용자 + 보안 그룹 조회 페이지"""

import pandas as pd
import streamlit as st

from src.tools.steampipe.inventory import list_iam_users, list_security_groups

st.header("보안")

# ── IAM 사용자 ──────────────────────────────────────────────
st.subheader("IAM 사용자")


@st.cache_data(ttl=300)
def fetch_iam_users() -> dict:
    return list_iam_users()


iam_result = fetch_iam_users()

if not iam_result["success"]:
    st.error(iam_result.get("error", "IAM 사용자 조회 실패"))
else:
    users = iam_result.get("data", [])
    no_mfa = [u for u in users if not u.get("mfa_enabled")]
    if no_mfa:
        st.warning(
            f"MFA 미활성 사용자 {len(no_mfa)}명: "
            + ", ".join(u.get("name", "") for u in no_mfa)
        )

    if users:
        df = pd.DataFrame(users)
        display_cols = [
            c
            for c in ["name", "user_id", "create_date", "password_last_used", "mfa_enabled"]
            if c in df.columns
        ]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("IAM 사용자가 없습니다.")

st.divider()

# ── 보안 그룹 ──────────────────────────────────────────────
st.subheader("보안 그룹")


@st.cache_data(ttl=300)
def fetch_security_groups() -> dict:
    return list_security_groups()


sg_result = fetch_security_groups()

if not sg_result["success"]:
    st.error(sg_result.get("error", "보안 그룹 조회 실패"))
else:
    sgs = sg_result.get("data", [])

    # 0.0.0.0/0 오픈 보안 그룹 경고
    open_sgs = []
    for sg in sgs:
        for rule in sg.get("ip_permissions", []) or []:
            for ip_range in rule.get("IpRanges", []):
                if ip_range.get("CidrIp") == "0.0.0.0/0":
                    open_sgs.append(sg.get("group_name", sg.get("group_id", "")))
                    break

    if open_sgs:
        st.warning(
            f"0.0.0.0/0 오픈 보안 그룹 {len(open_sgs)}개: " + ", ".join(open_sgs)
        )

    if sgs:
        df = pd.DataFrame(sgs)
        display_cols = [
            c
            for c in ["group_id", "group_name", "description", "vpc_id", "region"]
            if c in df.columns
        ]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("보안 그룹이 없습니다.")
