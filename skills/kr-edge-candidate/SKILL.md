---
name: kr-edge-candidate
description: 한국 시장 데이터 기반 엣지 후보 자동 탐지 및 파이프라인 내보내기. KOSPI200 종목에서 수급/기술적 시그널 기반 후보 선별.
---

# kr-edge-candidate

> 한국 시장 데이터 기반 엣지 후보 자동 탐지 및 파이프라인 내보내기 스킬.

## 개요

한국 주식 시장 데이터에서 엣지 후보를 자동 탐지하고,
edge-finder-candidate/v1 인터페이스로 검증하여 파이프라인용 strategy.yaml을 생성한다.
엣지 파이프라인의 최종 단계.

## 인터페이스: edge-finder-candidate/v1

필수 키: id, name, universe, signals, risk, cost_model, validation, promotion_gates

## 한국 유니버스

| 유니버스 | 설명 |
|----------|------|
| kospi200 | KOSPI200 구성종목 |
| kosdaq150 | KOSDAQ150 구성종목 |
| all_kospi | KOSPI 전체 |
| all_kosdaq | KOSDAQ 전체 |

## 파이프라인 위치

```
kr-edge-hint → kr-edge-concept → kr-edge-strategy → [kr-edge-candidate]
                                                          ↓
                                                    strategy.yaml
```

## 사용법

```bash
python auto_detect_candidates.py --ohlcv data.csv --output candidates/
python candidate_contract.py --ticket ticket.yaml --validate
python export_candidate.py --candidate candidate.json --output-dir strategies/
```
