#!/bin/bash
# cron_morning_briefing.sh — 매일 08:50 KST kr-morning-briefing 실행 + 이메일 발송
# crontab: 50 8 * * * /home/saisei/stock/scripts/cron_morning_briefing.sh

set -euo pipefail

STOCK_DIR="/home/saisei/stock"
LOG_FILE="$STOCK_DIR/logs/cron_morning_briefing.log"
CLAUDE_BIN="/home/saisei/.local/bin/claude"

mkdir -p "$STOCK_DIR/reports" "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "=== kr-morning-briefing cron 시작 ==="

cd "$STOCK_DIR"
unset CLAUDECODE 2>/dev/null || true
$CLAUDE_BIN -p "/kr-morning-briefing 메일발송도포함" \
    --allowedTools "WebSearch,WebFetch,Bash,Read,Write,Edit,Glob,Grep" \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "=== kr-morning-briefing cron 완료 (성공) ==="
else
    log "=== kr-morning-briefing cron 완료 (exit: $EXIT_CODE) ==="
fi
