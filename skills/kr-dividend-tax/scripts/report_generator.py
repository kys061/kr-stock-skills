"""kr-dividend-tax: 세금 리포트 생성."""


class DividendTaxReportGenerator:
    """배당 세금 리포트 생성기."""

    def __init__(self):
        self._tax_summary = None
        self._account_allocations = None
        self._threshold_status = None
        self._optimization_tips = []

    def add_tax_summary(self, summary):
        """세금 요약 추가."""
        self._tax_summary = summary

    def add_account_allocations(self, allocations):
        """계좌 배치 추가."""
        self._account_allocations = allocations

    def add_threshold_status(self, status):
        """금융소득 기준 상태 추가."""
        self._threshold_status = status

    def add_optimization_tips(self, tips):
        """절세 팁 추가."""
        self._optimization_tips = tips

    def generate(self):
        """리포트 생성."""
        lines = []
        lines.append('=' * 50)
        lines.append('배당 세금 최적화 리포트')
        lines.append('=' * 50)
        lines.append('')

        if self._tax_summary:
            lines.append('## 세금 요약')
            s = self._tax_summary
            lines.append(f"  배당소득세: {s.get('dividend_tax', 0):>12,}원")
            lines.append(f"  거래세:     {s.get('transaction_tax', 0):>12,}원")
            lines.append(f"  양도소득세: {s.get('gains_tax', 0):>12,}원")
            lines.append(f"  종합과세:   {s.get('financial_income_tax', 0):>12,}원")
            lines.append(f"  ─────────────────────────")
            lines.append(f"  총 세금:    {s.get('total_tax', 0):>12,}원")
            lines.append(f"  세후 소득:  {s.get('net_income', 0):>12,}원")
            lines.append(f"  실효세율:   {s.get('effective_rate', 0):>11.1%}")
            lines.append('')

        if self._account_allocations:
            lines.append('## 계좌 배치 추천')
            allocs = self._account_allocations
            for a in allocs.get('allocations', []):
                lines.append(f"  {a['name']:>10s} → {a['recommended_account']:<15s} "
                             f"(절세 {a['tax_saved']:,}원)")
            lines.append(f"  총 예상 절세: {allocs.get('total_tax_saved', 0):,}원")
            lines.append('')

        if self._threshold_status:
            t = self._threshold_status
            lines.append('## 금융소득종합과세 관리')
            lines.append(f"  현재 금융소득: {t['current_income']:,}원")
            lines.append(f"  기준선:       {t['threshold']:,}원")
            lines.append(f"  잔여 여유:    {t['remaining']:,}원")
            lines.append(f"  위험 수준:    {t['risk_level']}")
            lines.append('')

        if self._optimization_tips:
            lines.append('## 절세 팁')
            for i, tip in enumerate(self._optimization_tips, 1):
                benefit = tip.get('potential_benefit', 0)
                benefit_str = f" (절세 {benefit:,}원)" if benefit else ""
                lines.append(f"  {i}. {tip['name']}{benefit_str}")
                lines.append(f"     {tip['description']}")
            lines.append('')

        return '\n'.join(lines)
