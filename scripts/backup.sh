#!/usr/bin/env bash
# Backup Postgres của POS → 2 nơi off-site (R2 + Google Drive). Chạy bằng cron trên host.
set -euo pipefail

POS_DIR=/home/deploy/pos
cd "$POS_DIR"
set -a; source ./.env.prod; set +a   # nạp POSTGRES_USER / POSTGRES_DB

STAMP=$(date +%F_%H%M)
BACKUP_DIR=/home/deploy/backups
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/pos_$STAMP.sql.gz"

TMP="$FILE.tmp"
docker compose -f docker-compose.deploy.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$TMP"
gzip -f "$TMP"          # → $TMP.gz
mv "$TMP.gz" "$FILE"

rclone copy "$FILE" r2:pos-backups/        # off-site 1: Cloudflare R2 (free 10GB)
rclone copy "$FILE" gdrive:pos-backups/    # off-site 2: Google Drive

find "$BACKUP_DIR" -name '*.sql.gz' -mtime +14 -delete   # giữ 14 ngày local
echo "[backup] $FILE done"
