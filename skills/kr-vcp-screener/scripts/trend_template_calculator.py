"""Stage 2 트렌드 템플릿 (7-Point Minervini Template)."""

# ── 7-Point 조건 ────────────────────────────────────────────
# 1: Close > SMA(150) AND Close > SMA(200)
# 2: SMA(150) > SMA(200)
# 3: SMA(200) 22일+ 상승
# 4: Close > SMA(50)
# 5: Close >= 52W Low * 1.25
# 6: Close >= 52W High * 0.75
# 7: RS Rank > 70

TEMPLATE_PASS_THRESHOLD = 6   # 7점 중 6점 이상
TEMPLATE_PERFECT = 7
SMA200_RISING_DAYS = 22       # 200일 SMA 상승 판단 기간


def check_trend_template(price: float, sma50: float, sma150: float,
                         sma200: float, sma200_22d_ago: float,
                         high_52w: float, low_52w: float,
                         rs_rank: float) -> dict:
    """7-Point Stage 2 트렌드 템플릿 검사.

    Args:
        price: 현재 종가
        sma50: 50일 이동평균
        sma150: 150일 이동평균
        sma200: 200일 이동평균
        sma200_22d_ago: 22거래일 전 200일 SMA
        high_52w: 52주 고가
        low_52w: 52주 저가
        rs_rank: RS Rank (0-100, KOSPI 대비)
    Returns:
        {
            'score': int (0-100),
            'passed': bool,
            'points': int (0-7),
            'details': list of dict,
        }
    """
    checks = [
        {
            'id': 1,
            'name': 'Close > SMA150 & SMA200',
            'passed': price > sma150 and price > sma200,
        },
        {
            'id': 2,
            'name': 'SMA150 > SMA200',
            'passed': sma150 > sma200,
        },
        {
            'id': 3,
            'name': 'SMA200 22일+ 상승',
            'passed': sma200 > sma200_22d_ago if sma200_22d_ago > 0 else False,
        },
        {
            'id': 4,
            'name': 'Close > SMA50',
            'passed': price > sma50,
        },
        {
            'id': 5,
            'name': 'Close >= 52W Low +25%',
            'passed': price >= low_52w * 1.25 if low_52w > 0 else False,
        },
        {
            'id': 6,
            'name': 'Close >= 52W High -25%',
            'passed': price >= high_52w * 0.75 if high_52w > 0 else False,
        },
        {
            'id': 7,
            'name': 'RS Rank > 70',
            'passed': rs_rank > 70,
        },
    ]

    points = sum(1 for c in checks if c['passed'])
    passed = points >= TEMPLATE_PASS_THRESHOLD

    # Score: 0-100 변환 (7점 = 100, 6점 = 85, 5점 = 70, ...)
    score = round((points / TEMPLATE_PERFECT) * 100)

    return {
        'score': score,
        'passed': passed,
        'points': points,
        'details': checks,
    }
