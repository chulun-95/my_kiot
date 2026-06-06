# Spec: Deploy lên Oracle Cloud Free VPS

**Ngày:** 2026-06-06
**Phạm vi:** Infrastructure & deployment — không động backend/frontend code
**Mục tiêu:** Đưa hệ thống POS lên Oracle Cloud Free Tier, luôn sẵn sàng cho shop thật dùng hàng ngày

---

## 1. Bối cảnh

Hệ thống đã hoàn chỉnh (backend 6 module + frontend 7 phase, 184 tests pass). Cần triển khai lên môi trường production miễn phí, always-on — không sleep giữa chừng.

**Ràng buộc:**
- Miễn phí (free tier)
- Always-on (POS mở cả ngày)
- Chưa có domain — dùng IP trực tiếp (HTTP) trong giai đoạn này
- Single VPS (theo kiến trúc CLAUDE.md)

---

## 2. Kiến trúc

```
Browser (POS + Admin)
       │ HTTP port 80 — Oracle Cloud public IP
       ▼
    Oracle Cloud VM (Ubuntu 22.04 LTS, Ampere ARM)
    ├── Nginx (port 80)
    │    ├── /api/*  → proxy → 127.0.0.1:8000 (FastAPI/Uvicorn)
    │    └── /*      → /var/www/kiot/ (React build — SPA)
    ├── Uvicorn 2 workers — backend.main:app trên 127.0.0.1:8000
    └── PostgreSQL 16 — localhost:5432
```

**Oracle VM tier khuyến nghị:** Ampere ARM (VM.Standard.A1.Flex) — Oracle Always Free cho tối đa 4 OCPU + 24GB RAM tổng. Chạy 1 VM với 2 OCPU + 4GB RAM là hợp lý và hoàn toàn nằm trong free tier.

