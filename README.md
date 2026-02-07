# AIOps Agent

Amazon Bedrock AgentCore 기반 AWS 인프라 운영 자동화 에이전트.

## 개요

AWS 인프라를 지능적으로 모니터링하고 운영하는 AIOps 에이전트입니다.
[AgentCore E2E 튜토리얼](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/09-AgentCore-E2E) 패턴을 따릅니다.

### 핵심 기능

- **CloudWatch 모니터링**: 메트릭/알람/로그 분석
- **비용 최적화**: Cost Explorer 기반 비용 분석 및 라이트사이징 권장
- **보안 점검**: Security Hub, GuardDuty 통합
- **EC2 관리**: 인스턴스 상태, EBS 볼륨 관리
- **네트워크 분석**: VPC 토폴로지, 보안 그룹, 라우팅
- **리소스 인벤토리**: 전체 AWS 자산 요약

## 프로젝트 구조

```
aiops_agent/
├── agents/
│   ├── aiops_agent.py      # 에이전트 정의 + 도구 + 시스템 프롬프트
│   ├── memory.py            # AgentCore Memory 통합
│   ├── runtime.py           # AgentCore Runtime 엔트리포인트
│   └── utils.py             # SSM, IAM, 설정 유틸리티
├── tools/
│   ├── cloudwatch_tools.py  # CloudWatch 메트릭/알람/로그
│   ├── cost_explorer_tools.py # 비용 분석
│   ├── security_tools.py    # Security Hub / GuardDuty
│   ├── ec2_tools.py         # EC2 인스턴스 관리
│   ├── vpc_tools.py         # VPC 네트워크 분석
│   └── resource_inventory.py # 리소스 인벤토리
├── gateway/
│   ├── api_spec.json        # 21개 도구 MCP 스키마 정의
│   ├── lambda_handler.py    # Lambda 디스패치 핸들러
│   └── setup_gateway.py     # Gateway 생성/삭제 스크립트
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
python -m agents.runtime
```

## AgentCore Gateway (MCP)

21개 AIOps 도구를 MCP 프로토콜로 노출하여 다른 에이전트/서비스에서 재사용할 수 있습니다.
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
| `gateway/api_spec.json` | 21개 도구의 MCP JSON Schema 정의 |
| `gateway/lambda_handler.py` | Lambda 디스패치 핸들러 (도구 라우팅) |
| `gateway/setup_gateway.py` | Gateway + Cognito + Target 생성/삭제 |
| `AIOpsGatewayLambda` | CloudFormation Lambda 함수 |
| `GatewayAgentCoreRole` | Gateway → Lambda 호출 IAM 역할 |

### 인증

Cognito JWT 기반 인증을 사용합니다. Gateway 생성 시 자동으로 Cognito User Pool 이 생성됩니다.

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

| 모듈 | 도구 | 설명 |
|------|------|------|
| cloudwatch_tools | `get_cloudwatch_metrics` | CloudWatch 메트릭 조회 |
| cloudwatch_tools | `get_cloudwatch_alarms` | 알람 상태 조회 |
| cloudwatch_tools | `query_cloudwatch_logs` | Logs Insights 쿼리 |
| cloudwatch_tools | `describe_ec2_instances` | EC2 인스턴스 정보 |
| cost_explorer_tools | `get_cost_and_usage` | 비용 및 사용량 |
| cost_explorer_tools | `get_cost_forecast` | 비용 예측 |
| cost_explorer_tools | `get_rightsizing_recommendations` | 라이트사이징 권장 |
| cost_explorer_tools | `get_cost_by_service` | 서비스별 비용 |
| security_tools | `get_security_findings` | Security Hub 발견 사항 |
| security_tools | `get_guardduty_findings` | GuardDuty 위협 탐지 |
| security_tools | `get_iam_credential_report` | IAM 자격 증명 보고서 |
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

## 환경 변수

```bash
AWS_REGION=ap-northeast-2   # AWS 리전
AWS_PROFILE=default          # AWS CLI 프로필
```

## 참조

- [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Strands Agents SDK](https://github.com/strands-agents/strands-agents)
