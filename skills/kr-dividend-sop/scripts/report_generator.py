"""kr-dividend-sop: SOP 리포트 생성."""


class DividendSOPReportGenerator:
    """배당 SOP 리포트 생성기."""

    def __init__(self):
        self.sections = []

    def add_screening_result(self, total: int, passed: int, results: list):
        lines = [
            f"## Step 1: 스크리닝 결과",
            f"- 전체 종목: {total}개",
            f"- 통과 종목: {passed}개 ({passed/total*100:.1f}%)" if total > 0 else "- 통과: 0개",
            "",
        ]
        for r in results[:20]:
            status = "PASS" if r.get('passed') else "FAIL"
            lines.append(f"  - [{status}] {r.get('name', 'N/A')}")
        self.sections.append('\n'.join(lines))

    def add_entry_scores(self, scores: list):
        lines = ["## Step 2: 진입 점수", ""]
        lines.append("| 종목 | 점수 | 등급 | 밸류 | 배당 | 재무 | 타이밍 |")
        lines.append("|------|:----:|:----:|:----:|:----:|:----:|:------:|")
        for s in scores:
            c = s.get('components', {})
            lines.append(
                f"| {s.get('name', 'N/A')} | {s.get('score', 0):.1f} | {s.get('grade', '-')} "
                f"| {c.get('valuation', 0):.0f} | {c.get('dividend_quality', 0):.0f} "
                f"| {c.get('financial_health', 0):.0f} | {c.get('timing', 0):.0f} |"
            )
        self.sections.append('\n'.join(lines))

    def add_hold_status(self, statuses: list):
        lines = ["## Step 3: 보유 상태", ""]
        for s in statuses:
            emoji = {'HEALTHY': 'OK', 'CAUTION': 'CAUTION',
                     'WARNING': 'WARNING', 'EXIT_SIGNAL': 'EXIT'}
            status_str = emoji.get(s['status'], s['status'])
            lines.append(f"- [{status_str}] {s.get('name', s.get('ticker', 'N/A'))}")
            for issue in s.get('issues', []):
                lines.append(f"  - {issue}")
        self.sections.append('\n'.join(lines))

    def add_calendar(self, calendar: list):
        lines = ["## Step 4: 배당 캘린더", ""]
        lines.append("| 종목 | 배당락일 | 기준일 | 지급 예상 | DPS |")
        lines.append("|------|---------|--------|----------|----:|")
        for c in calendar:
            lines.append(
                f"| {c.get('name', c.get('ticker', ''))} | {c['ex_date']} "
                f"| {c['record_date']} | {c['payment_start']}~{c['payment_end']} "
                f"| {c.get('dps', 0):,.0f}원 |"
            )
        self.sections.append('\n'.join(lines))

    def add_exit_alerts(self, alerts: list):
        lines = ["## Step 5: EXIT 알림", ""]
        if not alerts:
            lines.append("- 트리거 발생 없음")
        for a in alerts:
            lines.append(
                f"- [{a.get('severity', 'INFO')}] {a.get('ticker', 'N/A')}: "
                f"{a.get('detail', '')} → {a.get('action', 'N/A')}"
            )
        self.sections.append('\n'.join(lines))

    def generate(self) -> str:
        header = "# 배당 SOP 리포트\n\n"
        return header + '\n\n---\n\n'.join(self.sections)
