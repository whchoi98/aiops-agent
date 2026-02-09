# AIOps Agent

Amazon Bedrock AgentCore 기반 AWS 인프라 운영 자동화 에이전트.

## 개요

AWS 인프라를 지능적으로 모니터링하고 운영하는 AIOps 에이전트입니다.
[AgentCore E2E 튜토리얼](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/09-AgentCore-E2E) 패턴을 따릅니다.

### 핵심 기능

- **CloudWatch 모니터링**: CloudWatch MCP + Application Signals MCP 연동 (메트릭/알람/로그/SLO)
- **비용 최적화**: Cost Explorer 기반 비용 분석 및 라이트사이징 권장
- **보안 점검**: Security Hub, GuardDuty, CloudTrail MCP 통합
- **EC2 관리**: 인스턴스 상태, EBS 볼륨 관리
- **컨테이너 관리**: EKS MCP, ECS MCP 연동
- **Lambda 관리**: Lambda Tool MCP 연동
- **네트워크 분석**: VPC 로컬 도구 + Network MCP 통합
- **리소스 인벤토리**: 전체 AWS 자산 요약 + AWS API MCP
- **자산 분석**: Steampipe SQL 기반 20+ 리소스 유형 인벤토리 조회
- **문서 참조**: AWS Documentation MCP 통합

## 프로젝트 구조

```
aiops_agent/
├── agents/
│   ├── aiops_agent.py        # 통합 에이전트 정의 (18개 도구 + 시스템 프롬프트)
│   ├── runtime_base.py       # 공유 팩토리 함수 (create_app)
│   ├── runtime.py            # 통합 Runtime 엔트리포인트 (하위 호환)
│   ├── memory.py             # AgentCore Memory 통합
│   ├── observability.py      # AgentCore Observability (OTEL 설정)
│   ├── mcp_manager.py        # Multi-MCP Client 관리자
│   ├── utils.py              # SSM, IAM, 설정 유틸리티
│   ├── monitoring/           # 모니터링 특화 런타임
│   │   ├── agent.py          #   도구: describe_ec2_instances + CloudWatch MCP
│   │   └── runtime.py        #   엔트리포인트
│   ├── cost/                 # 비용 최적화 특화 런타임
│   │   ├── agent.py          #   도구: cost_explorer_tools 4개
│   │   └── runtime.py        #   엔트리포인트
│   ├── security/             # 보안 특화 런타임
│   │   ├── agent.py          #   도구: security_tools 3개
│   │   └── runtime.py        #   엔트리포인트
│   ├── resource/             # 리소스 관리 특화 런타임
│   │   ├── agent.py          #   도구: ec2 4 + vpc 5 + inventory 2 (11개)
│   │   └── runtime.py        #   엔트리포인트
│   ├── inventory/            # 자산 인벤토리 특화 런타임 (Steampipe)
│   │   ├── agent.py          #   도구: steampipe_tools 10개
│   │   └── runtime.py        #   엔트리포인트
│   └── super/                # Super Agent (서브에이전트 오케스트레이션)
│       ├── agent.py          #   5개 @tool 서브에이전트 래퍼
│       └── runtime.py        #   엔트리포인트
├── tools/
│   ├── cost_explorer_tools.py # 비용 분석
│   ├── security_tools.py    # Security Hub / GuardDuty
│   ├── ec2_tools.py         # EC2 인스턴스 관리
│   ├── vpc_tools.py         # VPC 네트워크 분석
│   ├── resource_inventory.py # 리소스 인벤토리 (boto3)
│   └── steampipe_tools.py   # Steampipe SQL 기반 자산 인벤토리
├── gateway/
│   ├── api_spec.json        # 18개 도구 MCP 스키마 정의
│   ├── lambda_handler.py    # Lambda 디스패치 핸들러
│   └── setup_gateway.py     # Gateway 생성/삭제 스크립트
├── configs/
│   ├── mcp_servers.yaml     # 통합 MCP 설정 (전체 MCP 서버)
│   ├── monitoring.yaml      # 모니터링 MCP (cloudwatch, app-signals, network, docs)
│   ├── cost.yaml            # 비용 MCP (docs)
│   ├── security.yaml        # 보안 MCP (cloudtrail, docs)
│   ├── resource.yaml        # 리소스 MCP (eks, ecs, lambda, network, api, docs)
│   ├── inventory.yaml       # 인벤토리 MCP (docs)
│   └── super.yaml           # Super Agent MCP (전체 9개 MCP 서버)
├── prerequisite/
│   ├── infrastructure.yaml  # CloudFormation (IAM Role, Lambda, SSM)
│   └── deploy.sh            # 인프라 배포 스크립트
├── scripts/
│   ├── setup.sh             # 환경 설정
│   ├── run_with_otel.sh     # Observability 래퍼 (opentelemetry-instrument)
│   └── cleanup.sh           # 리소스 정리
├── tests/
│   ├── test_tools.py        # 도구 단위 테스트
│   └── test_local.py        # 로컬 에이전트 테스트
└── requirements.txt
```

