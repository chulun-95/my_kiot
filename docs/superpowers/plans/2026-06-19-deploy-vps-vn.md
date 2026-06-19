# Deploy VPS VN 1GB + Cloudflare — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa Backend (FastAPI) + Web (React) lên 1 VPS Việt Nam 1GB sau Cloudflare, truy cập qua `https://pos.timxe-namdinh.com`, always-on, chi phí ~70–90k/tháng.

**Architecture:** Nginx trên VPS serve React build ở `/` và reverse-proxy `/api` → uvicorn (same-origin → cookie `HttpOnly; SameSite=Strict` chạy chuẩn, không CORS). Postgres chạy nội bộ trong cùng Docker Compose, không expose. Cloudflare lo SSL/CDN/DDoS. CI/CD có sẵn (`deploy.yml`) build image lên GHCR rồi SSH vào VPS pull. Backup + monitoring chạy bằng cron trên host.

**Tech Stack:** Docker Compose, Nginx, FastAPI/uvicorn, PostgreSQL 16, GitHub Actions + GHCR, Cloudflare, rclone (R2 + Google Drive), bash/cron.

## Global Constraints

- Spec nguồn: `docs/superpowers/specs/2026-06-19-deploy-vps-vn-design.md`.
- VPS: **1GB RAM / ~1 vCPU**, Ubuntu 24.04, đặt tại Việt Nam. Right-size: uvicorn **1 worker**, swap **2GB**, Postgres `shared_buffers=128MB`, `effective_cache_size=512MB`, `work_mem=8MB`, `max_connections=30`; `mem_limit` api ~**512m**, db ~**384m**.
- Domain: subdomain **`pos.timxe-namdinh.com`** (zone `timxe-namdinh.com` đã ở Cloudflare — KHÔNG đụng bản ghi khác).
- Same-origin: FE giữ `baseURL='/api/v1'`, KHÔNG đặt `VITE_API_BASE_URL`.
- Kiến trúc image: **x86/amd64** (VPS VN là x86) — KHÔNG build arm64.
- Secrets (`.env.prod`, `ssl/`, token rclone/Telegram) chỉ nằm trên server, đã có trong `.gitignore` (`.env.prod`, `ssl/`, `backups/`). KHÔNG commit.
- `COOKIE_SECURE=true` ở production. `JWT_SECRET_KEY` + password Postgres random mạnh (`openssl rand -hex 32`).
- Postgres KHÔNG bao giờ bind port ra host. `ufw` chỉ mở 80/443/SSH.
- Mọi thông báo người dùng bằng tiếng Việt (CLAUDE.md).

---

## Phần A — Thay đổi trong repo (làm & kiểm tra tại máy dev, commit)

### Task 1: Cập nhật `frontend/nginx.conf` (domain + health proxy)

**Files:**
- Modify: `frontend/nginx.conf`

**Interfaces:**
- Produces: route `https://pos.timxe-namdinh.com/health` → uvicorn `/health`; `server_name` đúng subdomain. Task 9 (deploy) và Task 10 (nghiệm thu) dựa vào đây để health check từ ngoài.

- [ ] **Step 1: Đổi `server_name` ở cả 2 block (443 và 80)**

Trong `frontend/nginx.conf`, thay cả 2 dòng:
```
server_name app.tencuahang.vn;
```
thành:
```
server_name pos.timxe-namdinh.com;
```

- [ ] **Step 2: Thêm location `/health` proxy về API (đặt ngay trên block `location /api/`)**

```nginx
    # Health check cho UptimeRobot/monitor — /health nằm ở gốc uvicorn, không phải /api
    location = /health {
        proxy_pass http://api:8000/health;
        access_log off;
    }
```

- [ ] **Step 3: Kiểm tra cú pháp nginx bằng image chính thức**

