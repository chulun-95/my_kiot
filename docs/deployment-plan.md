# Kế hoạch Deploy — POS System

Hai giai đoạn:

- **Giai đoạn 1 (now → ~30 shop):** 1 VPS Hetzner CX22, Docker Compose (db + api + nginx), Cloudflare đứng trước. Chi phí ~110k VNĐ/tháng.
- **Giai đoạn 2 (→ 50 shop):** resize lên CX32, tách DB ra VPS riêng khi cần, tuning + monitoring + backup off-site. Chi phí ~330–550k VNĐ/tháng.

Nguyên tắc xuyên suốt: **FE + BE cùng 1 origin** (`https://app.tencuahang.vn`). Nginx serve React build ở `/`, reverse proxy `/api` → uvicorn. Nhờ vậy cookie refresh token (`HttpOnly; SameSite=Strict`) chạy same-origin, **không cần CORS, không cần cross-site cookie**.

```
Internet ──HTTPS──▶ Cloudflare (SSL, CDN ảnh, DDoS)
                        │ Origin cert (Full strict)
                        ▼
                 Hetzner VPS (1 máy)
                 ┌──────────────────────────────┐
                 │ Docker Compose                │
                 │  nginx  :443 ─┬─ /     → FE   │  (serve /dist tĩnh)
                 │               └─ /api  → api  │  (proxy → uvicorn:8000)
                 │  api    :8000  FastAPI/uvicorn │
                 │  db     :5432  postgres:16     │  (chỉ expose nội bộ)
                 └──────────────────────────────┘
                 R2 (Cloudflare) cho ảnh sản phẩm
```

---

# GIAI ĐOẠN 1 — 1 VPS Hetzner CX22

## 0. Mua sắm & chuẩn bị (1 lần)

| Việc | Chi tiết |
|---|---|
| **VPS** | Hetzner Cloud → tạo server **CX22** (2 vCPU, 4GB RAM, 40GB), image **Ubuntu 24.04**, region Falkenstein/Nuremberg. Bật **backup** (+20% giá ≈ €0.76/tháng) — nên bật. |
| **SSH key** | Tạo key, add vào server lúc tạo (không dùng password login). |
| **Domain** | Trỏ nameserver về **Cloudflare** (free plan). Tạo bản ghi `A app → <IP VPS>`, bật **proxy (đám mây cam)**. |
| **Cloudflare SSL** | SSL/TLS mode = **Full (strict)**. Tạo **Origin Certificate** (15 năm) → lưu `origin.pem` + `origin.key` để cắm vào Nginx. |
| **R2** | Tạo bucket `pos-images`, tạo API token (Access Key/Secret) cho backend presign + cho rclone backup. |

## 1. Harden server (chạy 1 lần, ~10 phút)

```bash
# SSH vào bằng root
adduser deploy && usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy   # copy authorized_keys

# /etc/ssh/sshd_config: PermitRootLogin no | PasswordAuthentication no
systemctl restart ssh

# Firewall: chỉ mở SSH + HTTPS. KHÔNG mở 5432, 8000 ra ngoài.
ufw allow OpenSSH && ufw allow 443/tcp && ufw allow 80/tcp && ufw --force enable

# (Khuyến nghị) chỉ cho Cloudflare gọi 443 — siết sau, xem mục Bảo mật.
# Cài Docker Engine + compose plugin theo hướng dẫn chính thức:
#   https://docs.docker.com/engine/install/ubuntu/  (curl -fsSL get.docker.com | sh là cách nhanh)
apt update && apt -y upgrade && apt -y install git
curl -fsSL https://get.docker.com | sh    # cài docker + plugin `docker compose`
systemctl enable --now docker
usermod -aG docker deploy
```

## 2. Files cần thêm vào repo

Tạo các file dưới đây (đặt trong repo, commit lại). Đây là toàn bộ phần "deploy" còn thiếu.

### 2.1 `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# deps trước để tận dụng cache
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# code
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000
# 4 worker đúng như CLAUDE.md (CX22 2 vCPU → 4 worker vẫn ổn vì I/O-bound)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2.2 `frontend/Dockerfile` (multi-stage: build → nginx serve)

```dockerfile
# --- build ---
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # ra /app/dist

# --- serve ---
FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
```

> FE giữ nguyên `baseURL = '/api/v1'` (mặc định trong `client.ts`) → **không cần `VITE_API_BASE_URL`**, vì cùng origin.

