# AWS AIOps Platform

Amazon Bedrock AgentCore 기반의 AWS 플랫폼 운영 자동화 시스템

## 프로젝트 개요

이 프로젝트는 Amazon Bedrock AgentCore를 활용하여 AWS 인프라를 지능적으로 모니터링하고 운영하는 AIOps 플랫폼입니다.

### 핵심 기능
- **자동 모니터링**: CloudWatch 메트릭/로그 분석 및 이상 탐지
- **비용 최적화**: Cost Explorer 기반 리소스 최적화 권장
- **보안 관리**: Security Hub, GuardDuty 통합 보안 모니터링
- **인시던트 대응**: 자동화된 문제 감지 및 해결 워크플로우
- **리소스 관리**: EC2, Lambda, ECS, RDS 등 리소스 라이프사이클 관리

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS AIOps Platform                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Monitoring  │  │    Cost      │  │   Security   │          │
│  │    Agent     │  │  Optimizer   │  │    Agent     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│  ┌──────┴─────────────────┴─────────────────┴───────┐          │
│  │              AgentCore Runtime                    │          │
│  │  (Serverless Agent Execution Environment)        │          │
│  └──────────────────────┬───────────────────────────┘          │
│                         │                                       │
│  ┌──────────────────────┴───────────────────────────┐          │
│  │              AgentCore Gateway                    │          │
│  │  (MCP-Compatible Tool Interface)                 │          │
│  └──────────────────────┬───────────────────────────┘          │
│                         │                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │CloudWatch│ │  Cost   │ │Security │ │   EC2   │ │ Lambda  │  │
│  │  Tools  │ │Explorer │ │  Hub    │ │  Tools  │ │  Tools  │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  AgentCore Memory │ AgentCore Identity │ AgentCore Observability│
└─────────────────────────────────────────────────────────────────┘
```

## 기술 스택

- **언어**: Python 3.11+
- **AI 프레임워크**: Strands Agents, Amazon Bedrock
- **모델**: Claude 4 (Anthropic)
- **인프라**: AWS CDK (TypeScript), Terraform
- **테스트**: pytest, pytest-asyncio
- **모니터링**: OpenTelemetry, CloudWatch

## 디렉토리 구조

```
aws-aiops-platform/
├── src/
│   ├── agents/                    # AI 에이전트 구현
│   │   ├── monitoring/            # 모니터링 에이전트
│   │   ├── cost_optimizer/        # 비용 최적화 에이전트
│   │   ├── security/              # 보안 에이전트
│   │   ├── incident_response/     # 인시던트 대응 에이전트
│   │   └── resource_manager/      # 리소스 관리 에이전트
│   ├── tools/                     # MCP 호환 도구들
│   │   ├── cloudwatch/            # CloudWatch 메트릭/로그 도구
│   │   ├── cost_explorer/         # 비용 분석 도구
│   │   ├── security_hub/          # 보안 허브 도구
│   │   ├── ec2/                   # EC2 관리 도구
│   │   ├── lambda/                # Lambda 관리 도구
│   │   ├── ecs/                   # ECS 관리 도구
│   │   └── rds/                   # RDS 관리 도구
│   ├── gateway/                   # AgentCore Gateway 설정
│   ├── memory/                    # AgentCore Memory 통합
│   ├── identity/                  # AgentCore Identity 설정
│   ├── observability/             # 관찰성 및 텔레메트리
│   ├── policy/                    # Cedar 정책 정의
│   └── shared/                    # 공유 유틸리티
│       ├── models/                # Pydantic 모델
│       ├── utils/                 # 헬퍼 함수
│       └── config/                # 설정 관리
├── infrastructure/                # IaC 코드
│   ├── cdk/                       # AWS CDK 스택
│   ├── terraform/                 # Terraform 모듈
│   └── cloudformation/            # CFn 템플릿
├── tests/                         # 테스트 코드
│   ├── unit/                      # 단위 테스트
│   ├── integration/               # 통합 테스트
│   └── e2e/                       # E2E 테스트
├── evaluations/                   # 에이전트 평가
│   ├── benchmarks/                # 성능 벤치마크
│   └── custom_evaluators/         # 커스텀 평가자
├── notebooks/                     # Jupyter 노트북
├── docs/                          # 문서
│   ├── architecture/              # 아키텍처 문서
│   ├── api/                       # API 문서
│   └── runbooks/                  # 운영 런북
├── scripts/                       # 유틸리티 스크립트
└── configs/                       # 환경별 설정
    ├── dev/
    ├── staging/
    └── prod/
