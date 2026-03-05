"""한국 시장 환경 분석 유틸리티.

한국 시장 핵심 지표를 KRClient에서 수집하여 JSON 스냅샷으로 반환.

Usage:
    python3 market_utils.py [--output-dir reports/]
"""

import sys
import os
import json
import argparse
from datetime import datetime

# KRClient import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from _kr_common.kr_client import KRClient
from _kr_common.models.market import INDEX_CODES
from _kr_common.utils import date_utils, ta_utils
import pandas as pd


def get_kr_market_snapshot(client: KRClient = None) -> dict:
    """한국 시장 핵심 지표 스냅샷.

    Returns:
        {
            'date': str,
            'kospi': {'close': float, 'change_pct': float, 'per': float, 'pbr': float},
            'kosdaq': {'close': float, 'change_pct': float, 'per': float, 'pbr': float},
            'usdkrw': float,
            'bond_yields': {'3Y': float, '5Y': float, '10Y': float},
            'investor_flow': {
                'foreign_today': float, 'foreign_5d': float,
                'institutional_today': float, 'institutional_5d': float
            },
            'vkospi': float,
        }
    """
    if client is None:
        client = KRClient()

    today = date_utils.today()
    recent = date_utils.get_recent_trading_day()
    five_days_ago = date_utils.get_n_days_ago(7)  # 영업일 5일 ≈ 달력 7일

    result = {'date': recent}

    # KOSPI / KOSDAQ 지수
    for name, code in [('kospi', INDEX_CODES['KOSPI']), ('kosdaq', INDEX_CODES['KOSDAQ'])]:
        try:
            idx_df = client.get_index(code, recent, recent)
            fund_df = client.get_index_fundamentals(code, recent, recent)

            idx_data = {'close': 0.0, 'change_pct': 0.0, 'per': 0.0, 'pbr': 0.0}
            if not idx_df.empty:
                row = idx_df.iloc[-1]
                idx_data['close'] = float(row.get('종가', row.get('Close', 0)))
                idx_data['change_pct'] = float(row.get('등락률', row.get('Change', 0)))
            if not fund_df.empty:
                frow = fund_df.iloc[-1]
                idx_data['per'] = float(frow.get('PER', 0))
                idx_data['pbr'] = float(frow.get('PBR', 0))

            result[name] = idx_data
        except Exception as e:
            result[name] = {'close': 0.0, 'change_pct': 0.0, 'per': 0.0, 'pbr': 0.0, 'error': str(e)}

    # 원달러 환율
    try:
        fx_df = client.get_global_index('USD/KRW', five_days_ago, today)
        if not fx_df.empty:
            result['usdkrw'] = float(fx_df.iloc[-1].get('Close', fx_df.iloc[-1].get('종가', 0)))
        else:
            result['usdkrw'] = 0.0
    except Exception:
        result['usdkrw'] = 0.0

    # 국고채 수익률
    try:
        bond_df = client.get_bond_yields(recent)
        bonds = {}
        if not bond_df.empty:
            for _, row in bond_df.iterrows():
                name_col = row.get('채권종류', row.index[0] if hasattr(row, 'index') else '')
                if '3년' in str(name_col) or '3Y' in str(name_col):
                    bonds['3Y'] = float(row.get('수익률', 0))
                elif '5년' in str(name_col) or '5Y' in str(name_col):
                    bonds['5Y'] = float(row.get('수익률', 0))
                elif '10년' in str(name_col) or '10Y' in str(name_col):
                    bonds['10Y'] = float(row.get('수익률', 0))
        result['bond_yields'] = bonds
    except Exception:
        result['bond_yields'] = {}

    # 수급 동향 (외국인/기관)
    try:
        inv_df = client.get_investor_trading_market(five_days_ago, recent, 'KOSPI')
        flow = {
            'foreign_today': 0.0, 'foreign_5d': 0.0,
            'institutional_today': 0.0, 'institutional_5d': 0.0
        }
        if not inv_df.empty:
            foreign_col = None
            inst_col = None
            for col in inv_df.columns:
                if '외국인' in str(col):
                    foreign_col = col
                if '기관' in str(col):
                    inst_col = col

            if foreign_col:
                flow['foreign_today'] = float(inv_df[foreign_col].iloc[-1])
                flow['foreign_5d'] = float(inv_df[foreign_col].sum())
            if inst_col:
                flow['institutional_today'] = float(inv_df[inst_col].iloc[-1])
                flow['institutional_5d'] = float(inv_df[inst_col].sum())

        result['investor_flow'] = flow
    except Exception:
        result['investor_flow'] = {
            'foreign_today': 0.0, 'foreign_5d': 0.0,
            'institutional_today': 0.0, 'institutional_5d': 0.0
        }

    # VKOSPI (지수코드 0060)
    try:
        vkospi_df = client.get_index('0060', recent, recent)
        if not vkospi_df.empty:
            result['vkospi'] = float(vkospi_df.iloc[-1].get('종가', vkospi_df.iloc[-1].get('Close', 0)))
        else:
            result['vkospi'] = 0.0
    except Exception:
        result['vkospi'] = 0.0

    return result


