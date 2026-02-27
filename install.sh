#!/bin/bash
# Korean Stock Trading Skills - Installer
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/kys061/kr-stock-skills/main/install.sh | bash
#   또는
#   git clone https://github.com/kys061/kr-stock-skills.git && cd kr-stock-skills && ./install.sh

set -e

SKILLS_DIR="$HOME/.claude/skills"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "================================================"
echo "  Korean Stock Trading Skills Installer"
echo "================================================"
echo ""

# 1. Claude Code skills 디렉토리 확인
if [ ! -d "$SKILLS_DIR" ]; then
    echo "Creating Claude Code skills directory..."
    mkdir -p "$SKILLS_DIR"
fi

# 2. Python 의존성 설치
echo "[1/3] Installing Python dependencies..."
pip install pykrx finance-datareader opendartreader pandas numpy 2>/dev/null || \
pip3 install pykrx finance-datareader opendartreader pandas numpy 2>/dev/null || \
echo "Warning: pip install failed. Please install manually: pip install pykrx finance-datareader opendartreader pandas numpy"

# 3. 스킬 복사 (skills/ 아래의 모든 폴더)
echo "[2/3] Installing skills..."
INSTALLED=0
for skill_dir in "$REPO_DIR"/skills/*/; do
    skill_name=$(basename "$skill_dir")
    target="$SKILLS_DIR/$skill_name"

    if [ -d "$target" ] && [ ! -L "$target" ]; then
        echo "  Backing up existing: $skill_name -> ${skill_name}.bak"
        mv "$target" "${target}.bak"
    fi

    # 심볼릭 링크 제거 후 복사
    rm -f "$target"
    cp -r "$skill_dir" "$target"
    echo "  Installed: $skill_name"
    INSTALLED=$((INSTALLED + 1))
done

# 4. _kr_common 심볼릭 링크 (Python import 호환)
if [ -d "$SKILLS_DIR/_kr-common" ]; then
    ln -sf "$SKILLS_DIR/_kr-common" "$SKILLS_DIR/_kr_common"
fi

# 5. agents 복사 (있으면)
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
echo "  $INSTALLED skill(s) installed to $SKILLS_DIR"
echo "================================================"
echo ""
echo "Optional setup:"
echo "  export DART_API_KEY='your-dart-api-key'   # DART 공시 데이터 (무료)"
echo "  Get key: https://opendart.fss.or.kr/"
echo ""
echo "Quick test:"
echo "  python3 -c \"import sys; sys.path.insert(0,'$SKILLS_DIR'); from _kr_common.kr_client import KRClient; print('OK')\""
echo ""
