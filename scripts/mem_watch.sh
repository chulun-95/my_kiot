#!/usr/bin/env bash
# Cảnh báo khi RAM > 70% liên tục >= 30 phút (6 lần × cron 5 phút). Chạy bằng cron trên host.
set -euo pipefail

SECRETS=/home/deploy/.deploy_secrets
[ -f "$SECRETS" ] && source "$SECRETS"
STATE=/home/deploy/.mem_watch_count

USED=$(free | awk '/Mem:/ {printf("%d", $3/$2*100)}')
if [ "$USED" -gt 70 ]; then
  c=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 ))
else
  c=0
fi
echo "$c" > "$STATE"

if [ "$c" -ge 6 ]; then
  curl -s "https://api.telegram.org/bot${TG_TOKEN:-}/sendMessage" \
    -d chat_id="${TG_CHAT:-}" \
    -d text="⚠️ POS VPS: RAM > 70% suốt 30 phút (hiện ${USED}%). Cân nhắc resize lên 2GB lúc vắng khách." || true
  echo 0 > "$STATE"
fi