Run:
```bash
docker run --rm -v "$PWD/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro" nginx:1.27-alpine nginx -t
```
Expected: `syntax is ok` + `test is successful` (cảnh báo về upstream `api` không phân giải được khi test rời — bỏ qua, vì `nginx -t` không resolve service name; quan trọng là không lỗi cú pháp).

- [ ] **Step 4: Commit**

```bash
git add frontend/nginx.conf
git commit -m "deploy(nginx): server_name pos.timxe-namdinh.com + health proxy"
```

---

### Task 2: Right-size `docker-compose.deploy.yml` cho 1GB RAM

**Files:**
- Modify: `docker-compose.deploy.yml`

**Interfaces:**
- Consumes: image GHCR `ghcr.io/chulun-95/my_kiot-api` / `-nginx` (đã có).
- Produces: service `db` có Postgres tuning + `mem_limit`; service `api` chạy `--workers 1` + `mem_limit`. Task 9/10 dựa vào RAM thấp này để chạy ổn trên 1GB.

- [ ] **Step 1: Thêm Postgres tuning + `mem_limit` cho service `db`**

Trong service `db`, thêm `command` và `mem_limit` (đặt cạnh `healthcheck`):
```yaml
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    command:
      - "postgres"
      - "-c"
      - "shared_buffers=128MB"
      - "-c"
      - "effective_cache_size=512MB"
      - "-c"
      - "work_mem=8MB"
      - "-c"
      - "max_connections=30"
    mem_limit: 384m
    volumes:
      - pos_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 10
```

- [ ] **Step 2: Đổi `--workers 4` → `--workers 1` và thêm `mem_limit` cho service `api`**

Trong service `api`, sửa `command` và thêm `mem_limit`:
```yaml
  api:
    image: ghcr.io/chulun-95/my_kiot-api:${IMAGE_TAG:-latest}
    restart: always
    env_file: .env.prod
    mem_limit: 512m
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1"
```

- [ ] **Step 3: Validate compose**

Run:
```bash
IMAGE_TAG=latest POSTGRES_USER=x POSTGRES_PASSWORD=y POSTGRES_DB=z docker compose -f docker-compose.deploy.yml config >/dev/null && echo OK
```
Expected: `OK` (không lỗi YAML/schema). Cảnh báo thiếu `.env.prod` khi `config` có thể xuất hiện — bỏ qua, nó chỉ đọc cấu trúc.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.deploy.yml
git commit -m "deploy(compose): right-size 1GB — 1 worker, mem_limit, postgres tuning"
```

---

### Task 3: Tạo `scripts/backup.sh` (backup DB → R2 + Google Drive)

**Files:**
- Create: `scripts/backup.sh`

**Interfaces:**
- Consumes: `.env.prod` trên VPS (`POSTGRES_USER`, `POSTGRES_DB`); rclone remote `r2` và `gdrive` (cấu hình ở Task 8).
- Produces: file `pos_<STAMP>.sql.gz` trên R2 + Google Drive; giữ 14 ngày local. Task 8 đăng ký cron gọi script này; Task 10 nghiệm thu.

- [ ] **Step 1: Tạo file `scripts/backup.sh`**

```bash
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

docker compose -f docker-compose.deploy.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$FILE"

rclone copy "$FILE" r2:pos-backups/        # off-site 1: Cloudflare R2 (free 10GB)
rclone copy "$FILE" gdrive:pos-backups/    # off-site 2: Google Drive

