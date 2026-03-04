"""kr-dividend-monitor: 모니터링 리포트 생성."""


class DividendMonitorReportGenerator:
    """배당 모니터링 리포트 생성기."""

    def __init__(self):
        self.sections = []

    def add_trigger_summary(self, triggers_by_stock: dict):
        lines = ["## 트리거 감지 요약", ""]
        if not triggers_by_stock:
            lines.append("- 감지된 트리거 없음")
        for ticker, triggers in triggers_by_stock.items():
            for t in triggers:
                severity = t.get('severity', 'INFO')
                lines.append(
                    f"- [{severity}] {ticker}: {t.get('detail', 'N/A')}")
        self.sections.append('\n'.join(lines))

    def add_state_changes(self, changes: list):
        lines = ["## 상태 변경", ""]
        if not changes:
            lines.append("- 상태 변경 없음")
        for c in changes:
            lines.append(
                f"- {c.get('ticker', 'N/A')}: {c.get('prev_state', '?')} "
                f"→ {c.get('new_state', '?')}")
        self.sections.append('\n'.join(lines))

    def add_safety_scores(self, scores: list):
        lines = ["## 배당 안전성 점수", ""]
        lines.append("| 종목 | 점수 | 등급 | 배당성향 | 실적 | 이력 | 부채 |")
        lines.append("|------|:----:|:----:|:-------:|:----:|:----:|:----:|")
        for s in scores:
            c = s.get('components', {})
            lines.append(
                f"| {s.get('name', 'N/A')} | {s.get('score', 0):.0f} "
                f"| {s.get('grade', '-')} | {c.get('payout_ratio', 0):.0f} "
                f"| {c.get('earnings_stability', 0):.0f} "
                f"| {c.get('dividend_history', 0):.0f} "
                f"| {c.get('debt_health', 0):.0f} |")
        self.sections.append('\n'.join(lines))

    def generate(self) -> str:
        header = "# 배당 모니터링 리포트\n\n"
        return header + '\n\n---\n\n'.join(self.sections)
