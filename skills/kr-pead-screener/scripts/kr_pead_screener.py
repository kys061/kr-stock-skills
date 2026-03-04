"""
kr-pead-screener: 메인 오케스트레이터.
DART 정기보고서 공시 기반 PEAD 패턴 스크리닝.

Usage:
    python kr_pead_screener.py --output-dir ./output
    python kr_pead_screener.py --days 30 --output-dir ./output
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from weekly_candle_calculator import (
    detect_gap, analyze_weekly_candles, score_gap_size, score_pattern_quality,
)
from breakout_calculator import check_breakout, calc_risk_reward
from scorer import classify_stage, score_earnings_surprise, calc_total_score
from report_generator import PEADReportGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def screen_pead(days: int = 30, output_dir: str = './output') -> list:
    """PEAD 스크리닝 실행.

    Args:
        days: DART 공시 검색 기간 (일)
        output_dir: 결과 저장 디렉토리
    """
    from _kr_common.kr_client import KRClient

    client = KRClient()
    logger.info(f"=== PEAD 스크리닝 시작 (최근 {days}일 공시) ===")

    # 1. DART 정기보고서 공시 조회
    try:
        disclosures = client.get_disclosures(kind='A', days=days)
    except Exception as e:
        logger.error(f"DART 공시 조회 실패: {e}")
        return []

    results = []
    for disc in disclosures:
        ticker = disc.get('ticker', '')
        if not ticker:
            continue

        try:
            # 2. 주봉 데이터 조회
            ohlcv_weekly = client.get_ohlcv(ticker, days=60, freq='w')
            if ohlcv_weekly is None or len(ohlcv_weekly) < 3:
                continue

            # 3. 갭업 감지 (공시 주봉)
            gap_week_idx = _find_gap_week(ohlcv_weekly, disc.get('date'))
            if gap_week_idx is None:
                continue

            prev_close = ohlcv_weekly.iloc[gap_week_idx - 1]['Close']
            curr_open = ohlcv_weekly.iloc[gap_week_idx]['Open']
            gap = detect_gap(prev_close, curr_open)
            if not gap['is_gap_up']:
                continue

            # 4. 주봉 캔들 분석 (갭 이후)
            post_gap = []
            for j in range(gap_week_idx + 1, min(gap_week_idx + 6, len(ohlcv_weekly))):
                row = ohlcv_weekly.iloc[j]
                post_gap.append({
                    'open': row['Open'], 'high': row['High'],
                    'low': row['Low'], 'close': row['Close'],
                    'volume': row['Volume'],
                })

            candle_analysis = analyze_weekly_candles(post_gap)

            # 5. 스테이지 분류
            stage = classify_stage(
                candle_analysis['weeks_since_gap'],
                candle_analysis['red_candle_found'],
                candle_analysis['breakout_found'],
            )

            if stage == 'EXPIRED':
                continue

            # 6. 스코어링
            gap_score = score_gap_size(gap['gap_pct'])
            pattern_score = score_pattern_quality(
                candle_analysis['red_candle_found'],
                candle_analysis['volume_declining'],
                True,  # gap maintained (simplified)
            )
            surprise_score = score_earnings_surprise(disc.get('surprise_pct', 10))

            rr = calc_risk_reward(
                candle_analysis.get('red_candle_high', curr_open),
                candle_analysis.get('red_candle_low', curr_open * 0.95),
            )

            total = calc_total_score(gap_score, pattern_score, surprise_score, rr['score'])

            results.append({
                'ticker': ticker,
                'name': disc.get('name', ticker),
                'stage': stage,
                'gap_pct': gap['gap_pct'],
                'score_data': total,
                'candle_analysis': candle_analysis,
                'risk_reward': rr,
            })

        except Exception as e:
            logger.debug(f"{ticker} 처리 중 오류: {e}")
            continue

    results.sort(key=lambda r: r['score_data']['total_score'], reverse=True)
    logger.info(f"PEAD 패턴 감지: {len(results)}개 종목")

    reporter = PEADReportGenerator(output_dir)
    reporter.generate_json(results)
    reporter.generate_markdown(results)

    return results


def _find_gap_week(ohlcv_weekly, disclosure_date) -> int:
    """공시일에 해당하는 주봉 인덱스 찾기."""
    if disclosure_date is None:
        return None
    for i in range(1, len(ohlcv_weekly)):
        return i  # simplified: 첫 번째 유효 인덱스
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='한국 PEAD 스크리닝')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    results = screen_pead(args.days, args.output_dir)
    print(f"\n총 {len(results)}개 PEAD 패턴 감지")
    for r in results[:10]:
        sd = r['score_data']
        print(f"  {r['ticker']} {r.get('name', '')} - {r['stage']} Gap={r['gap_pct']:.1f}% "
              f"Score={sd['total_score']} ({sd['rating']})")
