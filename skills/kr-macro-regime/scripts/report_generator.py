"""
kr-macro-regime: JSON + Markdown 리포트 생성기.
"""

import json
import os
from datetime import datetime


COMPONENT_LABELS = {
    'concentration': '시장 집중도',
    'yield_curve': '금리 곡선',
    'credit': '신용 환경',
    'size_factor': '사이즈 팩터',
    'equity_bond': '주식-채권 관계',
    'sector_rotation': '섹터 로테이션',
}


class ReportGenerator:
    """매크로 레짐 JSON + Markdown 리포트."""

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
                'classified': {
                    'regime', 'confidence', 'votes',
                    'transition_probs', 'strategic_implication', 'components',
                },
            }
        Returns:
            {'json_path', 'md_path', 'json_data', 'md_content'}
        """
        os.makedirs(self.output_dir, exist_ok=True)
        ts = self._get_timestamp()

        json_data = self._build_json(result)
        md_content = self._build_markdown(result)

        json_path = os.path.join(self.output_dir, f'kr_macro_regime_{ts}.json')
        md_path = os.path.join(self.output_dir, f'kr_macro_regime_{ts}.md')

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
        classified = result.get('classified', {})
        return {
            'skill': 'kr-macro-regime',
            'analysis_date': result.get('analysis_date',
                                        datetime.now().strftime('%Y-%m-%d')),
            'regime': classified.get('regime', 'Transitional'),
            'confidence': classified.get('confidence', 0),
            'votes': classified.get('votes', {}),
            'transition_probs': classified.get('transition_probs', {}),
            'strategic_implication': classified.get('strategic_implication', ''),
        }

    def _build_markdown(self, result: dict) -> str:
        date = result.get('analysis_date',
                          datetime.now().strftime('%Y-%m-%d'))
        classified = result.get('classified', {})
        components = classified.get('components', {})
        votes = classified.get('votes', {})
        trans = classified.get('transition_probs', {})

        lines = [
            '# 한국 매크로 레짐 리포트',
            '',
            f'> **분석일**: {date}',
            '> **방법론**: 6-컴포넌트 크로스에셋 비율 분석 (6M/12M SMA)',
            '',
            '---',
            '',
            '## 현재 레짐',
            '',
            '| 항목 | 값 |',
            '|------|-----|',
            f'| **레짐** | **{classified.get("regime", "Transitional")}** |',
            f'| **확신도** | {classified.get("confidence", 0):.1%} |',
            f'| **전략** | {classified.get("strategic_implication", "")} |',
            '',
            '---',
            '',
            '## 6-컴포넌트 시그널',
            '',
            '| # | 컴포넌트 | 가중치 | 레짐 시그널 |',
            '|---|---------|:------:|-----------|',
        ]

        from scorer import COMPONENT_WEIGHTS
        for i, (key, label) in enumerate(COMPONENT_LABELS.items(), 1):
            comp = components.get(key, {})
            weight = COMPONENT_WEIGHTS.get(key, 0)
            signal = comp.get('regime_signal', 'N/A')
            lines.append(f'| {i} | {label} | {weight:.0%} | {signal} |')

        lines.extend([
            '',
            '---',
            '',
            '## 레짐 투표 분포',
            '',
            '| 레짐 | 득표율 |',
            '|------|:------:|',
        ])

        for regime, vote in sorted(votes.items(),
                                    key=lambda x: x[1], reverse=True):
            lines.append(f'| {regime} | {vote:.1%} |')

        if trans:
            lines.extend([
                '',
                '---',
                '',
                '## 전환 확률',
                '',
                '| 대상 레짐 | 확률 |',
                '|----------|:----:|',
            ])
            for regime, prob in sorted(trans.items(),
                                        key=lambda x: x[1], reverse=True):
                lines.append(f'| {regime} | {prob:.1%} |')

        lines.extend([
            '',
            '---',
            '',
            '## 레짐 가이드',
            '',
            '| 레짐 | 전략 |',
            '|------|------|',
            '| Concentration | 대형 성장주 유지, 소형주 회피 |',
            '| Broadening | 소형/가치주 비중 확대 |',
            '| Contraction | 현금 확대, 방어 섹터 |',
            '| Inflationary | 실물자산, 에너지 |',
            '| Transitional | 포지션 축소, 관망 |',
        ])

        return '\n'.join(lines) + '\n'
