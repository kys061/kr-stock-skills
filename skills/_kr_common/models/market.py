"""시장/지수 데이터 모델."""

from dataclasses import dataclass


@dataclass
class IndexInfo:
    """지수 정보."""
    code: str
    name: str
    close: float = 0.0
    change_pct: float = 0.0
    per: float = 0.0
    pbr: float = 0.0
    div_yield: float = 0.0
    date: str = ''

    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'close': self.close,
            'change_pct': self.change_pct,
            'per': self.per,
            'pbr': self.pbr,
            'div_yield': self.div_yield,
            'date': self.date,
        }


# 주요 지수 코드
INDEX_CODES = {
    'KOSPI': '0001',
    'KOSDAQ': '1001',
    'KOSPI200': '0028',
    'KRX300': '0043',
    'KOSDAQ150': '0177',
}

# 투자자 분류
INVESTOR_TYPES = {
    'detail': [
        '금융투자', '보험', '투신', '사모', '은행',
        '기타금융', '연기금', '기타법인', '개인',
        '외국인', '기타외국인',
    ],
    'summary': ['기관합계', '외국인', '개인'],
}
