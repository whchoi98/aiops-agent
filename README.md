# AIOps Agent

Amazon Bedrock AgentCore 기반 AWS 인프라 운영 자동화 에이전트.

## 개요

AWS 인프라를 지능적으로 모니터링하고 운영하는 AIOps 에이전트입니다.
[AgentCore E2E 튜토리얼](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/09-AgentCore-E2E) 패턴을 따릅니다.

### 핵심 기능

- **CloudWatch 모니터링**: AWS 공식 CloudWatch MCP 서버 연동 (메트릭/알람/로그/이상탐지)
- **비용 최적화**: Cost Explorer 기반 비용 분석 및 라이트사이징 권장
- **보안 점검**: Security Hub, GuardDuty 통합
- **EC2 관리**: 인스턴스 상태, EBS 볼륨 관리
- **네트워크 분석**: VPC 토폴로지, 보안 그룹, 라우팅
- **리소스 인벤토리**: 전체 AWS 자산 요약

## 프로젝트 구조

```
aiops_agent/
├── agents/
│   ├── aiops_agent.py        # 통합 에이전트 정의 (18개 도구 + 시스템 프롬프트)
│   ├── runtime_base.py       # 공유 팩토리 함수 (create_app)
│   ├── runtime.py            # 통합 Runtime 엔트리포인트 (하위 호환)
│   ├── memory.py             # AgentCore Memory 통합
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
│   └── resource/             # 리소스 관리 특화 런타임
│       ├── agent.py          #   도구: ec2 4 + vpc 5 + inventory 2 (11개)
│       └── runtime.py        #   엔트리포인트
├── tools/
│   ├── cost_explorer_tools.py # 비용 분석
│   ├── security_tools.py    # Security Hub / GuardDuty
│   ├── ec2_tools.py         # EC2 인스턴스 관리
│   ├── vpc_tools.py         # VPC 네트워크 분석
│   └── resource_inventory.py # 리소스 인벤토리
├── gateway/
│   ├── api_spec.json        # 18개 도구 MCP 스키마 정의
│   ├── lambda_handler.py    # Lambda 디스패치 핸들러
│   └── setup_gateway.py     # Gateway 생성/삭제 스크립트
├── configs/
│   ├── mcp_servers.yaml     # 통합 MCP 설정 (전체 MCP 서버)
│   ├── monitoring.yaml      # 모니터링 MCP 설정 (aws-cloudwatch)
│   ├── cost.yaml            # 비용 MCP 설정 (빈 mcp_servers)
│   ├── security.yaml        # 보안 MCP 설정 (빈 mcp_servers)
│   └── resource.yaml        # 리소스 MCP 설정 (빈 mcp_servers)
├── prerequisite/
│   ├── infrastructure.yaml  # CloudFormation (IAM Role, Lambda, SSM)
│   └── deploy.sh            # 인프라 배포 스크립트
├── scripts/
│   ├── setup.sh             # 환경 설정
│   └── cleanup.sh           # 리소스 정리
├── tests/
│   ├── test_tools.py        # 도구 단위 테스트
│   └── test_local.py        # 로컬 에이전트 테스트
└── requirements.txt
```

## 시작하기

### 1. 환경 설정

```bash
bash scripts/setup.sh
```

### 2. 인프라 배포

```bash
bash prerequisite/deploy.sh
```

### 3. 로컬 실행

```bash
source .venv/bin/activate

python -c "
from agents.aiops_agent import create_agent
agent = create_agent()
response = agent('현재 EC2 인스턴스 상태를 확인해줘')
print(response)
"
```

### 4. AgentCore Runtime 실행

```bash
# 통합 런타임 (18개 도구 전체 + 모든 MCP)
python -m agents.runtime

# 도메인별 특화 런타임
python -m agents.monitoring.runtime   # CloudWatch MCP + EC2 상태
python -m agents.cost.runtime         # Cost Explorer 4개 도구
python -m agents.security.runtime     # Security Hub / GuardDuty / IAM
python -m agents.resource.runtime     # EC2 + VPC + 인벤토리 (11개 도구)
```

