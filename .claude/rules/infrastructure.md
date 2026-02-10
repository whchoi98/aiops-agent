---
paths:
  - "infrastructure/**/*"
---

# 인프라 코드 규칙

## CDK (TypeScript)

- 스택별로 파일 분리
- L2 Construct 우선 사용
- 환경별 설정은 cdk.json의 context 활용

## Terraform

- 모듈화하여 재사용성 확보
- 상태 파일은 S3 + DynamoDB 백엔드 사용
- 변수에 description과 validation 필수

## 공통

- 모든 리소스에 태깅 정책 적용
- 비용 추적을 위한 CostCenter 태그 필수
- 프로덕션 리소스는 삭제 보호 활성화