find "$BACKUP_DIR" -name '*.sql.gz' -mtime +14 -delete   # giữ 14 ngày local
echo "[backup] $FILE done"
```

- [ ] **Step 2: Kiểm tra cú pháp bash**

Run: `bash -n scripts/backup.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/backup.sh
git commit -m "deploy(scripts): backup.sh — pg_dump → R2 + Google Drive, giữ 14 ngày"
```

---

### Task 4: Tạo `scripts/mem_watch.sh` (cảnh báo RAM > 70% / 30 phút)

**Files:**
- Create: `scripts/mem_watch.sh`

**Interfaces:**
- Consumes: `/home/deploy/.deploy_secrets` (`TG_TOKEN`, `TG_CHAT`) — tạo ở Task 8.
- Produces: state file `/home/deploy/.mem_watch_count`; gửi Telegram khi RAM cao kéo dài. Task 8 đăng ký cron 5 phút/lần.

- [ ] **Step 1: Tạo file `scripts/mem_watch.sh`**

```bash
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
    -d text="⚠️ POS VPS: RAM > 70% suốt 30 phút (hiện ${USED}%). Cân nhắc resize lên 2GB lúc vắng khách." >/dev/null || true
  echo 0 > "$STATE"
fi
```

- [ ] **Step 2: Kiểm tra cú pháp + logic tính %**

Run: `bash -n scripts/mem_watch.sh && free | awk '/Mem:/ {printf("RAM used: %d%%\n", $3/$2*100)}'`
Expected: `RAM used: NN%` in ra một số hợp lệ 0–100.

- [ ] **Step 3: Commit**

```bash
git add scripts/mem_watch.sh
git commit -m "deploy(scripts): mem_watch.sh — cảnh báo Telegram khi RAM>70%/30 phút"
```

---

### Task 5: Tạo `scripts/setup-vps.sh` (wiring chạy một lần trên VPS)

**Files:**
- Create: `scripts/setup-vps.sh`

**Interfaces:**
- Consumes: `scripts/backup.sh`, `scripts/mem_watch.sh` (Task 3, 4) đã có trên VPS tại `/home/deploy/pos/scripts/`.
- Produces: swap 2GB, chmod +x scripts, file `/home/deploy/.deploy_secrets` (mẫu), crontab (backup 2h sáng + mem_watch 5 phút/lần). Task 6/8 gọi script này.

- [ ] **Step 1: Tạo file `scripts/setup-vps.sh`**

```bash
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
```

- [ ] **Step 2: Kiểm tra cú pháp bash**

Run: `bash -n scripts/setup-vps.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/setup-vps.sh
git commit -m "deploy(scripts): setup-vps.sh — swap + chmod + crontab (chạy 1 lần)"
```

---

### Task 6: Mở rộng `deploy.yml` để scp thêm `scripts/` lên VPS

**Files:**
- Modify: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: secret `SSH_HOST`, `SSH_USER`, `SSH_KEY` (khai báo ở Task 9).
- Produces: mỗi lần deploy, `docker-compose.deploy.yml` + thư mục `scripts/` được copy lên `~/pos/` → logic script tự cập nhật. (Crontab/secrets vẫn one-time qua Task 8.)

- [ ] **Step 1: Thêm `scripts` vào `source` của bước "Copy compose file → VPS"**

Trong job `deploy`, bước `appleboy/scp-action`, sửa khối `with:`:
```yaml
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_KEY }}
          source: "docker-compose.deploy.yml,scripts/backup.sh,scripts/mem_watch.sh,scripts/setup-vps.sh"
          target: ~/pos/
