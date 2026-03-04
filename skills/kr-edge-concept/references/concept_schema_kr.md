# 엣지 컨셉 스키마 (한국)

## 컨셉 구조

```yaml
concepts:
  - id: "concept-001"
    hypothesis_type: "breakout"
    title: "참여 확대 기반 추세 돌파"
    thesis: "외국인/기관 동반 매수 → 52주 신고가 돌파 시 추세 가속"
    invalidation:
      - "외국인 순매도 전환"
      - "KOSPI 200일 이동평균선 하회"
    playbooks:
      - "pivot_breakout: 신고가 돌파 + 거래량 확인"
    support:
      ticket_count: 3
      hint_count: 2
    regime: "RiskOn"
    export_ready: true
    entry_family: "pivot_breakout"
```

## 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| id | str | Y | 고유 식별자 |
| hypothesis_type | str | Y | 8개 가설 유형 |
| title | str | Y | 한국어 제목 |
| thesis | str | Y | 가설 설명 |
| invalidation | list[str] | Y | 무효화 조건 |
| playbooks | list[str] | Y | 전략 플레이북 |
| support.ticket_count | int | Y | 지지 티켓 수 |
| support.hint_count | int | N | 지지 힌트 수 |
| regime | str | N | RiskOn / RiskOff / Neutral |
| export_ready | bool | Y | 내보내기 가능 여부 |
| entry_family | str | N | pivot_breakout / gap_up_continuation |

## 합성 규칙

1. (hypothesis_type, regime) 기준으로 티켓 클러스터링
2. 클러스터 내 티켓 수 >= MIN_TICKET_SUPPORT 이상만 컨셉 생성
3. 같은 패밀리 힌트 매칭 → support.hint_count 증가
4. entry_family가 EXPORTABLE_FAMILIES에 포함 → export_ready = true