def get_per_band_position(client: KRClient = None, index_code: str = '0001',
                          years: int = 10) -> dict:
    """KOSPI PER 밴드 내 현재 위치 계산.

    Returns:
        {
            'current_per': float,
            'percentile': float,      # 0~100
            'zone': str,              # '저평가' / '적정' / '고평가' / '과열'
            'min_per': float,
            'max_per': float,
            'avg_per': float,
        }
    """
    if client is None:
        client = KRClient()

    today = date_utils.today()
    start = f"{int(today[:4]) - years}-01-01"

    try:
        fund_df = client.get_index_fundamentals(index_code, start, today)
        if fund_df.empty:
            return {}

        per_col = 'PER' if 'PER' in fund_df.columns else fund_df.columns[0]
        per_series = fund_df[per_col].dropna()
        per_series = per_series[per_series > 0]

        if per_series.empty:
            return {}

        current = float(per_series.iloc[-1])
        min_per = float(per_series.min())
        max_per = float(per_series.max())
        avg_per = float(per_series.mean())

        # 백분위 계산
        rank = (per_series < current).sum()
        percentile = round(rank / len(per_series) * 100, 1)

        # 존 판정
        if percentile <= 25:
            zone = '저평가'
        elif percentile <= 50:
            zone = '적정 (하단)'
        elif percentile <= 75:
            zone = '적정 (상단)'
        elif percentile <= 90:
            zone = '고평가'
        else:
            zone = '과열'

        return {
            'current_per': round(current, 2),
            'percentile': percentile,
            'zone': zone,
            'min_per': round(min_per, 2),
            'max_per': round(max_per, 2),
            'avg_per': round(avg_per, 2),
        }
    except Exception as e:
        return {'error': str(e)}


def categorize_vkospi(value: float) -> str:
    """VKOSPI 레벨 분류."""
    if value < 10:
        return '매우 낮음'
    elif value < 15:
        return '낮음'
    elif value < 20:
        return '보통'
    elif value < 25:
        return '높음'
    elif value < 30:
        return '매우 높음'
    else:
        return '극단적'


def format_investor_flow(flow: dict) -> str:
    """수급 동향 포맷팅 (억원 단위)."""
    def fmt(val):
        billions = val / 1e8  # 원 → 억원
        sign = '+' if billions > 0 else ''
        return f"{sign}{billions:,.0f}억"

    lines = []
    lines.append(f"외국인: 오늘 {fmt(flow.get('foreign_today', 0))}, "
                 f"5일 {fmt(flow.get('foreign_5d', 0))}")
    lines.append(f"기관:   오늘 {fmt(flow.get('institutional_today', 0))}, "
                 f"5일 {fmt(flow.get('institutional_5d', 0))}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='한국 시장 환경 스냅샷')
    parser.add_argument('--output-dir', default='reports/', help='출력 디렉토리')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("한국 시장 데이터 수집 중...")
    client = KRClient()

    snapshot = get_kr_market_snapshot(client)
    per_band = get_per_band_position(client)
    snapshot['per_band'] = per_band

    if snapshot.get('vkospi'):
        snapshot['vkospi_level'] = categorize_vkospi(snapshot['vkospi'])

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filepath = os.path.join(args.output_dir, f'kr_market_snapshot_{timestamp}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)

    print(f"스냅샷 저장: {filepath}")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))

    return snapshot


def estimate_foreign_flow_outlook(us_regime_score=None, kr_us_rate_diff=None,
                                  usdkrw_trend=None):
    """US 통화정책 기반 외국인 수급 전망 추정.

    Optional. us-monetary-regime 결과가 있을 때만 활용.
    입력이 모두 None이면 빈 dict 반환 (기존 호환).

    Args:
        us_regime_score: float or None, US 레짐 점수 (0~100).
        kr_us_rate_diff: float or None, 한미 금리차 (%p, KR-US).
        usdkrw_trend: str or None, 원달러 추세
            ('strengthening'/'stable'/'weakening').

    Returns:
        dict or {}: 외국인 수급 전망.
    """
    if us_regime_score is None:
        return {}

    # 기본 전망: US regime score 기반
    if us_regime_score >= 65:
        base_outlook = 'net_inflow'
        base_confidence = min(1.0, (us_regime_score - 50) / 50)
        reasoning = 'US 완화 환경 → 글로벌 유동성 확대 → EM 자금 유입 기대'
    elif us_regime_score <= 35:
        base_outlook = 'net_outflow'
        base_confidence = min(1.0, (50 - us_regime_score) / 50)
        reasoning = 'US 긴축 환경 → 달러 강세 → EM 자금 이탈 압력'
    else:
        base_outlook = 'neutral'
        base_confidence = 0.3
        reasoning = 'US 정책 관망기 → 외국인 방향성 약함'

    # 금리차 보정
    if kr_us_rate_diff is not None:
        if kr_us_rate_diff > 0.5:
            base_confidence = min(1.0, base_confidence + 0.1)
            reasoning += ' + 한국 금리 우위로 캐리 유인'
        elif kr_us_rate_diff < -1.0:
            base_confidence = min(1.0, base_confidence + 0.1)
            if base_outlook == 'net_inflow':
                base_outlook = 'neutral'
                reasoning += ' (단, 금리 역전으로 유입 제한적)'

    # 환율 추세 보정
    if usdkrw_trend == 'strengthening':
        base_confidence = min(1.0, base_confidence + 0.05)
        reasoning += ' + 원화 강세 트렌드'
    elif usdkrw_trend == 'weakening':
        if base_outlook == 'net_inflow':
            base_confidence = max(0.1, base_confidence - 0.1)
            reasoning += ' (단, 원화 약세로 실현 불확실)'

    return {
        'outlook': base_outlook,
        'confidence': round(base_confidence, 2),
        'reasoning': reasoning,
    }


if __name__ == '__main__':
    main()
