"""종목 데이터 모델."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StockPrice:
    """종목 시세 정보."""
    ticker: str
    name: str
    close: int
    open: int = 0
    high: int = 0
    low: int = 0
    volume: int = 0
    change_pct: float = 0.0
    market_cap: int = 0
    date: str = ''

    def to_dict(self) -> dict:
        return {
            'ticker': self.ticker,
            'name': self.name,
            'close': self.close,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'change_pct': self.change_pct,
            'market_cap': self.market_cap,
            'date': self.date,
        }


@dataclass
class StockFundamental:
    """종목 밸류에이션 정보."""
    ticker: str
    name: str = ''
    per: float = 0.0
    pbr: float = 0.0
    eps: float = 0.0
    div_yield: float = 0.0
    bps: float = 0.0
    roe: float = 0.0
    debt_ratio: float = 0.0

    def to_dict(self) -> dict:
        return {
            'ticker': self.ticker,
            'name': self.name,
            'per': self.per,
            'pbr': self.pbr,
            'eps': self.eps,
            'div_yield': self.div_yield,
            'bps': self.bps,
            'roe': self.roe,
            'debt_ratio': self.debt_ratio,
        }


@dataclass
class StockInfo:
    """종목 기본 정보."""
    ticker: str
    name: str
    market: str  # KOSPI, KOSDAQ
    sector: str = ''
    industry: str = ''

    def to_dict(self) -> dict:
        return {
            'ticker': self.ticker,
            'name': self.name,
            'market': self.market,
            'sector': self.sector,
            'industry': self.industry,
        }