## 사전 요구사항

| 항목 | 버전/요건 | 확인 방법 |
|------|-----------|-----------|
| Python | 3.9+ | `python3 --version` |
| AWS CLI | v2 | `aws --version` |
| AWS 자격 증명 | IAM 사용자 또는 역할 | `aws sts get-caller-identity` |
| uv (권장) 또는 pip | 최신 | `uv --version` 또는 `pip --version` |

### 선택 사항

| 항목 | 용도 | 필요 시점 |
|------|------|-----------|
| Steampipe + aws 플러그인 | Inventory Agent (SQL 기반 자산 조회) | 자산 인벤토리 분석 시 |
| Docker | AgentCore Runtime 로컬 테스트 | 컨테이너 배포 시 |
| Node.js / npx | 일부 MCP 서버 실행 | MCP 서버가 npx 기반일 때 |

## 설치 순서

### Step 1. 저장소 복제

```bash
git clone https://github.com/whchoi98/aiops-agent.git
cd aiops-agent
```

### Step 2. 환경 설정 (자동)

```bash
bash scripts/setup.sh
```

이 스크립트가 수행하는 작업:
1. Python 3 버전 확인
2. `.venv` 가상환경 생성
3. `requirements.txt` 의존성 설치 (`strands-agents`, `bedrock-agentcore`, `boto3` 등)
4. AWS 자격 증명 검증 (`aws sts get-caller-identity`)
5. AWS 리전 설정

### Step 3. 환경 변수 설정

```bash
# AWS 리전 및 프로필 설정
export AWS_REGION=ap-northeast-2
export AWS_PROFILE=default        # 사용할 AWS CLI 프로필
```

### Step 4. Steampipe 설치 (Inventory Agent 사용 시)

```bash
# Steampipe 설치 (Linux)
sudo /bin/sh -c "$(curl -fsSL https://steampipe.io/install/steampipe.sh)"

# AWS 플러그인 설치
steampipe plugin install aws

# 설치 확인
steampipe query "SELECT COUNT(*) FROM aws_ec2_instance"
```

> Steampipe 없이도 다른 에이전트(Monitoring, Cost, Security, Resource)는 정상 동작합니다.

### Step 5. 인프라 배포 (CloudFormation)

AgentCore Runtime에 필요한 IAM Role, Lambda 함수, SSM 파라미터를 배포합니다.

```bash
bash prerequisite/deploy.sh
```

이 스크립트가 수행하는 작업:
1. Lambda 코드 패키징 (`gateway/` + `tools/` → zip)
2. S3 버킷 생성 및 Lambda zip 업로드
3. CloudFormation 스택 배포 (`prerequisite/infrastructure.yaml`)
   - `AIOpsGatewayLambda`: 도구 디스패치 Lambda 함수
   - `GatewayAgentCoreRole`: IAM 역할
   - SSM 파라미터 (`/app/aiops/agentcore/*`)

