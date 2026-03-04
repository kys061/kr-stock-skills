"""kr-options-advisor: KOSPI200 옵션 Black-Scholes 가격결정 & 그릭스.

Usage:
    python black_scholes.py --spot 350 --strike 355 --dte 30 --vol 0.20 --type call
"""

import argparse
import math

# ─── KOSPI200 옵션 기본 상수 ───

KOSPI200_MULTIPLIER = 250_000      # 1포인트 = 25만원
KOSPI200_TICK_SIZE = 0.01          # 프리미엄 <3: 0.01pt, ≥3: 0.05pt
KOSPI200_TICK_VALUE = 2_500        # 0.01pt × 25만원

# ─── 금리 ───

KR_RISK_FREE_RATE = 0.035         # BOK 기준금리 3.5%

# ─── 변동성 ───

VKOSPI_DEFAULT = 0.20             # VKOSPI 기본값
HV_LOOKBACK = 90                  # 역사적 변동성 데이터 수집 기간
HV_WINDOW = 30                    # 역사적 변동성 계산 윈도우

# ─── ATM 판정 ───

ATM_TOLERANCE = 0.02              # ±2% 이내: ATM

# ─── 거래 정보 ───

TRADING_HOURS = (9, 0, 15, 45)    # 09:00-15:45 (KST)
SETTLEMENT = 'T+1'                # T+1 결제 (현금결제)
LAST_TRADING_DAY = '매월 2번째 목요일'

# ─── 18개 전략 ───

STRATEGIES = {
    'covered_call': {'legs': 2, 'category': 'income'},
    'cash_secured_put': {'legs': 1, 'category': 'income'},
    'poor_mans_covered_call': {'legs': 2, 'category': 'income'},
    'protective_put': {'legs': 2, 'category': 'protection'},
    'collar': {'legs': 3, 'category': 'protection'},
    'bull_call_spread': {'legs': 2, 'category': 'directional'},
    'bull_put_spread': {'legs': 2, 'category': 'directional'},
    'bear_call_spread': {'legs': 2, 'category': 'directional'},
    'bear_put_spread': {'legs': 2, 'category': 'directional'},
    'long_straddle': {'legs': 2, 'category': 'directional'},
    'long_strangle': {'legs': 2, 'category': 'directional'},
    'short_straddle': {'legs': 2, 'category': 'volatility'},
    'short_strangle': {'legs': 2, 'category': 'volatility'},
    'iron_condor': {'legs': 4, 'category': 'volatility'},
    'iron_butterfly': {'legs': 4, 'category': 'volatility'},
    'calendar_spread': {'legs': 2, 'category': 'advanced'},
    'diagonal_spread': {'legs': 2, 'category': 'advanced'},
    'ratio_spread': {'legs': 3, 'category': 'advanced'},
}

# ─── 그릭스 타겟 ───

GREEKS_TARGETS = {
    'delta': (-10, 10),
    'theta': 'positive',
    'vega_warning': 500,
}

# ─── 포지션 사이징 ───

POSITION_SIZING = {
    'risk_tolerance': 0.02,
}

# ─── IV Crush 모델 ───

IV_CRUSH_MODEL = {
    'pre_earnings_iv_premium': 1.5,
    'post_earnings_iv_drop': 0.625,
}


# ─── 표준정규분포 함수 ───

def _norm_cdf(x: float) -> float:
    """표준정규분포 누적분포함수 (근사)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """표준정규분포 확률밀도함수."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ─── d1, d2 계산 ───

def calc_d1_d2(spot: float, strike: float, t: float,
               vol: float, r: float) -> tuple:
    """d1, d2 계산.

    Args:
        spot: 기초자산 가격 (KOSPI200 지수)
        strike: 행사가
        t: 잔존일수 (연 단위)
        vol: 변동성 (연율)
        r: 무위험 이자율

    Returns:
        (d1, d2) 튜플
    """
    if t <= 0 or vol <= 0 or spot <= 0 or strike <= 0:
        return (0.0, 0.0)

    d1 = (math.log(spot / strike) + (r + 0.5 * vol ** 2) * t) / (vol * math.sqrt(t))
    d2 = d1 - vol * math.sqrt(t)
    return (d1, d2)


# ─── Black-Scholes 가격결정 ───

def bs_call_price(spot: float, strike: float, t: float,
                  vol: float, r: float = None) -> float:
    """Black-Scholes 콜 옵션 이론가.

    Args:
        spot: 기초자산 가격
        strike: 행사가
        t: 잔존기간 (연 단위)
        vol: 변동성
        r: 무위험 이자율 (None이면 KR 기본값)

    Returns:
        콜 옵션 이론가 (포인트)
    """
    if r is None:
        r = KR_RISK_FREE_RATE

    if t <= 0:
        return max(spot - strike, 0.0)

    d1, d2 = calc_d1_d2(spot, strike, t, vol, r)
    price = spot * _norm_cdf(d1) - strike * math.exp(-r * t) * _norm_cdf(d2)
    return round(price, 4)


