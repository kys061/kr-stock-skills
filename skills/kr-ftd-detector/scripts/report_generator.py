"""
kr-ftd-detector: FTD 탐지 리포트 생성기.
"""

import json
import os
from datetime import datetime


class ReportGenerator:
    """FTD 탐지 JSON + Markdown 리포트."""

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
                'kospi': dict (rally_tracker state),
                'kosdaq': dict (rally_tracker state),
                'ftd_result': dict (qualifier result) or None,
                'dual_ftd': bool,
            }
        Returns:
            {'json_path': str, 'md_path': str, 'json_data': dict, 'md_content': str}
        """
        os.makedirs(self.output_dir, exist_ok=True)
        ts = self._get_timestamp()

        json_data = self._build_json(result)
        md_content = self._build_markdown(result)

        json_path = os.path.join(self.output_dir, f'kr_ftd_{ts}.json')
        md_path = os.path.join(self.output_dir, f'kr_ftd_{ts}.md')

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
        ftd = result.get('ftd_result') or {}
        return {
            'skill': 'kr-ftd-detector',
            'analysis_date': result.get('analysis_date', self._get_date()),
            'kospi_state': result.get('kospi', {}).get('state', 'no_signal'),
            'kosdaq_state': result.get('kosdaq', {}).get('state', 'no_signal'),
            'is_ftd': ftd.get('is_ftd', False),
            'quality_score': ftd.get('quality_score', 0.0),
            'components': ftd.get('components', {}),
            'exposure': ftd.get('exposure', {}),
            'dual_ftd': result.get('dual_ftd', False),
        }

    def _build_markdown(self, result: dict) -> str:
        """Markdown 리포트 구축."""
        date = result.get('analysis_date', self._get_date())
        ftd = result.get('ftd_result') or {}
        kospi = result.get('kospi', {})
        kosdaq = result.get('kosdaq', {})

        is_ftd = ftd.get('is_ftd', False)
        quality = ftd.get('quality_score', 0.0)
        exposure = ftd.get('exposure', {})

        lines = [
            f'# 한국 FTD 탐지 리포트',
            f'',
            f'> **분석일**: {date}',
            f'> **방법론**: William O\'Neil FTD (KR Dual-Index)',
            f'',
            f'---',
            f'',
            f'## 종합 결과',
            f'',
            f'| 항목 | 값 |',
            f'|------|-----|',
            f'| **FTD 시그널** | **{"✅ 확인" if is_ftd else "❌ 없음"}** |',
            f'| 품질 점수 | {quality:.1f}/100 |',
            f'| 시그널 강도 | {exposure.get("name", "N/A")} |',
            f'| 노출 비율 | {exposure.get("exposure", "N/A")} |',
            f'| Dual FTD | {"✅ 양쪽 확인" if result.get("dual_ftd") else "단일/없음"} |',
            f'',
            f'---',
            f'',
            f'## 지수별 상태',
            f'',
            f'| 지수 | 상태 | 랠리 Day | 스윙 로우 |',
            f'|------|------|:--------:|:---------:|',
            f'| KOSPI | {kospi.get("state", "N/A")} | {kospi.get("rally_day", "-")} | {kospi.get("swing_low", "-")} |',
            f'| KOSDAQ | {kosdaq.get("state", "N/A")} | {kosdaq.get("rally_day", "-")} | {kosdaq.get("swing_low", "-")} |',
        ]

        if is_ftd and ftd.get('components'):
            comp = ftd['components']
            lines.extend([
                f'',
                f'---',
                f'',
                f'## FTD 품질 분석',
                f'',
                f'| 컴포넌트 | 점수 | 가중치 |',
                f'|---------|:----:|:------:|',
                f'| Volume Surge | {comp.get("volume_surge", 0):.0f} | 25% |',
                f'| Day Number | {comp.get("day_number", 0):.0f} | 15% |',
                f'| Gain Size | {comp.get("gain_size", 0):.0f} | 20% |',
                f'| Breadth Confirmation | {comp.get("breadth_confirmation", 0):.0f} | 20% |',
                f'| Foreign Flow | {comp.get("foreign_flow", 0):.0f} | 20% |',
            ])

        lines.extend([
            f'',
            f'---',
            f'',
            f'## 노출 가이드',
            f'',
            f'| 점수 | 시그널 | 노출 |',
            f'|:----:|--------|:----:|',
            f'| 80-100 | Strong FTD | 75-100% |',
            f'| 60-79 | Moderate FTD | 50-75% |',
            f'| 40-59 | Weak FTD | 25-50% |',
            f'| < 40 | No FTD | 0-25% |',
        ])

        return '\n'.join(lines) + '\n'