### 2.3 `frontend/nginx.conf`

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name app.tencuahang.vn;

    ssl_certificate     /etc/nginx/ssl/origin.pem;
    ssl_certificate_key /etc/nginx/ssl/origin.key;

    client_max_body_size 12m;             # cho upload ảnh SP
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;

    # SPA: file tĩnh, fallback index.html cho client-side routing
    root /usr/share/nginx/html;
    index index.html;

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API → uvicorn. Giữ nguyên path /api/... (router đã prefix /api/v1)
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }
}

# 80 → 443 (Cloudflare đã ép HTTPS, đây là dự phòng)
server {
    listen 80;
    server_name app.tencuahang.vn;
    return 301 https://$host$request_uri;
}
```

### 2.4 `docker-compose.prod.yml` (ở root repo)

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pos_db_data:/var/lib/postgresql/data
    # KHÔNG mở ports ra host — chỉ api truy cập nội bộ network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 10

  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: always
    env_file: .env.prod
    depends_on:
      db:
        condition: service_healthy
    # Chạy migration rồi mới start app
    command: >
      sh -c "alembic upgrade head &&
             uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4"

  nginx:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl:ro     # origin.pem + origin.key
    depends_on:
      - api

volumes:
  pos_db_data:
```

### 2.5 `.env.prod` (TẠO TRÊN SERVER, **không commit** — thêm vào `.gitignore`)

```bash
# --- DB (api ↔ db qua service name 'db') ---
POSTGRES_USER=pos_user
POSTGRES_PASSWORD=<random-mạnh-32-ký-tự>
POSTGRES_DB=pos_db
DATABASE_URL=postgresql+asyncpg://pos_user:<password-trên>@db:5432/pos_db

# --- App ---
APP_ENV=production
JWT_SECRET_KEY=<64-ký-tự-random>           # openssl rand -hex 32
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12

# QUAN TRỌNG: HTTPS production → cookie phải Secure
COOKIE_SECURE=true

# Same-origin nên CORS gần như không cần; để trống hoặc domain thật
CORS_ORIGINS=https://app.tencuahang.vn

# --- R2 ảnh sản phẩm (backend presign) ---
R2_ACCOUNT_ID=...
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_BUCKET=pos-images
```

> Lưu ý 2 thay đổi mấu chốt so với dev: `DATABASE_URL` host = `db` (tên service), và `COOKIE_SECURE=true`.

## 3. Quy trình deploy (mỗi lần lên phiên bản mới)

```bash
ssh deploy@<IP>
git clone <repo> ~/pos && cd ~/pos          # lần đầu; sau này chỉ git pull
# Lần đầu: tạo .env.prod + bỏ origin.pem/origin.key vào ~/pos/ssl/

# Deploy
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Migration tự chạy trong service 'api' (command ở trên). Kiểm tra:
docker compose -f docker-compose.prod.yml logs -f api
curl -k https://localhost/api/v1/../health    # hoặc gọi /health qua domain
```

Gợi ý: gói 3 dòng trên thành `deploy.sh` để bấm 1 phát.

## 4. Backup (bắt buộc — cron trên host)

`/home/deploy/backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%F_%H%M)
FILE=/home/deploy/backups/pos_$STAMP.sql.gz
mkdir -p /home/deploy/backups
docker compose -f /home/deploy/pos/docker-compose.prod.yml exec -T db \
  pg_dump -U pos_user pos_db | gzip > "$FILE"
# Đẩy off-site lên R2 (đã cấu hình rclone remote 'r2')
rclone copy "$FILE" r2:pos-backups/
# Giữ 14 ngày local
find /home/deploy/backups -name '*.sql.gz' -mtime +14 -delete
```

```bash
chmod +x backup.sh
crontab -e
# 2h sáng mỗi ngày
0 2 * * * /home/deploy/backup.sh >> /home/deploy/backup.log 2>&1
# 3h sáng: dọn refresh_token & audit hết hạn (xem CLAUDE.md retention)
```

## 5. Checklist nghiệm thu Giai đoạn 1

- [ ] `https://app.tencuahang.vn` mở được, hiện UI (Cloudflare cam, SSL Full strict)
- [ ] Login → set cookie `Secure; HttpOnly; SameSite=Strict`, refresh token chạy (mở lại tab vẫn đăng nhập)
- [ ] `GET /health` trả `{"status":"ok","env":"production"}`
- [ ] Tạo SP có ảnh → ảnh lưu R2, render qua CDN
- [ ] `ufw status`: chỉ 80/443/SSH; `docker ps`: cổng 5432/8000 KHÔNG bind ra host
- [ ] Chạy `backup.sh` thủ công 1 lần → có file trên R2; thử **restore vào DB tạm** để chắc backup dùng được
- [ ] Tạo 2 tenant test → xác nhận tenant A không thấy data tenant B

