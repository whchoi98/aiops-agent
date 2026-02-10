"""S3 버킷 조회 페이지"""

import pandas as pd
import streamlit as st

from src.tools.steampipe.inventory import list_s3_buckets

st.header("S3 버킷")


@st.cache_data(ttl=300)
def fetch_s3() -> dict:
    return list_s3_buckets()


result = fetch_s3()

if not result["success"]:
    st.error(result.get("error", "조회 실패"))
else:
    data = result.get("data", [])
    st.subheader(f"총 {len(data)}개 버킷")

    # 퍼블릭 버킷 경고
    public_buckets = [b for b in data if b.get("bucket_policy_is_public")]
    if public_buckets:
        st.warning(
            f"퍼블릭 액세스가 허용된 버킷 {len(public_buckets)}개: "
            + ", ".join(b.get("name", "") for b in public_buckets)
        )

    if data:
        df = pd.DataFrame(data)
        display_cols = [
            c
            for c in [
                "name",
                "region",
                "creation_date",
                "bucket_policy_is_public",
                "block_public_acls",
                "block_public_policy",
                "versioning_enabled",
            ]
            if c in df.columns
        ]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("버킷이 없습니다.")
