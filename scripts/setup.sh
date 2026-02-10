#!/bin/bash
# AWS AIOps Platform 초기 설정 스크립트
# 다른 환경에서 프로젝트를 복사한 후 이 스크립트를 실행하세요.

set -e

echo "========================================"
echo "  AWS AIOps Platform 초기 설정"
echo "========================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "프로젝트 디렉토리: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 1. Python 버전 확인
echo ""
echo "1. Python 버전 확인..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [[ $MAJOR -ge 3 && $MINOR -ge 11 ]]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION (요구사항: 3.11+)${NC}"
    else
        echo -e "${RED}✗ Python $PYTHON_VERSION - 3.11 이상이 필요합니다${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Python3가 설치되어 있지 않습니다${NC}"
    exit 1
fi

# 2. 가상환경 생성
echo ""
echo "2. 가상환경 설정..."
if [[ -d ".venv" ]]; then
    echo -e "${YELLOW}! 기존 가상환경이 있습니다. 재사용합니다.${NC}"
else
    if command -v uv &> /dev/null; then
        echo "uv로 가상환경 생성 중..."
        uv venv
    else
        echo "venv로 가상환경 생성 중..."
        python3 -m venv .venv
    fi
    echo -e "${GREEN}✓ 가상환경 생성 완료${NC}"
fi

# 가상환경 활성화
source .venv/bin/activate

# 3. 의존성 설치
echo ""
echo "3. 의존성 설치..."
if command -v uv &> /dev/null; then
    uv pip install -e ".[dev]"
else
    pip install -e ".[dev]"
fi
echo -e "${GREEN}✓ 의존성 설치 완료${NC}"

# 4. 환경 변수 설정
echo ""
echo "4. 환경 변수 설정..."
if [[ -f ".env" ]]; then
    echo -e "${YELLOW}! .env 파일이 이미 존재합니다${NC}"
else
    cp .env.example .env
    echo -e "${GREEN}✓ .env 파일 생성됨 (.env.example에서 복사)${NC}"
    echo -e "${YELLOW}! .env 파일을 열어 AWS_PROFILE, AWS_REGION을 설정하세요${NC}"
fi

# 5. AWS 자격 증명 확인
echo ""
echo "5. AWS 자격 증명 확인..."
if command -v aws &> /dev/null; then
    if aws sts get-caller-identity &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        echo -e "${GREEN}✓ AWS 자격 증명 유효 (Account: $ACCOUNT_ID)${NC}"
    else
        echo -e "${YELLOW}! AWS 자격 증명이 설정되지 않았습니다${NC}"
        echo "  다음 명령어로 설정하세요:"
        echo "    aws configure"
        echo "  또는 .env 파일에서 AWS_PROFILE을 설정하세요"
    fi
else
    echo -e "${YELLOW}! AWS CLI가 설치되어 있지 않습니다${NC}"
fi

# 6. Steampipe 확인 (선택사항)
echo ""
echo "6. Steampipe 확인 (선택사항)..."
if command -v steampipe &> /dev/null; then
    echo -e "${GREEN}✓ Steampipe 설치됨${NC}"
    steampipe --version
else
    echo -e "${YELLOW}! Steampipe가 설치되어 있지 않습니다${NC}"
    echo "  자산 인벤토리 기능을 사용하려면 다음 명령어로 설치하세요:"
    echo "    ./scripts/setup-steampipe.sh"
fi

# 7. MCP 서버 확인
echo ""
echo "7. MCP 서버 확인..."
if command -v uvx &> /dev/null; then
    echo -e "${GREEN}✓ uvx 사용 가능 (MCP 서버 실행용)${NC}"
else
    echo -e "${YELLOW}! uvx가 설치되어 있지 않습니다${NC}"
    echo "  MCP 서버를 사용하려면 다음 명령어로 설치하세요:"
    echo "    pip install uv"
fi

# 8. 테스트 실행
echo ""
echo "8. 테스트 실행..."
if python -m pytest tests/unit -v --tb=short 2>/dev/null; then
    echo -e "${GREEN}✓ 단위 테스트 통과${NC}"
else
    echo -e "${YELLOW}! 일부 테스트가 실패했습니다 (AWS 자격 증명 필요)${NC}"
fi

# 완료
echo ""
echo "========================================"
echo -e "${GREEN}  설정 완료!${NC}"
echo "========================================"
echo ""
echo "다음 단계:"
echo "  1. .env 파일을 열어 환경 변수를 확인하세요"
echo "  2. AWS 자격 증명을 설정하세요 (aws configure)"
echo "  3. 가상환경 활성화: source .venv/bin/activate"
echo "  4. 에이전트 테스트: python -m src.agents.monitoring.main"
echo ""
echo "Claude Code에서 사용:"
echo "  cd $PROJECT_DIR && claude"
echo ""