### Step 6. Gateway 설정 (선택)

다른 에이전트/서비스에서 AIOps 도구를 MCP로 사용하려면 Gateway를 생성합니다.

```bash
source .venv/bin/activate
python -m gateway.setup_gateway
```

### Step 7. 실행 확인

```bash
source .venv/bin/activate

# 도구 import 검증
python -c "
from agents.aiops_agent import TOOLS, SYSTEM_PROMPT
print(f'통합 에이전트: {len(TOOLS)}개 도구 OK')
"

# 테스트 실행
python -m pytest tests/ -v
```

## 실행 방법

### 런타임 선택 가이드

| 사용 목적 | 런타임 | 명령어 |
|-----------|--------|--------|
| 크로스 도메인 분석 (권장) | Super Agent | `python -m agents.super.runtime` |
| 전체 도구 단일 에이전트 | 통합 | `python -m agents.runtime` |
| CloudWatch 모니터링만 | Monitoring | `python -m agents.monitoring.runtime` |
| 비용 분석만 | Cost | `python -m agents.cost.runtime` |
| 보안 점검만 | Security | `python -m agents.security.runtime` |
| 리소스/네트워크 관리만 | Resource | `python -m agents.resource.runtime` |
| 자산 인벤토리 (Steampipe) | Inventory | `python -m agents.inventory.runtime` |

### AgentCore Runtime 실행

```bash
source .venv/bin/activate

# Super Agent (서브에이전트 오케스트레이션 + 전체 MCP) — 권장
python -m agents.super.runtime

# 통합 런타임 (18개 도구 전체 + 모든 MCP)
python -m agents.runtime

# 도메인별 특화 런타임
python -m agents.monitoring.runtime   # CloudWatch MCP + EC2 상태
python -m agents.cost.runtime         # Cost Explorer 4개 도구
python -m agents.security.runtime     # Security Hub / GuardDuty / IAM
python -m agents.resource.runtime     # EC2 + VPC + 인벤토리 (11개 도구)
python -m agents.inventory.runtime    # Steampipe SQL 기반 자산 분석 (10개 도구)
```

### Observability 포함 실행

```bash
# Super Agent + OTEL
bash scripts/run_with_otel.sh agents.super.runtime

# 통합 런타임 + OTEL
bash scripts/run_with_otel.sh
```

### 로컬 테스트 (Runtime 없이)

```bash
source .venv/bin/activate

python -c "
from agents.aiops_agent import create_agent
agent = create_agent()
response = agent('현재 EC2 인스턴스 상태를 확인해줘')
print(response)
"
```

## 정리 (리소스 삭제)

```bash
# Gateway + CloudFormation 스택 + SSM 파라미터 + S3 아티팩트 일괄 정리
bash scripts/cleanup.sh
```

### 멀티 런타임 아키텍처

독립 배포/스케일링/장애 격리가 가능한 5개 도메인별 런타임으로 분리되어 있습니다.
Super Agent는 이들을 @tool로 래핑하여 단일 진입점에서 크로스 도메인 오케스트레이션을 제공합니다.

