# Claude Code 작업 지침서 — Korean Stock Skills

## 필수 규칙

### 1. Git Commit & Push (필수)

스킬 파일(SKILL.md, scripts/, references/, tests/) 또는 프로젝트 설정(install.sh, README.md, .pdca-status.json)을 수정한 경우:

1. 수정 완료 후 반드시 `git add` → `git commit` → `git push origin main` 실행
2. `~/.claude/skills/`에도 변경된 SKILL.md 동기화
3. 커밋 메시지에 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` 포함

### 2. 스킬 수 동기화

새 스킬 추가/삭제 시 아래 3곳의 숫자를 일치시킨다:
- `README.md` 헤더 ("N개 전문 스킬")
- `README.md` Skills Reference 섹션 ("Skills Reference (N개)")
- `install.sh` ("N skills for KOSPI/KOSDAQ analysis")

### 2-1. README.md 동기화 (필수)

스킬 추가/수정 또는 프로젝트 설정 변경 시 `README.md`도 함께 업데이트한다:

| 변경 사항 | README.md 업데이트 대상 |
|-----------|----------------------|
| 새 스킬 추가/삭제 | 스킬 수, Skills Reference 섹션에 스킬 설명 추가/제거 |
| `_kr_common/` 공통 모듈 변경 (프로바이더 추가 등) | Tier 구조 설명, 설치 의존성(`pip install` 목록) |
| 데이터 소스 변경 (API 추가/제거) | Tier 구조 배지, Environment Variables 섹션 |
| `install.sh` 변경 | Installation 섹션 |
| 새 SKILL.md에 사용법 추가 | Skills Reference에 `/스킬명` 예시 추가 |

> **원칙**: `README.md`는 외부 사용자가 보는 문서이므로, 내부 변경이 사용자에게 영향을 주는 경우(설치 방법, 의존성, 사용 가능한 스킬, 데이터 소스 등) 반드시 반영한다.

### 3. Output Rule (개발자 지침)

모든 스킬 실행 결과는 마크다운 파일로 저장한다:
- 경로: `reports/{skill_name}_{종목코드}_{종목명}_{YYYYMMDD}.md`
- 종목 없는 분석: `reports/{skill_name}_market_{YYYYMMDD}.md`
- **리포트 템플릿**: `_kr_common/templates/` 에서 관리 (사용자에게 배포됨)
  - `report_rules.md` — 공통 포맷팅 규칙
  - `report_stock.md` — 개별 종목 분석 (Type A)
  - `report_screener.md` — 스크리닝 (Type B)
  - `report_macro.md` — 매크로/전략 (Type C)
- 새 스킬 추가 시 SKILL.md의 Output Rule에서 적절한 템플릿을 참조하도록 작성
- 템플릿 수정 시 `install.sh` 실행 필수 (`_kr_common/` 변경이므로)

### 4. 스킬 설치 동기화 (Deploy)

스킬 파일(SKILL.md, scripts/, references/, tests/) **또는 공통 모듈(`_kr_common/`)** 변경 시 **반드시** 아래 절차를 수행한다:

#### 4-1. 동기화 대상 범위
| 변경 대상 | 동기화 방법 | 비고 |
|-----------|-----------|------|
| 개별 스킬 (SKILL.md, scripts/) | `cp -r` 또는 `install.sh` | 해당 스킬만 |
| **`_kr_common/` (kr_client.py, providers/, utils/, config.py)** | **반드시 `install.sh` 실행** | **전 스킬이 import하는 공통 모듈** |
| install.sh, README.md | 해당 없음 (소스 직접 참조) | |

#### 4-2. 개별 스킬 동기화 (`~/.claude/skills/`)
```bash
# 변경된 스킬만 동기화
cp -r skills/{skill_name}/ ~/.claude/skills/{skill_name}/

# 여러 스킬 변경 시
for s in {skill_1} {skill_2} {skill_3}; do
  cp -r skills/$s/ ~/.claude/skills/$s/
done
```

#### 4-3. 전체 재설치 (공통 모듈 변경 시 필수)
```bash
./install.sh
```
> **`_kr_common/` 변경 시 반드시 `install.sh` 실행**. `~/.claude/skills/_kr_common/`이 구버전이면 모든 스킬이 구버전 코드로 동작한다.

#### 4-4. 동기화 검증
```bash
# 개별 스킬 검증
diff <(cat skills/{skill_name}/SKILL.md) <(cat ~/.claude/skills/{skill_name}/SKILL.md)

