"""
kr-market-top-detector: JSON + Markdown 리포트 생성기.
"""

import json
import os
from datetime import datetime


COMPONENT_LABELS = {
    'distribution': '분배일 카운트',
    'leading_stock': '선도주 건전성',
    'defensive_rotation': '방어 섹터 로테이션',
    'breadth_divergence': '시장폭 다이버전스',
    'index_technical': '지수 기술적 조건',
    'sentiment': '센티먼트 & 투기',
    'foreign_flow': '외국인 수급',
}


class ReportGenerator:
    """천장 탐지 JSON + Markdown 리포트."""

    def __init__(self, output_dir: str = './output'):
        self.output_dir = output_dir

    @staticmethod
    def _get_timestamp() -> str:
        return datetime.now().strftime('%Y-%m-%d_%H%M%S')

    def generate(self, result: dict) -> dict:
        """리포트 생성.

        Args:
            result: {
                'analysis_date': str,
                'scored': {'composite_score', 'risk_zone', 'components', 'weights'},
                'details': dict (선택적 상세 데이터),
            }
        Returns:
            {'json_path', 'md_path', 'json_data', 'md_content'}
        """
        os.makedirs(self.output_dir, exist_ok=True)
        ts = self._get_timestamp()

        json_data = self._build_json(result)
        md_content = self._build_markdown(result)

        json_path = os.path.join(self.output_dir, f'kr_market_top_{ts}.json')
        md_path = os.path.join(self.output_dir, f'kr_market_top_{ts}.md')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return {
            'json_path': json_path,
            'md_path': md_path,
            'json_data': json_data,
            'md_content': md_content,
        }

    def _build_json(self, result: dict) -> dict:
        scored = result.get('scored', {})
        zone = scored.get('risk_zone', {})
        return {
            'skill': 'kr-market-top-detector',
            'analysis_date': result.get('analysis_date',
                                        datetime.now().strftime('%Y-%m-%d')),
            'composite_score': scored.get('composite_score', 0),
            'risk_zone': zone.get('name', 'Green'),
            'risk_zone_label': zone.get('label', '정상'),
            'risk_budget': zone.get('budget', '100%'),
            'action': zone.get('action', ''),
            'components': scored.get('components', {}),
            'weights': scored.get('weights', {}),
        }

    def _build_markdown(self, result: dict) -> str:
        date = result.get('analysis_date',
                          datetime.now().strftime('%Y-%m-%d'))
        scored = result.get('scored', {})
        zone = scored.get('risk_zone', {})
        components = scored.get('components', {})
        weights = scored.get('weights', {})

        lines = [
            '# 한국 시장 천장 탐지 리포트',
            '',
            f'> **분석일**: {date}',
            '> **방법론**: O\'Neil 분배일 + Minervini 선도주 + 외국인 수급',
            '',
            '---',
            '',
            '## 종합 결과',
            '',
            '| 항목 | 값 |',
            '|------|-----|',
            f'| **복합 점수** | **{scored.get("composite_score", 0)} / 100** |',
            f'| **리스크 존** | **{zone.get("name", "Green")}** '
            f'({zone.get("label", "정상")}) |',
            f'| **리스크 예산** | **{zone.get("budget", "100%")}** |',
            f'| **행동 지침** | {zone.get("action", "")} |',
            '',
            '---',
            '',
            '## 7-컴포넌트 상세',
            '',
            '| # | 컴포넌트 | 점수 | 가중치 | 기여 |',
            '|---|---------|:----:|:------:|:----:|',
        ]

        for i, (key, label) in enumerate(COMPONENT_LABELS.items(), 1):
            score = components.get(key, 0)
            weight = weights.get(key, 0)
            contribution = round(score * weight, 1)
            lines.append(
                f'| {i} | {label} | {score}/100 | {weight:.0%} '
                f'| {contribution} |'
            )

        lines.extend([
            '',
            '---',
            '',
            '## 리스크 존 가이드',
            '',
            '| 점수 | 존 | 리스크 예산 | 행동 |',
            '|:----:|-----|:---------:|------|',
            '| 0-20 | Green | 100% | 정상 운영 |',
            '| 21-40 | Yellow | 80-90% | 손절 강화, 진입 축소 |',
            '| 41-60 | Orange | 60-75% | 약한 포지션 이익실현 |',
            '| 61-80 | Red | 40-55% | 적극적 이익실현 |',
            '| 81-100 | Critical | 20-35% | 최대 방어, 헤지 |',
        ])

        return '\n'.join(lines) + '\n'