```
                        ┌───────────────────────────────────────┐
                        │            Super Agent                │
                        │  ask_monitoring/cost/security/        │
                        │  resource/inventory_agent + 9 MCP     │
                        └──────────┬────────────────────────────┘
          ┌───────────┬──────┴───────┬────────────┬────────────┐
          ▼           ▼              ▼            ▼            ▼
  ┌──────────┐ ┌──────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │Monitoring│ │   Cost   │  │ Security │ │ Resource │ │Inventory │
  │  Agent   │ │  Agent   │  │  Agent   │ │  Agent   │ │  Agent   │
  │ (1 tool) │ │ (4 tools)│  │ (3 tools)│ │(11 tools)│ │(10 tools)│
  └──────────┘ └──────────┘  └──────────┘ └──────────┘ └──────────┘

                        ┌─────────────────────────────┐
                        │      runtime_base.py        │
                        │  create_app() 공유 팩토리   │
                        │  (Memory, Observability,    │
                        │   MCP, Gateway)             │
                        └──────────┬──────────────────┘
               ┌───────────┬──────┴───────┬────────────┐
               ▼           ▼              ▼            ▼
       ┌──────────┐ ┌──────────┐  ┌──────────┐ ┌──────────┐
       │Monitoring│ │   Cost   │  │ Security │ │ Resource │
       │ Runtime  │ │ Runtime  │  │ Runtime  │ │ Runtime  │
       ├──────────┤ ├──────────┤  ├──────────┤ ├──────────┤
       │EC2 (1)   │ │CE (4)    │  │SecHub (1)│ │EC2 (4)   │
       │+CW MCP   │ │+Docs MCP │  │GD (1)    │ │VPC (5)   │
       │+AppSig   │ │          │  │IAM (1)   │ │Inv (2)   │
       │+Network  │ │          │  │+Trail MCP│ │+EKS MCP  │
       │+Docs MCP │ │          │  │+Docs MCP │ │+ECS MCP  │
       │          │ │          │  │          │ │+Lambda   │
       │          │ │          │  │          │ │+Network  │
       │          │ │          │  │          │ │+API MCP  │
       │          │ │          │  │          │ │+Docs MCP │
       └──────────┘ └──────────┘  └──────────┘ └──────────┘
               ┌───────────┴──────────────┘
               ▼
       ┌──────────────┐
       │ 통합 Runtime │  ← agents/runtime.py (하위 호환)
       │  (18개 전체) │
       └──────────────┘
```

| 런타임 | 로컬 도구 | MCP 서버 | MCP 설정 |
|--------|-----------|----------|----------|
| **Super** | 5 서브에이전트 @tool | 전체 9개 | `configs/super.yaml` |
| **Monitoring** | describe_ec2_instances (1) | cloudwatch, app-signals, network, docs (4) | `configs/monitoring.yaml` |
| **Cost** | cost_explorer_tools (4) | docs (1) | `configs/cost.yaml` |
| **Security** | security_tools (3) | cloudtrail, docs (2) | `configs/security.yaml` |
| **Resource** | ec2 + vpc + inventory (11) | eks, ecs, lambda, network, api, docs (6) | `configs/resource.yaml` |
| **Inventory** | steampipe_tools (10) | docs (1) | `configs/inventory.yaml` |
| **통합** | 전체 18개 | 전체 9개 | `configs/mcp_servers.yaml` |

모든 런타임은 `agents/runtime_base.py`의 `create_app()` 팩토리를 공유하며,
Memory, MCP Manager, Utils 등 공통 모듈을 재사용합니다.

### 도메인별 런타임 설정

각 도메인 런타임은 `configs/` 디렉토리의 전용 YAML 파일로 MCP 서버를 관리합니다.
도메인별 MCP 서버를 추가하려면 해당 설정 파일의 `mcp_servers` 리스트에 항목을 추가하세요.

```yaml
# configs/monitoring.yaml — 모니터링 런타임 전용 MCP
gateway:
  enabled: true
mcp_servers:
  - name: aws-cloudwatch
    enabled: true
    transport: stdio
    command: uvx
    args: [awslabs.cloudwatch-mcp-server@latest]
    env:
      AWS_REGION: "${AWS_REGION}"
```

### 새 도메인 런타임 추가 방법

1. `agents/<domain>/` 디렉토리 생성
2. `agent.py`에 `TOOLS` 리스트와 `SYSTEM_PROMPT` 정의
3. `runtime.py`에서 `runtime_base.create_app()` 호출
4. `configs/<domain>.yaml`에 MCP 설정 작성
5. `python -m agents.<domain>.runtime` 으로 실행

## AgentCore Observability

