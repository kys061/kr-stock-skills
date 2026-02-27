"""재무 데이터 모델."""

from dataclasses import dataclass


@dataclass
class FinancialStatement:
    """재무제표 요약."""
    ticker: str
    year: int
    report_type: str = 'annual'  # annual, semi, q1, q3
    revenue: float = 0.0
    operating_income: float = 0.0
    net_income: float = 0.0
    total_assets: float = 0.0
    total_equity: float = 0.0
    total_debt: float = 0.0
    operating_cash_flow: float = 0.0

    @property
    def operating_margin(self) -> float:
        if self.revenue > 0:
            return (self.operating_income / self.revenue) * 100
        return 0.0

    @property
    def net_margin(self) -> float:
        if self.revenue > 0:
            return (self.net_income / self.revenue) * 100
        return 0.0

    @property
    def roe(self) -> float:
        if self.total_equity > 0:
            return (self.net_income / self.total_equity) * 100
        return 0.0

    @property
    def debt_ratio(self) -> float:
        if self.total_equity > 0:
            return (self.total_debt / self.total_equity) * 100
        return 0.0

    def to_dict(self) -> dict:
        return {
            'ticker': self.ticker,
            'year': self.year,
            'report_type': self.report_type,
            'revenue': self.revenue,
            'operating_income': self.operating_income,
            'net_income': self.net_income,
            'total_assets': self.total_assets,
            'total_equity': self.total_equity,
            'total_debt': self.total_debt,
            'operating_cash_flow': self.operating_cash_flow,
            'operating_margin': self.operating_margin,
            'net_margin': self.net_margin,
            'roe': self.roe,
            'debt_ratio': self.debt_ratio,
        }


@dataclass
class DividendInfo:
    """배당 정보."""
    ticker: str
    dividend_per_share: float = 0.0
    dividend_yield: float = 0.0
    payout_ratio: float = 0.0
    ex_date: str = ''
    pay_date: str = ''

    def to_dict(self) -> dict:
        return {
            'ticker': self.ticker,
            'dividend_per_share': self.dividend_per_share,
            'dividend_yield': self.dividend_yield,
            'payout_ratio': self.payout_ratio,
            'ex_date': self.ex_date,
            'pay_date': self.pay_date,
        }
