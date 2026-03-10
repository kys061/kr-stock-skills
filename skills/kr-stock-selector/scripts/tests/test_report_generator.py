"""report_generator.py 테스트."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from report_generator import (
    generate_report, build_header, build_summary,
    build_pass_table, build_condition_stats, build_watch_list,
    build_footer, save_report, _get_gap_values,
)


def _make_result(
    ticker: str = '005930',
    name: str = '삼성전자',
    all_pass: bool = True,
    pass_count: int = 5,
    market_cap: int = 400_000_000_000_000,
    conditions: dict = None,
    details: dict = None,
) -> dict:
    """테스트용 분석 결과 생성."""
    if conditions is None:
        conditions = {
            'ma_trend': True,
            'ma_alignment': True,
            'week52_low': True,
            'week52_high': True,
            'market_cap': True,
        }
    if details is None:
        details = {
            'ma_trend_days': 25,
            'sma50': 68000.0,
            'sma150': 65000.0,
            'sma200': 62000.0,
            'week52_low_pct': 0.45,
            'week52_high_pct': -0.08,
            'week52_low': 48000.0,
            'week52_high': 76000.0,
        }
    return {
        'ticker': ticker,
        'name': name,
        'market': 'KOSPI',
        'market_cap': market_cap,
        'close': 70000,
        'conditions': conditions,
        'details': details,
        'pass_count': pass_count,
        'all_pass': all_pass,
    }


class TestBuildHeader:
    """헤더 생성 테스트."""

    def test_header_format(self):
        header = build_header('2026-03-11', 'ALL')
        assert '주식종목선별 리포트' in header
        assert 'KOSPI+KOSDAQ' in header
        assert 'SCREENING' in header

    def test_header_market_filter(self):
        header = build_header('2026-03-11', 'KOSPI')
        assert 'KOSPI' in header


class TestBuildSummary:
    """요약 섹션 테스트."""

    def test_summary_counts(self):
        results = [_make_result(), _make_result(all_pass=False, pass_count=3)]
        summary = build_summary(results, universe_size=100)
        assert '100개' in summary
        assert '1개' in summary  # 1 passed

    def test_summary_zero(self):
        summary = build_summary([], universe_size=0)
        assert '0개' in summary


class TestBuildPassTable:
    """통과 종목 테이블 테스트."""

    def test_pass_table_sorted_by_mcap(self):
        """시가총액 내림차순 정렬."""
        r1 = _make_result(ticker='000660', name='SK하이닉스', market_cap=100e12)
        r2 = _make_result(ticker='005930', name='삼성전자', market_cap=400e12)
        table = build_pass_table([r1, r2])
        # 삼성전자(400조)가 먼저
        pos_samsung = table.find('005930')
        pos_skhynix = table.find('000660')
        assert pos_samsung < pos_skhynix

    def test_empty_pass(self):
        table = build_pass_table([])
        assert '통과 종목이 없습니다' in table

    def test_table_has_required_columns(self):
        table = build_pass_table([_make_result()])
        assert '종목코드' in table
        assert '종목명' in table
        assert '시총(억)' in table
        assert '52주대비저' in table


class TestBuildConditionStats:
    """조건별 통과율 테스트."""

    def test_stats_five_conditions(self):
        results = [_make_result()]
        stats = build_condition_stats(results)
        assert '조건 1' in stats
        assert '조건 5' in stats

    def test_stats_percentages(self):
        r1 = _make_result()
        r2 = _make_result(
            conditions={
                'ma_trend': False, 'ma_alignment': True,
                'week52_low': True, 'week52_high': True, 'market_cap': True,
            },
            all_pass=False, pass_count=4,
        )
        stats = build_condition_stats([r1, r2])
        assert '50.0%' in stats  # ma_trend: 1/2 = 50%
        assert '100.0%' in stats  # market_cap: 2/2 = 100%


class TestBuildWatchList:
    """Watch List 테스트."""

    def test_watch_list_4_of_5(self):
        """4/5 통과 종목 포함."""
        watch = _make_result(
            ticker='035420', name='NAVER',
            all_pass=False, pass_count=4,
            conditions={
                'ma_trend': False, 'ma_alignment': True,
                'week52_low': True, 'week52_high': True, 'market_cap': True,
            },
            details={'ma_trend_days': 17, 'sma50': 0, 'sma150': 0, 'sma200': 0,
                     'week52_low_pct': 0.35, 'week52_high_pct': -0.10,
                     'week52_low': 0, 'week52_high': 0},
        )
        result = build_watch_list([watch], min_pass=4)
        assert '035420' in result
        assert 'NAVER' in result
        assert '17일' in result

    def test_watch_list_excludes_5_of_5(self):
        """5/5 통과는 Watch List 아님."""
        result = build_watch_list([_make_result()])
        assert '해당 종목 없음' in result

    def test_watch_list_excludes_3_of_5(self):
        """3/5 통과는 Watch List 아님."""
        r = _make_result(all_pass=False, pass_count=3)
        result = build_watch_list([r])
        assert '해당 종목 없음' in result


class TestGetGapValues:
    """미충족 조건 수치 헬퍼 테스트."""

    def test_ma_trend_gap(self):
        current, need = _get_gap_values('ma_trend', {'ma_trend_days': 15})
        assert '15일' in current
        assert '20일' in need

    def test_week52_low_gap(self):
        current, need = _get_gap_values('week52_low', {'week52_low_pct': 0.25})
        assert '25.0%' in current
        assert '30.0%' in need


class TestSaveReport:
    """리포트 저장 테스트."""

    def test_save_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_report('# Test Report', date='2026-03-11', output_dir=tmpdir)
            assert os.path.exists(path)
            assert 'kr-stock-selector' in path
            assert '20260311' in path

    def test_save_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = '# 테스트 리포트\n내용'
            path = save_report(content, date='2026-03-11', output_dir=tmpdir)
            with open(path, 'r', encoding='utf-8') as f:
                assert f.read() == content


class TestGenerateReport:
    """통합 리포트 생성 테스트."""

    def test_full_report_structure(self):
        results = [
            _make_result(),
            _make_result(
                ticker='035420', name='NAVER', all_pass=False, pass_count=4,
                conditions={
                    'ma_trend': False, 'ma_alignment': True,
                    'week52_low': True, 'week52_high': True, 'market_cap': True,
                },
                details={'ma_trend_days': 17, 'sma50': 0, 'sma150': 0, 'sma200': 0,
                         'week52_low_pct': 0.35, 'week52_high_pct': -0.10,
                         'week52_low': 0, 'week52_high': 0},
            ),
        ]
        report = generate_report(results, universe_size=100, date='2026-03-11')

        assert '주식종목선별 리포트' in report
        assert '## 요약' in report
        assert '## 통과 종목' in report
        assert '## 조건별 통과율' in report
        assert '## Watch List' in report
        assert 'Generated by kr-stock-selector' in report