[E2E 튜토리얼 lab-05](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/09-AgentCore-E2E) 패턴을 따라
AWS OpenTelemetry Python Distro로 에이전트의 트레이스/메트릭/로그를 CloudWatch GenAI Observability에 전송합니다.

### 구성 요소

| 컴포넌트 | 설명 |
|----------|------|
| `agents/observability.py` | OTEL 환경 변수 설정 + 세션 컨텍스트 관리 |
| `scripts/run_with_otel.sh` | `opentelemetry-instrument` 래퍼 스크립트 |
| `aws-opentelemetry-distro` | AWS OTEL Python Distro (자동 계측) |

### 실행 방법

```bash
bash scripts/run_with_otel.sh                          # 통합 런타임
bash scripts/run_with_otel.sh agents.super.runtime      # Super Agent
bash scripts/run_with_otel.sh agents.monitoring.runtime  # 모니터링
bash scripts/run_with_otel.sh agents.cost.runtime        # 비용
bash scripts/run_with_otel.sh agents.security.runtime    # 보안
bash scripts/run_with_otel.sh agents.resource.runtime    # 리소스
bash scripts/run_with_otel.sh agents.inventory.runtime   # 인벤토리
```

### OTEL 환경 변수

| 변수 | 값 | 설명 |
|------|-----|------|
| `OTEL_PYTHON_DISTRO` | `aws_distro` | AWS Distro for OpenTelemetry |
| `OTEL_PYTHON_CONFIGURATOR` | `aws_configurator` | AWS ADOT 설정자 |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | 내보내기 프로토콜 |
| `OTEL_TRACES_EXPORTER` | `otlp` | 트레이스 내보내기 |
| `OTEL_EXPORTER_OTLP_LOGS_HEADERS` | `x-aws-log-group=...` | CloudWatch 로그 그룹 연결 |
| `OTEL_RESOURCE_ATTRIBUTES` | `service.name=aiops-agent-strands` | 서비스 식별자 |
| `AGENT_OBSERVABILITY_ENABLED` | `true` | ADOT 파이프라인 활성화 |

### 커스텀 설정

```bash
# 서비스 이름과 로그 그룹 변경
OTEL_SERVICE_NAME=my-agent \
OTEL_LOG_GROUP=agents/my-agent-logs \
bash scripts/run_with_otel.sh agents.monitoring.runtime
```

### CloudWatch에서 확인

1. CloudWatch 콘솔 > **GenAI Observability** > **Bedrock AgentCore**
2. **Sessions** 뷰에서 세션별 트레이스 확인
3. **Traces** 뷰에서 Bedrock 호출, 도구 실행 등 상세 추적

> **사전 조건**: CloudWatch Transaction Search를 활성화해야 합니다.
> [활성화 가이드](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html)

## AgentCore Gateway (MCP)

18개 AIOps 도구를 MCP 프로토콜로 노출하여 다른 에이전트/서비스에서 재사용할 수 있습니다.
CloudWatch 모니터링은 AWS 공식 CloudWatch MCP 서버로 대체되었습니다.
[E2E 튜토리얼 lab-03](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/09-AgentCore-E2E) 패턴을 따릅니다.

### Gateway 설정

```bash
# 1. 인프라 배포 (Lambda + IAM Role)
bash prerequisite/deploy.sh

# 2. Gateway 생성 (Cognito + MCP Gateway + Lambda Target)
python -m gateway.setup_gateway

# 3. Gateway 삭제
python -m gateway.setup_gateway --delete
```

### 구성 요소

| 컴포넌트 | 설명 |
|----------|------|
| `gateway/api_spec.json` | 18개 도구의 MCP JSON Schema 정의 |
| `gateway/lambda_handler.py` | Lambda 디스패치 핸들러 (도구 라우팅) |
| `gateway/setup_gateway.py` | Gateway + Cognito + Target 생성/삭제 |
| `AIOpsGatewayLambda` | CloudFormation Lambda 함수 |
| `GatewayAgentCoreRole` | Gateway → Lambda 호출 IAM 역할 |

