"""kr-skill-reviewer 테스트."""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from auto_reviewer import (
    AUTO_AXIS_WEIGHTS,
    check_metadata, check_workflow_coverage, check_execution_safety,
    check_artifacts, check_test_health, run_auto_review,
)
from review_merger import (
    MERGE_WEIGHTS, REVIEW_GRADES, merge_reviews,
)
from report_generator import generate_review_report


# ═══════════════════════════════════════════════════════
# 1. 상수 테스트
# ═══════════════════════════════════════════════════════

class TestConstants:
    """상수 정의 검증."""

    def test_auto_axis_5_components(self):
        assert len(AUTO_AXIS_WEIGHTS) == 5

    def test_auto_axis_weights_sum_1(self):
        total = sum(v['weight'] for v in AUTO_AXIS_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_auto_axis_weights_match_design(self):
        assert AUTO_AXIS_WEIGHTS['metadata_use_case']['weight'] == 0.20
        assert AUTO_AXIS_WEIGHTS['workflow_coverage']['weight'] == 0.25
        assert AUTO_AXIS_WEIGHTS['execution_safety']['weight'] == 0.25
        assert AUTO_AXIS_WEIGHTS['supporting_artifacts']['weight'] == 0.10
        assert AUTO_AXIS_WEIGHTS['test_health']['weight'] == 0.20

    def test_merge_weights(self):
        assert MERGE_WEIGHTS['auto'] == 0.50
        assert MERGE_WEIGHTS['llm'] == 0.50

    def test_review_grades_4(self):
        assert len(REVIEW_GRADES) == 4
        assert REVIEW_GRADES['PRODUCTION_READY'] == 90
        assert REVIEW_GRADES['USABLE'] == 80
        assert REVIEW_GRADES['NOTABLE_GAPS'] == 70
        assert REVIEW_GRADES['HIGH_RISK'] == 0

    def test_each_component_has_3_checks(self):
        for name, config in AUTO_AXIS_WEIGHTS.items():
            assert len(config['checks']) == 3, f'{name} should have 3 checks'


# ═══════════════════════════════════════════════════════
# 2. 메타데이터 체크 테스트
# ═══════════════════════════════════════════════════════

class TestCheckMetadata:
    """메타데이터 체크 테스트."""

    def test_complete_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_md = os.path.join(tmpdir, 'SKILL.md')
            with open(skill_md, 'w') as f:
                f.write('# Test Skill\n## 사용 시점\n- 테스트\n## 관련 스킬\n- other')
            result = check_metadata(tmpdir)
            assert result['score'] == 100.0

    def test_missing_skill_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_metadata(tmpdir)
            assert result['score'] == 0.0
            assert len(result['findings']) > 0

    def test_partial_skill_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'SKILL.md'), 'w') as f:
                f.write('# Test Skill\nSome content without sections')
            result = check_metadata(tmpdir)
            assert 0 < result['score'] < 100


# ═══════════════════════════════════════════════════════
# 3. 워크플로우 체크 테스트
# ═══════════════════════════════════════════════════════

class TestCheckWorkflow:
    """워크플로우 커버리지 테스트."""

    def test_with_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'SKILL.md'), 'w') as f:
                f.write('# Skill\n```bash\npython run.py\n```')
            scripts_dir = os.path.join(tmpdir, 'scripts')
            os.makedirs(scripts_dir)
            with open(os.path.join(scripts_dir, 'run.py'), 'w') as f:
                f.write('def analyze(data) -> dict:\n    if data is None:\n        return {}\n    return data')
            result = check_workflow_coverage(tmpdir)
            assert result['score'] == 100.0

    def test_empty_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_workflow_coverage(tmpdir)
            assert result['score'] < 100


# ═══════════════════════════════════════════════════════
# 4. 실행 안전성 테스트
# ═══════════════════════════════════════════════════════

class TestCheckExecutionSafety:
    """실행 안전성 테스트."""

    def test_safe_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'SKILL.md'), 'w') as f:
                f.write('# Skill\n```bash\npython run.py\n```')
            scripts_dir = os.path.join(tmpdir, 'scripts')
            os.makedirs(scripts_dir)
            with open(os.path.join(scripts_dir, 'calc.py'), 'w') as f:
                f.write('THRESHOLD = 100\nMAX_ITEMS = 50\ndef calc():\n    pass')
            result = check_execution_safety(tmpdir)
            assert result['score'] >= 66

    def test_hardcoded_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'SKILL.md'), 'w') as f:
                f.write('# Skill\n```bash\npython run.py\n```')
            scripts_dir = os.path.join(tmpdir, 'scripts')
            os.makedirs(scripts_dir)
            with open(os.path.join(scripts_dir, 'run.py'), 'w') as f:
                f.write('path = "/home/user/data"\nresult = open(path)')
            result = check_execution_safety(tmpdir)
            assert len(result['findings']) > 0


# ═══════════════════════════════════════════════════════
# 5. 아티팩트 체크 테스트
# ═══════════════════════════════════════════════════════

