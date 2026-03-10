"""kr-stock-selector: 주식종목선별 오케스트레이터.

5가지 트렌드 조건으로 KOSPI/KOSDAQ 종목을 자동 선별한다.

Usage:
    python kr_stock_selector.py [--market KOSPI|KOSDAQ] [--date 2026-03-11]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from universe_builder import load_config, build_universe, fetch_ohlcv_batch
from trend_analyzer import analyze_stock
from report_generator import generate_report, save_report

logger = logging.getLogger(__name__)


def run(
    market: str = None,
    date: str = None,
    output_dir: str = None,
) -> dict:
    """주식종목선별 실행.

    Args:
        market: 'KOSPI', 'KOSDAQ', None(전체)
        date: 기준일 (기본: 오늘)
        output_dir: 리포트 저장 디렉토리 (기본: reports/)

    Returns:
        {
            'success': bool,
            'report_path': str,
            'universe_size': int,
            'passed_count': int,
            'watch_count': int,
            'pass_rate': float,
            'passed_stocks': list[dict],
            'errors': list[str],
        }
    """
    errors = []
    config = load_config()
    conditions_cfg = config.get('conditions', {})

    # Step 1: KRX API 프로바이더 생성 (없으면 폴백)
    provider = _create_provider()

    # Step 2: 유니버스 구축
    try:
        universe = build_universe(
            provider=provider,
            date=date,
            market=market,
        )
    except Exception as e:
        return {
            'success': False,
            'report_path': '',
            'universe_size': 0,
            'passed_count': 0,
            'watch_count': 0,
            'pass_rate': 0.0,
            'passed_stocks': [],
            'errors': [f"유니버스 구축 실패: {e}"],
        }

    if not universe:
        return {
            'success': False,
            'report_path': '',
            'universe_size': 0,
            'passed_count': 0,
            'watch_count': 0,
            'pass_rate': 0.0,
            'passed_stocks': [],
            'errors': ['유니버스가 비어있습니다 (종목 0개)'],
        }

    universe_size = len(universe)
    logger.info(f"유니버스: {universe_size}개 종목")

    # Step 3: OHLCV 배치 다운로드
    try:
        ohlcv_dict = fetch_ohlcv_batch(universe)
    except Exception as e:
        errors.append(f"OHLCV 배치 다운로드 실패: {e}")
        ohlcv_dict = {}

    if not ohlcv_dict:
        return {
            'success': False,
            'report_path': '',
            'universe_size': universe_size,
            'passed_count': 0,
            'watch_count': 0,
            'pass_rate': 0.0,
            'passed_stocks': [],
            'errors': errors or ['OHLCV 데이터 수집 실패'],
        }

    # Step 4: 5조건 판정
    results = []
    for stock in universe:
        ticker = stock['ticker']
        df = ohlcv_dict.get(ticker)

        if df is None or df.empty:
            errors.append(f"{ticker} ({stock['name']}): OHLCV 데이터 없음")
            continue

        try:
            result = analyze_stock(
                df=df,
                ticker=ticker,
                name=stock['name'],
                market=stock['market'],
                market_cap=stock['market_cap'],
                config=conditions_cfg,
            )
            results.append(result)
        except Exception as e:
            errors.append(f"{ticker} ({stock['name']}): {e}")
            continue  # fail-safe

    # Step 5: 리포트 생성
    passed = [r for r in results if r.get('all_pass')]
    watch = [r for r in results if r.get('pass_count', 0) == 4]
    market_filter = market or "ALL"

    try:
        report_content = generate_report(
            results=results,
            universe_size=universe_size,
            date=date,
            market_filter=market_filter,
        )
        report_path = save_report(
            content=report_content,
            date=date,
            output_dir=output_dir,
        )
    except Exception as e:
        errors.append(f"리포트 생성 실패: {e}")
        report_path = ''

    pass_rate = len(passed) / universe_size * 100 if universe_size > 0 else 0.0

    return {
        'success': True,
        'report_path': report_path,
        'universe_size': universe_size,
        'passed_count': len(passed),
        'watch_count': len(watch),
        'pass_rate': pass_rate,
        'passed_stocks': [
            {'ticker': r['ticker'], 'name': r['name'], 'market': r['market']}
            for r in passed
        ],
        'errors': errors,
    }


def _create_provider():
    """KRX Open API 프로바이더 생성."""
    api_key = os.environ.get('KRX_API_KEY', '')
    if not api_key:
        logger.info("KRX_API_KEY 미설정 → yfinance 폴백 사용")
        return None

    try:
        common_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '_kr_common', 'providers'
        )
        sys.path.insert(0, common_path)
        from krx_openapi_provider import KRXOpenAPIProvider
        return KRXOpenAPIProvider(api_key)
    except Exception as e:
        logger.warning(f"KRX 프로바이더 생성 실패: {e}")
        return None


def main():
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description='주식종목선별 스크리너')
    parser.add_argument('--market', choices=['KOSPI', 'KOSDAQ'],
                        help='시장 필터 (기본: 전체)')
    parser.add_argument('--date', help='기준일 (YYYY-MM-DD)')
    parser.add_argument('--output-dir', help='리포트 저장 디렉토리')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    result = run(
        market=args.market,
        date=args.date,
        output_dir=args.output_dir,
    )

    if result['success']:
        print(f"\n=== 주식종목선별 완료 ===")
        print(f"유니버스: {result['universe_size']}개")
        print(f"통과 종목: {result['passed_count']}개 ({result['pass_rate']:.1f}%)")
        print(f"Watch List: {result['watch_count']}개")
        if result['report_path']:
            print(f"리포트: {result['report_path']}")
        if result['errors']:
            print(f"경고: {len(result['errors'])}개 종목 스킵")
    else:
        print(f"\n=== 실행 실패 ===")
        for e in result['errors']:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
