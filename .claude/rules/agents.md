---
paths:
  - "src/agents/**/*.py"
---

# 에이전트 개발 규칙

## 구조

- 모든 에이전트는 `strands.Agent`를 상속해야 함
- 에이전트별 디렉토리에 `main.py`, `tools.py`, `prompts.py` 파일 구성
- 도구 함수는 `@tool` 데코레이터 사용 필수

## 에러 처리

- AWS API 호출 시 `botocore.exceptions` 처리 필수
- 재시도 로직에 exponential backoff 적용
- 에러 로깅 시 컨텍스트 정보 포함

## 테스트

- 모든 에이전트 로직에 단위 테스트 작성
- AWS 서비스 호출은 moto 라이브러리로 모킹
