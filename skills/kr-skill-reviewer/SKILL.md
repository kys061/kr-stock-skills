# kr-skill-reviewer: 스킬 품질 리뷰

> Dual-Axis (Auto 50% + LLM 50%) 방식으로 스킬의 품질을 평가합니다.
> US dual-axis-skill-reviewer의 한국 적용 (메타 스킬).

## 사용 시점

- 새로 개발한 스킬의 품질을 정량 평가할 때
- 스킬의 프로덕션 준비 상태를 확인할 때
- 스킬 간 품질 비교가 필요할 때

## Dual-Axis 방법론

### Auto Axis (50%)
코드 기반 결정적 체크. 재현 가능한 점수.

| 체크 | 가중치 | 설명 |
|------|:------:|------|
| metadata_use_case | 20% | SKILL.md 존재, 사용 시점 정의, 트리거 |
| workflow_coverage | 25% | 실행 단계, 입출력 정의, 오류 처리 |
| execution_safety | 25% | 명령 예시, 경로 위생, 재현성 |
| supporting_artifacts | 10% | 스크립트, 참조 문서, 상수 정의 |
| test_health | 20% | 테스트 존재, 통과, 커버리지 |

### LLM Axis (50%)
LLM 딥 리뷰. 주관적 품질 평가.

## 등급 기준

| 등급 | 점수 | 의미 |
|------|:----:|------|
| PRODUCTION_READY | 90+ | 프로덕션 배포 가능 |
| USABLE | 80-89 | 개선 필요하나 사용 가능 |
| NOTABLE_GAPS | 70-79 | 주목할 갭 존재 |
| HIGH_RISK | <70 | 고위험, 드래프트 취급 |

## 실행 방법

```bash
cd ~/stock/skills/kr-skill-reviewer/scripts
python auto_reviewer.py --skill-path ../kr-stock-analysis/
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| 모든 kr-* 스킬 | 리뷰 대상 |
