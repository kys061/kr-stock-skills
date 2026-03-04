"""
kr-value-dividend: 메인 오케스트레이터.
3-Phase 필터 + 4-컴포넌트 스코어링으로 배당 가치주 발굴.

Usage:
    python kr_value_dividend_screener.py --market ALL --output-dir ./output
    python kr_value_dividend_screener.py --market KOSPI --min-yield 3.0 --output-dir ./output
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fundamental_filter import filter_all_phases
from scorer import (
    calc_value_score,
    calc_growth_score,
    calc_sustainability_score,
    calc_quality_score,
    calc_total_score,
)
from report_generator import ValueDividendReportGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def screen_value_dividend(market: str = 'ALL',
                          min_yield: float = 2.5,
                          output_dir: str = './output') -> list:
    """배당 가치주 스크리닝 실행.

    Args:
        market: KOSPI, KOSDAQ, or ALL
        min_yield: 최소 배당수익률 오버라이드
        output_dir: 결과 저장 디렉토리
    Returns:
        스크리닝 결과 리스트
    """
    from _kr_common.kr_client import KRClient

    client = KRClient()
    logger.info(f"=== 배당 가치주 스크리닝 시작 (시장: {market}) ===")

    # 1. 전종목 펀더멘털 데이터
    fundamentals = client.get_fundamentals(market=market)
    market_cap_df = client.get_market_cap(market=market)
    logger.info(f"전체 종목 수: {len(fundamentals)}")

    results = []
    for ticker in fundamentals.index:
        try:
            row = fundamentals.loc[ticker]
            cap_row = market_cap_df.loc[ticker] if ticker in market_cap_df.index else None

            # Phase 1 데이터 구성
            stock = {
                'ticker': ticker,
                'div_yield': float(row.get('DIV', 0) or 0),
                'per': float(row.get('PER', 0) or 0),
                'pbr': float(row.get('PBR', 0) or 0),
                'market_cap': float(cap_row.get('시가총액', 0)) if cap_row is not None else 0,
            }

            # Phase 1 필터 (빠른 필터링)
            from fundamental_filter import filter_phase1
            if not filter_phase1(stock):
                continue

            # Phase 2/3: 재무제표 추가 로드 (DART)
            try:
                div_info = _get_dividend_history(client, ticker)
                fin_data = _get_financial_data(client, ticker)
                stock.update(div_info)
                stock.update(fin_data)
            except Exception as e:
                logger.debug(f"{ticker} 재무 데이터 로드 실패: {e}")
                continue

            # 3-Phase 필터
            filter_result = filter_all_phases(stock)
            if not filter_result['passed']:
                continue

            # 4-컴포넌트 스코어링
            value = calc_value_score(stock['per'], stock['pbr'])
            growth = calc_growth_score(
                stock.get('dividend_cagr', 0),
                stock.get('revenue_trend_positive', False),
                stock.get('eps_trend_positive', False),
            )
            sustainability = calc_sustainability_score(
                stock.get('payout_ratio', 50),
                stock.get('de_ratio', 100),
            )
            quality = calc_quality_score(
                stock.get('roe', 0),
                stock.get('opm', 0),
            )
            total = calc_total_score(
                value['score'], growth['score'],
                sustainability['score'], quality['score'],
            )

            results.append({
                'ticker': ticker,
                'name': stock.get('name', ticker),
                'score_data': total,
                'filter_data': filter_result,
                'details': {
                    'value': value,
                    'growth': growth,
                    'sustainability': sustainability,
                    'quality': quality,
                },
            })

        except Exception as e:
            logger.debug(f"{ticker} 처리 중 오류: {e}")
            continue

    # 점수 기준 정렬
    results.sort(key=lambda r: r['score_data']['total_score'], reverse=True)
    logger.info(f"스크리닝 통과: {len(results)}개 종목")

    # 리포트 생성
    reporter = ValueDividendReportGenerator(output_dir)
    reporter.generate_json(results, {'market': market})
    reporter.generate_markdown(results, {'market': market})
    logger.info(f"리포트 저장: {output_dir}")

    return results


def _get_dividend_history(client, ticker: str) -> dict:
    """3년 배당 이력 조회."""
    from datetime import datetime
    current_year = datetime.now().year
    dividends = []
    for y in range(current_year - 3, current_year):
        try:
            info = client.get_dividend_info(ticker, y)
            dividends.append(info.get('DPS', 0) or 0)
        except Exception:
            dividends.append(0)

    cagr = 0
    if len(dividends) >= 3 and dividends[0] > 0 and dividends[-1] > 0:
        cagr = ((dividends[-1] / dividends[0]) ** (1 / (len(dividends) - 1)) - 1) * 100

    return {
        'dividend_history': dividends,
        'dividend_cagr': cagr,
    }


def _get_financial_data(client, ticker: str) -> dict:
    """재무 데이터 조회."""
    from datetime import datetime
    current_year = datetime.now().year

    revenues = []
    eps_list = []
    for y in range(current_year - 3, current_year):
        try:
            fs = client.get_financial_statements(ticker, y, 'annual')
            revenues.append(fs.get('revenue', 0) or 0)
            eps_list.append(fs.get('eps', 0) or 0)
        except Exception:
            pass

    ratios = {}
    try:
        ratios = client.get_financial_ratios(ticker, current_year - 1)
    except Exception:
        pass

    return {
        'revenue_history': revenues,
        'eps_history': eps_list,
        'revenue_trend_positive': len(revenues) >= 3 and revenues[-1] > revenues[0],
        'eps_trend_positive': len(eps_list) >= 3 and eps_list[-1] > eps_list[0],
        'payout_ratio': ratios.get('payout_ratio', 50),
        'de_ratio': ratios.get('DE_ratio', 100),
        'current_ratio': ratios.get('current_ratio', 1.0),
        'roe': ratios.get('ROE', 0),
        'opm': ratios.get('OPM', 0),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='한국 배당 가치주 스크리닝')
    parser.add_argument('--market', default='ALL', choices=['KOSPI', 'KOSDAQ', 'ALL'])
    parser.add_argument('--min-yield', type=float, default=2.5)
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    results = screen_value_dividend(args.market, args.min_yield, args.output_dir)
    print(f"\n총 {len(results)}개 종목 스크리닝 통과")
    for r in results[:10]:
        sd = r['score_data']
        print(f"  {r['ticker']} {r.get('name', '')} - {sd['total_score']}점 ({sd['rating']})")
