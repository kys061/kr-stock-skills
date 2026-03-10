"""한국 시장 영향 분석 모듈.

21개 지표별 변화 방향에 따른 한국 시장 영향을 긍정/부정/중립으로 분류한다.
"""

from enum import Enum


class Impact(Enum):
    POSITIVE = 'positive'
    NEGATIVE = 'negative'
    NEUTRAL = 'neutral'


# (indicator_id, direction) → (Impact, reason_template)
IMPACT_RULES = {
    ('gdp', '↑'): (Impact.POSITIVE, 'GDP 상승 → 미국 소비 확대 → 한국 수출 증가'),
    ('gdp', '↓'): (Impact.NEGATIVE, 'GDP 하락 → 미국 수요 둔화 → 한국 수출 감소'),
    ('fed_rate', '↓'): (Impact.POSITIVE, '기준금리 인하 → 한미 금리차 축소 → 외국인 유입'),
    ('fed_rate', '↑'): (Impact.NEGATIVE, '기준금리 인상 → 한미 금리차 확대 → 외국인 이탈'),
    ('treasury_10y', '↓'): (Impact.POSITIVE, '장기금리 하락 → 성장주 밸류에이션 개선'),
    ('treasury_10y', '↑'): (Impact.NEGATIVE, '장기금리 상승 → 성장주 밸류에이션 압박'),
    ('treasury_2y', '↓'): (Impact.POSITIVE, '단기금리 하락 → 인하 기대 반영'),
    ('treasury_2y', '↑'): (Impact.NEGATIVE, '단기금리 상승 → 인하 지연 반영'),
    ('cpi', '↓'): (Impact.POSITIVE, 'CPI 둔화 → Fed 인하 기대 유지 → 위험자산 선호'),
    ('cpi', '↑'): (Impact.NEGATIVE, 'CPI 가속 → 인하 지연/인상 우려 → 위험자산 회피'),
    ('pce', '↓'): (Impact.POSITIVE, 'PCE 둔화 → Fed 선호 지표 개선 → 인하 기대'),
    ('pce', '↑'): (Impact.NEGATIVE, 'PCE 가속 → Fed 매파 전환 가능'),
    ('ppi', '↓'): (Impact.POSITIVE, 'PPI 하락 → 기업 비용 압력 완화 → CPI 둔화 선행'),
    ('ppi', '↑'): (Impact.NEGATIVE, 'PPI 상승 → 기업 비용 전가 → CPI 상승 우려'),
    ('inflation_exp', '↓'): (Impact.POSITIVE, '인플레 기대 하락 → 기대 앵커링 성공'),
    ('inflation_exp', '↑'): (Impact.NEGATIVE, '인플레 기대 상승 → 자기실현적 인플레 우려'),
    ('unemployment', '↑'): (Impact.POSITIVE, '실업률 상승 → 고용 냉각 → 인하 기대 ↑ → 신흥국 유리'),
    ('unemployment', '↓'): (Impact.NEUTRAL, '실업률 하락 → 고용 견조 → 인하 지연 가능'),
    ('weekly_hours', '↓'): (Impact.NEGATIVE, '근무시간 감소 → 경기 냉각 신호'),
    ('weekly_hours', '↑'): (Impact.POSITIVE, '근무시간 증가 → 생산 확대 → 수출 수요'),
    ('hourly_earnings', '↑'): (Impact.NEGATIVE, '임금 가속 → 임금-물가 스파이럴 위험 → 인하 제약'),
    ('hourly_earnings', '↓'): (Impact.POSITIVE, '임금 둔화 → 인플레 완화 → 인하 여유'),
    ('real_earnings', '↑'): (Impact.POSITIVE, '실질임금 상승 → 소비력 개선 → 수요 지지'),
    ('real_earnings', '↓'): (Impact.NEGATIVE, '실질임금 하락 → 소비력 약화'),
    ('jobless_claims', '↓'): (Impact.POSITIVE, '실업수당 감소 → 고용 안정 → 미국 경기 양호'),
    ('jobless_claims', '↑'): (Impact.NEGATIVE, '실업수당 증가 → 고용 악화 신호'),
    ('retail_sales', '↑'): (Impact.POSITIVE, '소매판매 증가 → 미국 소비 견조 → 수출 수요'),
    ('retail_sales', '↓'): (Impact.NEGATIVE, '소매판매 감소 → 미국 소비 둔화 → 수출 타격'),
    ('ism_pmi', '↑'): (Impact.POSITIVE, 'ISM PMI 상승 → 제조업 확장 → 한국 수출 선행 개선'),
    ('ism_pmi', '↓'): (Impact.NEGATIVE, 'ISM PMI 하락 → 제조업 위축 → 한국 수출 둔화 우려'),
    ('consumer_sentiment', '↑'): (Impact.POSITIVE, '소비심리 개선 → 소비 회복 기대'),
    ('consumer_sentiment', '↓'): (Impact.NEGATIVE, '소비심리 악화 → 소비 둔화 우려'),
    ('consumer_confidence', '↑'): (Impact.POSITIVE, '소비자신뢰 상승 → 소비 의향 확대'),
    ('consumer_confidence', '↓'): (Impact.NEGATIVE, '소비자신뢰 하락 → 소비 위축 우려'),
    ('business_inventories', '↑'): (Impact.NEUTRAL, '기업재고 증가 → 수요 대비 과잉 가능성'),
    ('business_inventories', '↓'): (Impact.POSITIVE, '기업재고 감소 → 보충 주문 기대 → 수출 긍정'),
    ('housing_starts', '↑'): (Impact.POSITIVE, '주택착공 증가 → 건설/원자재 수요 → 철강/구리'),
    ('housing_starts', '↓'): (Impact.NEGATIVE, '주택착공 감소 → 건설 경기 둔화'),
    ('auto_sales', '↑'): (Impact.POSITIVE, '자동차판매 증가 → 부품 수출 수혜'),
    ('auto_sales', '↓'): (Impact.NEGATIVE, '자동차판매 감소 → 부품 수출 둔화'),
    ('current_account', '↓'): (Impact.NEUTRAL, '경상적자 확대 → 달러 약세 압력 → 신흥국 상대 유리'),
    ('current_account', '↑'): (Impact.NEUTRAL, '경상적자 축소 → 달러 강세 → 신흥국 부담'),
}


