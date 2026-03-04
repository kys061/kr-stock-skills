"""업트렌드 분석 JSON + Markdown 리포트 생성."""

import json
import os
from datetime import datetime


class ReportGenerator:
    """업트렌드 분석 리포트 생성기."""

    def __init__(self, output_dir: str = 'reports/'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def _get_date() -> str:
        """현재 날짜 문자열."""
        return datetime.now().strftime('%Y-%m-%d')

    def generate(self, sector_data: dict, score_data: dict,
                 trend: str, overall_ratio: float,
                 group_averages: dict = None) -> dict:
        """JSON + Markdown 리포트 생성.

        Returns:
            {'json_path': str, 'md_path': str}
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        date_str = datetime.now().strftime('%Y-%m-%d')

        # JSON 리포트
        json_data = {
            'date': date_str,
            'timestamp': timestamp,
            'overall_ratio': overall_ratio,
            'score': score_data,
            'sectors': sector_data,
            'group_averages': group_averages or {},
            'trend': trend,
        }

        json_path = os.path.join(self.output_dir, f'kr_uptrend_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # Markdown 리포트
        md = self._generate_markdown(
            date_str, sector_data, score_data, trend,
            overall_ratio, group_averages or {},
        )

        md_path = os.path.join(self.output_dir, f'kr_uptrend_{timestamp}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md)

        return {'json_path': json_path, 'md_path': md_path}

    def _generate_markdown(self, date: str, sector_data: dict,
                           score_data: dict, trend: str,
                           overall_ratio: float,
                           group_averages: dict) -> str:
        """Markdown 리포트 생성."""
        score = score_data['composite_score']
        zone = score_data['uptrend_zone']
        zone_kr = score_data['uptrend_zone_kr']
        exposure = score_data['equity_exposure']

        lines = [
            f"# 한국 업트렌드 분석 리포트",
            f"",
            f"**날짜**: {date}",
            f"**추세**: {trend}",
            f"",
            f"## 종합 점수: {score}/100 ({zone} / {zone_kr})",
            f"## 권장 노출도: {exposure}",
            f"## 전체 업트렌드 비율: {overall_ratio:.1f}%",
            f"",
            f"---",
            f"",
            f"## 컴포넌트 상세",
            f"",
            f"| 컴포넌트 | 점수 | 가중치 | 가중점수 | 판정 |",
            f"|----------|:----:|:-----:|:-------:|------|",
        ]

        for name, comp in score_data['components'].items():
            lines.append(
                f"| {name} | {comp['score']} | "
                f"{comp['weight']*100:.0f}% | "
                f"{comp['weighted']:.1f} | "
                f"{comp['detail']} |"
            )

        # 경고
        if score_data.get('warnings'):
            lines.extend([
                f"",
                f"## 경고 시스템",
                f"",
            ])
            for w in score_data['warnings']:
                lines.append(f"- **{w['description']}** ({w['penalty']:+d}점)")

        # 업종 히트맵
        lines.extend([
            f"",
            f"---",
            f"",
            f"## 업종 히트맵",
            f"",
            f"| 업종 | 그룹 | 업트렌드 비율 | 종목수 | 상태 |",
            f"|------|------|:------------:|:-----:|:----:|",
        ])

        # 비율 순 정렬
        sorted_sectors = sorted(
            sector_data.items(),
            key=lambda x: x[1]['ratio'],
            reverse=True,
        )

        for sector, sdata in sorted_sectors:
            ratio = sdata['ratio']
            if ratio >= 60:
                status = 'Strong'
            elif ratio >= 40:
                status = 'Moderate'
            else:
                status = 'Weak'

            lines.append(
                f"| {sector} | {sdata['group']} | "
                f"{ratio:.1f}% | "
                f"{sdata['uptrend']}/{sdata['total']} | "
                f"{status} |"
            )

        # 그룹 평균
        if group_averages:
            lines.extend([
                f"",
                f"## 그룹 평균",
                f"",
                f"| 그룹 | 평균 업트렌드 비율 |",
                f"|------|:----------------:|",
            ])
            for group, avg in sorted(group_averages.items(),
                                      key=lambda x: x[1], reverse=True):
                lines.append(f"| {group} | {avg:.1f}% |")

        return '\n'.join(lines) + '\n'