### 멀티 런타임 아키텍처

독립 배포/스케일링/장애 격리가 가능한 4개 도메인별 런타임으로 분리되어 있습니다.

```
                        ┌─────────────────────────────┐
                        │      runtime_base.py        │
                        │  create_app() 공유 팩토리   │
                        │  (Memory, MCP, Gateway)     │
                        └──────────┬──────────────────┘
               ┌───────────┬──────┴───────┬────────────┐
               ▼           ▼              ▼            ▼
       ┌──────────┐ ┌──────────┐  ┌──────────┐ ┌──────────┐
       │Monitoring│ │   Cost   │  │ Security │ │ Resource │
       │ Runtime  │ │ Runtime  │  │ Runtime  │ │ Runtime  │
       ├──────────┤ ├──────────┤  ├──────────┤ ├──────────┤
       │EC2 (1)   │ │CE (4)    │  │SecHub (1)│ │EC2 (4)   │
       │+CW MCP   │ │          │  │GD (1)    │ │VPC (5)   │
       │          │ │          │  │IAM (1)   │ │Inv (2)   │
       └──────────┘ └──────────┘  └──────────┘ └──────────┘
               ┌───────────┴──────────────┘
               ▼
       ┌──────────────┐
       │ 통합 Runtime │  ← agents/runtime.py (하위 호환)
       │  (18개 전체) │
       └──────────────┘
```

| 런타임 | 모듈 경로 | 로컬 도구 | MCP 서버 | MCP 설정 |
|--------|-----------|-----------|----------|----------|
| **Monitoring** | `agents/monitoring/` | describe_ec2_instances (1) | aws-cloudwatch (stdio) | `configs/monitoring.yaml` |
| **Cost** | `agents/cost/` | cost_explorer_tools 4개 | 없음 | `configs/cost.yaml` |
| **Security** | `agents/security/` | security_tools 3개 | 없음 | `configs/security.yaml` |
| **Resource** | `agents/resource/` | ec2 4 + vpc 5 + inventory 2 (11) | 없음 | `configs/resource.yaml` |
| **통합** | `agents/runtime.py` | 전체 18개 | aws-cloudwatch | `configs/mcp_servers.yaml` |

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

`configs/mcp_servers.yaml` 에서 외부 MCP 서버를 설정 기반으로 관리합니다.
MCP 서버 추가 시 설정 파일만 수정하면 되고, 코드 변경은 필요 없습니다.

```yaml
# configs/mcp_servers.yaml
mcp_servers:
  - name: aws-cloudwatch
    enabled: true
    transport: stdio
    command: uvx
    args: [awslabs.cloudwatch-mcp-server@latest]
    env:
      AWS_REGION: "${AWS_REGION}"
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

### AWS CloudWatch MCP (외부)

CloudWatch 모니터링은 AWS 공식 CloudWatch MCP 서버로 대체되었습니다.
Gateway 또는 MCP 클라이언트를 통해 다음 도구에 접근할 수 있습니다.

| MCP 도구 | 설명 |
|----------|------|
| `get_metric_data` | 메트릭 데이터 조회 (고급 필터링/페이지네이션) |
| `analyze_metric` | 메트릭 트렌드/계절성 분석 |
| `get_active_alarms` | 활성 알람 조회 |
| `get_alarm_history` | 알람 상태 이력 |
| `get_recommended_metric_alarms` | 알람 임계값 추천 |
| `execute_log_insights_query` | Logs Insights 쿼리 |
| `analyze_log_group` | 로그 이상 탐지/패턴 분석 |
| `describe_log_groups` | 로그 그룹 목록 |

## 환경 변수

```bash
AWS_REGION=ap-northeast-2   # AWS 리전
AWS_PROFILE=default          # AWS CLI 프로필
```

## 참조

- [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Strands Agents SDK](https://github.com/strands-agents/strands-agents)
