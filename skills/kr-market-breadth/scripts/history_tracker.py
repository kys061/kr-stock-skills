"""시장폭 점수 히스토리 관리.

파일: ~/.cache/kr-stock-skills/breadth_history.json
용도: 점수 추세 (개선중/악화중/안정) 판단
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_PATH = os.path.expanduser('~/.cache/kr-stock-skills/breadth_history.json')
MAX_ENTRIES = 30


class HistoryTracker:
    """점수 히스토리 관리."""

    def __init__(self, filepath: str = None):
        self.filepath = filepath or DEFAULT_HISTORY_PATH
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def load(self) -> list:
        """히스토리 로드."""
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"히스토리 로드 실패: {e}")
            return []

    def save(self, entry: dict):
        """히스토리에 엔트리 추가.

        Args:
            entry: {
                'date': str,
                'market': str,
                'composite_score': float,
                'breadth_raw': float,
                'health_zone': str,
            }
        """
        history = self.load()
        entry['timestamp'] = datetime.now().isoformat()
        history.append(entry)

        # 최대 엔트리 유지
        if len(history) > MAX_ENTRIES:
            history = history[-MAX_ENTRIES:]

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"히스토리 저장 실패: {e}")

    def get_trend(self, market: str = None) -> str:
        """최근 점수 추세 판단.

        Returns:
            'improving' / 'deteriorating' / 'stable' / 'insufficient'
        """
        history = self.load()
        if market:
            history = [h for h in history if h.get('market') == market]

        if len(history) < 3:
            return 'insufficient'

        recent = [h['composite_score'] for h in history[-5:]]
        diff = recent[-1] - recent[0]

        if diff > 5:
            return 'improving'
        elif diff < -5:
            return 'deteriorating'
        return 'stable'

    def get_breadth_raw_history(self, market: str = None) -> list:
        """Breadth Raw 히스토리 값 리스트 (MA 계산용)."""
        history = self.load()
        if market:
            history = [h for h in history if h.get('market') == market]
        return [h.get('breadth_raw', 0) for h in history]