**Về HTTPS:** Giai đoạn này dùng HTTP qua IP. Nâng cấp sau khi ổn định: mua domain → Cloudflare DNS → SSL miễn phí (Cloudflare Full mode hoặc Let's Encrypt).

**Oracle Cloud Security List:** Mặc định Oracle block tất cả incoming traffic. Phải thêm Ingress Rule trong OCI Console:
- Source: `0.0.0.0/0`, Protocol: TCP, Destination Port: `80`
- Source: `0.0.0.0/0`, Protocol: TCP, Destination Port: `22` (SSH — có thể giới hạn IP)

---

## 3. Cấu trúc files triển khai

```
deploy/
├── setup.sh              # Chạy 1 lần: cài packages, Postgres, Nginx, Python, Node
├── nginx.conf            # Config Nginx (reverse proxy + static files)
├── kiot-api.service      # systemd unit cho Uvicorn
├── deploy.sh             # Chạy mỗi lần release: pull → migrate → build → restart
└── backup.sh             # pg_dump nightly backup
```

File `.env.production.example` ở root repo (`.env.production` thật KHÔNG commit vào git).

---

## 3.5. Bước 0 — Tạo requirements.txt (làm trên máy dev trước)

`requirements.txt` chưa tồn tại trong repo. Cần tạo từ venv hiện tại:
```bash
# Trên máy dev (Windows):
.venv\Scripts\pip freeze > requirements.txt
# Kiểm tra: loại bỏ các package dev-only nếu có (aiosqlite dùng cho test — giữ lại nếu cần)
git add requirements.txt && git commit -m "chore: add requirements.txt for deployment"
```

Sau đó server chạy `pip install -r requirements.txt` sẽ có đúng deps.

---

## 4. setup.sh — Chi tiết

Script chạy một lần trên server mới. Chạy với quyền root hoặc sudo.

**Các bước:**
1. `apt update && apt upgrade -y`
2. Cài packages: `python3.11 python3.11-venv python3-pip postgresql nginx nodejs npm`
3. Tạo PostgreSQL role + database:
   ```sql
   CREATE USER pos_user WITH PASSWORD 'CHANGEME';
   CREATE DATABASE pos_db OWNER pos_user;
   ```
4. Tạo system user `kiot` (UID bình thường, không sudo):
   ```bash
   useradd -m -s /bin/bash kiot
   ```
5. Clone repo vào `/opt/kiot/`:
   ```bash
   git clone https://github.com/<user>/my_kiot.git /opt/kiot
   chown -R kiot:kiot /opt/kiot
   ```
6. Tạo Python venv + cài deps:
   ```bash
   sudo -u kiot python3.11 -m venv /opt/kiot/.venv
   sudo -u kiot /opt/kiot/.venv/bin/pip install -r /opt/kiot/requirements.txt
   ```
7. Copy `.env.production` → `/opt/kiot/.env`
8. Chạy Alembic migrations:
   ```bash
   sudo -u kiot bash -c 'cd /opt/kiot && .venv/bin/alembic upgrade head'
   ```
9. Build frontend:
   ```bash
   sudo -u kiot bash -c 'cd /opt/kiot/frontend && npm ci && npm run build'
   mkdir -p /var/www/kiot
   cp -r /opt/kiot/frontend/dist/* /var/www/kiot/
   ```
10. Copy Nginx config + reload:
    ```bash
    cp /opt/kiot/deploy/nginx.conf /etc/nginx/sites-available/kiot
    ln -s /etc/nginx/sites-available/kiot /etc/nginx/sites-enabled/kiot
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    ```
11. Install + start systemd service:
    ```bash
    cp /opt/kiot/deploy/kiot-api.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable kiot-api
    systemctl start kiot-api
    ```
12. Setup backup cron:
    ```bash
    cp /opt/kiot/deploy/backup.sh /usr/local/bin/kiot-backup.sh
    chmod +x /usr/local/bin/kiot-backup.sh
    echo "0 2 * * * kiot /usr/local/bin/kiot-backup.sh" | crontab -u kiot -
    ```

---

## 5. nginx.conf

```nginx
server {
    listen 80;
    server_name _;

    # Deny direct access (không qua /api/ prefix)
    # API → FastAPI
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
        client_max_body_size 10m;  # upload ảnh sản phẩm
    }

    # Frontend → React SPA build
    location / {
        root       /var/www/kiot;
        try_files  $uri $uri/ /index.html;
        expires    1h;
        add_header Cache-Control "public, max-age=3600";
    }

    # Static assets với cache dài hơn
    location ~* \.(js|css|png|svg|ico|webmanifest)$ {
        root    /var/www/kiot;
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }
}
```

**Lưu ý:** Backend FastAPI mount tất cả routes dưới `/api/v1/` (xem `backend/main.py`). Frontend Vite phải config `VITE_API_BASE_URL=/api/v1` hoặc `axios` base URL tương ứng.

---

## 6. kiot-api.service

```ini
[Unit]
Description=Kiot POS FastAPI Backend
Documentation=https://github.com/<user>/my_kiot
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=kiot
Group=kiot
WorkingDirectory=/opt/kiot
EnvironmentFile=/opt/kiot/.env
ExecStart=/opt/kiot/.venv/bin/uvicorn backend.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --log-level info \
    --access-log
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kiot-api

[Install]
WantedBy=multi-user.target
```

**Workers:** 2 cho AMD Micro (1GB RAM). Nếu dùng Ampere ARM với 4GB+ RAM → đổi thành `--workers 4`.

---

## 7. deploy.sh — Update khi release mới

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/kiot
WEBROOT=/var/www/kiot

echo "[deploy] Pulling latest code..."
cd "$APP_DIR"
git pull origin master

echo "[deploy] Installing Python dependencies..."
sudo -u kiot "$APP_DIR/.venv/bin/pip" install -r requirements.txt --quiet

echo "[deploy] Running database migrations..."
sudo -u kiot bash -c "cd $APP_DIR && .venv/bin/alembic upgrade head"

echo "[deploy] Building frontend..."
sudo -u kiot bash -c "cd $APP_DIR/frontend && npm ci --quiet && npm run build"

echo "[deploy] Copying build to webroot..."
rm -rf "$WEBROOT"/*
cp -r "$APP_DIR/frontend/dist/." "$WEBROOT/"

echo "[deploy] Restarting API service..."
systemctl restart kiot-api

echo "[deploy] Done. Status:"
systemctl status kiot-api --no-pager -l
```

Chạy: `sudo bash /opt/kiot/deploy/deploy.sh`

---

## 8. backup.sh — pg_dump nightly

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=/home/kiot/backups
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pos_db_$DATE.sql.gz"

mkdir -p "$BACKUP_DIR"

pg_dump -U pos_user -h localhost pos_db | gzip > "$BACKUP_FILE"

# Giữ tối đa 30 ngày backup
find "$BACKUP_DIR" -name "pos_db_*.sql.gz" -mtime +30 -delete

echo "Backup saved: $BACKUP_FILE"
```

Cần `.pgpass` hoặc `PGPASSWORD` env trong cron. Setup `.pgpass`:
```
localhost:5432:pos_db:pos_user:CHANGEME
```
File `~/.pgpass` của user `kiot`, chmod `600`.

---

## 9. .env.production.example

```env
# Database
DATABASE_URL=postgresql+asyncpg://pos_user:CHANGEME@localhost:5432/pos_db

# JWT — sinh bằng: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=CHANGE_THIS_64_CHAR_SECRET

JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12

# App
APP_ENV=production

# CORS — IP của VPS (thêm cả http:// và không có trailing slash)
CORS_ORIGINS=http://<VPS_PUBLIC_IP>
```

---

## 10. Frontend API URL config

`frontend/src/api/client.ts` đã có sẵn:
```ts
const baseURL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api/v1';
```

Vì Nginx serve cả frontend lẫn API trên cùng host, relative URL `/api/v1` hoạt động đúng ngay. **Không cần tạo `frontend/.env.production`** — không cần sửa gì ở frontend cho deployment này.

---

## 11. Oracle Cloud — checklist quan trọng

- [ ] Tạo VM: Shape **VM.Standard.A1.Flex** (Ampere ARM), Ubuntu 22.04, 2 OCPU + 4GB RAM
- [ ] Download SSH key khi tạo VM (không có cơ hội download lại)
- [ ] Trong OCI Console → VCN → Security List → thêm Ingress Rules:
  - TCP port 22 (SSH)
  - TCP port 80 (HTTP)
- [ ] Trên Ubuntu: `sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT` (Oracle Ubuntu có iptables rule block port 80 mặc định ngoài Security List)
- [ ] Persistent iptables: `sudo netfilter-persistent save` (cài gói `iptables-persistent` trước)

---

## 12. Acceptance criteria

- [ ] `curl http://<VPS_IP>/api/v1/health` → `{"status":"ok","env":"production"}`
- [ ] `curl http://<VPS_IP>/` → trả về HTML của React app
- [ ] Đăng ký shop mới từ browser trên điện thoại/máy tính khác → thành công
- [ ] Tạo sản phẩm, tạo hóa đơn POS → thành công
- [ ] `systemctl status kiot-api` → `active (running)`
- [ ] Backup cron chạy: kiểm tra `/home/kiot/backups/` có file sau 2h sáng
- [ ] `journalctl -u kiot-api -f` không có ERROR