def bs_put_price(spot: float, strike: float, t: float,
                 vol: float, r: float = None) -> float:
    """Black-Scholes 풋 옵션 이론가.

    Args:
        spot: 기초자산 가격
        strike: 행사가
        t: 잔존기간 (연 단위)
        vol: 변동성
        r: 무위험 이자율 (None이면 KR 기본값)

    Returns:
        풋 옵션 이론가 (포인트)
    """
    if r is None:
        r = KR_RISK_FREE_RATE

    if t <= 0:
        return max(strike - spot, 0.0)

    d1, d2 = calc_d1_d2(spot, strike, t, vol, r)
    price = strike * math.exp(-r * t) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)
    return round(price, 4)


def bs_price(spot: float, strike: float, t: float,
             vol: float, option_type: str = 'call',
             r: float = None) -> float:
    """Black-Scholes 옵션 이론가 (콜/풋 통합).

    Args:
        spot: 기초자산 가격
        strike: 행사가
        t: 잔존기간 (연 단위)
        vol: 변동성
        option_type: 'call' 또는 'put'
        r: 무위험 이자율

    Returns:
        옵션 이론가 (포인트)
    """
    if option_type == 'call':
        return bs_call_price(spot, strike, t, vol, r)
    else:
        return bs_put_price(spot, strike, t, vol, r)


# ─── 그릭스 계산 ───

def calc_greeks(spot: float, strike: float, t: float,
                vol: float, option_type: str = 'call',
                r: float = None) -> dict:
    """옵션 그릭스 계산.

    Args:
        spot: 기초자산 가격
        strike: 행사가
        t: 잔존기간 (연 단위)
        vol: 변동성
        option_type: 'call' 또는 'put'
        r: 무위험 이자율

    Returns:
        {'delta', 'gamma', 'theta', 'vega', 'rho'} dict
    """
    if r is None:
        r = KR_RISK_FREE_RATE

    if t <= 0 or vol <= 0:
        intrinsic = max(spot - strike, 0) if option_type == 'call' else max(strike - spot, 0)
        delta = 1.0 if option_type == 'call' and spot > strike else (
            -1.0 if option_type == 'put' and spot < strike else 0.0)
        return {
            'delta': delta,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'rho': 0.0,
        }

    d1, d2 = calc_d1_d2(spot, strike, t, vol, r)
    sqrt_t = math.sqrt(t)
    exp_rt = math.exp(-r * t)
    pdf_d1 = _norm_pdf(d1)

    # Gamma (동일 for call/put)
    gamma = pdf_d1 / (spot * vol * sqrt_t)

    # Vega (동일 for call/put, per 1% vol change → /100)
    vega = spot * sqrt_t * pdf_d1 / 100.0

    if option_type == 'call':
        delta = _norm_cdf(d1)
        theta = (-(spot * pdf_d1 * vol) / (2.0 * sqrt_t)
                 - r * strike * exp_rt * _norm_cdf(d2)) / 365.0
        rho = strike * t * exp_rt * _norm_cdf(d2) / 100.0
    else:
        delta = _norm_cdf(d1) - 1.0
        theta = (-(spot * pdf_d1 * vol) / (2.0 * sqrt_t)
                 + r * strike * exp_rt * _norm_cdf(-d2)) / 365.0
        rho = -strike * t * exp_rt * _norm_cdf(-d2) / 100.0

    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 6),
        'theta': round(theta, 4),
        'vega': round(vega, 4),
        'rho': round(rho, 4),
    }


# ─── 유틸리티 함수 ───

def dte_to_years(dte: int) -> float:
    """잔존일수를 연 단위로 변환."""
    return dte / 365.0


def classify_moneyness(spot: float, strike: float,
                       option_type: str = 'call') -> str:
    """옵션 머니니스 판정.

    Returns:
        'ITM', 'ATM', 'OTM'
    """
    if spot <= 0 or strike <= 0:
        return 'OTM'

    ratio = abs(spot - strike) / spot
    if ratio <= ATM_TOLERANCE:
        return 'ATM'

    if option_type == 'call':
        return 'ITM' if spot > strike else 'OTM'
    else:
        return 'ITM' if spot < strike else 'OTM'


def premium_to_krw(premium: float, contracts: int = 1) -> int:
    """프리미엄(포인트)을 원화로 변환.

    Args:
        premium: 프리미엄 (포인트)
        contracts: 계약 수

    Returns:
        원화 금액
    """
    return round(premium * KOSPI200_MULTIPLIER * contracts)


