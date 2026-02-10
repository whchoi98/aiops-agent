#!/bin/bash
# Steampipe AWS 플러그인 설치 스크립트

set -e

echo "=== Steampipe 설치 스크립트 ==="

# OS 감지
OS=$(uname -s)
ARCH=$(uname -m)

echo "OS: $OS, Architecture: $ARCH"

# Steampipe 설치
if command -v steampipe &> /dev/null; then
    echo "✓ Steampipe가 이미 설치되어 있습니다."
    steampipe --version
else
    echo "Steampipe 설치 중..."

    if [[ "$OS" == "Darwin" ]]; then
        # macOS
        brew install turbot/tap/steampipe
    elif [[ "$OS" == "Linux" ]]; then
        # Linux
        sudo /bin/sh -c "$(curl -fsSL https://steampipe.io/install/steampipe.sh)"
    else
        echo "지원되지 않는 OS입니다: $OS"
        exit 1
    fi

    echo "✓ Steampipe 설치 완료"
fi

# AWS 플러그인 설치
echo "AWS 플러그인 설치 중..."
steampipe plugin install aws

echo "✓ AWS 플러그인 설치 완료"

# 플러그인 버전 확인
echo ""
echo "=== 설치된 플러그인 ==="
steampipe plugin list

# AWS 자격 증명 확인
echo ""
echo "=== AWS 자격 증명 확인 ==="
if aws sts get-caller-identity &> /dev/null; then
    echo "✓ AWS 자격 증명이 유효합니다."
    aws sts get-caller-identity
else
    echo "⚠ AWS 자격 증명을 확인해주세요."
    echo "  - AWS_PROFILE 환경 변수 설정"
    echo "  - aws configure 실행"
fi

# 테스트 쿼리
echo ""
echo "=== 테스트 쿼리 실행 ==="
echo "SELECT COUNT(*) as vpc_count FROM aws_vpc;"
steampipe query "SELECT COUNT(*) as vpc_count FROM aws_vpc" --output table || echo "⚠ 쿼리 실행 실패 - AWS 자격 증명을 확인하세요."

echo ""
echo "=== 설치 완료 ==="
echo ""
echo "사용 예시:"
echo "  steampipe query \"SELECT * FROM aws_ec2_instance WHERE instance_state = 'running'\""
echo "  steampipe query \"SELECT name, mfa_enabled FROM aws_iam_user\""
echo "  steampipe query \"SELECT * FROM aws_s3_bucket\""
