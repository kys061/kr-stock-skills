"""kr-skill-reviewer: Auto Axis 리뷰 엔진."""

import os
import subprocess


# ─── Auto Axis 가중치 ───

AUTO_AXIS_WEIGHTS = {
    'metadata_use_case': {
        'weight': 0.20,
        'checks': ['skill_md_exists', 'use_case_defined', 'triggers_listed'],
    },
    'workflow_coverage': {
        'weight': 0.25,
        'checks': ['execution_steps', 'input_output_defined', 'error_handling'],
    },
    'execution_safety': {
        'weight': 0.25,
        'checks': ['command_examples', 'path_hygiene', 'reproducibility'],
    },
    'supporting_artifacts': {
        'weight': 0.10,
        'checks': ['scripts_exist', 'references_exist', 'constants_defined'],
    },
    'test_health': {
        'weight': 0.20,
        'checks': ['tests_exist', 'tests_pass', 'coverage_adequate'],
    },
}


def check_metadata(skill_path):
    """메타데이터 및 사용 시점 체크.

    Args:
        skill_path: str, 스킬 디렉토리 경로.

    Returns:
        dict: {score, findings}
    """
    findings = []
    checks_passed = 0
    total_checks = 3

    # 1. SKILL.md 존재
    skill_md = os.path.join(skill_path, 'SKILL.md')
    if os.path.exists(skill_md):
        checks_passed += 1
        content = _read_file(skill_md)

        # 2. 사용 시점 섹션
        if '사용 시점' in content or '## 사용' in content or 'When to use' in content.lower():
            checks_passed += 1
        else:
            findings.append('SKILL.md에 "사용 시점" 섹션 없음')

        # 3. 트리거/관련 스킬
        if '관련 스킬' in content or 'trigger' in content.lower() or '실행' in content:
            checks_passed += 1
        else:
            findings.append('SKILL.md에 트리거/관련 스킬 정보 없음')
    else:
        findings.append('SKILL.md 파일 없음')

    score = round(checks_passed / total_checks * 100, 1)
    return {'score': score, 'findings': findings}


def check_workflow_coverage(skill_path):
    """워크플로우 커버리지 체크.

    Args:
        skill_path: str, 스킬 디렉토리 경로.

    Returns:
        dict: {score, findings}
    """
    findings = []
    checks_passed = 0
    total_checks = 3

    skill_md = os.path.join(skill_path, 'SKILL.md')
    content = _read_file(skill_md) if os.path.exists(skill_md) else ''

    # 1. 실행 단계
    if '```' in content or '실행' in content or 'bash' in content.lower():
        checks_passed += 1
    else:
        findings.append('실행 단계 설명 없음')

    # 2. 입출력 정의 (Python 파일에서 함수 시그니처 확인)
    scripts_dir = os.path.join(skill_path, 'scripts')
    if os.path.isdir(scripts_dir):
        py_files = [f for f in os.listdir(scripts_dir) if f.endswith('.py') and f != '__init__.py']
        has_functions = False
        for py_file in py_files:
            py_content = _read_file(os.path.join(scripts_dir, py_file))
            if 'def ' in py_content and '->' in py_content:
                has_functions = True
                break
        if has_functions:
            checks_passed += 1
        else:
            findings.append('함수 시그니처에 반환 타입 힌트 없음')
    else:
        findings.append('scripts/ 디렉토리 없음')

    # 3. 오류 처리 (try/except 또는 예외 문서화)
    if os.path.isdir(scripts_dir):
        for py_file in [f for f in os.listdir(scripts_dir) if f.endswith('.py')]:
            py_content = _read_file(os.path.join(scripts_dir, py_file))
            if 'if ' in py_content and 'None' in py_content:
                checks_passed += 1
                break
        else:
            findings.append('오류 처리 패턴 부족')
    else:
        findings.append('scripts/ 디렉토리 없음 (오류 처리 확인 불가)')

    score = round(checks_passed / total_checks * 100, 1)
    return {'score': score, 'findings': findings}


def check_execution_safety(skill_path):
    """실행 안전성 체크.

    Args:
        skill_path: str, 스킬 디렉토리 경로.

    Returns:
        dict: {score, findings}
    """
    findings = []
    checks_passed = 0
    total_checks = 3

    skill_md = os.path.join(skill_path, 'SKILL.md')
    content = _read_file(skill_md) if os.path.exists(skill_md) else ''

    # 1. 명령 예시
    if '```bash' in content or '```python' in content or '```' in content:
        checks_passed += 1
    else:
        findings.append('실행 명령 예시 없음')

    # 2. 경로 위생 (절대 경로 사용 확인)
    scripts_dir = os.path.join(skill_path, 'scripts')
    if os.path.isdir(scripts_dir):
        py_files = [f for f in os.listdir(scripts_dir)
                    if f.endswith('.py') and not f.startswith('test')]
        hardcoded = False
        for py_file in py_files:
            py_content = _read_file(os.path.join(scripts_dir, py_file))
            if '/home/' in py_content or 'C:\\' in py_content:
                hardcoded = True
                findings.append(f'{py_file}에 하드코딩된 경로 발견')
                break
        if not hardcoded:
            checks_passed += 1
    else:
        checks_passed += 1  # No scripts = no path issues

    # 3. 재현성 (상수 정의 확인)
    if os.path.isdir(scripts_dir):
        for py_file in [f for f in os.listdir(scripts_dir)
                        if f.endswith('.py') and not f.startswith('test')]:
            py_content = _read_file(os.path.join(scripts_dir, py_file))
            if any(c.isupper() and '_' in c for line in py_content.split('\n')
                   for c in line.split('=')[0:1] if c.strip()):
                checks_passed += 1
                break
        else:
            findings.append('상수 정의(대문자_변수) 패턴 없음')
    else:
        findings.append('scripts/ 없음')

    score = round(checks_passed / total_checks * 100, 1)
    return {'score': score, 'findings': findings}


