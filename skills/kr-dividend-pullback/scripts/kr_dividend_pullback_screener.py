"""
kr-dividend-pullback: 메인 오케스트레이터.
고성장 배당주 (CAGR ≥ 8%) + RSI ≤ 40 타이밍.

Usage:
    python kr_dividend_pullback_screener.py --market ALL --output-dir ./output
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from growth_filter import filter_growth, filter_rsi, calc_dividend_cagr
from scorer import (
    calc_dividend_growth_score,
    calc_financial_quality_score,
    calc_technical_setup_score,
    calc_valuation_score,
    calc_total_score,
)
from report_generator import PullbackReportGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def screen_dividend_pullback(market: str = 'ALL', output_dir: str = './output') -> list:
    """배당 성장 풀백 스크리닝."""
    from _kr_common.kr_client import KRClient
    from _kr_common.ta_utils import rsi

    client = KRClient()
    logger.info(f"=== 배당 성장 풀백 스크리닝 시작 (시장: {market}) ===")

    fundamentals = client.get_fundamentals(market=market)
    market_cap_df = client.get_market_cap(market=market)

    results = []
    for ticker in fundamentals.index:
        try:
            row = fundamentals.loc[ticker]
            cap_row = market_cap_df.loc[ticker] if ticker in market_cap_df.index else None

            # 배당/재무 데이터 수집
            stock = _build_stock_data(client, ticker, row, cap_row)
            if not stock:
                continue

            # Phase 1: 배당 성장 필터
            if not filter_growth(stock):
                continue

            # Phase 2: RSI 타이밍
            ohlcv = client.get_ohlcv(ticker, days=60)
            rsi_val = rsi(ohlcv['Close'])
            if rsi_val is None or not filter_rsi(rsi_val):
                continue

            # 4-컴포넌트 스코어링
            dg = calc_dividend_growth_score(stock['dividend_cagr'], stock.get('consecutive_years', 0))
            fq = calc_financial_quality_score(stock.get('roe', 0), stock.get('opm', 0), stock.get('de_ratio', 100))
            ts = calc_technical_setup_score(rsi_val)
            val = calc_valuation_score(stock.get('per', 15), stock.get('pbr', 1.0))
            total = calc_total_score(dg['score'], fq['score'], ts['score'], val['score'])

            results.append({
                'ticker': ticker,
                'name': stock.get('name', ticker),
                'rsi': rsi_val,
                'cagr': stock['dividend_cagr'],
                'score_data': total,
            })

        except Exception as e:
            logger.debug(f"{ticker} 처리 중 오류: {e}")
            continue

    results.sort(key=lambda r: r['score_data']['total_score'], reverse=True)
    logger.info(f"스크리닝 통과: {len(results)}개 종목")

    reporter = PullbackReportGenerator(output_dir)
    reporter.generate_json(results, {'market': market})
    reporter.generate_markdown(results, {'market': market})

    return results


def _build_stock_data(client, ticker, row, cap_row) -> dict:
    """종목 데이터 구성."""
    from datetime import datetime
    current_year = datetime.now().year

    try:
        dividends = []
        for y in range(current_year - 4, current_year):
            info = client.get_dividend_info(ticker, y)
            dividends.append(info.get('DPS', 0) or 0)

        ratios = client.get_financial_ratios(ticker, current_year - 1)

        # 매출/EPS 3년 추세
        revenues, eps_list = [], []
        for y in range(current_year - 3, current_year):
            fs = client.get_financial_statements(ticker, y, 'annual')
            revenues.append(fs.get('revenue', 0) or 0)
            eps_list.append(fs.get('eps', 0) or 0)

        return {
            'ticker': ticker,
            'name': ticker,
            'div_yield': float(row.get('DIV', 0) or 0),
            'per': float(row.get('PER', 0) or 0),
            'pbr': float(row.get('PBR', 0) or 0),
            'market_cap': float(cap_row.get('시가총액', 0)) if cap_row is not None else 0,
            'dividend_history': dividends,
            'dividend_cagr': calc_dividend_cagr(dividends),
            'consecutive_years': _count_consecutive(dividends),
            'revenue_trend_positive': len(revenues) >= 3 and revenues[-1] > revenues[0],
            'eps_trend_positive': len(eps_list) >= 3 and eps_list[-1] > eps_list[0],
            'de_ratio': ratios.get('DE_ratio', 100),
            'current_ratio': ratios.get('current_ratio', 1.0),
            'payout_ratio': ratios.get('payout_ratio', 50),
            'roe': ratios.get('ROE', 0),
            'opm': ratios.get('OPM', 0),
        }
    except Exception:
        return None


def _count_consecutive(dividends: list) -> int:
    """연속 배당 증가 년수."""
    count = 0
    for i in range(len(dividends) - 1, 0, -1):
        if dividends[i] >= dividends[i - 1] and dividends[i - 1] > 0:
            count += 1
        else:
            break
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='한국 배당 성장 풀백 스크리닝')
    parser.add_argument('--market', default='ALL', choices=['KOSPI', 'KOSDAQ', 'ALL'])
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    results = screen_dividend_pullback(args.market, args.output_dir)
    print(f"\n총 {len(results)}개 종목 스크리닝 통과")
    for r in results[:10]:
        sd = r['score_data']
        print(f"  {r['ticker']} RSI={r['rsi']:.1f} CAGR={r['cagr']:.1f}% - {sd['total_score']}점 ({sd['rating']})")
