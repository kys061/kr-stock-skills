"""daily-market-check 테스트."""

import pytest

from market_check import (
    judge_vix,
    judge_cnn_fg,
    judge_usdkrw,
    overall_judgment,
    format_value,
    format_change,
)


class TestJudgeVix:
    def test_normal(self):
        assert judge_vix(15.0) == "정상"
        assert judge_vix(19.9) == "정상"

    def test_caution(self):
        assert judge_vix(20.0) == "주의"
        assert judge_vix(34.9) == "주의"

    def test_warning(self):
        assert judge_vix(35.0) == "경고"
        assert judge_vix(44.9) == "경고"

    def test_extreme_fear(self):
        assert judge_vix(45.0) == "극공포"
        assert judge_vix(80.0) == "극공포"

    def test_boundary(self):
        assert judge_vix(0) == "정상"


class TestJudgeCnnFg:
    def test_greed(self):
        assert judge_cnn_fg(61) == "탐욕"
        assert judge_cnn_fg(90) == "탐욕"

    def test_neutral(self):
        assert judge_cnn_fg(40) == "중립"
        assert judge_cnn_fg(60) == "중립"

    def test_fear(self):
        assert judge_cnn_fg(20) == "공포"
        assert judge_cnn_fg(39) == "공포"

    def test_extreme_fear(self):
        assert judge_cnn_fg(19) == "극공포"
        assert judge_cnn_fg(0) == "극공포"


class TestJudgeUsdkrw:
    def test_normal(self):
        assert judge_usdkrw(1300) == "정상"
        assert judge_usdkrw(1349) == "정상"

    def test_caution(self):
        assert judge_usdkrw(1350) == "주의"
        assert judge_usdkrw(1400) == "주의"

    def test_warning(self):
        assert judge_usdkrw(1401) == "경고"
        assert judge_usdkrw(1500) == "경고"


class TestOverallJudgment:
    def test_normal(self):
        status, _ = overall_judgment(15.0, 55.0, 1300.0)
        assert status == "정상"

    def test_caution_vix(self):
        status, _ = overall_judgment(25.0, 55.0, 1300.0)
        assert status == "주의"

    def test_caution_usdkrw(self):
        status, _ = overall_judgment(15.0, 55.0, 1380.0)
        assert status == "주의"

    def test_caution_cnn(self):
        status, _ = overall_judgment(15.0, 30.0, 1300.0)
        assert status == "주의"

    def test_warning_vix(self):
        status, _ = overall_judgment(40.0, 55.0, 1300.0)
        assert status == "경고"

    def test_warning_cnn(self):
        status, _ = overall_judgment(15.0, 10.0, 1300.0)
        assert status == "경고"

    def test_warning_usdkrw(self):
        status, _ = overall_judgment(15.0, 55.0, 1450.0)
        assert status == "경고"

    def test_danger_multiple_extremes(self):
        status, _ = overall_judgment(50.0, 10.0, 1450.0)
        assert status == "위험"

    def test_cnn_none(self):
        status, _ = overall_judgment(15.0, None, 1300.0)
        assert status == "정상"

    def test_cnn_none_with_vix_warning(self):
        status, _ = overall_judgment(40.0, None, 1300.0)
        assert status == "경고"


class TestFormatValue:
    def test_vix(self):
        assert format_value("VIX", 18.52) == "18.52"

    def test_kospi(self):
        assert format_value("KOSPI", 2650.31) == "2,650.31"

    def test_sp500(self):
        assert format_value("S&P 500", 5123.45) == "5,123.45"

    def test_ewy(self):
        assert format_value("EWY", 55.32) == "$55.32"

    def test_usdkrw(self):
        assert format_value("USD/KRW", 1365.50) == "1,365.50"


class TestFormatChange:
    def test_positive(self):
        assert format_change(1.23) == "+1.23%"

    def test_negative(self):
        assert format_change(-0.85) == "-0.85%"

    def test_zero(self):
        assert format_change(0.0) == "+0.00%"
