"""kr-stock-analysis: 분석 리포트 생성."""


class StockAnalysisReportGenerator:
    """종목 분석 리포트 생성기."""

    def __init__(self, ticker=None, name=None):
        self._ticker = ticker
        self._name = name
        self._fundamental = None
        self._technical = None
        self._supply_demand = None
        self._comprehensive = None

    def add_fundamental(self, data):
        """펀더멘털 분석 결과 추가."""
        self._fundamental = data

    def add_technical(self, data):
        """기술적 분석 결과 추가."""
        self._technical = data

    def add_supply_demand(self, data):
        """수급 분석 결과 추가."""
        self._supply_demand = data

    def add_comprehensive(self, data):
        """종합 분석 결과 추가."""
        self._comprehensive = data

    def generate(self):
        """리포트 생성."""
        lines = []
        header = f'{self._ticker} {self._name}' if self._name else (self._ticker or '종목')
        lines.append('=' * 55)
        lines.append(f' {header} 종합 분석 리포트')
        lines.append('=' * 55)
        lines.append('')

        if self._comprehensive:
            c = self._comprehensive
            lines.append(f'## 종합 등급: {c["grade"]} ({c["score"]:.1f}/100)')
            lines.append('')
            rec = c.get('recommendation', {})
            lines.append(f'  {rec.get("summary", "")}')
            if rec.get('strengths'):
                lines.append(f'  강점: {", ".join(rec["strengths"])}')
            if rec.get('weaknesses'):
                lines.append(f'  약점: {", ".join(rec["weaknesses"])}')
            lines.append('')

            lines.append('## 컴포넌트별 점수')
            for name, comp in c.get('components', {}).items():
                bar_len = int(comp['score'] / 5)
                bar = '█' * bar_len + '░' * (20 - bar_len)
                lines.append(f'  {name:<15s} {bar} {comp["score"]:.1f}')
            lines.append('')

        if self._fundamental:
            f = self._fundamental
            lines.append(f'## 펀더멘털 (점수: {f["score"]:.1f})')
            for group in ('valuation', 'profitability', 'growth', 'health'):
                group_data = f.get(group, {})
                if isinstance(group_data, dict):
                    data = group_data.get('data', {})
                    gscore = group_data.get('score', '-')
                    lines.append(f'  [{group}] score={gscore}')
                    for k, v in data.items():
                        if isinstance(v, float):
                            lines.append(f'    {k}: {v:.2f}')
                        else:
                            lines.append(f'    {k}: {v}')
            lines.append('')

        if self._technical:
            t = self._technical
            lines.append(f'## 기술적 분석 (점수: {t["score"]:.1f})')
            trend = t.get('trend', {})
            ma = trend.get('moving_averages', {})
            lines.append(f'  현재가: {trend.get("current_price", "-")}')
            for k, v in ma.items():
                lines.append(f'  {k}: {v}')

            momentum = t.get('momentum', {})
            lines.append(f'  RSI: {momentum.get("rsi", "-")}')
            macd = momentum.get('macd')
            if macd:
                lines.append(f'  MACD: {macd["macd"]}, Signal: {macd["signal"]}, '
                             f'Hist: {macd["histogram"]}')

            vol = t.get('volatility', {})
            bb = vol.get('bollinger')
            if bb:
                lines.append(f'  BB: upper={bb["upper"]}, middle={bb["middle"]}, '
                             f'lower={bb["lower"]}')
                lines.append(f'  %B: {bb["percent_b"]:.1f}')
            lines.append('')

        if self._supply_demand:
            s = self._supply_demand
            lines.append(f'## 수급 분석 (점수: {s["score"]:.1f})')
            lines.append(f'  시그널: {s["signal"]}')
            for investor in ('foreign', 'institution', 'individual'):
                inv_data = s.get(investor, {})
                flows = inv_data.get('flows', {})
                inv_score = inv_data.get('score', '-')
                flow_str = ', '.join(f'{p}일: {v:+,}' for p, v in sorted(flows.items()))
                lines.append(f'  {investor}: score={inv_score} ({flow_str})')
            lines.append('')

        return '\n'.join(lines)