def check_artifacts(skill_path):
    """지원 아티팩트 체크.

    Args:
        skill_path: str, 스킬 디렉토리 경로.

    Returns:
        dict: {score, findings}
    """
    findings = []
    checks_passed = 0
    total_checks = 3

    # 1. scripts/ 존재
    scripts_dir = os.path.join(skill_path, 'scripts')
    if os.path.isdir(scripts_dir):
        py_files = [f for f in os.listdir(scripts_dir)
                    if f.endswith('.py') and not f.startswith('test') and f != '__init__.py']
        if py_files:
            checks_passed += 1
        else:
            findings.append('scripts/에 Python 파일 없음')
    else:
        findings.append('scripts/ 디렉토리 없음')

    # 2. references/ 존재
    refs_dir = os.path.join(skill_path, 'references')
    if os.path.isdir(refs_dir):
        ref_files = os.listdir(refs_dir)
        if ref_files:
            checks_passed += 1
        else:
            findings.append('references/ 디렉토리 비어 있음')
    else:
        findings.append('references/ 디렉토리 없음')

    # 3. 상수 정의 (ALL_CAPS 변수)
    if os.path.isdir(scripts_dir):
        has_constants = False
        for py_file in [f for f in os.listdir(scripts_dir)
                        if f.endswith('.py') and not f.startswith('test')]:
            content = _read_file(os.path.join(scripts_dir, py_file))
            for line in content.split('\n'):
                stripped = line.strip()
                if (stripped and '=' in stripped and not stripped.startswith('#')
                        and not stripped.startswith('def ')
                        and not stripped.startswith('class ')):
                    var_name = stripped.split('=')[0].strip()
                    if var_name.isupper() or (var_name.replace('_', '').isupper()
                                               and '_' in var_name):
                        has_constants = True
                        break
            if has_constants:
                break
        if has_constants:
            checks_passed += 1
        else:
            findings.append('상수 정의 없음')
    else:
        findings.append('상수 확인 불가 (scripts/ 없음)')

    score = round(checks_passed / total_checks * 100, 1)
    return {'score': score, 'findings': findings}


def check_test_health(skill_path):
    """테스트 건강도 체크.

    Args:
        skill_path: str, 스킬 디렉토리 경로.

    Returns:
        dict: {score, findings, test_count, pass_count}
    """
    findings = []
    test_count = 0
    pass_count = 0

    tests_dir = os.path.join(skill_path, 'scripts', 'tests')

    # 1. tests/ 존재
    if not os.path.isdir(tests_dir):
        findings.append('tests/ 디렉토리 없음')
        return {'score': 0, 'findings': findings, 'test_count': 0, 'pass_count': 0}

    # 2. 테스트 파일 존재
    test_files = [f for f in os.listdir(tests_dir) if f.startswith('test_') and f.endswith('.py')]
    if not test_files:
        findings.append('테스트 파일 없음')
        return {'score': 0, 'findings': findings, 'test_count': 0, 'pass_count': 0}

    # 3. 테스트 실행
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', 'tests/', '-v', '--tb=short'],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.join(skill_path, 'scripts'),
        )
        output = result.stdout + result.stderr

        # 테스트 수 파싱
        for line in output.split('\n'):
            if 'passed' in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == 'passed':
                        try:
                            pass_count = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
                    if p == 'failed':
                        try:
                            failed = int(parts[i - 1])
                            test_count = pass_count + failed
                        except (ValueError, IndexError):
                            pass
                if test_count == 0:
                    test_count = pass_count

        if test_count > 0:
            pass_rate = pass_count / test_count
            score = round(pass_rate * 100, 1)
        else:
            score = 0
            findings.append('테스트 결과 파싱 실패')

    except subprocess.TimeoutExpired:
        score = 0
        findings.append('테스트 실행 타임아웃')
    except FileNotFoundError:
        score = 50  # pytest 미설치 → 존재만으로 50점
        findings.append('pytest 실행 불가')

    return {
        'score': score,
        'findings': findings,
        'test_count': test_count,
        'pass_count': pass_count,
    }


def run_auto_review(skill_path):
    """Auto Axis 전체 리뷰 실행.

    Args:
        skill_path: str, 스킬 디렉토리 경로.

    Returns:
        dict: {score, components, findings}
    """
    components = {}
    all_findings = []

    checks = {
        'metadata_use_case': check_metadata,
        'workflow_coverage': check_workflow_coverage,
        'execution_safety': check_execution_safety,
        'supporting_artifacts': check_artifacts,
        'test_health': check_test_health,
    }

    weighted_sum = 0
    for name, func in checks.items():
        result = func(skill_path)
        weight = AUTO_AXIS_WEIGHTS[name]['weight']
        components[name] = {
            'score': result['score'],
            'weight': weight,
            'findings': result.get('findings', []),
        }
        weighted_sum += result['score'] * weight
        all_findings.extend(result.get('findings', []))

    return {
        'score': round(weighted_sum, 1),
        'components': components,
        'findings': all_findings,
    }


def _read_file(path):
    """안전한 파일 읽기."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, UnicodeDecodeError):
        return ''
