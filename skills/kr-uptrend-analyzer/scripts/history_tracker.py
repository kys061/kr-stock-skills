"""업트렌드 점수 히스토리 관리.

파일: ~/.cache/kr-stock-skills/uptrend_history.json
최대 30개 엔트리 유지.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_PATH = os.path.expanduser('~/.cache/kr-stock-skills/uptrend_history.json')
MAX_ENTRIES = 30


class HistoryTracker:
    """업트렌드 점수 히스토리 관리."""

    def __init__(self, filepath: str = None):
        self.filepath = filepath or DEFAULT_PATH
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def load(self) -> list:
        """히스토리 로드."""
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"히스토리 로드 실패: {e}")
            return []

    def save(self, entry: dict):
        """엔트리 추가. 최대 {MAX_ENTRIES}개 유지."""
        history = self.load()
        history.append(entry)
        if len(history) > MAX_ENTRIES:
            history = history[-MAX_ENTRIES:]

        with open(self.filepath, 'w') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def get_trend(self, market: str = None) -> str:
        """최근 5회 점수 기반 추세 판단.

        Returns:
            'improving' | 'deteriorating' | 'stable' | 'insufficient'
        """
        history = self.load()
        if market:
            history = [h for h in history if h.get('market') == market]

        if len(history) < 3:
            return 'insufficient'

        recent = [h['composite_score'] for h in history[-5:]]
        if len(recent) < 3:
            return 'insufficient'

        # 선형 회귀 기울기
        x = list(range(len(recent)))
        mean_x = sum(x) / len(x)
        mean_y = sum(recent) / len(recent)
        slope = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, recent))
        denom = sum((xi - mean_x) ** 2 for xi in x)

        if denom == 0:
            return 'stable'

        slope = slope / denom

        if slope > 2:
            return 'improving'
        elif slope < -2:
            return 'deteriorating'
        return 'stable'

    def get_overall_ratio_history(self, market: str = None) -> list:
        """전체 업트렌드 비율 히스토리."""
        history = self.load()
        if market:
            history = [h for h in history if h.get('market') == market]
        return [h.get('overall_ratio', 0) for h in history]

    def get_score_history(self, market: str = None) -> list:
        """종합 점수 히스토리."""
        history = self.load()
        if market:
            history = [h for h in history if h.get('market') == market]
        return [h.get('composite_score', 0) for h in history]
