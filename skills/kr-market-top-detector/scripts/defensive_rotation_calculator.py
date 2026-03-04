"""
kr-market-top-detector: 방어 vs 성장 섹터 로테이션 계산기.
KRX 업종지수 기반.
"""


# KRX 업종코드
KR_DEFENSIVE_SECTORS = ['1013', '1001', '1005']  # 전기가스, 음식료, 의약품
KR_GROWTH_SECTORS = ['1009', '1021', '1012']     # 전기전자, 서비스, 유통


def calc_relative_performance(defensive_returns: list[float],
                              growth_returns: list[float]) -> float:
    """방어 - 성장 상대 성과.

    Args:
        defensive_returns: 방어 섹터 수익률 리스트
        growth_returns: 성장 섹터 수익률 리스트
    Returns:
        상대 성과 (양수 = 방어 outperform)
    """
    if not defensive_returns or not growth_returns:
        return 0.0
    def_avg = sum(defensive_returns) / len(defensive_returns)
    gro_avg = sum(growth_returns) / len(growth_returns)
    return def_avg - gro_avg


def score_rotation(relative_perf: float) -> float:
    """상대 성과 → 점수 (0-100).

    | 상대 성과 | 점수 |
    |:--------:|:----:|
    | < -3% | 0-10 |
    | -3~0% | 10-30 |
    | 0~+2% | 30-50 |
    | +2~+5% | 50-75 |
    | > +5% | 75-100 |
    """
    pct = relative_perf * 100  # 소수점 → %

    if pct < -3.0:
        return max(0.0, 10.0 + (pct + 3.0) * 3.3)  # 하한 0
    elif pct < 0.0:
        return 10.0 + (pct + 3.0) / 3.0 * 20.0  # 10→30
    elif pct < 2.0:
        return 30.0 + pct / 2.0 * 20.0  # 30→50
    elif pct < 5.0:
        return 50.0 + (pct - 2.0) / 3.0 * 25.0  # 50→75
    else:
        return min(100.0, 75.0 + (pct - 5.0) * 5.0)  # 75→100


class DefensiveRotationCalculator:
    """방어 vs 성장 섹터 로테이션 계산."""

    def calculate(self, sector_returns: dict) -> dict:
        """업종별 수익률 → 상대 성과.

        Args:
            sector_returns: {'1013': 0.02, '1001': 0.01, ...}
        Returns:
            {'defensive_avg', 'growth_avg', 'relative_performance'}
        """
        def_rets = [sector_returns.get(s, 0.0) for s in KR_DEFENSIVE_SECTORS]
        gro_rets = [sector_returns.get(s, 0.0) for s in KR_GROWTH_SECTORS]

        def_avg = sum(def_rets) / len(def_rets) if def_rets else 0.0
        gro_avg = sum(gro_rets) / len(gro_rets) if gro_rets else 0.0

        return {
            'defensive_avg': def_avg,
            'growth_avg': gro_avg,
            'relative_performance': def_avg - gro_avg,
        }

    def score(self, rotation: dict) -> float:
        """상대 성과 → 점수(0-100)."""
        return score_rotation(rotation.get('relative_performance', 0.0))
