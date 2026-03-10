"""미국 경제지표 대시보드 리포트 생성 모듈.

4-Section 마크다운 리포트를 조합하여 저장한다.
"""

import os
from datetime import datetime

from indicator_collector import (
    CATEGORY_MAP, CATEGORY_ORDER, CATEGORY_NAMES_KR,
)
from regime_classifier import REGIME_DESCRIPTIONS, Regime
from kr_impact_analyzer import format_impact_section, NET_IMPACT_KR
from calendar_tracker import format_calendar_section


def build_header(collection_stats: dict, regime: dict) -> str:
    """리포트 헤더 생성."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    total = collection_stats.get('total', 21)
    collected = collection_stats.get('collected', 0)
    rate = collection_stats.get('rate', 0)

    regime_name = regime.get('regime_kr', 'Unknown')
    if hasattr(regime.get('regime'), 'value'):
        regime_val = regime['regime'].value
    else:
        regime_val = str(regime.get('regime', 'Unknown'))

    lines = [
        '# 미국 경제지표 대시보드',
        f'> 생성일: {now} | 수집: {collected}/{total} ({rate}%) | 레짐: {regime_val}',
        '',
    ]
    return '\n'.join(lines)


def _format_value(value, unit: str, ind_id: str = '') -> str:
    """값 포맷팅."""
    if value is None:
        return 'N/A'

    if unit == 'K':
        return f"{value:.0f}K"
    elif unit == '$B':
        return f"${value:.1f}B"
    elif unit == 'M':
        return f"{value:.1f}M"
    elif unit == 'index':
        return f"{value:.1f}"
    elif unit == '%':
        return f"{value:.2f}%"
    elif unit == 'hrs':
        return f"{value:.1f}h"
    else:
        return f"{value}"


def _format_change(change, unit: str, direction: str) -> str:
    """변화량 포맷팅."""
    if change is None:
        return '-'

    if unit == 'K':
        sign = '+' if change > 0 else ''
        return f"{sign}{change:.0f}K"
    elif unit == '$B':
        sign = '+' if change > 0 else ''
        return f"{sign}${abs(change):.1f}B"
    elif unit == 'M':
        sign = '+' if change > 0 else ''
        return f"{sign}{change:.2f}M"
    elif unit in ('%', ''):
        sign = '+' if change > 0 else ''
        return f"{sign}{change:.2f}%p"
    elif unit == 'index':
        sign = '+' if change > 0 else ''
        return f"{sign}{change:.1f}"
    elif unit == 'hrs':
        sign = '+' if change > 0 else ''
        return f"{sign}{change:.1f}h"
    else:
        sign = '+' if change > 0 else ''
        return f"{sign}{change}"


def build_dashboard_section(indicators: list) -> str:
    """Section 1: 7개 카테고리별 대시보드 테이블 생성."""
    lines = ['## Section 1: 지표 대시보드', '']

    # 카테고리별 그룹화
    ind_by_id = {ind['id']: ind for ind in indicators}

    for cat_key in CATEGORY_ORDER:
        cat_name = CATEGORY_NAMES_KR.get(cat_key, cat_key)
        cat_ids = CATEGORY_MAP.get(cat_key, [])

        if not cat_ids:
            continue

        lines.append(f'### {cat_name}')
        lines.append('')
        lines.append('| 지표 | 현재값 | 이전값 | 변화 | 방향 | 추세 |')
        lines.append('|------|:------:|:------:|:----:|:----:|------|')

        for ind_id in cat_ids:
            ind = ind_by_id.get(ind_id, {})
            name = ind.get('name_kr', ind_id)
            unit = ind.get('unit', '')
            value = ind.get('value')
            prev_value = ind.get('prev_value')
            change = ind.get('change')
            direction = ind.get('direction', '→')
            trend = ind.get('trend_label', '')

            val_str = _format_value(value, unit, ind_id)
            prev_str = _format_value(prev_value, unit, ind_id)
            chg_str = _format_change(change, unit, direction)

            lines.append(
                f"| {name} | {val_str} | {prev_str} | {chg_str} | {direction} | {trend} |"
            )

        lines.append('')

    return '\n'.join(lines)


def _level_kr(component: str, level: str) -> str:
    """컴포넌트 레벨 한국어 변환."""
    level_map = {
        'inflation': {
            'low': '안정(Low)', 'moderate': '보통(Moderate)',
            'high': '높음(High)', 'very_high': '매우높음(Very High)',
            'unknown': '미확인',
        },
        'growth': {
            'strong': '강세(Strong)', 'moderate': '적정(Moderate)',
            'weak': '약세(Weak)', 'recession': '침체(Recession)',
            'unknown': '미확인',
        },
        'employment': {
            'tight': '과열(Tight)', 'balanced': '균형(Balanced)',
            'cooling': '냉각(Cooling)', 'weak': '약화(Weak)',
            'unknown': '미확인',
        },
        'sentiment': {
            'optimistic': '낙관(Optimistic)', 'neutral': '중립(Neutral)',
            'cautious': '경계(Cautious)', 'pessimistic': '비관(Pessimistic)',
            'unknown': '미확인',
        },
        'external': {
            'healthy': '양호(Healthy)', 'moderate': '보통(Moderate)',
            'deficit_widening': '적자확대(Widening)',
            'unknown': '미확인',
        },
    }
    return level_map.get(component, {}).get(level, level)


COMPONENT_NAMES_KR = {
    'inflation': '물가',
    'growth': '경기',
    'employment': '고용',
    'sentiment': '심리',
    'external': '대외',
}


def build_regime_section(regime_result: dict) -> str:
    """Section 2: 종합 진단 생성."""
    lines = []

    regime_kr = regime_result.get('regime_kr', 'Unknown')
    kr_impact = regime_result.get('kr_impact', '')
    composite = regime_result.get('composite_score', 0)

    lines.append(f'## Section 2: 종합 진단 — {regime_kr}')
    lines.append('')
    if kr_impact:
        lines.append(f'**한국 시장 영향**: {kr_impact}')
        lines.append('')

    # 5-컴포넌트 스코어 테이블
    lines.append('### 5-컴포넌트 스코어')
    lines.append('')
    lines.append('| 컴포넌트 | 스코어 | 가중치 | 가중점수 | 수준 |')
    lines.append('|---------|:------:|:------:|:-------:|------|')

    components = regime_result.get('components', {})
    component_details = regime_result.get('component_details', {})

    for comp_key in ['inflation', 'growth', 'employment', 'sentiment', 'external']:
        comp = components.get(comp_key, {})
        detail = component_details.get(comp_key, {})
        comp_name = COMPONENT_NAMES_KR.get(comp_key, comp_key)
        score = comp.get('score', 0)
        weight = comp.get('weight', 0)
        weighted = comp.get('weighted', 0)
        level = detail.get('level', 'unknown')
        level_kr = _level_kr(comp_key, level)

        lines.append(
            f"| {comp_name} | {score:.0f} | {weight*100:.0f}% | {weighted:.1f} | {level_kr} |"
        )

    lines.append(f"| **합계** | | | **{composite:.1f}** | |")
    lines.append('')

    return '\n'.join(lines)


def build_impact_section(impact_result: dict) -> str:
    """Section 3: 한국 시장 영향 분석."""
    return format_impact_section(impact_result)


def build_calendar_section(upcoming: list) -> str:
    """Section 4: 다음 발표 일정."""
    return format_calendar_section(upcoming)


def build_footer() -> str:
    """리포트 푸터."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [
        '---',
        f'*Generated by us-indicator-dashboard | {now}*',
    ]
    return '\n'.join(lines)


def generate_report(indicators: list, regime: dict,
                    impact: dict, upcoming: list,
                    collection_stats: dict) -> str:
    """4-Section 리포트 전체 조합."""
    sections = [
        build_header(collection_stats, regime),
        build_dashboard_section(indicators),
        build_regime_section(regime),
        build_impact_section(impact),
        build_calendar_section(upcoming),
        build_footer(),
    ]
    return '\n'.join(sections)


def save_report(content: str, date_str: str = None) -> str:
    """리포트를 reports/ 디렉토리에 저장.

    Returns:
        저장된 파일 경로
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')

    # reports/ 디렉토리 (프로젝트 루트)
    reports_dir = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'reports'
    )
    reports_dir = os.path.abspath(reports_dir)
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"us-indicator-dashboard_macro_미국경제지표_{date_str}.md"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath
