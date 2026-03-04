"""종목 → 테마 분류 및 테마 통계 계산.

kr_themes.yaml의 정의를 기반으로 테마별 통계 산출.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class ThemeClassifier:
    """테마 분류 및 통계 계산."""

    def classify(self, theme_data: dict) -> dict:
        """테마별 통계 계산.

        Args:
            theme_data: IndustryDataCollector.collect()의 결과

        Returns:
            {
                'ai_semiconductor': {
                    'name': 'AI/반도체',
                    'avg_change_1w': 2.1,
                    'avg_change_1m': 5.3,
                    'weighted_change_1w': 1.8,    # 시총 가중
                    'weighted_change_1m': 4.5,    # 시총 가중
                    'avg_volume_ratio': 1.35,
                    'uptrend_ratio': 75.0,
                    'breadth_5d': 60.0,           # 5일 양봉 비율
                    'stock_count': 4,
                    'core_count': 2,
                },
                ...
            }
        """
        results = {}

        for theme_id, data in theme_data.items():
            stocks = data.get('stocks', [])
            if not stocks:
                results[theme_id] = self._empty_stats(data['name'])
                continue

            results[theme_id] = self._calc_theme_stats(data['name'], stocks)

        return results

    def _calc_theme_stats(self, name: str, stocks: list) -> dict:
        """테마 통계 계산."""
        changes_1w = [s['change_1w'] for s in stocks]
        changes_1m = [s['change_1m'] for s in stocks]
        volume_ratios = [s['volume_ratio'] for s in stocks]
        above_200ma = [s['above_200ma'] for s in stocks]
        positive_5d = [s['positive_5d'] for s in stocks]
        market_caps = [s.get('market_cap', 1) for s in stocks]

        total = len(stocks)

        # 시총 가중 수익률
        total_cap = sum(market_caps) if sum(market_caps) > 0 else total
        if total_cap > 0 and sum(market_caps) > 0:
            w_1w = sum(c * m for c, m in zip(changes_1w, market_caps)) / total_cap
            w_1m = sum(c * m for c, m in zip(changes_1m, market_caps)) / total_cap
        else:
            w_1w = np.mean(changes_1w) if changes_1w else 0
            w_1m = np.mean(changes_1m) if changes_1m else 0

        # 업트렌드 비율
        uptrend_count = sum(1 for a in above_200ma if a)
        uptrend_ratio = uptrend_count / total * 100 if total > 0 else 0

        # 5일 양봉 비율 (breadth)
        avg_positive = np.mean(positive_5d) if positive_5d else 0
        breadth_5d = avg_positive / 5 * 100  # 0~100

        return {
            'name': name,
            'avg_change_1w': round(float(np.mean(changes_1w)), 2),
            'avg_change_1m': round(float(np.mean(changes_1m)), 2),
            'weighted_change_1w': round(float(w_1w), 2),
            'weighted_change_1m': round(float(w_1m), 2),
            'avg_volume_ratio': round(float(np.mean(volume_ratios)), 2),
            'uptrend_ratio': round(float(uptrend_ratio), 1),
            'breadth_5d': round(float(breadth_5d), 1),
            'stock_count': total,
            'core_count': sum(1 for s in stocks if s.get('role') == 'core'),
        }

    @staticmethod
    def _empty_stats(name: str) -> dict:
        """빈 통계."""
        return {
            'name': name,
            'avg_change_1w': 0, 'avg_change_1m': 0,
            'weighted_change_1w': 0, 'weighted_change_1m': 0,
            'avg_volume_ratio': 1.0, 'uptrend_ratio': 0,
            'breadth_5d': 0, 'stock_count': 0, 'core_count': 0,
        }