```

- [ ] **Step 2: Validate YAML**

Run:
```bash
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy.yml')); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "deploy(ci): scp thêm scripts/ lên VPS mỗi lần deploy"
```

---

### Task 7: Cập nhật `.env.prod.example` cho domain mới

**Files:**
- Modify: `.env.prod.example`

**Interfaces:**
- Produces: mẫu env chuẩn để copy thành `.env.prod` trên VPS (Task 8). Không chứa secret thật.

- [ ] **Step 1: Đổi `CORS_ORIGINS` sang subdomain thật**

Trong `.env.prod.example`, sửa dòng:
```
CORS_ORIGINS=https://app.tencuahang.vn
```
thành:
```
CORS_ORIGINS=https://pos.timxe-namdinh.com
```

- [ ] **Step 2: Commit**

```bash
git add .env.prod.example
git commit -m "deploy(env): mẫu CORS_ORIGINS = https://pos.timxe-namdinh.com"
```

---

## Phần B — Provision VPS & cấu hình (làm trên server / dashboard, một lần)

> Các task dưới đây chạy trên VPS và Cloudflare dashboard. "Test" = lệnh xác minh với output mong đợi. Không commit code (trừ khi sửa repo).

### Task 8: Mua + harden VPS + cài Docker

**Files:** (không có file repo — thao tác server)

**Interfaces:**
- Produces: VPS Ubuntu 24.04 có user `deploy` (SSH key, không password), Docker + compose plugin, `ufw` chỉ 80/443/SSH. IP public dùng cho Task 9 (Cloudflare A record) và Task 11 (GitHub secret `SSH_HOST`).

- [ ] **Step 1: Mua VPS VN 1GB**

Chọn nhà cung cấp **có sẵn cả gói 1GB và 2GB+** (AZDIGI / Vietnix / BizFly) để sau resize trong cùng hệ thống. OS: **Ubuntu 24.04**. Trả Momo/CK. Ghi lại **IP public**.

- [ ] **Step 2: Tạo user `deploy` + SSH key (SSH vào bằng root)**

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
```

- [ ] **Step 3: Tắt root login + password auth**

Sửa `/etc/ssh/sshd_config`: `PermitRootLogin no`, `PasswordAuthentication no`, rồi:
```bash
systemctl restart ssh
```
Verify: mở terminal mới `ssh deploy@<IP>` vào được; `ssh root@<IP>` bị từ chối.

- [ ] **Step 4: Firewall — chỉ SSH/80/443**

```bash
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
ufw status
```
Expected: chỉ liệt kê OpenSSH, 80, 443. KHÔNG có 5432/8000.

- [ ] **Step 5: Cài Docker + compose plugin**

```bash
apt update && apt -y upgrade && apt -y install git rclone
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
usermod -aG docker deploy
```
Verify (đăng nhập lại bằng `deploy`): `docker compose version` in ra version.

---

### Task 9: Cloudflare — subdomain + Origin Certificate

**Files:** (Cloudflare dashboard + file `ssl/` trên VPS)

**Interfaces:**
- Consumes: IP VPS (Task 8).
- Produces: bản ghi `A pos → IP` (proxied); `~/pos/ssl/origin.pem` + `origin.key` trên VPS. Task 12 nghiệm thu HTTPS.

- [ ] **Step 1: Thêm DNS record**

Cloudflare → zone `timxe-namdinh.com` → DNS → Add record: `A` | name `pos` | IPv4 `<IP VPS>` | Proxy **ON** (cam). KHÔNG sửa bản ghi gốc.

- [ ] **Step 2: SSL/TLS = Full (strict)**

Cloudflare → SSL/TLS → Overview → **Full (strict)**.

- [ ] **Step 3: Tạo Origin Certificate**

Cloudflare → SSL/TLS → Origin Server → Create Certificate (mặc định 15 năm) → copy nội dung 2 phần.

- [ ] **Step 4: Đặt cert lên VPS**

```bash
mkdir -p ~/pos/ssl
nano ~/pos/ssl/origin.pem   # dán phần certificate
nano ~/pos/ssl/origin.key   # dán phần private key
chmod 600 ~/pos/ssl/origin.key
```
Verify: `openssl x509 -in ~/pos/ssl/origin.pem -noout -subject` in ra subject hợp lệ.

---

### Task 10: Tạo `.env.prod` + wiring (setup-vps.sh) + rclone + Telegram

**Files:** (`~/pos/.env.prod` trên VPS — không commit)

**Interfaces:**
- Consumes: repo đã clone tại `~/pos` (hoặc scripts đã scp ở lần deploy đầu).
- Produces: `.env.prod` đầy đủ secret; swap + crontab (qua `setup-vps.sh`); rclone remote `r2`+`gdrive`; `.deploy_secrets` có Telegram. Task 11/12 dựa vào.

