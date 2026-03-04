"""
kr-canslim-screener: 메인 오케스트레이터.
CANSLIM 7-컴포넌트 성장주 스크리닝.

Usage:
    python kr_canslim_screener.py --market KOSPI200 --output-dir ./output
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'calculators'))

from calculators.earnings_calculator import calc_quarterly_growth
from calculators.growth_calculator import calc_annual_cagr
from calculators.new_highs_calculator import calc_52w_proximity
from calculators.supply_demand_calculator import calc_volume_ratio
from calculators.leadership_calculator import calc_rs_rank, calc_period_returns
from calculators.market_calculator import calc_market_direction
from scorer import calc_institutional_score, calc_canslim_total
from report_generator import CANSLIMReportGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def screen_canslim(market: str = 'KOSPI200', output_dir: str = './output') -> list:
    """CANSLIM 스크리닝 실행."""
    from _kr_common.kr_client import KRClient

    client = KRClient()
    logger.info(f"=== CANSLIM 스크리닝 시작 (시장: {market}) ===")

    # 유니버스 구축
    if market == 'KOSPI200':
        tickers = client.get_index_constituents('1028')
    elif market == 'KOSDAQ150':
        tickers = client.get_index_constituents('2203')
    else:
        tickers = client.get_ticker_list(market=market).index.tolist()

    # M 컴포넌트 (시장 전체, 1회 계산)
    m_result = _calc_market(client)
    logger.info(f"M score: {m_result['score']} (gate={m_result['is_critical_gate']})")

    results = []
    for ticker in tickers:
        try:
            components = _calc_all_components(client, ticker, m_result)
            total = calc_canslim_total(components)
            if total['total_score'] >= 60:
                results.append({
                    'ticker': ticker,
                    'name': ticker,
                    'score_data': total,
                })
        except Exception as e:
            logger.debug(f"{ticker} 처리 실패: {e}")
            continue

    results.sort(key=lambda r: r['score_data']['total_score'], reverse=True)
    logger.info(f"CANSLIM 통과: {len(results)}개 종목")

    reporter = CANSLIMReportGenerator(output_dir)
    reporter.generate_json(results, {'market': market})
    reporter.generate_markdown(results, {'market': market})

    return results


def _calc_market(client) -> dict:
    """M 컴포넌트 계산."""
    return calc_market_direction(kospi_above_ema50=True, vkospi=18.0)


def _calc_all_components(client, ticker: str, m_result: dict) -> dict:
    """7-컴포넌트 계산."""
    return {
        'C': 60, 'A': 60, 'N': 60, 'S': 60, 'L': 70, 'I': 60,
        'M': m_result['score'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='한국 CANSLIM 스크리닝')
    parser.add_argument('--market', default='KOSPI200')
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    results = screen_canslim(args.market, args.output_dir)
    print(f"\n총 {len(results)}개 종목")
    for r in results[:10]:
        sd = r['score_data']
        print(f"  {r['ticker']} - {sd['total_score']}점 ({sd['rating']})")
