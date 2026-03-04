"""kr-dart-disclosure-monitor: 공시 유형 분류."""


# ─── DART 공시 유형 ───

DISCLOSURE_TYPES = {
    'EARNINGS': {
        'label': '실적 공시',
        'subtypes': ['preliminary', 'confirmed', 'guidance'],
        'dart_kinds': ['A001', 'A002', 'A003', 'D001', 'D002'],
        'keywords': ['사업보고서', '분기보고서', '반기보고서', '잠정실적', '영업실적'],
    },
    'DIVIDEND': {
        'label': '배당 관련',
        'subtypes': ['increase', 'decrease', 'omission', 'record_date'],
        'keywords': ['배당', '현금배당', '주식배당', '기준일'],
    },
    'CAPITAL': {
        'label': '자본 변동',
        'subtypes': ['rights_offering', 'bonus_issue', 'reduction', 'convertible'],
        'keywords': ['유상증자', '무상증자', '감자', '전환사채', 'CB', 'BW'],
    },
    'MA': {
        'label': 'M&A',
        'subtypes': ['merger', 'acquisition', 'spin_off', 'business_transfer'],
        'keywords': ['합병', '인수', '분할', '영업양수도', '주식교환'],
    },
    'GOVERNANCE': {
        'label': '지배구조',
        'subtypes': ['ceo_change', 'board', 'articles'],
        'keywords': ['대표이사', '이사선임', '정관변경', '감사', '이사회'],
    },
    'STAKE': {
        'label': '지분 변동',
        'subtypes': ['major_holder', 'officer_trade', 'treasury_stock'],
        'keywords': ['대량보유', '임원', '자사주', '주요주주', '특정증권'],
    },
    'LEGAL': {
        'label': '법적 이벤트',
        'subtypes': ['lawsuit', 'sanction', 'penalty'],
        'keywords': ['소송', '제재', '과징금', '조치', '위반'],
    },
    'IPO': {
        'label': '상장 관련',
        'subtypes': ['listing', 'delisting', 'spac'],
        'keywords': ['상장', '상장폐지', '스팩', '신규상장'],
    },
    'REGULATION': {
        'label': '규제',
        'subtypes': ['management_issue', 'investment_warning', 'trading_halt'],
        'keywords': ['관리종목', '투자주의', '매매정지', '투자위험'],
    },
    'OTHER': {
        'label': '기타',
        'subtypes': ['contract', 'patent', 'facility'],
        'keywords': ['수주', '특허', '공장', '설립', '계약'],
    },
}


def classify_disclosure(title, report_code=None):
    """DART 공시 제목 기반 유형 분류.

    Args:
        title: DART 공시 제목 문자열.
        report_code: DART 리포트 코드 (예: 'A001', optional).

    Returns:
        dict: {type, subtype, keywords_matched, label}
    """
    if not title:
        return {'type': 'OTHER', 'subtype': None, 'keywords_matched': [], 'label': '기타'}

    # 리포트 코드 기반 우선 분류 (EARNINGS)
    if report_code:
        for dtype, info in DISCLOSURE_TYPES.items():
            dart_kinds = info.get('dart_kinds', [])
            if report_code in dart_kinds:
                subtype = _detect_subtype(title, info['subtypes'], dtype)
                return {
                    'type': dtype,
                    'subtype': subtype,
                    'keywords_matched': [report_code],
                    'label': info['label'],
                }

    # 키워드 기반 분류
    matched_type = 'OTHER'
    matched_keywords = []
    best_match_count = 0

    for dtype, info in DISCLOSURE_TYPES.items():
        keywords = info.get('keywords', [])
        matches = [kw for kw in keywords if kw in title]
        if len(matches) > best_match_count:
            best_match_count = len(matches)
            matched_type = dtype
            matched_keywords = matches

    info = DISCLOSURE_TYPES[matched_type]
    subtype = _detect_subtype(title, info.get('subtypes', []), matched_type)

    return {
        'type': matched_type,
        'subtype': subtype,
        'keywords_matched': matched_keywords,
        'label': info['label'],
    }


def _detect_subtype(title, subtypes, dtype):
    """세부 유형 탐지."""
    title_lower = title.lower() if title else ''

    # 유형별 세부 키워드 매핑
    subtype_keywords = {
        'EARNINGS': {
            'preliminary': ['잠정'],
            'confirmed': ['사업보고서', '분기보고서', '반기보고서'],
            'guidance': ['전망', '가이던스'],
        },
        'DIVIDEND': {
            'increase': ['증배', '배당금 증가', '배당 증액'],
            'decrease': ['감배', '배당금 감소', '배당 감액'],
            'omission': ['무배당', '배당 미실시'],
            'record_date': ['기준일'],
        },
        'CAPITAL': {
            'rights_offering': ['유상증자'],
            'bonus_issue': ['무상증자'],
            'reduction': ['감자'],
            'convertible': ['전환사채', 'CB', 'BW'],
        },
        'MA': {
            'merger': ['합병'],
            'acquisition': ['인수'],
            'spin_off': ['분할'],
            'business_transfer': ['영업양수도'],
        },
        'GOVERNANCE': {
            'ceo_change': ['대표이사'],
            'board': ['이사선임', '이사회'],
            'articles': ['정관변경'],
        },
        'STAKE': {
            'major_holder': ['대량보유', '주요주주'],
            'officer_trade': ['임원', '특정증권'],
            'treasury_stock': ['자사주'],
        },
        'LEGAL': {
            'lawsuit': ['소송'],
            'sanction': ['제재'],
            'penalty': ['과징금'],
        },
        'IPO': {
            'delisting': ['상장폐지'],
            'spac': ['스팩'],
            'listing': ['신규상장', '상장'],
        },
        'REGULATION': {
            'management_issue': ['관리종목'],
            'investment_warning': ['투자주의', '투자위험'],
            'trading_halt': ['매매정지'],
        },
        'OTHER': {
            'contract': ['수주', '계약'],
            'patent': ['특허'],
            'facility': ['공장', '설립'],
        },
    }

    keywords_map = subtype_keywords.get(dtype, {})
    for subtype, keywords in keywords_map.items():
        for kw in keywords:
            if kw in title:
                return subtype

    return subtypes[0] if subtypes else None


def classify_batch(disclosures):
    """공시 목록 일괄 분류.

    Args:
        disclosures: list of dict [{title, report_code, date, corp_name}]

    Returns:
        list: [{...original, type, subtype, keywords_matched, label}]
    """
    results = []
    for d in disclosures:
        classification = classify_disclosure(
            d.get('title', ''),
            d.get('report_code'),
        )
        results.append({**d, **classification})
    return results