```

## 자주 사용하는 명령어

### 개발 환경

```bash
# 의존성 설치
pip install -e ".[dev]"

# 가상환경 활성화 (uv 사용 시)
uv venv && source .venv/bin/activate

# 로컬 에이전트 실행
python -m src.agents.monitoring.main

# 로컬 테스트 (HTTP)
curl -X POST http://localhost:8000/invoke -d '{"query": "EC2 상태 확인"}'
```

### 테스트

```bash
# 전체 테스트
pytest

# 단위 테스트만
pytest tests/unit -v

# 통합 테스트
pytest tests/integration -v

# 커버리지 포함
pytest --cov=src --cov-report=html
```

### AgentCore CLI

```bash
# AgentCore 설정
agentcore configure

# 에이전트 배포
agentcore launch --name aiops-monitoring-agent

# 에이전트 호출 테스트
agentcore invoke --name aiops-monitoring-agent --query "현재 EC2 상태는?"

# 에이전트 목록
agentcore list

# 로그 확인
agentcore logs --name aiops-monitoring-agent
```

### 인프라 배포

```bash
# CDK 배포
cd infrastructure/cdk && cdk deploy --all

# Terraform 배포
cd infrastructure/terraform && terraform apply

# CloudFormation 배포
aws cloudformation deploy --template-file infrastructure/cloudformation/main.yaml --stack-name aiops-platform
```

### 린트 및 포맷팅

```bash
# 코드 포맷팅
ruff format src tests

# 린트 검사
ruff check src tests

# 타입 검사
mypy src
```

## 코드 스타일

### Python 컨벤션

- **포맷터**: Ruff (Black 호환)
- **린터**: Ruff
- **타입 힌트**: 모든 함수에 타입 힌트 필수
- **독스트링**: Google 스타일
- **들여쓰기**: 4칸 스페이스
- **최대 줄 길이**: 100자

### 네이밍 컨벤션

- **클래스**: PascalCase (예: `MonitoringAgent`)
- **함수/메서드**: snake_case (예: `get_ec2_metrics`)
- **상수**: UPPER_SNAKE_CASE (예: `DEFAULT_REGION`)
- **파일**: snake_case (예: `monitoring_agent.py`)

### 에이전트 구현 패턴

```python
from strands import Agent, tool
from bedrock_agentcore import AgentCoreRuntime

@tool
def get_cloudwatch_metrics(namespace: str, metric_name: str) -> dict:
    """CloudWatch 메트릭을 조회합니다.

    Args:
        namespace: AWS 서비스 네임스페이스 (예: AWS/EC2)
        metric_name: 메트릭 이름 (예: CPUUtilization)

    Returns:
        메트릭 데이터 딕셔너리
    """
    # 구현
    pass

class MonitoringAgent(Agent):
    """AWS 리소스 모니터링 에이전트"""

    def __init__(self):
        super().__init__(
            name="monitoring-agent",
            model="anthropic.claude-4-opus",
            tools=[get_cloudwatch_metrics],
        )
```

## 환경 변수

```bash
# 필수
AWS_REGION=ap-northeast-2
AWS_PROFILE=aiops-dev

# AgentCore
AGENTCORE_ENDPOINT=https://agentcore.{region}.amazonaws.com
AGENTCORE_RUNTIME_ROLE_ARN=arn:aws:iam::123456789012:role/AgentCoreRuntime

# 모델 설정
BEDROCK_MODEL_ID=anthropic.claude-4-opus
BEDROCK_MAX_TOKENS=4096

# 관찰성
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=aws-aiops-platform