def analyze_impact(indicators: list) -> dict:
    """21개 지표별 한국 시장 영향 분석."""
    positive = []
    negative = []
    neutral = []

    for ind in indicators:
        ind_id = ind.get('id')
        value = ind.get('value')
        direction = ind.get('direction', '→')

        if value is None:
            continue

        key = (ind_id, direction)
        if key in IMPACT_RULES:
            impact, reason = IMPACT_RULES[key]
        elif direction == '→':
            impact = Impact.NEUTRAL
            reason = f"{ind.get('name_kr', ind_id)} 변화 없음"
        else:
            impact = Impact.NEUTRAL
            reason = f"{ind.get('name_kr', ind_id)} 영향 판단 불가"

        entry = {
            'id': ind_id,
            'name_kr': ind.get('name_kr', ind_id),
            'direction': direction,
            'reason': reason,
        }

        if impact == Impact.POSITIVE:
            positive.append(entry)
        elif impact == Impact.NEGATIVE:
            negative.append(entry)
        else:
            neutral.append(entry)

    # net_impact 판정
    pos_count = len(positive)
    neg_count = len(negative)
    diff = pos_count - neg_count

    if diff >= 4:
        net_impact = 'strongly_positive'
    elif diff >= 1:
        net_impact = 'mildly_positive'
    elif diff <= -4:
        net_impact = 'strongly_negative'
    elif diff <= -1:
        net_impact = 'mildly_negative'
    else:
        net_impact = 'neutral'

    # summary 생성
    summary_parts = []
    if positive:
        summary_parts.append(f"긍정({pos_count}): {positive[0]['reason']}")
    if negative:
        summary_parts.append(f"부정({neg_count}): {negative[0]['reason']}")
    summary = ' / '.join(summary_parts) if summary_parts else '분석 데이터 부족'

    return {
        'positive': positive,
        'negative': negative,
        'neutral': neutral,
        'summary': summary,
        'net_impact': net_impact,
    }


NET_IMPACT_KR = {
    'strongly_positive': '강한 긍정적 (Strongly Positive)',
    'mildly_positive': '약간 긍정적 (Mildly Positive)',
    'neutral': '중립 (Neutral)',
    'mildly_negative': '약간 부정적 (Mildly Negative)',
    'strongly_negative': '강한 부정적 (Strongly Negative)',
}


def format_impact_section(impact_result: dict) -> str:
    """한국 영향 분석 결과를 마크다운으로 포맷팅."""
    lines = ['## 한국 시장 영향 분석', '']
    net = impact_result.get('net_impact', 'neutral')
    lines.append(f"**종합 판정**: {NET_IMPACT_KR.get(net, net)}")
    lines.append('')

    pos = impact_result.get('positive', [])
    neg = impact_result.get('negative', [])
    neu = impact_result.get('neutral', [])

    if pos:
        lines.append(f'### 긍정 요인 ({len(pos)}개)')
        for p in pos:
            lines.append(f"- {p['reason']}")
        lines.append('')

    if neg:
        lines.append(f'### 부정 요인 ({len(neg)}개)')
        for n in neg:
            lines.append(f"- {n['reason']}")
        lines.append('')

    if neu:
        lines.append(f'### 중립 요인 ({len(neu)}개)')
        for n in neu:
            lines.append(f"- {n['reason']}")
        lines.append('')

    return '\n'.join(lines)
