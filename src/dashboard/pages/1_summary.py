"""자산 요약 대시보드 — 리소스 유형별 카운트"""

import streamlit as st

from src.tools.steampipe.inventory import get_asset_summary

st.header("자산 요약")


@st.cache_data(ttl=300)
def fetch_summary() -> dict:
    return get_asset_summary()


result = fetch_summary()

if not result["success"]:
    st.warning("일부 리소스 조회에 실패했습니다.")
    if result.get("errors"):
        for err in result["errors"]:
            st.error(err)

summary: dict = result.get("summary", {})

st.metric("총 리소스 수", result.get("total_resources", 0))
st.divider()

# 3열 레이아웃으로 metric 카드 배치
labels = {
    "ec2_instances": "EC2 인스턴스",
    "ec2_running": "EC2 (Running)",
    "s3_buckets": "S3 버킷",
    "rds_instances": "RDS 인스턴스",
    "lambda_functions": "Lambda 함수",
    "vpcs": "VPC",
    "security_groups": "보안 그룹",
    "iam_users": "IAM 사용자",
    "iam_roles": "IAM 역할",
    "eks_clusters": "EKS 클러스터",
    "ecs_clusters": "ECS 클러스터",
    "ebs_volumes": "EBS 볼륨",
}

cols = st.columns(3)
for idx, (key, label) in enumerate(labels.items()):
    value = summary.get(key, "-")
    cols[idx % 3].metric(label, value)