- [ ] **Step 1: Clone repo + tạo `.env.prod`**

```bash
cd ~ && git clone <repo-url> pos-src 2>/dev/null || true
# Lấy mẫu env:
cp ~/pos-src/.env.prod.example ~/pos/.env.prod   # hoặc tự tạo theo mẫu
nano ~/pos/.env.prod
```
Điền: `POSTGRES_PASSWORD` (random `openssl rand -hex 32`), `DATABASE_URL` host=`db` dùng password đó, `JWT_SECRET_KEY` (`openssl rand -hex 32`), `COOKIE_SECURE=true`, `CORS_ORIGINS=https://pos.timxe-namdinh.com`.
Verify: `grep -E 'COOKIE_SECURE|CORS_ORIGINS' ~/pos/.env.prod` đúng giá trị.

- [ ] **Step 2: Copy scripts vào ~/pos (lần đầu, trước khi CI scp) + chạy setup-vps.sh**

```bash
mkdir -p ~/pos/scripts
cp ~/pos-src/scripts/{backup.sh,mem_watch.sh,setup-vps.sh} ~/pos/scripts/
bash ~/pos/scripts/setup-vps.sh
```
Expected: log "swap 2GB đã bật", "crontab đã ghi". Verify: `free -h` thấy swap 2.0Gi; `crontab -l` có 2 dòng backup + mem_watch.

- [ ] **Step 3: Cấu hình rclone (R2 + Google Drive)**

```bash
rclone config
```
Tạo remote tên **`r2`** (type `s3`, provider `Cloudflare`, điền R2 Access Key/Secret + endpoint) và **`gdrive`** (type `drive`, OAuth). Tạo bucket/thư mục `pos-backups`.
Verify: `rclone lsd r2:` và `rclone lsd gdrive:` không lỗi.

- [ ] **Step 4: Điền Telegram secrets**

```bash
nano /home/deploy/.deploy_secrets   # điền TG_TOKEN, TG_CHAT
```
Verify: `bash ~/pos/scripts/mem_watch.sh` chạy không lỗi (nếu RAM<70% sẽ không gửi gì — bình thường).

---

### Task 11: GitHub secrets + deploy lần đầu

**Files:** (GitHub repo settings)

**Interfaces:**
- Consumes: IP VPS, user `deploy`, private key CI.
- Produces: pipeline `deploy.yml` chạy được; container lên trên VPS. Task 12 nghiệm thu.

- [ ] **Step 1: Tạo SSH key riêng cho CI + cài public key lên VPS**

Trên máy dev:
```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ci_deploy -N ""
ssh-copy-id -i ci_deploy.pub deploy@<IP_VPS>
```

- [ ] **Step 2: Khai báo GitHub Secrets**

Repo → Settings → Secrets and variables → Actions → thêm: `SSH_HOST` = IP VPS, `SSH_USER` = `deploy`, `SSH_KEY` = toàn bộ nội dung file `ci_deploy` (private).

- [ ] **Step 3: Trigger deploy**

Push 1 commit lên `master` (các commit Phần A), hoặc Actions → Deploy → Run workflow.
Verify (trên VPS):
```bash
cd ~/pos && docker compose -f docker-compose.deploy.yml ps
```
Expected: `db`, `api`, `nginx` đều `Up` (db `healthy`). `docker compose logs api` thấy `alembic upgrade head` chạy xong + uvicorn start với 1 worker.

---

### Task 12: Nghiệm thu (Definition of Done)

**Files:** (không có — kiểm thử end-to-end)

**Interfaces:**
- Consumes: toàn bộ Task 1–11.

- [ ] **Step 1: HTTPS + UI + site gốc**

Mở `https://pos.timxe-namdinh.com` → hiện UI, ổ khóa SSL hợp lệ (Full strict). Mở `https://timxe-namdinh.com` → site gốc **vẫn chạy bình thường**.

