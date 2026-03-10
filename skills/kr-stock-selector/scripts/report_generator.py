"""마크다운 리포트 생성 모듈.

통과 종목, 조건별 통과율, Watch List를 마크다운 테이블로 생성.
report_rules.md 규칙 준수.
"""

import logging
import os
from datetime import datetime

from trend_analyzer import CONDITION_NAMES

logger = logging.getLogger(__name__)


def generate_report(
    results: list[dict],
    universe_size: int,
    date: str = None,
    market_filter: str = "ALL",
) -> str:
    """마크다운 리포트 문자열 생성."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    parts = [
        build_header(date, market_filter),
        build_summary(results, universe_size),
        build_pass_table(results),
        build_condition_stats(results),
        build_watch_list(results),
        build_footer(date),
    ]
    return '\n'.join(parts)


def build_header(date: str, market_filter: str) -> str:
    """리포트 헤더."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    market_label = market_filter if market_filter != "ALL" else "KOSPI+KOSDAQ"
    return (
        f"# 주식종목선별 리포트\n\n"
        f"> 생성일: {now} | 대상: {market_label} | 시총 >= 1,000억원\n"
        f"> 데이터 소스: KRX Open API (Tier 0) + yfinance (Tier 1) | 분석 유형: SCREENING\n"
    )


def build_summary(results: list[dict], universe_size: int) -> str:
    """요약 섹션."""
    passed = [r for r in results if r.get('all_pass')]
    pass_count = len(passed)
    pct = (pass_count / universe_size * 100) if universe_size > 0 else 0.0

    return (
        f"\n---\n\n## 요약\n\n"
        f"- 분석 대상: {universe_size}개 (시총 >= 1,000억원)\n"
        f"- **통과 종목: {pass_count}개** ({pct:.1f}%)\n"
    )


def build_pass_table(results: list[dict]) -> str:
    """통과 종목 테이블 (시가총액 내림차순)."""
    passed = sorted(
        [r for r in results if r.get('all_pass')],
        key=lambda x: x.get('market_cap', 0),
        reverse=True,
    )

    if not passed:
        return "\n---\n\n## 통과 종목\n\n통과 종목이 없습니다.\n"

    lines = [
        "\n---\n\n## 통과 종목\n",
        "| # | 종목코드 | 종목명 | 섹터 | 시장 | 시총(억) | 현재가 | 52주대비저 | 52주대비고 |",
        "|---|---------|--------|------|------|-------:|------:|:---------:|:---------:|",
    ]

    for i, r in enumerate(passed, 1):
        details = r.get('details', {})
        mcap_eok = r.get('market_cap', 0) / 1e8
        low_pct = details.get('week52_low_pct', 0) * 100
        high_pct = details.get('week52_high_pct', 0) * 100
        sector = r.get('sector', '미분류') or '미분류'
        lines.append(
            f"| {i} | {r['ticker']} | {r['name']} | {sector} | {r['market']} "
            f"| {mcap_eok:,.0f} | {r.get('close', 0):,} "
            f"| +{low_pct:.1f}% | {high_pct:+.1f}% |"
        )

    return '\n'.join(lines) + '\n'


def build_condition_stats(results: list[dict]) -> str:
    """조건별 통과율 테이블."""
    total = len(results)
    if total == 0:
        return "\n---\n\n## 조건별 통과율\n\n분석 대상 없음.\n"

    condition_keys = ['ma_trend', 'ma_alignment', 'week52_low', 'week52_high', 'market_cap']

    lines = [
        "\n---\n\n## 조건별 통과율\n",
        "| 조건 | 설명 | 통과 | 비율 |",
        "|------|------|:----:|:----:|",
    ]

    for i, key in enumerate(condition_keys, 1):
        desc = CONDITION_NAMES.get(key, key)
        count = sum(1 for r in results if r.get('conditions', {}).get(key, False))
        pct = count / total * 100

        note = " (사전필터)" if key == 'market_cap' else ""
        lines.append(
            f"| 조건 {i} | {desc} | {count} | {pct:.1f}%{note} |"
        )

    return '\n'.join(lines) + '\n'


def build_watch_list(results: list[dict], min_pass: int = 4) -> str:
    """Watch List (4/5 통과 종목)."""
    watch = sorted(
        [r for r in results if r.get('pass_count', 0) == min_pass],
        key=lambda x: x.get('market_cap', 0),
        reverse=True,
    )

    if not watch:
        return f"\n---\n\n## Watch List ({min_pass}/5 통과)\n\n해당 종목 없음.\n"

    lines = [
        f"\n---\n\n## Watch List ({min_pass}/5 통과)\n",
        "| 종목코드 | 종목명 | 섹터 | 미충족 조건 | 현재 수치 | 필요 수치 |",
        "|---------|--------|------|-----------|:--------:|:--------:|",
    ]

    for r in watch:
        conditions = r.get('conditions', {})
        details = r.get('details', {})
        sector = r.get('sector', '미분류') or '미분류'

        # 미충족 조건 찾기
        failed = [k for k, v in conditions.items() if not v]
        for key in failed:
            current_val, need_val = _get_gap_values(key, details)
            desc = CONDITION_NAMES.get(key, key)
            lines.append(
                f"| {r['ticker']} | {r['name']} | {sector} | {desc} | {current_val} | {need_val} |"
            )

    return '\n'.join(lines) + '\n'


def _get_gap_values(condition_key: str, details: dict) -> tuple[str, str]:
    """미충족 조건의 현재/필요 수치 반환."""
    if condition_key == 'ma_trend':
        days = details.get('ma_trend_days', 0)
        return f"{days}일", "20일"
    elif condition_key == 'ma_alignment':
        close = details.get('close', 0)
        sma50 = details.get('sma50', 0)
        if close and sma50 and close <= sma50:
            return f"종가 < 50SMA", "종가 > 50SMA"
        sma150 = details.get('sma150', 0)
        if sma50 and sma150 and sma50 <= sma150:
            return f"50SMA < 150SMA", "50SMA > 150SMA"
        return "역전", "정배열"
    elif condition_key == 'week52_low':
        pct = details.get('week52_low_pct', 0) * 100
        return f"+{pct:.1f}%", "+30.0%"
    elif condition_key == 'week52_high':
        pct = details.get('week52_high_pct', 0) * 100
        return f"{pct:+.1f}%", "-25.0%"
    elif condition_key == 'market_cap':
        return "-", ">= 1,000억"
    return "-", "-"


def build_footer(date: str) -> str:
    """리포트 풋터."""
    return f"\n---\n*Generated by kr-stock-selector | {date}*\n"


def save_report(
    content: str,
    date: str = None,
    output_dir: str = None,
) -> str:
    """리포트 파일 저장.

    Returns:
        저장된 파일 경로
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    date_compact = date.replace('-', '')

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'reports'
        )

    os.makedirs(output_dir, exist_ok=True)

    filename = f"kr-stock-selector_market_주식종목선별_{date_compact}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"리포트 저장: {filepath}")
    return filepath
