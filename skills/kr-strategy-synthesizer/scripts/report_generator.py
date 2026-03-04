"""kr-strategy-synthesizer: 전략 통합 리포트 생성."""


class StrategySynthesizerReportGenerator:
    """전략 통합 리포트 생성기."""

    def __init__(self):
        self._conviction = None
        self._pattern = None
        self._allocation = None
        self._meta = None

    def add_conviction(self, data):
        """확신도 결과 추가."""
        self._conviction = data

    def add_pattern(self, data):
        """패턴 분류 결과 추가."""
        self._pattern = data

    def add_allocation(self, data):
        """자산 배분 결과 추가."""
        self._allocation = data

    def add_meta(self, meta):
        """리포트 메타 정보 추가."""
        self._meta = meta

    def generate(self):
        """리포트 생성."""
        lines = []
        lines.append('=' * 55)
        lines.append(' KR 전략 통합 합성 리포트')
        lines.append('=' * 55)
        lines.append('')

        if self._conviction:
            c = self._conviction
            lines.append(f'## 확신도: {c["score"]:.1f}/100 [{c["zone"]}]')
            lines.append('')

            # 컴포넌트별 점수
            lines.append('### 컴포넌트별 점수')
            components = c.get('components', {})
            for name, comp in components.items():
                score = comp.get('score', 0)
                bar_len = int(score / 5)
                bar = '█' * bar_len + '░' * (20 - bar_len)
                desc = comp.get('description', name)
                lines.append(f'  {desc:<20s} {bar} {score:.1f}')
            lines.append('')

            # 존 상세
            zd = c.get('zone_details', {})
            if zd:
                eq_range = zd.get('equity_range', (0, 0))
                lines.append(f'  주식 목표 비중: {eq_range[0]}-{eq_range[1]}%')
                lines.append(f'  일일 변동성 한도: {zd.get("daily_vol", 0):.4f}')
                lines.append(f'  최대 단일 종목: {zd.get("max_single_position", 0):.0%}')
            lines.append('')

        if self._pattern:
            p = self._pattern
            lines.append(f'## 시장 패턴: {p["pattern"]} ({p["name"]})')
            lines.append(f'  확신도: {p["confidence"]:.1f}%')
            lines.append(f'  원칙: "{p["principle"]}"')
            eq_range = p.get('equity_range', (0, 0))
            lines.append(f'  패턴 주식 비중: {eq_range[0]}-{eq_range[1]}%')
            lines.append('')

        if self._allocation:
            a = self._allocation
            lines.append('## 자산 배분 추천')
            lines.append(f'  주식:     {a["equity"]:>5.1f}%')
            lines.append(f'  채권:     {a["bonds"]:>5.1f}%')
            lines.append(f'  대체투자: {a["alternatives"]:>5.1f}%')
            lines.append(f'  현금:     {a["cash"]:>5.1f}%')
            lines.append(f'  ────────────────')
            total = a['equity'] + a['bonds'] + a['alternatives'] + a['cash']
            lines.append(f'  합계:     {total:>5.1f}%')
            lines.append(f'  최대 단일: {a["max_single"]:.0%}')
            lines.append('')

        if self._meta:
            m = self._meta
            lines.append('## 데이터 커버리지')
            lines.append(f'  로드: {len(m.get("loaded", []))} / {m.get("total_required", 8)}')
            if m.get('missing'):
                lines.append(f'  누락: {", ".join(m["missing"])}')
            if m.get('stale'):
                lines.append(f'  만료: {", ".join(m["stale"])}')
            lines.append('')

        return '\n'.join(lines)
