"""한국 테마 탐지기 메인.

Usage:
    python3 kr_theme_detector.py --output-dir reports/
    python3 kr_theme_detector.py --max-themes 5 --skip-narrative --output-dir reports/
"""

import sys
import os
import argparse
import logging
import yaml

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from industry_data_collector import IndustryDataCollector
from theme_classifier import ThemeClassifier
from scorer import ThemeScorer
from report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_THEMES_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'config', 'kr_themes.yaml'
)


def load_themes(path: str) -> dict:
    """YAML에서 테마 정의 로드."""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('themes', {})


def analyze(output_dir: str, themes_path: str = None, max_themes: int = None):
    """테마 탐지 실행."""
    from _kr_common.kr_client import KRClient

    logger.info("=== 한국 테마 탐지 시작 ===")

    # 1. 테마 정의 로드
    themes = load_themes(themes_path or DEFAULT_THEMES_PATH)
    logger.info(f"테마 {len(themes)}개 로드")

    # 2. 데이터 수집
    client = KRClient()
    collector = IndustryDataCollector(client)
    theme_data = collector.collect(themes)

    # 3. 테마 분류 & 통계
    classifier = ThemeClassifier()
    classified = classifier.classify(theme_data)

    # 4. 3D 스코어링
    scorer = ThemeScorer()
    scored = scorer.score_all(classified)

    # 5. max_themes 필터
    if max_themes and max_themes < len(scored):
        sorted_themes = sorted(scored.items(), key=lambda x: x[1]['heat'], reverse=True)
        scored = dict(sorted_themes[:max_themes])
        logger.info(f"상위 {max_themes}개 테마만 출력")

    # 6. 리포트 생성
    reporter = ReportGenerator(output_dir)
    paths = reporter.generate(scored)
    logger.info(f"JSON: {paths['json_path']}")
    logger.info(f"Markdown: {paths['md_path']}")

    return {
        'themes': scored,
        'report_paths': paths,
    }


def main():
    parser = argparse.ArgumentParser(description='한국 테마 탐지기')
    parser.add_argument('--output-dir', default='reports/',
                        help='리포트 출력 디렉토리')
    parser.add_argument('--themes-file', default=None,
                        help='커스텀 테마 정의 파일')
    parser.add_argument('--max-themes', type=int, default=None,
                        help='상위 N개 테마만 분석')
    parser.add_argument('--skip-narrative', action='store_true',
                        help='WebSearch 내러티브 건너뛰기')
    args = parser.parse_args()

    try:
        result = analyze(args.output_dir, args.themes_file, args.max_themes)

        print(f"\n{'='*60}")
        print(f"테마 탐지 결과 ({len(result['themes'])}개)")
        print(f"{'='*60}")
        for tid, t in sorted(result['themes'].items(),
                              key=lambda x: x[1]['heat'], reverse=True):
            print(f"  {t['name']:12s}  Heat: {t['heat']:5.1f}  "
                  f"{t['direction']:8s}  {t['lifecycle']:10s}  {t['confidence']}")
        print(f"{'='*60}\n")
    except Exception as e:
        logger.error(f"테마 탐지 실패: {e}")


if __name__ == '__main__':
    main()
