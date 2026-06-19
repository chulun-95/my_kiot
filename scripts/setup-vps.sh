#!/usr/bin/env bash
# Chạy MỘT LẦN trên VPS (user 'deploy', tại ~/pos) để wiring backup + monitoring.
# An toàn khi chạy lại (idempotent).
set -euo pipefail

POS_DIR=/home/deploy/pos

# 1. Swap 2GB (chống OOM trên 1GB RAM)
if ! swapon --show 2>/dev/null | grep -q '/swapfile'; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo "[setup] swap 2GB đã bật"
else
  echo "[setup] swap đã có, bỏ qua"
fi

# 2. chmod scripts
chmod +x "$POS_DIR/scripts/backup.sh" "$POS_DIR/scripts/mem_watch.sh"

# 3. File secrets Telegram (mẫu — điền tay sau)
SECRETS=/home/deploy/.deploy_secrets
if [ ! -f "$SECRETS" ]; then
  cat > "$SECRETS" <<'EOF'
# Điền token bot Telegram + chat id rồi lưu (giữ file 600):
TG_TOKEN=
TG_CHAT=
EOF
  chmod 600 "$SECRETS"
  echo "[setup] → Hãy điền TG_TOKEN, TG_CHAT vào $SECRETS"
fi

# 4. Crontab (xóa dòng cũ của 2 script rồi thêm lại — tránh trùng)
( crontab -l 2>/dev/null | grep -v 'backup.sh\|mem_watch.sh' ; \
  echo '0 2 * * * /home/deploy/pos/scripts/backup.sh >> /home/deploy/backup.log 2>&1' ; \
  echo '*/5 * * * * /home/deploy/pos/scripts/mem_watch.sh >> /home/deploy/mem_watch.log 2>&1' \
) | crontab -
echo "[setup] crontab đã ghi (backup 2h sáng, mem_watch mỗi 5 phút)"

echo "[setup] XONG. Việc còn lại làm tay: 'rclone config' tạo remote 'r2' và 'gdrive'; điền $SECRETS."
