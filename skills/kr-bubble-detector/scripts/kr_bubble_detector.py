"""
kr-bubble-detector: 한국 시장 버블 탐지기 메인 오케스트레이터.
Minsky/Kindleberger v2.1 프레임워크 한국 적용.

Usage:
    python kr_bubble_detector.py --output-dir ./output
    python kr_bubble_detector.py --output-dir ./output --breadth-json ../kr-market-breadth/output/latest.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

from bubble_scorer import (
    BubbleScorer,
    score_vkospi_market,
    score_credit_balance,
    score_ipo_heat,
    score_breadth_anomaly,
    score_price_acceleration,
    score_per_band,
)
from report_generator import ReportGenerator


def _load_breadth_json(path: str) -> dict:
    """kr-market-breadth JSON 로드."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _parse_qualitative(qual_str: str) -> dict:
    """정성 조정 JSON 문자열 파싱."""
    if not qual_str:
        return {}
    try:
        return json.loads(qual_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def collect_data(breadth_json: str = None) -> dict:
    """데이터 수집 (KRClient + WebSearch).

    실제 운영 시:
    - KRClient로 KOSPI, VKOSPI, PER 데이터 자동 수집
    - WebSearch로 신용잔고, IPO 데이터 보충
    - breadth_json으로 kr-market-breadth 결과 참조

    현재는 데이터 수집 인터페이스만 정의.
    """
    data = {
        'vkospi': None,
        'kospi_52w_high': None,
        'kospi_close': None,
        'kospi_per': None,
        'credit_yoy': None,
        'credit_is_ath': None,
        'ipo_quarterly_count': None,
        'ipo_avg_5y': None,
        'ipo_competition': None,
        'kospi_return_3m': None,
        'kospi_return_percentile': None,
        'breadth_200ma': None,
        'is_new_high': None,
    }

    # kr-market-breadth JSON 크로스레퍼런스
    if breadth_json:
        breadth_data = _load_breadth_json(breadth_json)
        if breadth_data:
            raw = breadth_data.get('components', {}).get('breadth_level', {})
            if raw.get('raw') is not None:
                data['breadth_200ma'] = raw['raw'] / 100.0  # % → ratio

    return data


def build_indicators(data: dict) -> dict:
    """수집된 데이터를 지표 인수로 변환."""
    indicators = {}

    # 지표 1: VKOSPI + 시장 위치
    if data.get('vkospi') is not None and data.get('kospi_close') is not None:
        high = data.get('kospi_52w_high', data['kospi_close'])
        pct = (data['kospi_close'] - high) / high if high > 0 else 0
        indicators['vkospi_market'] = {
            'vkospi': data['vkospi'],
            'pct_from_high': pct,
        }

    # 지표 2: 신용잔고
    if data.get('credit_yoy') is not None:
        indicators['credit_balance'] = {
            'credit_yoy': data['credit_yoy'],
            'is_ath': data.get('credit_is_ath', False),
        }

    # 지표 3: IPO 과열도
    if data.get('ipo_quarterly_count') is not None:
        indicators['ipo_heat'] = {
            'quarterly_ipo_count': data['ipo_quarterly_count'],
            'avg_5y': data.get('ipo_avg_5y', 18.0),
            'avg_competition': data.get('ipo_competition', 100.0),
        }

    # 지표 4: 시장폭 이상
    if data.get('breadth_200ma') is not None:
        indicators['breadth_anomaly'] = {
            'is_new_high': data.get('is_new_high', False),
            'breadth_200ma': data['breadth_200ma'],
        }

    # 지표 5: 가격 가속화
    if data.get('kospi_return_3m') is not None:
        indicators['price_acceleration'] = {
            'return_3m': data['kospi_return_3m'],
            'percentile': data.get('kospi_return_percentile', 0.5),
        }

    # 지표 6: KOSPI PER 밴드
    if data.get('kospi_per') is not None:
        indicators['per_band'] = {
            'kospi_per': data['kospi_per'],
        }

    return indicators


def analyze(output_dir: str = './output', breadth_json: str = None,
            qualitative: dict = None) -> dict:
    """버블 탐지 메인 분석 함수.

    Args:
        output_dir: 리포트 출력 디렉토리
        breadth_json: kr-market-breadth JSON 경로 (선택)
        qualitative: 정성 조정 dict (선택)
    Returns:
        분석 결과 dict
    """
    scorer = BubbleScorer()
    reporter = ReportGenerator(output_dir)

    # 1. 데이터 수집
    data = collect_data(breadth_json)

    # 2. 지표 인수 구축
    indicators = build_indicators(data)

    # 3. 정량 스코어링
    quant = scorer.score_quantitative(indicators)

    # 4. 정성 스코어링
    qual = scorer.score_qualitative(qualitative or {})

    # 5. 최종 점수
    final = scorer.calculate_final(quant, qual)

    # 6. 결과 조합
    result = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'quantitative': quant,
        'qualitative': qual,
        'final': final,
    }

    # 7. 리포트 생성
    report = reporter.generate(result)

    return {**result, **report}


def main():
    parser = argparse.ArgumentParser(description='kr-bubble-detector: 한국 시장 버블 탐지기')
    parser.add_argument('--output-dir', default='./output', help='리포트 출력 디렉토리')
    parser.add_argument('--breadth-json', default=None,
                        help='kr-market-breadth JSON 경로 (선택)')
    parser.add_argument('--qualitative', default=None,
                        help='정성 조정 JSON 문자열 (선택)')
    args = parser.parse_args()

    qualitative = _parse_qualitative(args.qualitative)
    result = analyze(
        output_dir=args.output_dir,
        breadth_json=args.breadth_json,
        qualitative=qualitative,
    )

    zone = result.get('final', {}).get('risk_zone', {})
    print(f"[kr-bubble-detector] 최종 점수: {result['final']['final_score']}/15")
    print(f"[kr-bubble-detector] 리스크 존: {zone.get('name')} ({zone.get('label')})")
    print(f"[kr-bubble-detector] 리스크 예산: {zone.get('budget')}")


if __name__ == '__main__':
    main()
