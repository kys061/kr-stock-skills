#!/usr/bin/env python3
"""News Tone Classifier — Classify KOSPI/KOSDAQ news headlines by sentiment.

Classifies headlines into three tones: fear (공포), neutral (중립), stable (안정).
Calculates tone ratios and determines market sentiment transition status.
"""

import argparse
import json
import os
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

_REF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'references')
_KEYWORDS_PATH = os.path.join(_REF_DIR, 'tone_keywords.json')


def load_tone_keywords():
    """Load tone keyword dictionaries from references/tone_keywords.json."""
    if not os.path.exists(_KEYWORDS_PATH):
        return _default_keywords()
    with open(_KEYWORDS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _default_keywords():
    """Fallback keywords when reference file is missing."""
    return {
        'fear': {
            'ko': ['폭락', '패닉', '서킷브레이커', '위기', '급락', '붕괴', '마진콜', '투매', '공포'],
            'en': ['crash', 'panic', 'plunge', 'circuit breaker', 'crisis', 'rout', 'selloff'],
        },
        'neutral': {
            'ko': ['보합', '혼조', '관망', '횡보', '등락', '변동성'],
            'en': ['mixed', 'flat', 'cautious', 'volatile', 'sideways', 'uncertain'],
        },
        'stable': {
            'ko': ['반등', '회복', '저가매수', '안정화', '대책', '지원', '순매수', '상승'],
            'en': ['rebound', 'recovery', 'rally', 'stabilize', 'support', 'surge', 'bounce'],
        },
    }


# ---------------------------------------------------------------------------
# Tone classification
# ---------------------------------------------------------------------------

def classify_headline(headline, keywords=None):
    """Classify a single headline into fear/neutral/stable.

    Args:
        headline: The headline text to classify.
        keywords: dict with fear/neutral/stable keyword lists.

    Returns:
        dict with tone, matched_keywords, confidence.
    """
    if keywords is None:
        keywords = load_tone_keywords()

    headline_lower = headline.lower()
    matches = {'fear': [], 'neutral': [], 'stable': []}

    for tone, lang_keywords in keywords.items():
        for lang in ['ko', 'en']:
            for kw in lang_keywords.get(lang, []):
                if kw.lower() in headline_lower:
                    matches[tone].append(kw)

    # Determine tone by match count, then by first-match position
    if not any(matches.values()):
        return {'tone': 'neutral', 'matched_keywords': [], 'confidence': 'low'}

    # Count matches per tone
    counts = {tone: len(kws) for tone, kws in matches.items()}
    max_count = max(counts.values())
    top_tones = [t for t, c in counts.items() if c == max_count and c > 0]

    if len(top_tones) == 1:
        tone = top_tones[0]
    else:
        # Tie-break: first keyword position in headline
        positions = {}
        for t in top_tones:
            for kw in matches[t]:
                pos = headline_lower.find(kw.lower())
                if pos >= 0:
                    if t not in positions or pos < positions[t]:
                        positions[t] = pos
        tone = min(positions, key=positions.get) if positions else top_tones[0]

    all_matched = matches[tone]
    confidence = 'high' if len(all_matched) >= 2 else 'medium'

    return {
        'tone': tone,
        'matched_keywords': all_matched,
        'confidence': confidence,
    }


def classify_headlines(headlines, keywords=None):
    """Classify multiple headlines and return individual results.

    Args:
        headlines: list of dicts with 'headline' and optional 'source' keys.
        keywords: tone keyword dict.

    Returns:
        list of dicts with headline, source, tone, matched_keywords.
    """
    if keywords is None:
        keywords = load_tone_keywords()

    results = []
    for item in headlines:
        if isinstance(item, str):
            text = item
            source = ''
        else:
            text = item.get('headline', '')
            source = item.get('source', '')

        classification = classify_headline(text, keywords)
        results.append({
            'headline': text,
            'source': source,
            'tone': classification['tone'],
            'matched_keywords': classification['matched_keywords'],
            'confidence': classification['confidence'],
        })

    return results


# ---------------------------------------------------------------------------
# Tone ratio calculation
# ---------------------------------------------------------------------------

def calculate_tone_ratio(classified_headlines):
    """Calculate tone distribution from classified headlines.

    Returns dict with fear/neutral/stable counts and percentages.
    """
    total = len(classified_headlines)
    if total == 0:
        return {
            'fear': {'count': 0, 'pct': 0},
            'neutral': {'count': 0, 'pct': 0},
            'stable': {'count': 0, 'pct': 0},
            'total': 0,
        }

    counts = {'fear': 0, 'neutral': 0, 'stable': 0}
    for item in classified_headlines:
        tone = item.get('tone', 'neutral')
        if tone in counts:
            counts[tone] += 1

    return {
        'fear': {'count': counts['fear'],
                 'pct': round(counts['fear'] / total * 100, 1)},
        'neutral': {'count': counts['neutral'],
                    'pct': round(counts['neutral'] / total * 100, 1)},
        'stable': {'count': counts['stable'],
                   'pct': round(counts['stable'] / total * 100, 1)},
        'total': total,
    }


# ---------------------------------------------------------------------------
# Transition judgment
# ---------------------------------------------------------------------------

def judge_transition(tone_ratio):
    """Judge market sentiment transition status.

    Args:
        tone_ratio: dict from calculate_tone_ratio().

    Returns:
        dict with status ('fear', 'transitioning', 'stable'),
        label_ko, reasoning.
    """
    stable_pct = tone_ratio['stable']['pct']
    fear_pct = tone_ratio['fear']['pct']

    if stable_pct >= 70 and fear_pct < 20:
        return {
            'status': 'stable',
            'label_ko': '안정',
            'reasoning': f'안정 톤 {stable_pct}% (≥70%), 공포 톤 {fear_pct}% (<20%) → 톤 전환 완료',
        }
    elif stable_pct >= 50:
        return {
            'status': 'transitioning',
            'label_ko': '전환 중',
            'reasoning': f'안정 톤 {stable_pct}% (≥50%)이나 공포 톤 {fear_pct}% 잔존 → 전환 진행 중',
        }
    else:
        return {
            'status': 'fear',
            'label_ko': '공포',
            'reasoning': f'안정 톤 {stable_pct}% (<50%), 공포 톤 {fear_pct}% → 아직 전환 안 됨',
        }


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def analyze_news_tone(headlines, keywords=None):
    """Run full news tone analysis pipeline.

    Args:
        headlines: list of headline dicts or strings.
        keywords: optional keyword dict.

    Returns:
        dict with classified, tone_ratio, transition, summary.
    """
    classified = classify_headlines(headlines, keywords)
    tone_ratio = calculate_tone_ratio(classified)
    transition = judge_transition(tone_ratio)

    summary = (
        f"뉴스 톤이 [{transition['label_ko']}]으로 판단됩니다. "
        f"근거: {transition['reasoning']}"
    )

    return {
        'classified': classified,
        'tone_ratio': tone_ratio,
        'transition': transition,
        'summary': summary,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

TONE_LABEL_KO = {
    'fear': '공포',
    'neutral': '중립',
    'stable': '안정',
}

DEMO_HEADLINES = [
    {'headline': 'Panic Sweeps South Korea Stocks in Biggest Two-Day Crash Since 2008',
     'source': 'Bloomberg'},
    {'headline': '한국 증시는 비정상… 거품 붕괴-대폭락 오는가?',
     'source': '뉴데일리'},
    {'headline': 'KOSPI·KOSDAQ 서킷브레이커 발동 — 초유의 동반 폭락',
     'source': '전국인력신문'},
    {'headline': "'Rollercoaster KOSPI' Surges on Prospects of US-Iran Ceasefire",
     'source': '아시아경제'},
    {'headline': "'검은 수요일' 폭락 만회… 코스피·코스닥 역대급 반등",
     'source': '한국연합신문'},
    {'headline': 'Asia markets bounce back: KOSPI soars 12% in historic rebound',
     'source': 'Seeking Alpha'},
    {'headline': '중동 충격에 급락한 코스피… 반등 가능성 주목',
     'source': '파이낸셜뉴스'},
    {'headline': '금융위, 중동 피해기업에 13.3조 긴급 지원',
     'source': '서울신문'},
]


def main():
    parser = argparse.ArgumentParser(
        description='News Tone Classifier — Classify KOSPI/KOSDAQ headlines')
    parser.add_argument('--headline', type=str,
                        help='Single headline to classify')
    parser.add_argument('--headlines-file', type=str,
                        help='JSON file with headlines list')
    parser.add_argument('--demo', action='store_true',
                        help='Run demo with sample headlines')
    parser.add_argument('--format', choices=['json', 'markdown'],
                        default='markdown', help='Output format')
    args = parser.parse_args()

    keywords = load_tone_keywords()

    if args.headline:
        result = classify_headline(args.headline, keywords)
        if args.format == 'json':
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            tone_ko = TONE_LABEL_KO.get(result['tone'], result['tone'])
            print(f"톤: {tone_ko} | 매칭: {', '.join(result['matched_keywords'])} "
                  f"| 신뢰도: {result['confidence']}")
        return

    if args.headlines_file:
        with open(args.headlines_file, 'r', encoding='utf-8') as f:
            headlines = json.load(f)
    elif args.demo:
        headlines = DEMO_HEADLINES
    else:
        print("ERROR: --headline, --headlines-file, or --demo required",
              file=sys.stderr)
        sys.exit(1)

    analysis = analyze_news_tone(headlines, keywords)

    if args.format == 'json':
        print(json.dumps(analysis, ensure_ascii=False, indent=2, default=str))
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        print(f"# News Tone Analysis — {now}")
        print()
        print("## 헤드라인 분류")
        print()
        print("| # | 헤드라인 | 소스 | 톤 | 매칭 키워드 |")
        print("|:-:|---------|------|:--:|-----------|")
        for i, item in enumerate(analysis['classified'], 1):
            tone_ko = TONE_LABEL_KO.get(item['tone'], item['tone'])
            kws = ', '.join(item['matched_keywords'][:3])
            print(f"| {i} | {item['headline'][:50]}... | "
                  f"{item['source']} | {tone_ko} | {kws} |")

        print()
        print("## 톤 비율")
        print()
        tr = analysis['tone_ratio']
        print(f"- 공포: {tr['fear']['count']}건 ({tr['fear']['pct']}%)")
        print(f"- 중립: {tr['neutral']['count']}건 ({tr['neutral']['pct']}%)")
        print(f"- 안정: {tr['stable']['count']}건 ({tr['stable']['pct']}%)")

        print()
        t = analysis['transition']
        print(f"## 판단: **{t['label_ko']}**")
        print(f"> {analysis['summary']}")


if __name__ == '__main__':
    main()