def tick_size_for_premium(premium: float) -> float:
    """프리미엄에 따른 호가 단위."""
    return 0.05 if premium >= 3.0 else KOSPI200_TICK_SIZE


def round_to_tick(premium: float) -> float:
    """호가 단위로 반올림."""
    tick = tick_size_for_premium(premium)
    return round(round(premium / tick) * tick, 2)


def calc_iv_crush(current_iv: float) -> dict:
    """IV Crush 시뮬레이션.

    Args:
        current_iv: 현재 내재변동성

    Returns:
        {'pre_earnings_iv', 'post_earnings_iv', 'crush_pct'}
    """
    pre = current_iv * IV_CRUSH_MODEL['pre_earnings_iv_premium']
    post = pre * IV_CRUSH_MODEL['post_earnings_iv_drop']
    crush_pct = (pre - post) / pre * 100 if pre > 0 else 0

    return {
        'pre_earnings_iv': round(pre, 4),
        'post_earnings_iv': round(post, 4),
        'crush_pct': round(crush_pct, 2),
    }


def calc_historical_volatility(prices: list, window: int = None) -> float:
    """역사적 변동성 계산.

    Args:
        prices: 종가 리스트 (최근 → 과거 순)
        window: 계산 윈도우 (None이면 기본값)

    Returns:
        연율 변동성
    """
    if window is None:
        window = HV_WINDOW

    if len(prices) < window + 1:
        return VKOSPI_DEFAULT

    returns = []
    for i in range(window):
        if prices[i + 1] > 0:
            returns.append(math.log(prices[i] / prices[i + 1]))

    if len(returns) < 2:
        return VKOSPI_DEFAULT

    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(252)

    return round(annual_vol, 4)


def calc_position_size(account_value: float, premium: float,
                       contracts_max: int = 100) -> dict:
    """포지션 사이징 계산.

    Args:
        account_value: 계좌 규모 (원)
        premium: 옵션 프리미엄 (포인트)
        contracts_max: 최대 계약 수

    Returns:
        {'max_contracts', 'required_capital', 'risk_pct'}
    """
    risk_amount = account_value * POSITION_SIZING['risk_tolerance']
    cost_per_contract = premium * KOSPI200_MULTIPLIER

    if cost_per_contract <= 0:
        return {'max_contracts': 0, 'required_capital': 0, 'risk_pct': 0}

    max_contracts = min(int(risk_amount / cost_per_contract), contracts_max)
    required_capital = max_contracts * cost_per_contract
    risk_pct = required_capital / account_value * 100 if account_value > 0 else 0

    return {
        'max_contracts': max_contracts,
        'required_capital': round(required_capital),
        'risk_pct': round(risk_pct, 2),
    }


def price_option(spot: float, strike: float, dte: int,
                 vol: float = None, option_type: str = 'call',
                 r: float = None) -> dict:
    """옵션 종합 분석 (가격 + 그릭스 + 머니니스).

    Args:
        spot: 기초자산 가격
        strike: 행사가
        dte: 잔존일수
        vol: 변동성 (None이면 VKOSPI 기본값)
        option_type: 'call' 또는 'put'
        r: 무위험 이자율

    Returns:
        종합 분석 dict
    """
    if vol is None:
        vol = VKOSPI_DEFAULT
    if r is None:
        r = KR_RISK_FREE_RATE

    t = dte_to_years(dte)
    price = bs_price(spot, strike, t, vol, option_type, r)
    greeks = calc_greeks(spot, strike, t, vol, option_type, r)
    moneyness = classify_moneyness(spot, strike, option_type)

    return {
        'spot': spot,
        'strike': strike,
        'dte': dte,
        'option_type': option_type,
        'volatility': vol,
        'risk_free_rate': r,
        'price': price,
        'price_krw': premium_to_krw(price),
        'moneyness': moneyness,
        'greeks': greeks,
        'tick_size': tick_size_for_premium(price),
    }


def main():
    parser = argparse.ArgumentParser(description='KOSPI200 옵션 BS 가격결정')
    parser.add_argument('--spot', type=float, required=True)
    parser.add_argument('--strike', type=float, required=True)
    parser.add_argument('--dte', type=int, required=True)
    parser.add_argument('--vol', type=float, default=VKOSPI_DEFAULT)
    parser.add_argument('--type', choices=['call', 'put'], default='call')
    args = parser.parse_args()

    result = price_option(args.spot, args.strike, args.dte, args.vol, args.type)

    print(f'[Option] {args.type.upper()} {args.strike}')
    print(f'  KOSPI200: {args.spot}')
    print(f'  이론가: {result["price"]:.4f}pt '
          f'({result["price_krw"]:,}원)')
    print(f'  머니니스: {result["moneyness"]}')
    print(f'  Greeks:')
    for k, v in result['greeks'].items():
        print(f'    {k}: {v}')


if __name__ == '__main__':
    main()
