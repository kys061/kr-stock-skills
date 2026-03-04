"""
kr-bubble-detector: 버블 탐지 리포트 생성기.
JSON + Markdown 리포트 출력.
"""

import json
import os
from datetime import datetime


class ReportGenerator:
    """버블 탐지 JSON + Markdown 리포트."""

    def __init__(self, output_dir: str = './output'):
        self.output_dir = output_dir

    @staticmethod
    def _get_date() -> str:
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def _get_timestamp() -> str:
        return datetime.now().strftime('%Y-%m-%d_%H%M%S')

    def generate(self, result: dict) -> dict:
        """리포트 생성.

        Args:
            result: {
                'analysis_date': str,
                'quantitative': {'scores': dict, 'total': int},
                'qualitative': {'adjustments': dict, 'total': int},
                'final': {'final_score': int, 'risk_zone': dict, ...},
            }
        Returns:
            {'json_path': str, 'md_path': str, 'json_data': dict, 'md_content': str}
        """
        os.makedirs(self.output_dir, exist_ok=True)
        ts = self._get_timestamp()

        json_data = self._build_json(result)
        md_content = self._build_markdown(result)

        json_path = os.path.join(self.output_dir, f'kr_bubble_{ts}.json')
        md_path = os.path.join(self.output_dir, f'kr_bubble_{ts}.md')

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
        """JSON 데이터 구축."""
        final = result.get('final', {})
        zone = final.get('risk_zone', {})
        return {
            'skill': 'kr-bubble-detector',
            'analysis_date': result.get('analysis_date', self._get_date()),
            'framework': 'Minsky/Kindleberger v2.1 (KR)',
            'quantitative': result.get('quantitative', {}),
            'qualitative': result.get('qualitative', {}),
            'final_score': final.get('final_score', 0),
            'max_possible': 15,
            'risk_zone': zone.get('name', 'Normal'),
            'risk_zone_label': zone.get('label', '정상'),
            'risk_budget': zone.get('budget', '100%'),
        }

    def _build_markdown(self, result: dict) -> str:
        """Markdown 리포트 구축."""
        date = result.get('analysis_date', self._get_date())
        final = result.get('final', {})
        zone = final.get('risk_zone', {})
        quant = result.get('quantitative', {})
        qual = result.get('qualitative', {})

        lines = [
            f'# 한국 시장 버블 탐지 리포트',
            f'',
            f'> **분석일**: {date}',
            f'> **프레임워크**: Minsky/Kindleberger v2.1 (KR)',
            f'',
            f'---',
            f'',
            f'## 종합 결과',
            f'',
            f'| 항목 | 값 |',
            f'|------|-----|',
            f'| **최종 점수** | **{final.get("final_score", 0)} / 15** |',
            f'| 정량 점수 | {quant.get("total", 0)} / 12 |',
            f'| 정성 조정 | +{qual.get("total", 0)} / 3 |',
            f'| **리스크 존** | **{zone.get("name", "Normal")}** ({zone.get("label", "정상")}) |',
            f'| **리스크 예산** | **{zone.get("budget", "100%")}** |',
            f'',
            f'---',
            f'',
            f'## Phase 2: 정량 지표 (6개)',
            f'',
            f'| # | 지표 | 점수 |',
            f'|---|------|:----:|',
        ]

        indicator_labels = {
            'vkospi_market': 'VKOSPI + 시장 위치',
            'credit_balance': '신용잔고 변화',
            'ipo_heat': 'IPO 과열도',
            'breadth_anomaly': '시장폭 이상',
            'price_acceleration': '가격 가속화',
            'per_band': 'KOSPI PER 밴드',
        }

        scores = quant.get('scores', {})
        for i, (key, label) in enumerate(indicator_labels.items(), 1):
            score = scores.get(key, 0)
            lines.append(f'| {i} | {label} | {score}/2 |')

        lines.append(f'| | **정량 합계** | **{quant.get("total", 0)}/12** |')

        lines.extend([
            f'',
            f'---',
            f'',
            f'## Phase 3: 정성 조정 (3개)',
            f'',
            f'| 조정 | 충족 | 점수 |',
            f'|------|:----:|:----:|',
        ])

        adj_labels = {
            'social_penetration': '사회적 침투도',
            'media_trend': '미디어/검색 트렌드',
            'valuation_disconnect': '밸류에이션 괴리',
        }

        adjustments = qual.get('adjustments', {})
        for key, label in adj_labels.items():
            score = adjustments.get(key, 0)
            check = '✅' if score else '❌'
            lines.append(f'| {label} | {check} | +{score} |')

        lines.append(f'| **정성 합계** | | **+{qual.get("total", 0)}/3** |')

        lines.extend([
            f'',
            f'---',
            f'',
            f'## 리스크 존 가이드',
            f'',
            f'| 점수 | 존 | 리스크 예산 | 행동 |',
            f'|:----:|-----|:---------:|------|',
            f'| 0-4 | Normal | 100% | 정상 투자 |',
            f'| 5-7 | Caution | 70-80% | 부분 이익실현 |',
            f'| 8-9 | Elevated Risk | 50-70% | 이익실현 강화 |',
            f'| 10-12 | Euphoria | 40-50% | 적극 이익실현 |',
            f'| 13-15 | Critical | 20-30% | 최대 방어 |',
        ])

        return '\n'.join(lines) + '\n'
