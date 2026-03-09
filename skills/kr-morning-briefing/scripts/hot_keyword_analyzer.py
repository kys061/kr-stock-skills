"""장 초반 핫 키워드 분석 모듈.

WebSearch로 수집된 뉴스에서 핵심 키워드를 추출하고 관련주를 매핑.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 기본 테마 매핑 테이블 ────────────────────
THEME_STOCK_MAP = {
    '방산': ['한화에어로스페이스', 'LIG넥스원', '한화시스템', '현대로템'],
    'AI반도체': ['삼성전자', 'SK하이닉스', '한미반도체', '리노공업'],
    '원전': ['두산에너빌리티', '한전기술', 'HD현대일렉트릭', 'LS ELECTRIC'],
    '2차전지': ['LG에너지솔루션', '삼성SDI', '에코프로비엠', 'POSCO홀딩스'],
    '정유': ['SK이노베이션', 'S-Oil', 'GS칼텍스', 'HD현대오일뱅크'],
    '바이오': ['삼성바이오로직스', '셀트리온', 'SK바이오팜', '유한양행'],
    '건설': ['현대건설', 'DL이앤씨', 'GS건설', 'HDC현대산업개발'],
    '금융': ['KB금융', '신한지주', '하나금융지주', '우리금융지주'],
    '조선': ['HD한국조선해양', '한화오션', '삼성중공업'],
    '게임엔터': ['하이브', 'SM', 'JYP Ent.', '크래프톤', '넷마블'],
}

# 키워드 → 테마 매핑 힌트
KEYWORD_THEME_HINTS = {
    '전쟁': '방산', '군사': '방산', '미사일': '방산', '이란': '방산',
    'AI': 'AI반도체', '반도체': 'AI반도체', 'GPU': 'AI반도체', '엔비디아': 'AI반도체',
    '원전': '원전', '원자력': '원전', 'SMR': '원전',
    '배터리': '2차전지', '리튬': '2차전지', 'EV': '2차전지', '전기차': '2차전지',
    '유가': '정유', 'WTI': '정유', '원유': '정유',
    '신약': '바이오', '임상': '바이오', 'FDA': '바이오',
    '금리': '금융', 'FOMC': '금융', '기준금리': '금융',
    'LNG': '조선', '선박': '조선', '수주': '조선',
    'BTS': '게임엔터', '컴백': '게임엔터', '게임': '게임엔터',
    '아파트': '건설', '부동산': '건설', '재건축': '건설',
}


def map_related_stocks(keyword: str, category: str = '') -> list:
    """키워드/카테고리에서 관련주를 매핑.

    Args:
        keyword: 핫 키워드
        category: 카테고리 힌트

    Returns:
        관련 종목명 리스트
    """
    # 직접 테마 매핑
    if category in THEME_STOCK_MAP:
        return THEME_STOCK_MAP[category]

    # 키워드에서 테마 힌트 탐색
    keyword_lower = keyword.lower() if keyword else ''
    for hint_word, theme in KEYWORD_THEME_HINTS.items():
        if hint_word.lower() in keyword_lower:
            return THEME_STOCK_MAP.get(theme, [])

    return []


def extract_keywords_from_news(headlines: list, max_keywords: int = 3) -> list:
    """뉴스 헤드라인에서 핵심 키워드를 추출.

    Args:
        headlines: 뉴스 헤드라인 리스트
        max_keywords: 최대 키워드 수

    Returns:
        [{'headline': str, 'category': str}, ...]
    """
    if not headlines:
        return []

    seen = set()
    unique = []
    for h in headlines:
        h_stripped = h.strip()
        if h_stripped and h_stripped not in seen:
            seen.add(h_stripped)
            unique.append(h_stripped)

    results = []
    used_themes = set()

    for headline in unique:
        if len(results) >= max_keywords:
            break

        # 테마 감지
        detected_theme = None
        for hint_word, theme in KEYWORD_THEME_HINTS.items():
            if hint_word.lower() in headline.lower():
                detected_theme = theme
                break

        # 카테고리 다양성: 같은 테마 최대 2개
        if detected_theme and used_themes.get(detected_theme, 0) if isinstance(used_themes, dict) else False:
            continue

        results.append({
            'headline': headline,
            'category': detected_theme or '기타',
        })

        if detected_theme:
            if not isinstance(used_themes, dict):
                used_themes = {}
            used_themes[detected_theme] = used_themes.get(detected_theme, 0) + 1

    return results[:max_keywords]


def analyze_hot_keywords(websearch_context: dict = None) -> dict:
    """핫 키워드 2-3개를 분석하고 관련주를 매핑.

    Args:
        websearch_context: WebSearch로 수집된 뉴스 데이터
            {
                'keywords': [
                    {'headline': str, 'summary': str, 'impact': str,
                     'related_stocks': [str], 'sentiment': str},
                    ...
                ],
                'one_liner': str,
            }
            OR
            {
                'headlines': [str, ...],
            }

    Returns:
        {
            'keywords': [{rank, headline, summary, impact, related_stocks, sentiment}, ...],
            'one_liner': str,
            'keyword_count': int,
        }
    """
    empty_result = {
        'keywords': [],
        'one_liner': '',
        'keyword_count': 0,
    }

    if not websearch_context:
        return empty_result

    # 이미 구조화된 데이터가 주입된 경우
    if 'keywords' in websearch_context and isinstance(websearch_context['keywords'], list):
        keywords = websearch_context['keywords']
        for i, kw in enumerate(keywords):
            kw.setdefault('rank', i + 1)
            kw.setdefault('summary', '')
            kw.setdefault('impact', '')
            kw.setdefault('sentiment', 'neutral')
            if not kw.get('related_stocks'):
                kw['related_stocks'] = map_related_stocks(
                    kw.get('headline', ''), kw.get('category', ''))

        return {
            'keywords': keywords,
            'one_liner': websearch_context.get('one_liner', ''),
            'keyword_count': len(keywords),
        }

    # 헤드라인만 있는 경우 — 키워드 추출
    headlines = websearch_context.get('headlines', [])
    if not headlines:
        return empty_result

    extracted = extract_keywords_from_news(headlines)
    keywords = []
    for i, kw in enumerate(extracted):
        related = map_related_stocks(kw['headline'], kw['category'])
        keywords.append({
            'rank': i + 1,
            'headline': kw['headline'],
            'summary': '',
            'impact': '',
            'related_stocks': related,
            'sentiment': 'neutral',
        })

    return {
        'keywords': keywords,
        'one_liner': '',
        'keyword_count': len(keywords),
    }
