# AgentCore 참조 저장소 가이드

이 문서는 AWS AIOps Platform 개발 시 참조해야 할 Amazon Bedrock AgentCore 샘플 저장소에 대한 상세 가이드입니다.

## 참조 저장소

### 1. AWS Labs 공식 저장소
- **URL**: https://github.com/awslabs/amazon-bedrock-agentcore-samples
- **용도**: 최신 공식 업데이트, 베스트 프랙티스

### 2. whchoi98 포크
- **URL**: https://github.com/whchoi98/amazon-bedrock-agentcore-samples
- **용도**: 한국어 환경 참조, 추가 예제

## 디렉토리별 참조 매핑

### src/agents/ 구현 시 참조

| 에이전트 | 참조 경로 | 핵심 파일 |
|----------|-----------|-----------|
| monitoring | `02-use-cases/aws-operations-agent/` | agent.py, tools/ |
| cost_optimizer | `02-use-cases/cost-optimization-agent/` | - |
| security | `02-use-cases/aws-operations-agent/` | security 관련 도구 |
| incident_response | `02-use-cases/sre-agent/` | - |
| resource_manager | `02-use-cases/device-management-agent/` | - |

### src/tools/ 구현 시 참조

```
01-tutorials/02-AgentCore-gateway/
├── creating-mcp-tools.ipynb      # MCP 도구 생성 방법
├── lambda-gateway.ipynb          # Lambda 기반 게이트웨이
└── api-gateway-integration.ipynb # API Gateway 통합
```

### src/gateway/ 구현 시 참조

```
01-tutorials/02-AgentCore-gateway/
└── gateway-configuration.ipynb   # 게이트웨이 설정
```

### src/memory/ 구현 시 참조

```
01-tutorials/04-AgentCore-memory/
├── memory-basics.ipynb           # 메모리 기본 개념
├── session-memory.ipynb          # 세션 메모리
└── long-term-memory.ipynb        # 장기 메모리
```

### src/identity/ 구현 시 참조

```
01-tutorials/03-AgentCore-identity/
├── cognito-integration.ipynb     # Cognito 통합
├── okta-integration.ipynb        # Okta 통합
└── oauth-flows.ipynb             # OAuth 플로우
```

### src/observability/ 구현 시 참조

```
01-tutorials/06-AgentCore-observability/
├── opentelemetry-setup.ipynb     # OpenTelemetry 설정
├── cloudwatch-integration.ipynb  # CloudWatch 연동
└── tracing.ipynb                 # 분산 추적
```

### src/policy/ 구현 시 참조

```
01-tutorials/08-AgentCore-policy/
├── cedar-basics.ipynb            # Cedar 정책 기본
├── policy-examples.ipynb         # 정책 예제
└── fine-grained-access.ipynb     # 세밀한 접근 제어
```

### infrastructure/ 구현 시 참조

```
04-infrastructure-as-code/
├── cloudformation/
│   ├── agentcore-stack.yaml      # 기본 스택
│   └── networking.yaml           # 네트워킹
├── cdk/
│   ├── lib/                      # CDK 컨스트럭트
│   └── bin/                      # 엔트리포인트
└── terraform/
    ├── modules/                  # 재사용 모듈
    └── environments/             # 환경별 설정
```

### evaluations/ 구현 시 참조

```
01-tutorials/07-AgentCore-evaluations/
├── builtin-evaluators.ipynb      # 내장 평가자
├── custom-evaluators.ipynb       # 커스텀 평가자
└── benchmarking.ipynb            # 벤치마킹
```

## Use Cases 상세 참조

### aws-operations-agent
**경로**: `02-use-cases/aws-operations-agent/`

AWS 운영 자동화를 위한 종합적인 에이전트 구현:
- Okta 인증 통합
- CloudWatch 모니터링
- EC2/Lambda/RDS 관리
- 인시던트 대응

**참조 파일**:
```
aws-operations-agent/
├── agent.py                      # 메인 에이전트
├── tools/
│   ├── cloudwatch_tools.py       # CloudWatch 도구
│   ├── ec2_tools.py              # EC2 도구
│   └── lambda_tools.py           # Lambda 도구
├── prompts/
│   └── system_prompt.py          # 시스템 프롬프트
└── config/
    └── settings.py               # 설정
```

### cost-optimization-agent
**경로**: `02-use-cases/cost-optimization-agent/`

비용 최적화 분석 및 권장:
- Cost Explorer 통합
- Rightsizing 권장
- Reserved Instance 분석
- Savings Plans 제안

### sre-agent
**경로**: `02-use-cases/sre-agent/`

SRE 자동화:
- 인시던트 감지
- 자동 복구
- 런북 실행
- 포스트모템 생성

## 프레임워크 통합 참조

### Strands Agents (권장)
**경로**: `03-integrations/strands-agents/`

```python
from strands import Agent, tool

@tool
def my_tool(param: str) -> dict:
    """도구 설명"""
    pass

agent = Agent(
    name="my-agent",
    model="anthropic.claude-4-opus",
    tools=[my_tool],
)
```

### CrewAI (멀티에이전트)
**경로**: `03-integrations/crewai/`

복잡한 멀티에이전트 워크플로우 구현 시 참조

### LangGraph (워크플로우)
**경로**: `03-integrations/langgraph/`

상태 기반 에이전트 워크플로우 구현 시 참조

## 클론 및 참조 방법

```bash
# 참조 저장소 클론
git clone https://github.com/awslabs/amazon-bedrock-agentcore-samples.git ~/agentcore-samples

# whchoi98 포크 클론
git clone https://github.com/whchoi98/amazon-bedrock-agentcore-samples.git ~/agentcore-samples-kr

# 특정 튜토리얼 노트북 실행
cd ~/agentcore-samples/01-tutorials/01-AgentCore-runtime
jupyter notebook
```

## 업데이트 추적

참조 저장소의 최신 변경사항을 추적하려면:

```bash
cd ~/agentcore-samples
git fetch origin
git log origin/main --oneline -10
```
