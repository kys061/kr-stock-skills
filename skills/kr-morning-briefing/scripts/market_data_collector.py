"""글로벌 시장 데이터 수집 모듈.

yfinance 배치 다운로드(17개) + WebSearch 컨텍스트(10개) = 27개 항목 수집.
"""

import logging
from datetime import datetime

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# ── yfinance 티커 매핑 (17개) ──────────────────
YFINANCE_TICKERS = {
    # 미국 지수 (3)
    'dow': {'ticker': '^DJI', 'name': '다우지수', 'category': '미국지수', 'unit': 'p'},
    'nasdaq': {'ticker': '^IXIC', 'name': '나스닥', 'category': '미국지수', 'unit': 'p'},
    'sp500': {'ticker': '^GSPC', 'name': 'S&P500', 'category': '미국지수', 'unit': 'p'},
    # 환율 (3)
    'usd_krw': {'ticker': 'KRW=X', 'name': '원/달러', 'category': '환율', 'unit': '원'},
    'usd_jpy': {'ticker': 'JPY=X', 'name': '엔/달러', 'category': '환율', 'unit': '엔'},
    'dxy': {'ticker': 'DX-Y.NYB', 'name': '달러인덱스', 'category': '환율', 'unit': ''},
    # 국채 (1)
    'us10y': {'ticker': '^TNX', 'name': '국고채 10년', 'category': '미국국채', 'unit': '%'},
    # 유가 (2)
    'wti': {'ticker': 'CL=F', 'name': 'WTI', 'category': '유가', 'unit': '$'},
    'brent': {'ticker': 'BZ=F', 'name': '브렌트유', 'category': '유가', 'unit': '$'},
    # 안전자산 (2)
    'gold': {'ticker': 'GC=F', 'name': '금', 'category': '안전자산', 'unit': '$'},
    'btc_krw': {'ticker': 'BTC-KRW', 'name': '비트코인', 'category': '안전자산', 'unit': '원'},
    # 광물 (1)
    'copper': {'ticker': 'HG=F', 'name': '구리', 'category': '광물', 'unit': '$'},
    # 농산물 (5)
    'corn': {'ticker': 'ZC=F', 'name': '옥수수', 'category': '농산물', 'unit': '¢'},
    'wheat': {'ticker': 'ZW=F', 'name': '소맥', 'category': '농산물', 'unit': '¢'},
    'soybean': {'ticker': 'ZS=F', 'name': '대두', 'category': '농산물', 'unit': '¢'},
    'coffee': {'ticker': 'KC=F', 'name': '커피', 'category': '농산물', 'unit': '¢'},
    'cotton': {'ticker': 'CT=F', 'name': '원면', 'category': '농산물', 'unit': '¢'},
}

# ── WebSearch 항목 (10개) ──────────────────────
WEBSEARCH_ITEMS = {
    'us2y': {'name': '국고채 2년', 'category': '미국국채', 'unit': '%',
             'query': '미국 국채 2년 수익률 오늘'},
    'dubai_oil': {'name': '두바이유', 'category': '유가', 'unit': '$',
                  'query': '두바이유 가격 오늘'},
    'aluminum': {'name': '알루미늄', 'category': '광물', 'unit': '$/톤',
                 'query': 'LME 알루미늄 가격'},
    'nickel': {'name': '니켈', 'category': '광물', 'unit': '$/톤',
               'query': 'LME 니켈 가격'},
    'iron_ore': {'name': '철광석', 'category': '광물', 'unit': '$/톤',
                 'query': '철광석 가격 오늘'},
    'coal': {'name': '유연탄', 'category': '광물', 'unit': '$/톤',
             'query': '호주 유연탄 가격 Newcastle'},
    'lithium': {'name': '리튬', 'category': '광물', 'unit': '$/kg',
                'query': '리튬 카보네이트 가격'},
    'rice': {'name': '쌀', 'category': '농산물', 'unit': '$/톤',
             'query': '쌀 국제 가격 CBOT'},
    'scfi': {'name': 'SCFI', 'category': '운임지수', 'unit': '',
             'query': 'SCFI 상하이 컨테이너 운임지수 최신'},
    'bdi': {'name': 'BDI', 'category': '운임지수', 'unit': '',
            'query': 'BDI 발틱운임지수 오늘'},
}

# ── 카테고리 출력 순서 ────────────────────────
CATEGORY_ORDER = [
    '미국지수', '환율', '미국국채', '유가',
    '안전자산', '광물', '농산물', '운임지수',
]


