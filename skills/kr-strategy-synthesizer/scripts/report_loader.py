"""kr-strategy-synthesizer: 업스트림 스킬 리포트 로더."""

import json
import os
import time


# ─── 리포트 설정 ───

REPORT_CONFIG = {
    'max_age_hours': 72,
    'required_skills': [
        'kr-market-breadth',
        'kr-uptrend-analyzer',
        'kr-market-top-detector',
        'kr-ftd-detector',
        'kr-macro-regime',
        'kr-theme-detector',
        'kr-vcp-screener',
        'kr-canslim-screener',
    ],
}

# ─── 스킬별 필수 필드 ───

REQUIRED_FIELDS = {
    'kr-market-breadth': ['breadth_score', 'above_ma200_pct'],
    'kr-uptrend-analyzer': ['uptrend_score', 'uptrend_ratio'],
    'kr-market-top-detector': ['top_risk_score', 'distribution_days'],
    'kr-ftd-detector': ['ftd_confirmed', 'rally_day'],
    'kr-macro-regime': ['regime', 'transition_probability'],
    'kr-theme-detector': ['bullish_themes', 'bearish_themes'],
    'kr-vcp-screener': ['vcp_candidates'],
    'kr-canslim-screener': ['canslim_candidates'],
}


def validate_report(report, skill_name):
    """리포트 유효성 검증.

    Args:
        report: dict, JSON으로 로드된 리포트.
        skill_name: str, 스킬 이름.

    Returns:
        bool: 필수 필드가 모두 존재하면 True.
    """
    if not isinstance(report, dict):
        return False

    required = REQUIRED_FIELDS.get(skill_name, [])
    for field in required:
        if field not in report:
            return False
    return True


def _is_report_fresh(file_path, max_age_hours):
    """리포트가 유효 기간 내인지 확인."""
    if not os.path.exists(file_path):
        return False
    mtime = os.path.getmtime(file_path)
    age_hours = (time.time() - mtime) / 3600
    return age_hours <= max_age_hours


def load_skill_reports(report_dir, max_age_hours=None):
    """업스트림 스킬 리포트 로드.

    Args:
        report_dir: str, 리포트 디렉토리 경로.
        max_age_hours: int, 최대 유효 시간 (기본 72h).

    Returns:
        dict: {skill_name: report_data, ..., '_meta': {loaded, missing, stale}}
    """
    if max_age_hours is None:
        max_age_hours = REPORT_CONFIG['max_age_hours']

    reports = {}
    loaded = []
    missing = []
    stale = []

    for skill in REPORT_CONFIG['required_skills']:
        file_path = os.path.join(report_dir, f'{skill}.json')

        if not os.path.exists(file_path):
            missing.append(skill)
            continue

        if not _is_report_fresh(file_path, max_age_hours):
            stale.append(skill)
            # Load anyway but mark as stale
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                if validate_report(data, skill):
                    data['_stale'] = True
                    reports[skill] = data
            except (json.JSONDecodeError, IOError):
                missing.append(skill)
            continue

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            if validate_report(data, skill):
                reports[skill] = data
                loaded.append(skill)
            else:
                missing.append(skill)
        except (json.JSONDecodeError, IOError):
            missing.append(skill)

    reports['_meta'] = {
        'loaded': loaded,
        'missing': missing,
        'stale': stale,
        'total_required': len(REPORT_CONFIG['required_skills']),
        'coverage': len(loaded) / len(REPORT_CONFIG['required_skills']),
    }

    return reports
