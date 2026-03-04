"""kr-scenario-analyzer: 한국 뉴스/이벤트 → 18개월 시나리오 분석.

Usage:
    python kr_scenario_analyzer.py --headline "BOK 기준금리 0.25%p 인하"
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ─── 시나리오 구조 ───

SCENARIO_STRUCTURE = {
    'base': {'name': '기본 시나리오', 'probability': None},
    'bull': {'name': '강세 시나리오', 'probability': None},
    'bear': {'name': '약세 시나리오', 'probability': None},
}

TIME_HORIZON_MONTHS = 18

IMPACT_ORDERS = ['1차 영향', '2차 영향', '3차 영향']

RECOMMENDATION_COUNT = {
    'positive': (3, 5),
    'negative': (3, 5),
}

# ─── 한국 섹터 ───

KR_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학', '바이오/제약',
    '금융/은행', '유통/소비재', '건설/부동산', 'IT/소프트웨어',
    '통신', '에너지/유틸리티', '엔터테인먼트', '방산', '2차전지',
]

# ─── 한국 이벤트 유형 ───

KR_EVENT_TYPES = [
    'bok_rate_decision',
    'north_korea_geopolitical',
    'china_trade_policy',
    'semiconductor_cycle',
    'exchange_rate_shock',
    'government_policy',
    'earnings_surprise',
]

# ─── 이벤트 → 섹터 영향 매핑 ───

EVENT_SECTOR_IMPACT = {
    'bok_rate_decision': {
        'positive': ['금융/은행', '건설/부동산', '유통/소비재'],
        'negative': [],
        'description': 'BOK 금리 결정 — 금융/부동산 민감',
    },
    'north_korea_geopolitical': {
        'positive': ['방산'],
        'negative': ['건설/부동산', '금융/은행'],
        'description': '북한 리스크 — 방산 수혜, 금융/건설 약세',
    },
    'china_trade_policy': {
        'positive': ['방산', 'IT/소프트웨어'],
        'negative': ['철강/화학', '반도체'],
        'description': '중국 통상 — 수출주 타격, 내수주 수혜',
    },
    'semiconductor_cycle': {
        'positive': ['반도체', 'IT/소프트웨어'],
        'negative': [],
        'description': '반도체 사이클 — 삼성전자/SK하이닉스 주도',
    },
    'exchange_rate_shock': {
        'positive': ['자동차', '조선/해운'],
        'negative': ['유통/소비재', '에너지/유틸리티'],
        'description': '환율 변동 — 수출주/내수주 차별화',
    },
    'government_policy': {
        'positive': [],
        'negative': ['건설/부동산'],
        'description': '정부 정책 — 규제 방향에 따라 변동',
    },
    'earnings_surprise': {
        'positive': [],
        'negative': [],
        'description': '실적 서프라이즈 — 개별 종목/섹터 영향',
    },
}

# ─── 이벤트 키워드 매핑 ───

EVENT_KEYWORDS = {
    'bok_rate_decision': ['금리', '금통위', 'BOK', '기준금리', '한국은행'],
    'north_korea_geopolitical': ['북한', '미사일', '핵', '도발', '휴전'],
    'china_trade_policy': ['중국', '무역', '통상', '관세', '수출규제'],
    'semiconductor_cycle': ['반도체', 'DRAM', 'NAND', '메모리', 'HBM'],
    'exchange_rate_shock': ['환율', '원/달러', '원화', '달러', 'FX'],
    'government_policy': ['규제', '정책', '부동산', '법안', '세제'],
    'earnings_surprise': ['실적', '영업이익', '매출', '어닝', '서프라이즈'],
}


def classify_event(headline: str) -> str:
    """헤드라인에서 이벤트 유형 분류.

    Args:
        headline: 뉴스 헤드라인

    Returns:
        이벤트 유형 문자열
    """
    if not headline:
        return 'earnings_surprise'

    headline_lower = headline.lower()
    best_match = 'earnings_surprise'
    best_count = 0

    for event_type, keywords in EVENT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in headline_lower)
        if count > best_count:
            best_count = count
            best_match = event_type

    return best_match


def get_sector_impact(event_type: str) -> dict:
    """이벤트 유형에 따른 섹터 영향 조회.

    Args:
        event_type: 이벤트 유형

    Returns:
        {'positive': [...], 'negative': [...], 'description': str}
    """
    return EVENT_SECTOR_IMPACT.get(event_type, {
        'positive': [], 'negative': [],
        'description': '일반 이벤트',
    })


def build_impact_chain(event_type: str, sector_impact: dict) -> list:
    """1차/2차/3차 영향 체인 생성.

    Args:
        event_type: 이벤트 유형
        sector_impact: 섹터 영향 정보

    Returns:
        [{'order': '1차 영향', 'description': str}, ...]
    """
    chain = []

    # 1차 영향: 직접 섹터
    positive = sector_impact.get('positive', [])
    negative = sector_impact.get('negative', [])
    desc_1st = sector_impact.get('description', '')
    if positive:
        desc_1st += f' — 수혜: {", ".join(positive)}'
    if negative:
        desc_1st += f' — 피해: {", ".join(negative)}'
    chain.append({'order': '1차 영향', 'description': desc_1st})

    # 2차 영향: 관련 업종/밸류체인
    chain.append({
        'order': '2차 영향',
        'description': '관련 밸류체인 및 업종 전파 — '
                       '소재/부품/장비 → 완제품 → 유통',
    })

    # 3차 영향: 매크로/심리
    chain.append({
        'order': '3차 영향',
        'description': '시장 심리 및 매크로 환경 변화 — '
                       '외국인 수급 방향, KOSPI/KOSDAQ 지수 영향',
    })

    return chain


def build_scenarios(headline: str, event_type: str,
                    sector_impact: dict) -> list:
    """3가지 시나리오 생성.

    Args:
        headline: 뉴스 헤드라인
        event_type: 이벤트 유형
        sector_impact: 섹터 영향

    Returns:
        시나리오 리스트
    """
    positive = sector_impact.get('positive', [])
    negative = sector_impact.get('negative', [])

    scenarios = [
        {
            'name': '기본 시나리오',
            'probability': 50,
            'description': f'{headline} — 시장 예상 수준의 전개',
            'kospi_impact': '±2% 내외',
            'key_sectors': positive[:3] if positive else ['전체 시장'],
            'time_horizon': f'{TIME_HORIZON_MONTHS}개월',
        },
        {
            'name': '강세 시나리오',
            'probability': 25,
            'description': f'{headline} — 예상 상회, 추가 호재 동반',
            'kospi_impact': '+5~10%',
            'key_sectors': positive[:3] if positive else ['성장 섹터'],
            'time_horizon': f'{TIME_HORIZON_MONTHS}개월',
        },
        {
            'name': '약세 시나리오',
            'probability': 25,
            'description': f'{headline} — 예상 하회, 추가 악재 동반',
            'kospi_impact': '-5~10%',
            'key_sectors': negative[:3] if negative else ['방어 섹터'],
            'time_horizon': f'{TIME_HORIZON_MONTHS}개월',
        },
    ]

    return scenarios


def build_recommendations(sector_impact: dict) -> dict:
    """수혜/피해 종목 추천 (섹터 기반).

    Args:
        sector_impact: 섹터 영향

    Returns:
        {'positive': [...], 'negative': [...]}
    """
    positive_sectors = sector_impact.get('positive', [])
    negative_sectors = sector_impact.get('negative', [])

    # 섹터 → 대표 종목 매핑
    sector_stocks = {
        '반도체': ['삼성전자(005930)', 'SK하이닉스(000660)'],
        '자동차': ['현대차(005380)', '기아(000270)'],
        '조선/해운': ['HD한국조선해양(009540)', 'HMM(011200)'],
        '철강/화학': ['POSCO홀딩스(005490)', 'LG화학(051910)'],
        '바이오/제약': ['삼성바이오로직스(207940)', '셀트리온(068270)'],
        '금융/은행': ['KB금융(105560)', '신한지주(055550)'],
        '유통/소비재': ['삼성물산(028260)', 'CJ제일제당(097950)'],
        '건설/부동산': ['현대건설(000720)', 'GS건설(006360)'],
        'IT/소프트웨어': ['네이버(035420)', '카카오(035720)'],
        '통신': ['SK텔레콤(017670)', 'KT(030200)'],
        '에너지/유틸리티': ['한국전력(015760)', 'SK이노베이션(096770)'],
        '엔터테인먼트': ['하이브(352820)', 'JYP Ent.(035900)'],
        '방산': ['한화에어로스페이스(012450)', 'LIG넥스원(079550)'],
        '2차전지': ['LG에너지솔루션(373220)', '삼성SDI(006400)'],
    }

    positive_stocks = []
    for sector in positive_sectors:
        positive_stocks.extend(sector_stocks.get(sector, []))

    negative_stocks = []
    for sector in negative_sectors:
        negative_stocks.extend(sector_stocks.get(sector, []))

    return {
        'positive': positive_stocks[:5],
        'negative': negative_stocks[:5],
    }


def analyze_scenario(headline: str) -> dict:
    """전체 시나리오 분석 실행.

    Args:
        headline: 뉴스 헤드라인

    Returns:
        분석 결과 dict
    """
    event_type = classify_event(headline)
    sector_impact = get_sector_impact(event_type)
    impact_chain = build_impact_chain(event_type, sector_impact)
    scenarios = build_scenarios(headline, event_type, sector_impact)
    recommendations = build_recommendations(sector_impact)

    return {
        'headline': headline,
        'event_type': event_type,
        'event_description': sector_impact.get('description', ''),
        'impact_chain': impact_chain,
        'scenarios': scenarios,
        'recommendations': recommendations,
        'meta': {
            'analyzed_at': datetime.now().isoformat(),
            'time_horizon_months': TIME_HORIZON_MONTHS,
            'total_sectors': len(KR_SECTORS),
        },
    }


def generate_report(result: dict) -> str:
    """Markdown 리포트 생성.

    Args:
        result: 분석 결과

    Returns:
        Markdown 문자열
    """
    lines = [f'# 시나리오 분석: {result["headline"]}']
    lines.append(f'\n> 분석일시: {result["meta"]["analyzed_at"][:16]}')
    lines.append(f'> 이벤트 유형: {result["event_type"]}')
    lines.append(f'> 분석 기간: {TIME_HORIZON_MONTHS}개월\n')

    lines.append('## 영향 분석')
    for impact in result['impact_chain']:
        lines.append(f'\n### {impact["order"]}')
        lines.append(impact['description'])

    lines.append('\n## 시나리오')
    for s in result['scenarios']:
        lines.append(f'\n### {s["name"]} (확률: {s["probability"]}%)')
        lines.append(f'- **KOSPI 영향**: {s["kospi_impact"]}')
        lines.append(f'- **주요 섹터**: {", ".join(s["key_sectors"])}')
        lines.append(f'- {s["description"]}')

    recs = result['recommendations']
    lines.append('\n## 종목 추천')
    if recs['positive']:
        lines.append('\n### 수혜 종목')
        for stock in recs['positive']:
            lines.append(f'- {stock}')
    if recs['negative']:
        lines.append('\n### 피해 종목')
        for stock in recs['negative']:
            lines.append(f'- {stock}')

    lines.append('\n---\n*Generated by kr-scenario-analyzer*')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='한국 시나리오 분석기')
    parser.add_argument('--headline', required=True)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    result = analyze_scenario(args.headline)
    report = generate_report(result)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'[Scenario] 분석 완료 → {args.output}')
    else:
        print(report)


if __name__ == '__main__':
    main()