def format_price(price: float, unit: str) -> str:
    """가격을 단위에 맞게 포맷팅."""
    if price is None:
        return 'N/A'
    if unit == '원':
        return f'{price:,.0f}원'
    elif unit == '$':
        return f'${price:,.2f}'
    elif unit == '¢':
        return f'{price:,.2f}¢'
    elif unit == '%':
        return f'{price:.2f}%'
    elif unit == 'p':
        return f'{price:,.2f}p'
    elif unit in ('엔', '$/톤', '$/kg'):
        return f'{price:,.2f}{unit}'
    else:
        return f'{price:,.2f}'


def format_change(change_pct: float) -> str:
    """등락률 + 방향 아이콘 포맷팅."""
    if change_pct is None:
        return 'N/A'
    if change_pct > 0:
        return f'+{change_pct:.2f}% ↑'
    elif change_pct < 0:
        return f'{change_pct:.2f}% ↓'
    return '0.00% -'


def collect_yfinance_data(days: int = 5) -> dict:
    """yfinance 배치 다운로드로 17개 항목 수집.

    Args:
        days: 조회 기간 (최근 N 거래일, 등락률 계산용)

    Returns:
        {key: {name, category, price, change_pct, direction, unit, error}, ...}
    """
    results = {}
    ticker_list = [v['ticker'] for v in YFINANCE_TICKERS.values()]
    ticker_str = ' '.join(ticker_list)

    try:
        data = yf.download(ticker_str, period=f'{days}d',
                           group_by='ticker', progress=False)
    except Exception as e:
        logger.error(f"yfinance 배치 다운로드 실패: {e}")
        for key, info in YFINANCE_TICKERS.items():
            results[key] = {
                'name': info['name'], 'category': info['category'],
                'price': None, 'change_pct': None,
                'direction': '-', 'unit': info['unit'],
                'error': str(e),
            }
        return results

    for key, info in YFINANCE_TICKERS.items():
        ticker = info['ticker']
        try:
            if len(YFINANCE_TICKERS) == 1:
                close = data['Close']
            else:
                close = data[(ticker, 'Close')] if isinstance(data.columns, pd.MultiIndex) else data['Close']

            close = close.dropna()
            if len(close) < 2:
                raise ValueError(f"데이터 부족: {len(close)}일")

            last_close = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])
            change_pct = round((last_close - prev_close) / prev_close * 100, 2)
            direction = '↑' if change_pct > 0 else '↓' if change_pct < 0 else '-'

            results[key] = {
                'name': info['name'], 'category': info['category'],
                'price': round(last_close, 2), 'change_pct': change_pct,
                'direction': direction, 'unit': info['unit'],
                'error': None,
            }
        except Exception as e:
            logger.warning(f"[{key}] {ticker} 처리 실패: {e}")
            results[key] = {
                'name': info['name'], 'category': info['category'],
                'price': None, 'change_pct': None,
                'direction': '-', 'unit': info['unit'],
                'error': str(e),
            }

    return results


def collect_websearch_data(websearch_context: dict = None) -> dict:
    """WebSearch 컨텍스트에서 10개 항목 추출.

    Args:
        websearch_context: 외부 주입 데이터
            {key: {price: float, change_pct: float}, ...}

    Returns:
        {key: {name, category, price, change_pct, direction, unit, error}, ...}
    """
    results = {}

    for key, info in WEBSEARCH_ITEMS.items():
        if websearch_context and key in websearch_context:
            ctx = websearch_context[key]
            price = ctx.get('price')
            change_pct = ctx.get('change_pct')
            direction = '↑' if change_pct and change_pct > 0 else '↓' if change_pct and change_pct < 0 else '-'
            results[key] = {
                'name': info['name'], 'category': info['category'],
                'price': price, 'change_pct': change_pct,
                'direction': direction, 'unit': info['unit'],
                'error': None,
            }
        else:
            results[key] = {
                'name': info['name'], 'category': info['category'],
                'price': None, 'change_pct': None,
                'direction': '-', 'unit': info['unit'],
                'error': 'WebSearch 데이터 없음',
            }

    return results


def collect_all(websearch_context: dict = None) -> dict:
    """27개 항목 전체 수집 — yfinance + WebSearch 결합.

    Args:
        websearch_context: WebSearch 결과 외부 주입

    Returns:
        {
            'items': {key: item_dict, ...},
            'categories': {category: [items], ...},
            'summary': {total, success, failed, timestamp},
        }
    """
    yf_data = collect_yfinance_data()
    ws_data = collect_websearch_data(websearch_context)

    items = {}
    items.update(yf_data)
    items.update(ws_data)

    # 카테고리별 그룹핑
    categories = {}
    for cat in CATEGORY_ORDER:
        categories[cat] = []
    for key, item in items.items():
        cat = item['category']
        if cat in categories:
            categories[cat].append({**item, 'key': key})

    success = sum(1 for v in items.values() if v['error'] is None)
    failed = len(items) - success

    return {
        'items': items,
        'categories': categories,
        'summary': {
            'total': len(items),
            'success': success,
            'failed': failed,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        },
    }
