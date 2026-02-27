# Korean Stock Trading Skills for Claude Code

한국 주식 시장 분석을 위한 Claude Code 커스텀 스킬 모음.

> **Tier 1**: 증권 계좌 없이 즉시 사용 가능 (PyKRX + FinanceDataReader + OpenDartReader)
> **Tier 2**: 한국투자증권 Open API 연동 (선택)

## Quick Install

```bash
git clone https://github.com/kys061/kr-stock-skills.git
cd kr-stock-skills
./install.sh
```

## Features

### Common Data Client (`_kr-common`)
모든 KR 스킬이 공유하는 통합 데이터 클라이언트.

| 기능 | 데이터 소스 | Tier |
|------|------------|------|
| 시세 (OHLCV) | PyKRX, FDR | 1 |
| 밸류에이션 (PER/PBR/EPS) | PyKRX | 1 |
| 투자자별 매매동향 (12분류) | PyKRX | 1 |
| 공매도 잔고/거래량 | PyKRX | 1 |
| 재무제표 (BS/IS/CF) | DART | 1* |
| 글로벌 지수/환율/원자재 | FDR | 1 |
| FRED 경제지표 | FDR | 1 |
| ETF NAV/괴리율/구성종목 | PyKRX | 1 |
| 국채/회사채 수익률 | PyKRX | 1 |
| 공시/대주주/배당 | DART | 1* |
| 실시간 시세/분봉/호가 | 한투 API | 2 |

\* DART API 키 필요 (무료 발급: https://opendart.fss.or.kr/)

### Usage

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/skills'))
from _kr_common.kr_client import KRClient

client = KRClient()

# 삼성전자 최근 1년 일봉
df = client.get_ohlcv('삼성전자', '2025-03-01')

# 외국인 순매수 상위
top = client.get_top_net_purchases('2026-02-01', investor='외국인')

# PER/PBR 밸류에이션
fund = client.get_fundamentals('005930', '2026-01-01')
```

## Project Structure

```
kr-stock-skills/
├── README.md
├── install.sh              # 설치 스크립트
├── .gitignore
├── skills/
│   ├── _kr-common/         # 공통 데이터 클라이언트 (Phase 1)
│   └── (future skills)     # Phase 2~9에서 추가
├── agents/                 # Agent 정의
└── docs/                   # PDCA 설계 문서
    ├── 01-plan/
    ├── 02-design/
    ├── 03-analysis/
    └── 04-report/
```

## Development Roadmap

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 공통 모듈 (`_kr-common`) | Done |
| 2 | 시장 분석 스킬 (7개) | - |
| 3 | 마켓 타이밍 스킬 (5개) | - |
| 4 | 스크리닝 스킬 (8개) | - |
| 5 | 캘린더/이벤트 스킬 (3개) | - |
| 6 | 전략 스킬 (6개) | - |
| 7 | 배당/가치 스킬 (5개) | - |
| 8 | 메타/포트폴리오 스킬 (5개) | - |
| 9 | KR 전용 스킬 (5개) | - |

## Requirements

- Python 3.9+
- Claude Code CLI

### Python Dependencies
```
pykrx>=1.0.0
finance-datareader>=0.9.0
opendartreader>=0.2.0
pandas>=2.0.0
numpy>=1.24.0
```

## License

MIT