### 인증

Cognito JWT 기반 인증을 사용합니다. Gateway 생성 시 자동으로 Cognito User Pool 이 생성됩니다.

## 외부 MCP 서버 연동

`configs/mcp_servers.yaml` (통합) 또는 `configs/<domain>.yaml` (도메인별)에서
외부 MCP 서버를 설정 기반으로 관리합니다.
MCP 서버 추가 시 설정 파일만 수정하면 되고, 코드 변경은 필요 없습니다.

현재 9개의 AWS 공식 MCP 서버가 설정되어 있습니다:

```yaml
# configs/mcp_servers.yaml (통합 — 일부 발췌)
mcp_servers:
  - name: aws-cloudwatch                    # 메트릭/알람/로그
  - name: aws-cloudwatch-applicationsignals # 서비스 SLO
  - name: aws-network                       # 네트워크 트러블슈팅
  - name: aws-cloudtrail                    # API 감사 로그
  - name: aws-eks                           # Kubernetes
  - name: aws-ecs                           # 컨테이너
  - name: aws-lambda-tool                   # Lambda 실행
  - name: aws-api                           # 범용 AWS API
  - name: aws-documentation                 # AWS 문서 검색
```

### 지원 transport

| Transport | 설명 | 용도 |
|-----------|------|------|
| `stdio` | 로컬 프로세스로 MCP 서버 실행 | AWS 공식 MCP 서버 (uvx/npx) |
| `streamable_http` | HTTP 엔드포인트에 연결 | 원격 MCP 서버 |

### MCP 서버 추가 방법

`configs/mcp_servers.yaml` 에 항목을 추가합니다:

```yaml
mcp_servers:
  - name: my-new-mcp
    enabled: true
    transport: stdio
    command: uvx
    args: [my-mcp-package@latest]
    env:
      AWS_REGION: "${AWS_REGION}"
```

## 테스트

```bash
# 전체 테스트
python -m pytest tests/ -v

# 도구 단위 테스트
python -m pytest tests/test_tools.py -v

# 구조 검증 테스트
python -m pytest tests/test_local.py -v
```

## 도구 목록

### 도메인별 로컬 도구

**Monitoring Runtime** (1개 로컬 + CloudWatch MCP)

| 모듈 | 도구 | 설명 |
|------|------|------|
| ec2_tools | `describe_ec2_instances` | EC2 인스턴스 정보 |

**Cost Runtime** (4개)

| 모듈 | 도구 | 설명 |
|------|------|------|
| cost_explorer_tools | `get_cost_and_usage` | 비용 및 사용량 |
| cost_explorer_tools | `get_cost_forecast` | 비용 예측 |
| cost_explorer_tools | `get_rightsizing_recommendations` | 라이트사이징 권장 |
| cost_explorer_tools | `get_cost_by_service` | 서비스별 비용 |

**Security Runtime** (3개)

| 모듈 | 도구 | 설명 |
|------|------|------|
| security_tools | `get_security_findings` | Security Hub 발견 사항 |
| security_tools | `get_guardduty_findings` | GuardDuty 위협 탐지 |
| security_tools | `get_iam_credential_report` | IAM 자격 증명 보고서 |

**Resource Runtime** (11개)

| 모듈 | 도구 | 설명 |
|------|------|------|
| ec2_tools | `describe_ec2_instances` | EC2 인스턴스 정보 |
| ec2_tools | `list_ec2_instances` | EC2 목록 (페이지네이션) |
| ec2_tools | `get_instance_status` | 인스턴스 상태 검사 |
| ec2_tools | `get_ebs_volumes` | EBS 볼륨 정보 |
| vpc_tools | `describe_vpcs` | VPC 목록 |
| vpc_tools | `describe_subnets` | 서브넷 목록 |
| vpc_tools | `describe_security_groups` | 보안 그룹 |
| vpc_tools | `describe_route_tables` | 라우팅 테이블 |
| vpc_tools | `analyze_network_topology` | 네트워크 토폴로지 분석 |
| resource_inventory | `get_resource_summary` | 전체 자산 요약 |
| resource_inventory | `list_resources_by_type` | 유형별 리소스 목록 |