# 개발용
DEBUG=true
LOG_LEVEL=INFO
```

## Git 워크플로우

### 브랜치 전략

- `main`: 프로덕션 배포 브랜치
- `develop`: 개발 통합 브랜치
- `feature/*`: 기능 개발 브랜치
- `hotfix/*`: 긴급 수정 브랜치

### 커밋 메시지 컨벤션

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**: feat, fix, docs, style, refactor, test, chore
**Scope**: agents, tools, infra, tests, docs

예시:
```
feat(agents): add cost optimization agent

- Implement Cost Explorer integration
- Add rightsizing recommendations
- Support Reserved Instance analysis

Refs: #123
```

## 보안 가이드라인

- AWS 자격 증명을 코드에 하드코딩하지 않음
- IAM 역할 기반 인증 사용
- 최소 권한 원칙 적용
- 민감한 정보는 AWS Secrets Manager 사용
- Cedar 정책으로 에이전트 액션 제어

## 참조 저장소

이 프로젝트는 아래 AgentCore 샘플 저장소를 참조하여 구현합니다.

### 메인 참조 저장소

| 저장소 | 설명 |
|--------|------|
| [awslabs/amazon-bedrock-agentcore-samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) | AWS 공식 AgentCore 샘플 |
| [whchoi98/amazon-bedrock-agentcore-samples](https://github.com/whchoi98/amazon-bedrock-agentcore-samples) | 한국어 환경 최적화 포크 |

### 튜토리얼 구조 (01-tutorials/)

| 번호 | 컴포넌트 | 설명 | 적용 대상 |
|------|----------|------|-----------|
| 01 | Runtime | 서버리스 에이전트 실행 환경 | 모든 에이전트 |
| 02 | Gateway | API를 MCP 도구로 변환 | tools/ 디렉토리 |
| 03 | Identity | AWS/타사 앱 접근 관리 | identity/ 디렉토리 |
| 04 | Memory | 관리형 메모리 인프라 | memory/ 디렉토리 |
| 05 | Tools | 코드 인터프리터, 브라우저 | 확장 도구 |
| 06 | Observability | OpenTelemetry 모니터링 | observability/ 디렉토리 |
| 07 | Evaluations | 에이전트 품질 평가 | evaluations/ 디렉토리 |
| 08 | Policy | Cedar 정책 보안 제어 | policy/ 디렉토리 |
| 09 | E2E | 통합 엔드투엔드 예제 | 전체 통합 참조 |

### 참조할 Use Cases (02-use-cases/)

이 프로젝트와 관련된 주요 사용 사례:

| 사용 사례 | 설명 | 참조 에이전트 |
|-----------|------|---------------|
| aws-operations-agent | Okta 인증 + AWS 운영 보조 | monitoring, resource_manager |
| cost-optimization-agent | 비용 최적화 권장 | cost_optimizer |
| sre-agent | SRE 자동화 | incident_response |
| database-performance-analyzer | DB 성능 분석 | monitoring (RDS) |
| device-management-agent | IoT 디바이스 관리 | resource_manager |

### 인프라 참조 (04-infrastructure-as-code/)

```
04-infrastructure-as-code/
├── cloudformation/          # CFn 템플릿 참조
├── cdk/                     # CDK 스택 참조
└── terraform/               # Terraform 모듈 참조
```

### 프레임워크 통합 참조 (03-integrations/)

```
03-integrations/
├── strands-agents/          # Strands Agents 통합 (주요 사용)
├── crewai/                  # CrewAI 멀티에이전트
└── langgraph/               # LangGraph 워크플로우
```

## 학습 권장 순서

1. **기초**: 01-Runtime → 02-Gateway → 05-Tools
2. **보안**: 03-Identity → 08-Policy
3. **운영**: 04-Memory → 06-Observability → 07-Evaluations
4. **통합**: 09-E2E → 02-use-cases/aws-operations-agent

## 참고 자료

- [Amazon Bedrock AgentCore 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Strands Agents SDK](https://github.com/strands-agents/strands-agents)
- [AgentCore Samples (공식)](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [AgentCore Samples (whchoi98)](https://github.com/whchoi98/amazon-bedrock-agentcore-samples)