# 공통 모듈 검증 (핵심 파일)
diff skills/_kr_common/kr_client.py ~/.claude/skills/_kr_common/kr_client.py
diff skills/_kr_common/providers/ ~/.claude/skills/_kr_common/providers/ -r
```

#### 4-5. install.sh 업데이트
스킬 추가/삭제 시 `install.sh` 헤더의 스킬 수를 반드시 업데이트한다:
```bash
# install.sh 내 "N skills for KOSPI/KOSDAQ analysis" 숫자 변경
```

> **주의**: `~/.claude/skills/` 동기화를 빠뜨리면 Claude Code가 구버전 코드를 참조하여 잘못된 분석을 수행할 수 있다. 특히 `_kr_common/`의 프로바이더(yfinance, KRX API 등)나 `kr_client.py` 폴백 로직 변경 시 동기화 누락은 데이터 소스 폴백이 동작하지 않는 원인이 된다.

### 5. 데이터 소스 우선순위 (Fallback Policy)

스킬 실행 시 데이터 수집은 아래 우선순위를 따른다:

```
Tier 0: KRX Open API (인증키 기반, 일 10,000회, 승인 완료)  ← OHLCV, 시총, 지수
Tier 1: yfinance (무료, 무제한, OHLCV+재무+밸류에이션)  ← PER/PBR/재무제표 보완
Tier 2: KRClient (pykrx/FDR) — KRX 차단 시 사용 불가
Tier 3: KIS Open API (한국투자증권, 계좌 기반)
Tier 4: WebSearch 폴백 (항상 가용)
```
- KRX API: `.env`에 `KRX_API_KEY` 설정 완료, 전 서비스 승인 완료 (OHLCV/시총/지수)
- KRX API 미제공: PER/PBR/투자자별 매매동향 → yfinance(Tier 1)로 보완
- yfinance Provider: `_kr_common/providers/yfinance_provider.py` (KOSPI→.KS, KOSDAQ→.KQ)
- KRX Provider: `_kr_common/providers/krx_openapi_provider.py`
- 통합: `kr_client.py`에서 Tier 0 → Tier 1(yfinance) → Tier 2(PyKRX/FDR) 순 폴백
- **스킬 실행 시 반드시 Tier 0/1을 먼저 시도하고, 실패 시에만 WebSearch 폴백**

#### 5-1. WebSearch 폴백 규칙
Tier 0-2가 모두 실패(401/403/에러/미설정)할 경우 **WebSearch로 데이터를 수집**하여 분석을 계속한다:

- **개별 종목 분석**: 종목명+지표명으로 검색 (예: "알테오젠 PER PBR 시가총액 2026")
- **전 종목 스크리닝**: 섹터별/조건별 다중 검색 후 후보군 통합
- **수급 데이터**: "코스닥 외국인 순매수 상위" 등 집계 데이터 검색
- **기술적 지표**: 증권사 리포트, 목표가, 차트 분석 기사 활용

#### 5-2. WebSearch 폴백 시 리포트 표기
WebSearch 폴백으로 분석한 경우 리포트에 반드시 아래를 명시한다:
```markdown
> **데이터 소스**: WebSearch 폴백 (Tier 0-2 실패)
> **정밀도 한계**: PER/PBR/ROE 등 정량 지표는 뉴스/리포트 기반 추정치
```

#### 5-3. KRX Open API 상태 (2026-03-07 업데이트)
- `krx_openapi_provider.py` → `kr_client.py` Tier 0 통합 완료
- **전 서비스 승인 완료**: 주식 일별시세(KOSPI/KOSDAQ), 종목 상장정보, 지수 일별시세
- **미제공 데이터**: PER/PBR, 투자자별 매매동향 → yfinance(Tier 1) 또는 PyKRX(Tier 2)로 보완

### 6. US 통화정책 오버레이 (필수)

아래 12개 스킬 실행 시 **반드시** US 통화정책 분석을 포함한다:

**스코어링 오버레이 적용 (점수 조정)**:
- `kr-stock-analysis` — 종합 점수에 B방식 오버레이 가산
- `kr-sector-analyst` — 섹터별 민감도 반영 영향도 평가
- `kr-growth-outlook` — 금리 환경의 할인율 영향 반영
- `kr-portfolio-manager` — 자산배분에 통화정책 방향 반영
- `kr-strategy-synthesizer` — 확신도에 오버레이 가산

**컨텍스트 필수 포함 (정성 분석)**:
- `kr-macro-regime` — Fed 정책의 한국 레짐 전환 영향
- `kr-market-environment` — US 통화정책 현황 별도 섹션
- `kr-market-breadth` — 글로벌 유동성과 시장폭 관계
- `kr-scenario-analyzer` — 시나리오에 Fed 정책 경로 포함
- `kr-earnings-trade` — 통화정책 환경의 실적 모멘텀 영향
- `kr-economic-calendar` — FOMC 일정 병행 표시
- `kr-weekly-strategy` — 주간 체크리스트에 Fed 변수 추가

**공통 절차**:
1. WebSearch로 현재 Fed 금리, FOMC 기조, DXY, BOK 금리, 한미 금리차 조회
2. US Regime Score 산출 (stance×0.35 + rate×0.30 + liquidity×0.35)
3. 리포트에 US 통화정책 섹션 필수 포함

### 7. 리포트 이메일 발송

리포트 MD 파일(`reports/` 디렉토리)을 생성한 후, 이메일 발송을 시도한다:

```bash
cd ~/stock && python3 skills/_kr_common/utils/email_sender.py "reports/{파일명}.md" "{스킬명}"
```

- `EMAIL_ENABLED=false`(기본값)이면 자동 스킵
- 발송 실패 시에도 리포트 생성은 정상 완료로 간주 (fail-safe)
- `.env`에 Gmail App Password 설정 필요 (`EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`, `EMAIL_TO`)

### 8. 테스트

스크립트 수정 시 해당 스킬의 테스트를 실행하여 기존 테스트가 깨지지 않았는지 확인한다:
```bash
cd skills/{skill_name}/scripts && python -m pytest tests/ -v
```

## 프로젝트 구조

- **스킬**: `skills/kr-*/`, `skills/us-*/`
- **공통 모듈**: `skills/_kr_common/`
- **PDCA 문서**: `docs/01-plan/`, `docs/02-design/`, `docs/03-analysis/`, `docs/04-report/`
- **아카이브**: `docs/archive/YYYY-MM/`
- **리포트 출력**: `reports/` (.gitignore 대상)
- **PDCA 상태**: `.pdca-status.json`

## 현재 상태

- 총 46개 스킬 (Phase 1-9 + 3 Patch)
- 누적 2,009+ 테스트
- Phase 3-9 + 3 Patch 연속 10회 97% Match Rate
