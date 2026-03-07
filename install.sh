#!/bin/bash
# Korean Stock Trading Skills - Installer
#
# Usage:
#   Method 1 (Claude Code Plugin - Recommended):
#     Claude Code에서: /plugin marketplace add kys061/kr-stock-skills
#                     /plugin install kr-stock-skills
#     이후 Python 의존성만: ./install.sh --deps-only
#
#   Method 2 (Standalone):
#     git clone https://github.com/kys061/kr-stock-skills.git
#     cd kr-stock-skills && ./install.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPS_ONLY=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --deps-only)
            DEPS_ONLY=true
            ;;
    esac
done

echo "================================================"
echo "  Korean Stock Trading Skills Installer"
echo "  47 skills for KOSPI/KOSDAQ analysis"
echo "================================================"
echo ""

# 1. Python 의존성 설치
echo "[1/3] Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install pykrx finance-datareader opendartreader pandas numpy
elif command -v pip &> /dev/null; then
    pip install pykrx finance-datareader opendartreader pandas numpy
else
    echo "WARNING: pip not found. Please install manually:"
    echo "  pip install pykrx finance-datareader opendartreader pandas numpy"
fi

if [ "$DEPS_ONLY" = true ]; then
    echo ""
    echo "================================================"
    echo "  Python dependencies installed!"
    echo "================================================"
    echo ""
    echo "Environment variables (optional):"
    echo "  export DART_API_KEY='your-dart-api-key'"
    echo "  Get key: https://opendart.fss.or.kr/"
    echo ""
    exit 0
fi

# 2. Claude Code skills 디렉토리에 스킬 설치
SKILLS_DIR="$HOME/.claude/skills"
echo "[2/3] Installing skills to $SKILLS_DIR..."

if [ ! -d "$SKILLS_DIR" ]; then
    mkdir -p "$SKILLS_DIR"
fi

INSTALLED=0
for skill_dir in "$REPO_DIR"/skills/*/; do
    skill_name=$(basename "$skill_dir")
    target="$SKILLS_DIR/$skill_name"

    # 기존 디렉토리 제거 (심볼릭 링크는 건너뜀)
    if [ -d "$target" ] && [ ! -L "$target" ]; then
        rm -rf "$target"
    elif [ -L "$target" ]; then
        rm -f "$target"
    fi

    cp -r "$skill_dir" "$target"
    echo "  Installed: $skill_name"
    INSTALLED=$((INSTALLED + 1))
done

# 구 _kr-common 디렉토리/심링크 정리 (리네임 이전 잔존물)
if [ -d "$SKILLS_DIR/_kr-common" ] && [ ! -L "$SKILLS_DIR/_kr-common" ]; then
    rm -rf "$SKILLS_DIR/_kr-common"
    echo "  Cleaned up legacy _kr-common directory"
elif [ -L "$SKILLS_DIR/_kr-common" ]; then
    rm -f "$SKILLS_DIR/_kr-common"
fi

# 3. agents 복사
echo "[3/3] Installing agents..."
if [ -d "$REPO_DIR/agents" ]; then
    AGENTS_DIR="$HOME/.claude/agents"
    mkdir -p "$AGENTS_DIR"
    for agent_file in "$REPO_DIR"/agents/*.md; do
        [ -f "$agent_file" ] || continue
        cp "$agent_file" "$AGENTS_DIR/"
        echo "  Installed agent: $(basename "$agent_file")"
    done
fi

echo ""
echo "================================================"
echo "  Installation complete!"
echo "  $INSTALLED skill(s) installed"
echo "================================================"
echo ""
echo "Environment variables (optional):"
echo "  export DART_API_KEY='your-dart-api-key'"
echo "  Get key: https://opendart.fss.or.kr/"
echo ""
echo "Quick start in Claude Code:"
echo "  /kr-market-environment       시장 환경 분석"
echo "  /kr-canslim-screener         성장주 스크리닝"
echo "  /kr-stock-analysis 삼성전자    종합 분석"
echo ""