---

# CI/CD — Tự động test + build + deploy (GitHub Actions)

Mô hình: **build trên GitHub → đẩy image lên GHCR → VPS chỉ pull + restart.** VPS CX22 không phải tự build (tiết kiệm RAM/CPU lúc deploy).

```
PR / push nhánh  ──▶ ci.yml      : pytest + FE lint/build   (chặn merge code hỏng)
push master      ──▶ deploy.yml  : test ▸ build+push GHCR ▸ SSH vào VPS pull+up -d
```

File liên quan (đã tạo trong repo):
- `.github/workflows/ci.yml` — test gate cho PR/nhánh
- `.github/workflows/deploy.yml` — build + push GHCR + deploy khi push master
- `docker-compose.deploy.yml` — compose chạy TRÊN VPS, dùng `image:` từ GHCR (khác `docker-compose.prod.yml` vốn `build:` tại chỗ — file đó giữ để bootstrap/chạy tay)

## 1. Tạo SSH key cho CI (1 lần)

```bash
# Trên máy bạn — tạo key riêng cho CI (đừng dùng key cá nhân)
ssh-keygen -t ed25519 -C "github-deploy" -f ci_deploy -N ""
# Public key → thêm vào VPS cho user deploy
ssh-copy-id -i ci_deploy.pub deploy@<IP_VPS>      # hoặc dán vào ~deploy/.ssh/authorized_keys
# Private key (nội dung file ci_deploy) → dán vào GitHub secret SSH_KEY
```

## 2. Khai báo GitHub Secrets

Repo → **Settings ▸ Secrets and variables ▸ Actions ▸ New repository secret**:

| Secret | Giá trị |
|---|---|
| `SSH_HOST` | IP public của VPS |
| `SSH_USER` | `deploy` |
| `SSH_KEY` | Toàn bộ nội dung private key `ci_deploy` |

> Không cần secret cho GHCR: workflow dùng `GITHUB_TOKEN` tự cấp (có quyền `packages: write` để push, và forward sang VPS để `docker login` pull). Image GHCR mặc định **private** — chỉ VPS (qua token) và bạn pull được.

## 3. Bootstrap VPS (1 lần, trước lần deploy đầu)

CI chỉ pull image + chạy compose; **dữ liệu cấu hình phải có sẵn trên VPS**:

```bash
ssh deploy@<IP_VPS>
mkdir -p ~/pos/ssl
# 1) .env.prod — copy từ .env.prod.example rồi điền secret thật
nano ~/pos/.env.prod
# 2) Cloudflare Origin Certificate
nano ~/pos/ssl/origin.pem      # dán cert
nano ~/pos/ssl/origin.key      # dán private key
```

Sau đó **push lên master** (hoặc bấm *Run workflow* ở tab Actions) → pipeline tự build + deploy. Lần đầu, service `api` sẽ tự `alembic upgrade head` tạo schema.

## 4. Cách hoạt động & vận hành

- **Mỗi commit master** → image gắn 2 tag: `latest` và `:<git-sha>`. VPS deploy đúng tag sha của commit đó (reproducible).
- **Rollback:** SSH vào VPS, đặt tag cũ rồi up lại:
  ```bash
  cd ~/pos && export IMAGE_TAG=<git-sha-cũ>
  docker compose -f docker-compose.deploy.yml up -d
  ```
- **Migration** chạy tự động trong service `api` mỗi lần lên. Migration phải **backward-compatible** (cộng cột nullable trước, bỏ cột ở release sau) để rollback an toàn.
- **Deploy tay** khi cần: tab Actions → *Deploy* → *Run workflow* (dùng tag `latest`).

## 5. (Tùy chọn) Bảo vệ nhánh master

Settings ▸ Branches ▸ thêm rule cho `master`: yêu cầu PR + **CI phải pass** mới merge được → mọi thứ lên production đều đã qua test.

---

# GIAI ĐOẠN 2 — Nâng lên ~50 cửa hàng

Không viết lại kiến trúc. Nâng cấp theo **trigger** (chỉ làm khi chạm ngưỡng), theo thứ tự rẻ → đắt.

## Bước 2.1 — Resize VPS (làm đầu tiên, ~5 phút, gần như không downtime)

Khi RAM/CPU thường xuyên > 70%:
- Hetzner Console → **Resize CX22 → CX32** (4 vCPU, 8GB). Giữ nguyên disk & data.
- Tăng worker uvicorn theo CPU: `--workers` ≈ `2 × vCPU` (I/O-bound) → **8 worker**.
- Trong `docker-compose.prod.yml` đặt `mem_limit` cho `db` và `api` để Postgres không bị OOM.

