"""테마 탐지 JSON + Markdown 리포트 생성."""

import json
import os
from datetime import datetime


class ReportGenerator:
    """테마 탐지 리포트 생성기."""

    def __init__(self, output_dir: str = 'reports/'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, scored_themes: dict) -> dict:
        """JSON + Markdown 리포트 생성.

        Args:
            scored_themes: ThemeScorer.score_all()의 결과

        Returns:
            {'json_path': str, 'md_path': str}
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        date_str = datetime.now().strftime('%Y-%m-%d')

        # JSON
        json_data = {
            'date': date_str,
            'timestamp': timestamp,
            'themes': scored_themes,
            'summary': self._build_summary(scored_themes),
        }

        json_path = os.path.join(self.output_dir, f'kr_themes_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # Markdown
        md = self._generate_markdown(date_str, scored_themes)
        md_path = os.path.join(self.output_dir, f'kr_themes_{timestamp}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md)

        return {'json_path': json_path, 'md_path': md_path}

    def _build_summary(self, themes: dict) -> dict:
        """요약 통계."""
        bullish = [t for t in themes.values() if t['direction'] == 'Bullish']
        bearish = [t for t in themes.values() if t['direction'] == 'Bearish']
        avg_heat = sum(t['heat'] for t in themes.values()) / len(themes) if themes else 0

        return {
            'total_themes': len(themes),
            'bullish_count': len(bullish),
            'bearish_count': len(bearish),
            'neutral_count': len(themes) - len(bullish) - len(bearish),
            'avg_heat': round(avg_heat, 1),
            'hottest': max(themes.items(), key=lambda x: x[1]['heat'])[1]['name'] if themes else None,
            'coldest': min(themes.items(), key=lambda x: x[1]['heat'])[1]['name'] if themes else None,
        }

    def _generate_markdown(self, date: str, themes: dict) -> str:
        """Markdown 리포트."""
        summary = self._build_summary(themes)

        lines = [
            f"# 한국 테마 탐지 리포트",
            f"",
            f"**날짜**: {date}",
            f"**분석 테마**: {summary['total_themes']}개",
            f"**평균 Heat**: {summary['avg_heat']}",
            f"",
            f"---",
            f"",
            f"## 테마 대시보드",
            f"",
            f"| 테마 | Heat | 방향 | 라이프사이클 | 신뢰도 |",
            f"|------|:----:|:----:|:----------:|:------:|",
        ]

        # Heat 순 정렬
        sorted_themes = sorted(
            themes.items(),
            key=lambda x: x[1]['heat'],
            reverse=True,
        )

        direction_icon = {
            'Bullish': 'Bullish',
            'Bearish': 'Bearish',
            'Neutral': 'Neutral',
        }

        for theme_id, t in sorted_themes:
            lines.append(
                f"| {t['name']} | {t['heat']} | "
                f"{direction_icon.get(t['direction'], t['direction'])} | "
                f"{t['lifecycle']} | {t['confidence']} |"
            )

        # Bullish 테마 상세
        bullish = [(tid, t) for tid, t in sorted_themes if t['direction'] == 'Bullish']
        if bullish:
            lines.extend([
                f"",
                f"---",
                f"",
                f"## Bullish 테마 상세",
                f"",
            ])
            for tid, t in bullish:
                stats = t['stats']
                lines.extend([
                    f"### {t['name']} (Heat: {t['heat']}, {t['lifecycle']})",
                    f"- 1주 수익률: {stats['weighted_change_1w']:+.1f}%",
                    f"- 1개월 수익률: {stats['weighted_change_1m']:+.1f}%",
                    f"- 업트렌드 비율: {stats['uptrend_ratio']:.0f}%",
                    f"- 거래량 비율: {stats['avg_volume_ratio']:.2f}x",
                    f"- 종목수: {stats['stock_count']}개 (core: {stats['core_count']})",
                    f"",
                ])

        # Bearish 테마 상세
        bearish = [(tid, t) for tid, t in sorted_themes if t['direction'] == 'Bearish']
        if bearish:
            lines.extend([
                f"---",
                f"",
                f"## Bearish 테마 상세",
                f"",
            ])
            for tid, t in bearish:
                stats = t['stats']
                lines.extend([
                    f"### {t['name']} (Heat: {t['heat']}, {t['lifecycle']})",
                    f"- 1주 수익률: {stats['weighted_change_1w']:+.1f}%",
                    f"- 1개월 수익률: {stats['weighted_change_1m']:+.1f}%",
                    f"- 업트렌드 비율: {stats['uptrend_ratio']:.0f}%",
                    f"- 거래량 비율: {stats['avg_volume_ratio']:.2f}x",
                    f"",
                ])

        return '\n'.join(lines) + '\n'
