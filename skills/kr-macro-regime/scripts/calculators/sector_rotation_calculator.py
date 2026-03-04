"""
kr-macro-regime: 섹터 로테이션 계산기.
경기민감 vs 방어 업종 상대 성과.
"""


# KRX 업종코드
KR_CYCLICAL_SECTORS = ['1011', '1007', '1014']   # 운수장비, 철강금속, 건설
KR_DEFENSIVE_SECTORS = ['1016', '1001', '1005']   # 통신, 음식료, 의약품


def calc_relative_perf(cyclical_returns: list[float],
                       defensive_returns: list[float]) -> float:
    """경기민감 - 방어 상대 성과.

    Returns:
        양(+) = 경기민감 강세, 음(-) = 방어 강세
    """
    if not cyclical_returns or not defensive_returns:
        return 0.0
    cyc_avg = sum(cyclical_returns) / len(cyclical_returns)
    def_avg = sum(defensive_returns) / len(defensive_returns)
    return cyc_avg - def_avg


def classify_rotation(relative_perf: float,
                      threshold: float = 0.01) -> str:
    """상대 성과 → 분류.

    Args:
        relative_perf: 경기민감 - 방어 (소수)
        threshold: 임계값 (1%)
    Returns:
        'cyclical_leading' | 'defensive_leading' | 'mixed'
    """
    if relative_perf > threshold:
        return 'cyclical_leading'
    elif relative_perf < -threshold:
        return 'defensive_leading'
    return 'mixed'


def regime_signal(rotation: str) -> str:
    """로테이션 → 레짐 시그널."""
    mapping = {
        'cyclical_leading': 'Broadening',
        'defensive_leading': 'Contraction',
        'mixed': 'Transitional',
    }
    return mapping.get(rotation, 'Transitional')


class SectorRotationCalculator:
    """섹터 로테이션 분석."""

    def calculate(self, sector_returns: dict) -> dict:
        """경기민감/방어 상대 성과 분석.

        Args:
            sector_returns: {'1011': 0.05, '1007': 0.02, ...}
        Returns:
            {'cyclical_avg', 'defensive_avg', 'relative_perf',
             'rotation', 'regime_signal'}
        """
        cyc_rets = [sector_returns.get(s, 0.0) for s in KR_CYCLICAL_SECTORS]
        def_rets = [sector_returns.get(s, 0.0) for s in KR_DEFENSIVE_SECTORS]

        cyc_avg = sum(cyc_rets) / len(cyc_rets) if cyc_rets else 0.0
        def_avg = sum(def_rets) / len(def_rets) if def_rets else 0.0
        rel_perf = cyc_avg - def_avg

        rotation = classify_rotation(rel_perf)

        return {
            'cyclical_avg': round(cyc_avg, 4),
            'defensive_avg': round(def_avg, 4),
            'relative_perf': round(rel_perf, 4),
            'rotation': rotation,
            'regime_signal': regime_signal(rotation),
        }