## Bước 2.2 — Tuning PostgreSQL (miễn phí, hiệu quả nhất)

Mount file tuning vào service `db` (volume `./postgres.conf:/etc/postgresql/postgresql.conf`) hoặc `command: -c ...`. Với 8GB RAM, ~½ cho DB:

```conf
shared_buffers = 2GB
effective_cache_size = 4GB
work_mem = 32MB
maintenance_work_mem = 256MB
max_connections = 100
random_page_cost = 1.1        # SSD
```

- **Verify index đang được dùng:** chạy `EXPLAIN ANALYZE` cho 3 query nóng nhất (POS search SP, dashboard hôm nay, kardex). Các index trong CLAUDE.md Phần 8 phải hit — nếu seq scan thì thiếu index.
- Bật `pg_stat_statements` để tìm query chậm.

## Bước 2.3 — Tách DB ra VPS riêng (khi DB và app tranh tài nguyên)

Trigger: dashboard/report aggregate làm chậm POS, hoặc CPU DB thường > 60%.

1. Tạo **CX22 thứ 2** chỉ chạy Postgres, **đặt cùng private network** Hetzner (miễn phí, nội bộ).
2. App server đổi `DATABASE_URL` → IP private của DB server. Postgres `listen_addresses` chỉ mở trên private network, `pg_hba.conf` chỉ cho subnet nội bộ. **Không bao giờ** expose Postgres ra Internet.
3. Migrate data: `pg_dump` từ máy cũ → `pg_restore` máy mới, cập nhật `DATABASE_URL`, đổi lịch backup sang chạy trên DB server.
4. (Tùy chọn) Cân nhắc managed DB thay vì tự quản: DigitalOcean Managed PG (~$15–30) hoặc Neon Scale (~$69) — đổi tiền lấy backup/HA tự động.

## Bước 2.4 — Quan sát & độ bền (nên có ở mức 50 shop)

- **Monitoring:** UptimeRobot (free) ping `/health` mỗi 5 phút + báo Telegram/email. Thêm `docker stats`/netdata cho CPU/RAM/disk.
- **Log:** gom log uvicorn + nginx (docker logging driver, rotate). Cảnh báo khi 5xx tăng.
- **Sentry** (free tier) cho lỗi backend — bắt exception thật từ người dùng.
- **Cloudflare:** bật rate-limit rule cho `/api/v1/auth/*` (bổ trợ slowapi). Bật caching cho ảnh R2.
- **Backup:** giữ pg_dump đêm + thêm **Hetzner snapshot** hằng tuần; test restore hằng tháng. Retention audit/stock_movements 1 năm (cron như CLAUDE.md).

## Bước 2.5 — Zero-downtime deploy (tùy chọn, khi không được phép gián đoạn)

- Chạy 2 replica `api`, Nginx load-balance, deploy lăn (rolling) từng cái.
- Tách bước migration ra khỏi lệnh start app (chạy `alembic upgrade head` 1 lần trước khi rollout), để không 2 worker cùng migrate.

## Bảng quyết định nâng cấp (chỉ làm khi chạm trigger)

| Trigger quan sát được | Hành động | Chi phí thêm |
|---|---|---|
| RAM/CPU app > 70% kéo dài | Resize CX22→CX32, tăng workers | +~€7/th |
| Query chậm, seq scan | Tuning Postgres + kiểm tra index | €0 |
| Report làm chậm POS | Tách DB ra VPS riêng (private network) | +~€4/th |
| Cần backup/HA tự động, ngại tự quản DB | Managed Postgres | +$15–69/th |
| Cần uptime cao, deploy không downtime | 2 replica api + rolling deploy | €0 (cùng VPS) |

---

## Phụ lục — Lưu ý bảo mật chốt lại

1. **Postgres không bao giờ ra Internet.** GĐ1 không bind port; GĐ2 chỉ private network + `pg_hba` siết subnet.
2. **Secrets** (`.env.prod`, `origin.key`, R2 keys) chỉ nằm trên server, trong `.gitignore`. Không commit.
3. **Siết 443 chỉ cho Cloudflare** (GĐ2): `ufw` chỉ allow dải IP Cloudflare vào 443 → chặn truy cập thẳng IP gốc, không bypass được WAF.
4. **`COOKIE_SECURE=true`** ở production (đã có trong config). Triển khai lần đầu sẽ **logout toàn bộ user 1 lần** (đổi thuộc tính cookie) — bình thường.
5. Đổi mặc định: `JWT_SECRET_KEY` random 64 ký tự, password Postgres mạnh, không dùng `pos_secret`.
```