class TestCheckArtifacts:
    """아티팩트 체크 테스트."""

    def test_complete_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scripts_dir = os.path.join(tmpdir, 'scripts')
            refs_dir = os.path.join(tmpdir, 'references')
            os.makedirs(scripts_dir)
            os.makedirs(refs_dir)
            with open(os.path.join(scripts_dir, 'calc.py'), 'w') as f:
                f.write('MY_CONSTANT = 42\ndef calc():\n    pass')
            with open(os.path.join(refs_dir, 'guide.md'), 'w') as f:
                f.write('# Guide')
            result = check_artifacts(tmpdir)
            assert result['score'] == 100.0

    def test_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_artifacts(tmpdir)
            assert result['score'] == 0.0


# ═══════════════════════════════════════════════════════
# 6. 테스트 건강도 테스트
# ═══════════════════════════════════════════════════════

class TestCheckTestHealth:
    """테스트 건강도 테스트."""

    def test_no_tests_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_test_health(tmpdir)
            assert result['score'] == 0

    def test_empty_tests_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'scripts', 'tests'))
            result = check_test_health(tmpdir)
            assert result['score'] == 0

    def test_real_skill_tests(self):
        # kr-stock-analysis의 실제 테스트로 확인
        skill_path = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                                  'kr-stock-analysis')
        if os.path.exists(skill_path):
            result = check_test_health(skill_path)
            assert result['score'] == 100.0
            assert result['pass_count'] > 0


# ═══════════════════════════════════════════════════════
# 7. 전체 Auto Review 테스트
# ═══════════════════════════════════════════════════════

class TestRunAutoReview:
    """전체 Auto Review 테스트."""

    def test_complete_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # SKILL.md
            with open(os.path.join(tmpdir, 'SKILL.md'), 'w') as f:
                f.write('# Skill\n## 사용 시점\n- test\n## 관련 스킬\n```bash\npython x.py\n```')
            # scripts/
            scripts_dir = os.path.join(tmpdir, 'scripts')
            os.makedirs(scripts_dir)
            with open(os.path.join(scripts_dir, 'calc.py'), 'w') as f:
                f.write('MY_CONST = 10\ndef calc(x) -> dict:\n    if x is None:\n        return {}\n    return {"v": x}')
            # references/
            refs_dir = os.path.join(tmpdir, 'references')
            os.makedirs(refs_dir)
            with open(os.path.join(refs_dir, 'guide.md'), 'w') as f:
                f.write('# Guide')
            # tests/ (empty, will get 0 for test_health)
            os.makedirs(os.path.join(scripts_dir, 'tests'))

            result = run_auto_review(tmpdir)
            assert 'score' in result
            assert 'components' in result
            assert len(result['components']) == 5
            # Without passing tests, score should be less than 100
            assert result['score'] < 100

    def test_returns_findings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_auto_review(tmpdir)
            assert isinstance(result['findings'], list)


# ═══════════════════════════════════════════════════════
# 8. 병합 테스트
# ═══════════════════════════════════════════════════════

class TestMergeReviews:
    """리뷰 병합 테스트."""

    def test_auto_only(self):
        auto = {'score': 85, 'findings': ['issue 1']}
        result = merge_reviews(auto)
        assert result['final_score'] == 85
        assert result['llm_score'] is None
        assert result['grade'] == 'USABLE'

    def test_auto_plus_llm(self):
        auto = {'score': 80, 'findings': []}
        llm = {'score': 90, 'findings': ['good structure']}
        result = merge_reviews(auto, llm)
        assert result['final_score'] == 85.0
        assert result['llm_score'] == 90

    def test_production_ready(self):
        auto = {'score': 95, 'findings': []}
        llm = {'score': 92, 'findings': []}
        result = merge_reviews(auto, llm)
        assert result['grade'] == 'PRODUCTION_READY'

    def test_high_risk(self):
        auto = {'score': 50, 'findings': ['many issues']}
        llm = {'score': 60, 'findings': ['poor quality']}
        result = merge_reviews(auto, llm)
        assert result['grade'] == 'HIGH_RISK'

    def test_custom_weights(self):
        auto = {'score': 100, 'findings': []}
        llm = {'score': 0, 'findings': []}
        result = merge_reviews(auto, llm, weights={'auto': 0.80, 'llm': 0.20})
        assert result['final_score'] == 80.0

    def test_improvements_merged(self):
        auto = {'score': 80, 'findings': ['auto issue']}
        llm = {'score': 85, 'findings': ['llm issue']}
        result = merge_reviews(auto, llm)
        assert len(result['improvements']) == 2
        sources = [i['source'] for i in result['improvements']]
        assert 'auto' in sources
        assert 'llm' in sources


# ═══════════════════════════════════════════════════════
# 9. 리포트 생성 테스트
# ═══════════════════════════════════════════════════════

class TestReportGenerator:
    """리포트 생성 테스트."""

    def test_basic_report(self):
        merged = {
            'final_score': 85.0,
            'grade': 'USABLE',
            'auto_score': 82.0,
            'llm_score': 88.0,
            'improvements': [
                {'source': 'auto', 'finding': '테스트 커버리지 부족'},
            ],
        }
        report = generate_review_report(merged, 'kr-stock-analysis')
        assert 'kr-stock-analysis' in report
        assert 'USABLE' in report
        assert '85.0' in report

    def test_report_without_llm(self):
        merged = {
            'final_score': 80.0,
            'grade': 'USABLE',
            'auto_score': 80.0,
            'llm_score': None,
            'improvements': [],
        }
        report = generate_review_report(merged)
        assert '미사용' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
