# 참조 저장소 활용 규칙

## 필수 참조

새로운 에이전트나 도구를 구현할 때는 반드시 아래 저장소의 관련 예제를 먼저 확인:

- https://github.com/awslabs/amazon-bedrock-agentcore-samples

## 참조 우선순위

1. **01-tutorials/**: 컴포넌트별 기본 패턴 학습
2. **02-use-cases/**: 실제 구현 패턴 참조
3. **03-integrations/**: 프레임워크 통합 방법
4. **04-infrastructure-as-code/**: IaC 템플릿

## 코드 참조 시 주의사항

- 저장소 코드를 그대로 복사하지 않고 프로젝트 컨벤션에 맞게 수정
- 라이선스(Apache-2.0) 준수
- 버전 호환성 확인 (bedrock-agentcore, strands-agents)

## 상세 매핑

자세한 참조 매핑은 @docs/architecture/REFERENCE_REPOS.md 참조