**Inventory Runtime** (10개 — Steampipe 필요)

| 모듈 | 도구 | 설명 |
|------|------|------|
| steampipe_tools | `run_steampipe_query` | 범용 Steampipe SQL 쿼리 |
| steampipe_tools | `query_aws_inventory` | 유형별 자산 조회 (20+ 유형) |
| steampipe_tools | `get_asset_summary` | 전체 자산 요약 (12개 유형 카운트) |
| steampipe_tools | `list_ec2_instances_steampipe` | EC2 인스턴스 (상태/유형/리전 필터) |
| steampipe_tools | `list_s3_buckets_steampipe` | S3 버킷 (퍼블릭 액세스 필터) |
| steampipe_tools | `list_rds_instances_steampipe` | RDS 인스턴스 (엔진/상태 필터) |
| steampipe_tools | `list_lambda_functions_steampipe` | Lambda 함수 (런타임/리전 필터) |
| steampipe_tools | `list_iam_users_steampipe` | IAM 사용자 (MFA 필터) |
| steampipe_tools | `list_vpc_resources_steampipe` | VPC + 서브넷 |
| steampipe_tools | `list_security_groups_steampipe` | 보안 그룹 (인터넷 개방 필터) |

### 외부 MCP 서버 (9개)

설정 기반(`configs/*.yaml`)으로 연결되는 AWS 공식 MCP 서버입니다.

| MCP 서버 | 패키지 | 도메인 | 설명 |
|----------|--------|--------|------|
| aws-cloudwatch | `awslabs.cloudwatch-mcp-server` | Monitoring | 메트릭/알람/로그/이상탐지 |
| aws-cloudwatch-applicationsignals | `awslabs.cloudwatch-applicationsignals-mcp-server` | Monitoring | 서비스 레벨 헬스/SLO |
| aws-network | `awslabs.aws-network-mcp-server` | Monitoring, Resource | VPC/TGW/Cloud WAN/Firewall 트러블슈팅 |
| aws-cloudtrail | `awslabs.cloudtrail-mcp-server` | Security | API 호출 이력/보안 감사 |
| aws-eks | `awslabs.eks-mcp-server` | Resource | Kubernetes 클러스터 관리 |
| aws-ecs | `awslabs.ecs-mcp-server` | Resource | 컨테이너 서비스 관리 |
| aws-lambda-tool | `awslabs.lambda-tool-mcp-server` | Resource | Lambda 함수 실행/관리 |
| aws-api | `awslabs.aws-api-mcp-server` | Resource | 범용 AWS API 호출 |
| aws-documentation | `awslabs.aws-documentation-mcp-server` | 전체 (공유) | AWS 공식 문서 검색/조회 |

## 환경 변수

```bash
# 필수
AWS_REGION=ap-northeast-2   # AWS 리전
AWS_PROFILE=default          # AWS CLI 프로필

# Observability (scripts/run_with_otel.sh 에서 자동 설정)
OTEL_SERVICE_NAME=aiops-agent-strands  # 서비스 식별자
OTEL_LOG_GROUP=agents/aiops-agent-logs # CloudWatch 로그 그룹
OTEL_LOG_STREAM=default                # CloudWatch 로그 스트림
```

## 참조

- [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [AgentCore Observability 문서](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
- [AgentCore Observability 샘플](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/06-AgentCore-observability)
- [Strands Agents SDK](https://github.com/strands-agents/strands-agents)
- [AWS MCP Servers](https://awslabs.github.io/mcp/) — AWS 공식 MCP 서버 목록