- [ ] **Step 2: Health check qua domain**

Run: `curl -s https://pos.timxe-namdinh.com/health`
Expected: `{"status":"ok","env":"production"}`

- [ ] **Step 3: Cookie + refresh token**

Đăng nhập trên web → DevTools → Application → Cookies: refresh token có `Secure; HttpOnly; SameSite=Strict`. Đóng/mở lại tab → vẫn đăng nhập (refresh chạy).

- [ ] **Step 4: Cách ly tenant + cổng đóng**

Tạo 2 tenant test → tenant A không thấy data tenant B. Trên VPS: `docker ps` → KHÔNG có cổng 5432/8000 bind ra host; `ufw status` chỉ 80/443/SSH.

- [ ] **Step 5: Android dùng chung API**

App Android trỏ `https://pos.timxe-namdinh.com/api` → đăng nhập + bán hàng chạy.

- [ ] **Step 6: Backup thật + restore thử**

```bash
bash ~/pos/scripts/backup.sh
rclone ls r2:pos-backups/ | tail -1
rclone ls gdrive:pos-backups/ | tail -1
```
Expected: file `pos_<STAMP>.sql.gz` xuất hiện ở **cả hai**. Thử restore vào DB tạm để chắc backup dùng được:
```bash
LATEST=$(ls -t ~/pos/backups/*.sql.gz | head -1)
docker compose -f ~/pos/docker-compose.deploy.yml exec -T db \
  sh -c 'createdb -U $POSTGRES_USER pos_restore_test && gunzip | psql -U $POSTGRES_USER pos_restore_test' < "$LATEST"
docker compose -f ~/pos/docker-compose.deploy.yml exec -T db \
  psql -U "$POSTGRES_USER" pos_restore_test -c '\dt' | head
```
Expected: liệt kê bảng (`tenants`, `users`, …). Dọn: `dropdb -U $POSTGRES_USER pos_restore_test`.

- [ ] **Step 7: Monitoring**

`free -h` thấy swap 2.0Gi; `crontab -l` có 2 dòng. Giả lập cảnh báo: tạm sửa ngưỡng trong `mem_watch.sh` (đổi `-gt 70` → `-gt 0`) + chạy 6 lần để ép gửi → nhận tin Telegram; sau đó **revert** ngưỡng.

---

## Self-Review

**1. Spec coverage:**
- Kiến trúc same-origin → Task 1 (nginx). ✅
- Right-size 1GB → Task 2 (compose) + Task 10 (swap). ✅
- Domain/Cloudflare → Task 9 + Task 1 (server_name) + Task 7 (CORS). ✅
- Triển khai/CI → Task 6 + Task 11. ✅
- Backup R2+GDrive → Task 3 + Task 10 (rclone) + Task 12 step 6. ✅
- Monitoring RAM → Task 4 + Task 10 + Task 12 step 7. ✅
- Scripts trong repo + setup-vps.sh → Task 3/4/5/6. ✅
- Nghiệm thu (DoD) → Task 12. ✅
- Bảo mật (no expose, secrets, COOKIE_SECURE) → Task 8 step 4, Task 10 step 1, Global Constraints. ✅
- Lối thoát/scale → tài liệu trong spec mục 6 (vận hành sau, không phải task triển khai ban đầu) — cố ý không tạo task. ✅

**2. Placeholder scan:** `<repo-url>`, `<IP VPS>`, `<STAMP>` là giá trị điền lúc chạy (đúng bản chất ops), không phải TODO logic. Không có "TBD/implement later".

**3. Type consistency:** Tên file/script (`backup.sh`, `mem_watch.sh`, `setup-vps.sh`), đường dẫn (`/home/deploy/pos`, `~/pos/scripts/`, `.deploy_secrets`, `.mem_watch_count`), remote rclone (`r2`, `gdrive`), service (`db`/`api`/`nginx`) nhất quán giữa các task.
