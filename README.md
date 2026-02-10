# AWS AIOps Platform

Amazon Bedrock AgentCore 기반의 AWS 플랫폼 운영 자동화 시스템

## 빠른 시작

### 1. 프로젝트 복사

```bash
# 전체 디렉토리 복사
cp -r ~/aws-aiops-platform /path/to/new/location

# 또는 git clone (git 초기화 후)
git clone <repository-url>
```

### 2. 초기 설정

```bash
cd aws-aiops-platform
./scripts/setup.sh
```

### 3. 환경 변수 설정

```bash
# .env 파일 편집
vi .env

# 필수 설정
AWS_REGION=ap-northeast-2
AWS_PROFILE=your-profile-name
```

### 4. AgentCore Runtime 배포 (선택)

에이전트를 AgentCore 서버리스 환경에 배포합니다.

```bash
# 전체 에이전트 배포
bash scripts/deploy_runtime.sh all

# 개별 에이전트 배포
bash scripts/deploy_runtime.sh monitoring

# 배포 상태 확인
bash scripts/deploy_runtime.sh list
```

### 5. Claude Code에서 사용

```bash
cd aws-aiops-platform
claude
```

## 환경별 설정

### 필수 변경 사항

| 항목 | 파일 | 설명 |
|------|------|------|
| AWS 리전 | `.env` | `AWS_REGION` 설정 |
| AWS 프로필 | `.env` | `AWS_PROFILE` 설정 |
| MCP 서버 프로필 | `.mcp.json` | `AWS_PROFILE` 값 변경 |

### .mcp.json 프로필 일괄 변경

```bash
# aiops-dev를 your-profile로 변경
sed -i 's/aiops-dev/your-profile/g' .mcp.json
```

## 요구 사항

- Python 3.11+
- AWS CLI
- AWS 자격 증명 (IAM 사용자 또는 역할)
- uv 또는 pip

### 선택 사항

- Steampipe (자산 인벤토리 기능)
- Docker (AgentCore Runtime 로컬 테스트)

## 인벤토리 대시보드

Steampipe 기반 AWS 자산 인벤토리를 Streamlit 대시보드로 시각화합니다.

### 실행

```bash
bash scripts/start_dashboard.sh
# http://<EC2-IP>:8501 으로 접속
```

### 페이지 구성

| 페이지 | 설명 |
|--------|------|
| Summary | 리소스 유형별 카운트 (EC2, S3, RDS, Lambda 등) |
| EC2 | 인스턴스 목록 + 상태/유형/리전 필터 |
| S3 | 버킷 목록 + 퍼블릭 액세스 경고 |
| Security | IAM 사용자 (MFA 경고) + 보안 그룹 (0.0.0.0/0 경고) |
| Network | VPC/서브넷 목록 + VPC ID 필터 |

- `src/tools/steampipe/inventory.py`의 기존 `@tool` 함수를 그대로 재활용
- 5분 캐시(`@st.cache_data(ttl=300)`)로 반복 호출 최소화
- Steampipe가 설치·실행 중이어야 데이터가 표시됩니다

## 아키텍처

### 목표 구성

EC2는 개발/운영 콘솔만 담당하고, 에이전트는 AgentCore 서버리스에서 실행됩니다.

```
┌─ Phase 1 EC2 (개발/운영 콘솔) ──────────────────────┐
│  code-server (VSCode IDE)                           │
│  Streamlit Dashboard (운영 대시보드)                 │
│  CLI 콘솔 (agentcore invoke, 관리 명령)             │
└─────────────┬───────────────────────────────────────┘
              │ agentcore invoke
              ▼
┌─ AgentCore (서버리스) ──────────────────────────────┐
│  Runtime: Monitoring / Cost / Security /            │
│           Resource / Inventory Agent                │
│  Gateway: Lambda + MCP 도구                         │
│  Memory: 세션/컨텍스트 저장                          │
│  Identity: Cognito 인증                             │
│  Observability: OTEL → CloudWatch                   │
└─────────────────────────────────────────────────────┘
```

## 프로젝트 구조

```
aws-aiops-platform/
├── src/
│   ├── agents/           # AI 에이전트
│   ├── tools/            # MCP 도구
│   ├── dashboard/        # Streamlit 인벤토리 대시보드
│   ├── gateway/          # AgentCore Gateway
│   └── shared/           # 공유 유틸리티
├── infrastructure/       # IaC (CDK, Terraform)
├── tests/                # 테스트
├── scripts/              # 유틸리티 스크립트
├── .mcp.json             # MCP 서버 설정
├── CLAUDE.md             # Claude Code 프로젝트 메모리
└── pyproject.toml        # Python 패키지 설정
```

## 에이전트

| 에이전트 | 설명 | 도구 |
|----------|------|------|
| monitoring | CloudWatch 모니터링 | aws-cloudwatch |
| cost_optimizer | 비용 최적화 | aws-cost-explorer |
| resource_manager | 네트워크/리소스 관리 | aws-network, aws-ccapi |
| inventory | 자산 인벤토리 | steampipe |

## MCP 서버

| 서버 | 용도 |
|------|------|
| aws-cloudwatch | 로그/메트릭 모니터링 |
| aws-cost-explorer | 비용 분석 |
| aws-eks | EKS/Kubernetes 관리 |
| aws-ecs | ECS 컨테이너 관리 |
| aws-network | 네트워크 분석 |
| aws-ccapi | Cloud Control API |
| aws-iam | IAM 보안 |
| steampipe | SQL 기반 자산 조회 |

## 실행 방법

| 모드 | 명령어 | 용도 |
|------|--------|------|
| AgentCore Runtime (권장) | `agentcore invoke --name aiops-monitoring-agent` | 프로덕션 |
| 로컬 개발 | `python -m src.agents.monitoring.agent` | 디버깅/개발 |

```bash
# AgentCore Runtime으로 에이전트 호출
agentcore invoke --name aiops-monitoring-agent --query "현재 EC2 상태 확인"

# 에이전트 로그 확인
agentcore logs --name aiops-monitoring-agent
```

## 라이선스

Apache-2.0
