"""daily-market-check: 글로벌 매크로 6개 지표 조회 스크립트.

yfinance로 VIX, KOSPI, S&P500, EWY, USD/KRW 수치를 수집하고
상태 판정 + 종합 시장 판단을 출력한다.

CNN Fear & Greed Index는 yfinance 미제공 → 별도 입력 또는 WebSearch 필요.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance 미설치. pip install yfinance")
    sys.exit(1)


# ─── 지표 설정 ───

TICKERS = {
    "VIX": "^VIX",
    "KOSPI": "^KS11",
    "S&P 500": "^GSPC",
    "EWY": "EWY",
    "USD/KRW": "KRW=X",
}


# ─── 상태 판정 ───

def judge_vix(value: float) -> str:
    if value < 20:
        return "정상"
    elif value < 35:
        return "주의"
    elif value < 45:
        return "경고"
    else:
        return "극공포"


def judge_cnn_fg(value: float) -> str:
    if value > 60:
        return "탐욕"
    elif value >= 40:
        return "중립"
    elif value >= 20:
        return "공포"
    else:
        return "극공포"


def judge_usdkrw(value: float) -> str:
    if value < 1350:
        return "정상"
    elif value <= 1400:
        return "주의"
    else:
        return "경고"


def overall_judgment(vix: float, cnn_fg: Optional[float], usdkrw: float) -> tuple:
    """종합 판단: (상태, 근거)."""
    vix_status = judge_vix(vix)
    usdkrw_status = judge_usdkrw(usdkrw)
    cnn_status = judge_cnn_fg(cnn_fg) if cnn_fg is not None else "N/A"

    danger_count = 0
    warnings = []

    if vix >= 45:
        danger_count += 1
        warnings.append(f"VIX {vix:.1f} 극공포")
    elif vix >= 35:
        warnings.append(f"VIX {vix:.1f} 경고")
    elif vix >= 20:
        warnings.append(f"VIX {vix:.1f} 변동성 확대")

    if cnn_fg is not None:
        if cnn_fg < 20:
            danger_count += 1
            warnings.append(f"CNN F&G {cnn_fg:.0f} 극공포")
        elif cnn_fg < 40:
            warnings.append(f"CNN F&G {cnn_fg:.0f} 공포")

    if usdkrw > 1400:
        warnings.append(f"USD/KRW {usdkrw:,.0f} 경고")
    elif usdkrw > 1350:
        warnings.append(f"USD/KRW {usdkrw:,.0f} 원화약세")

    if danger_count >= 2:
        return "위험", "; ".join(warnings)
    elif vix >= 35 or (cnn_fg is not None and cnn_fg < 20) or usdkrw > 1400:
        return "경고", "; ".join(warnings)
    elif warnings:
        return "주의", "; ".join(warnings)
    else:
        return "정상", "전 지표 안정권"


# ─── 데이터 수집 ───

def fetch_market_data() -> dict:
    """yfinance로 5개 지표 수집."""
    results = {}
    symbols = list(TICKERS.values())
    tickers = yf.Tickers(" ".join(symbols))

    for name, symbol in TICKERS.items():
        try:
            ticker = tickers.tickers[symbol]
            hist = ticker.history(period="5d")
            if hist.empty:
                results[name] = {"error": "데이터 없음"}
                continue

            current = hist["Close"].iloc[-1]
            if len(hist) >= 2:
                prev = hist["Close"].iloc[-2]
                change_pct = (current - prev) / prev * 100
            else:
                change_pct = 0.0

            results[name] = {
                "value": round(current, 2),
                "change_pct": round(change_pct, 2),
                "date": str(hist.index[-1].date()),
            }

            # 상태 판정
            if name == "VIX":
                results[name]["status"] = judge_vix(current)
            elif name == "USD/KRW":
                results[name]["status"] = judge_usdkrw(current)
            else:
                results[name]["status"] = "-"

        except Exception as e:
            results[name] = {"error": str(e)}

    return results


def format_value(name: str, value: float) -> str:
    """지표별 포맷팅."""
    if name == "USD/KRW":
        return f"{value:,.2f}"
    elif name in ("KOSPI", "S&P 500"):
        return f"{value:,.2f}"
    elif name == "EWY":
        return f"${value:.2f}"
    elif name == "VIX":
        return f"{value:.2f}"
    return f"{value:.2f}"


def format_change(change_pct: float) -> str:
    """변화율 포맷팅."""
    sign = "+" if change_pct >= 0 else ""
    return f"{sign}{change_pct:.2f}%"


# ─── 출력 ───

def print_markdown(results: dict, cnn_fg: Optional[float] = None):
    """마크다운 테이블 출력."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"# Daily Market Check - {today}\n")
    print("| 지표 | 현재 수치 | 변화 | 상태 | 출처 |")
    print("|------|----------|------|------|------|")

    vix_val = None
    usdkrw_val = None

    for name in ["VIX", "CNN F&G", "KOSPI", "USD/KRW", "S&P 500", "EWY"]:
        if name == "CNN F&G":
            if cnn_fg is not None:
                status = judge_cnn_fg(cnn_fg)
                print(f"| CNN F&G | {cnn_fg:.0f} | - | {status} | WebSearch |")
            else:
                print("| CNN F&G | N/A | - | N/A | WebSearch 필요 |")
            continue

        data = results.get(name, {})
        if "error" in data:
            print(f"| {name} | ERROR | - | - | {data['error']} |")
            continue

        val = data["value"]
        change = format_change(data["change_pct"])
        status = data.get("status", "-")
        formatted = format_value(name, val)

        if name == "VIX":
            vix_val = val
        elif name == "USD/KRW":
            usdkrw_val = val

        print(f"| {name} | {formatted} | {change} | {status} | yfinance |")

    # 종합 판단
    print()
    if vix_val is not None and usdkrw_val is not None:
        judgment, reason = overall_judgment(vix_val, cnn_fg, usdkrw_val)
        print(f"> **종합 판단**: {judgment}")
        print(f"> **판단 근거**: {reason}")
    else:
        print("> **종합 판단**: 데이터 부족으로 판단 불가")


def print_json(results: dict, cnn_fg: Optional[float] = None):
    """JSON 출력."""
    vix_val = results.get("VIX", {}).get("value")
    usdkrw_val = results.get("USD/KRW", {}).get("value")

    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "indicators": results,
    }

    if cnn_fg is not None:
        output["indicators"]["CNN F&G"] = {
            "value": cnn_fg,
            "status": judge_cnn_fg(cnn_fg),
        }

    if vix_val and usdkrw_val:
        judgment, reason = overall_judgment(vix_val, cnn_fg, usdkrw_val)
        output["overall"] = {"status": judgment, "reason": reason}

    print(json.dumps(output, ensure_ascii=False, indent=2))


# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(description="Daily Market Check - 글로벌 매크로 6개 지표")
    parser.add_argument("--cnn-fg", type=float, default=None,
                        help="CNN Fear & Greed Index 수동 입력 (0-100)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="출력 형식 (default: markdown)")
    args = parser.parse_args()

    results = fetch_market_data()

    if args.format == "json":
        print_json(results, args.cnn_fg)
    else:
        print_markdown(results, args.cnn_fg)


if __name__ == "__main__":
    main()
