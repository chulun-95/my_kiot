# Spec Deploy — VPS Việt Nam 1GB (khởi đầu) → resize/đổi VPS (lối thoát)

> Ngày: 2026-06-19
> Mục tiêu: đưa Backend (FastAPI) + Web (React) lên Internet cho người dùng ngoài truy cập,
> phục vụ ~5 cửa hàng, chi phí thấp nhất có thể mà vẫn **always-on** (không cold-start),
> và dễ dàng scale/chuyển đổi khi nhiều cửa hàng hơn.

## 0. Bối cảnh & quyết định đã chốt

Repo đã có sẵn kế hoạch deploy VPS ([docs/deployment-plan.md](../../deployment-plan.md)) cùng
artifact: `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`,
`docker-compose.deploy.yml`, `docker-compose.prod.yml`, `.env.prod.example`, và CI/CD
(`.github/workflows/ci.yml`, `deploy.yml`). Spec này **không viết lại** chúng — chỉ chốt
provider, right-size cho 1GB, và bổ sung phần còn thiếu (monitoring, backup 2 nơi, subdomain).

Các quyết định đã chốt qua brainstorming:

| Hạng mục | Quyết định | Lý do |
|---|---|---|
| Hạ tầng | **1 VPS Việt Nam, 1GB RAM** (AZDIGI / Vietnix / Tinohost…) | Không cần thẻ quốc tế (trả Momo/CK), latency thấp nhất (<20ms), always-on, không lo thu hồi máy |
| Khu vực | Việt Nam | Khách 5 cửa hàng ở VN, bấm POS mượt nhất |
| Web hosting | Nginx trên cùng VPS serve React build | **Same-origin** → cookie `HttpOnly; SameSite=Strict` chạy chuẩn, không cần CORS |
| CDN/SSL/DDoS | Cloudflare (free) | Domain `timxe-namdinh.com` **đã ở Cloudflare** |
| Domain | Subdomain `pos.timxe-namdinh.com` | Tái dùng domain có sẵn; không đụng site gốc |
| Backup | Local 14 ngày + đẩy **song song R2 + Google Drive** | 2 bản off-site ở 2 nhà khác nhau cho an toàn |
| Scale | Giám sát tự động → **cảnh báo** → người tự bấm resize lên 2GB | VPS prepaid không auto-scale; resize cần reboot nên phải chủ động chọn giờ |
| Kiến trúc CPU | x86 (amd64) | VPS VN là x86 → **giữ nguyên** image hiện có, không cần build arm64 |

**Đã loại trừ (và lý do):**
- *Oracle Cloud Always Free*: 0đ nhưng bắt add thẻ (không xóa được), rủi ro thu hồi VM idle, cần CI build arm64.
- *AWS*: free chỉ 12 tháng rồi tính tiền; cần thẻ.
- *Managed PaaS (Render/Railway/Fly)*: free tier sleep (cold-start); always-on phải trả phí + tách origin gây phức tạp cookie.
- *Deploy hết lên Cloudflare*: Workers chạy JS (không chạy FastAPI/asyncpg/bcrypt), D1 là SQLite (mất `JSONB`, `pg_trgm`, `SELECT FOR UPDATE` chống race tồn kho) → phải viết lại cả BE + DB. Không đáng.

## 1. Kiến trúc đích

```
Internet ──HTTPS──▶ Cloudflare (free: SSL, CDN, DDoS)
                    (timxe-namdinh.com đã ở Cloudflare; thêm bản ghi A: pos → IP VPS)
                        │  Origin Certificate (SSL/TLS = Full strict)
                        ▼
              VPS Việt Nam — 1GB RAM / ~1 vCPU / 40–50GB SSD, Ubuntu 24.04
              ┌──────────────────────────────────────┐
              │ Docker Compose (docker-compose.deploy.yml)
              │  nginx :443 ─┬ /     → FE (dist tĩnh)  │  same-origin
              │              └ /api  → api:8000        │  reverse proxy
              │  api          FastAPI/uvicorn (1 worker)│
              │  db           postgres:16-alpine        │  KHÔNG expose ra host
              └──────────────────────────────────────┘
              + swap 2GB (chống OOM)
              + cron: backup đêm, cleanup token, monitoring RAM
              (Android app dùng chung: https://pos.timxe-namdinh.com/api)
```

Nguyên tắc xuyên suốt giữ nguyên từ plan gốc: **FE + BE cùng 1 origin** (`https://pos.timxe-namdinh.com`).
Nginx serve React ở `/`, reverse proxy `/api` → uvicorn. FE giữ `baseURL = '/api/v1'` (mặc định
trong `client.ts`) → **không cần** `VITE_API_BASE_URL`.

## 2. Right-size cho 1GB RAM (điều chỉnh quan trọng so với plan gốc)

Plan gốc thiết kế cho VPS 4GB (CX22) với 4 worker. Trên 1GB phải hạ tải:

| Thông số | Plan gốc (4GB) | Spec này (1GB) | File chỉnh |
|---|---|---|---|
| uvicorn workers | 4 | **1** | `docker-compose.deploy.yml` (command của service `api`) |
| swap | — | **2GB** | tạo trên host (1 lần) |
| `mem_limit` api | — | ~**512MB** | `docker-compose.deploy.yml` |
| `mem_limit` db | — | ~**384MB** | `docker-compose.deploy.yml` |
| Postgres `shared_buffers` | (mặc định) | **128MB** | command `-c` hoặc conf mount |
| Postgres `effective_cache_size` | — | **512MB** | nt |
| Postgres `work_mem` | — | **8MB** | nt |
| Postgres `max_connections` | 100 | **30** | nt |

> Lý do: 1GB phải chia cho Postgres + uvicorn + nginx + OS. 1 worker async của FastAPI dư sức
> cho 5 cửa hàng (tải I/O-bound, đồng thời thấp). Swap 2GB là phao cứu sinh khi cao điểm.

**Sửa command service `api` trong `docker-compose.deploy.yml`:**
`uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1`
(hiện đang `--workers 4`).

## 3. Tên miền & Cloudflare (đơn giản vì domain đã ở Cloudflare)

1. Cloudflare Dashboard → zone `timxe-namdinh.com` → DNS → thêm bản ghi:
   `A` | name `pos` | IPv4 = `<IP public VPS>` | Proxy **ON** (đám mây cam).
   → **Không** ảnh hưởng site gốc `timxe-namdinh.com` / các bản ghi khác.
2. SSL/TLS → mode = **Full (strict)**.
3. SSL/TLS → Origin Server → **Create Certificate** (15 năm) → lưu thành `origin.pem` + `origin.key`
   → đặt vào `~/pos/ssl/` trên VPS (nginx đọc theo `frontend/nginx.conf`).
4. `frontend/nginx.conf`: đổi `server_name` thành `pos.timxe-namdinh.com` (hiện đang placeholder
   `app.tencuahang.vn`).

## 4. Triển khai

### 4.1 Một lần — chuẩn bị VPS
1. Mua VPS VN 1GB (chọn nhà cung cấp **có sẵn cả gói 1GB và 2GB+** để sau resize trong cùng hệ thống:
   AZDIGI / Vietnix / BizFly…). Trả Momo/CK. OS: **Ubuntu 24.04**.
2. Harden (theo `deployment-plan.md` mục 1):
   - Tạo user `deploy`, thêm SSH key, copy `authorized_keys`.
   - `sshd_config`: `PermitRootLogin no`, `PasswordAuthentication no` → restart ssh.
   - `ufw allow OpenSSH && ufw allow 80,443/tcp && ufw --force enable`. **KHÔNG** mở 5432/8000.
3. Cài Docker Engine + compose plugin (`curl -fsSL https://get.docker.com | sh`), `usermod -aG docker deploy`.
4. **Tạo swap 2GB** (1 lần):
   ```bash
   fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```
5. `mkdir -p ~/pos/ssl` → đặt `.env.prod` (từ `.env.prod.example`, điền secret thật, `COOKIE_SECURE=true`,
   `CORS_ORIGINS=https://pos.timxe-namdinh.com`, password DB + `JWT_SECRET_KEY` random `openssl rand -hex 32`)
   + `ssl/origin.pem`, `ssl/origin.key`.

### 4.2 Mỗi lần — CI/CD tự động (đã có sẵn)
- Khai báo 3 GitHub secret: `SSH_HOST` (IP VPS), `SSH_USER` (`deploy`), `SSH_KEY` (private key CI).
- Push `master` → `deploy.yml`: test → build image (amd64) lên GHCR → SSH vào VPS `pull + up -d`.
  Migration `alembic upgrade head` tự chạy trong service `api`.
- Rollback: SSH vào VPS, `export IMAGE_TAG=<git-sha-cũ>` rồi `docker compose -f docker-compose.deploy.yml up -d`.

### 4.3 Backup (cron trên host — KHÔNG phải BE)
`/home/deploy/backup.sh` (chạy 2h sáng qua cron):
```bash
#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%F_%H%M)
FILE=/home/deploy/backups/pos_$STAMP.sql.gz
mkdir -p /home/deploy/backups
docker compose -f /home/deploy/pos/docker-compose.deploy.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$FILE"
rclone copy "$FILE" r2:pos-backups/        # off-site 1: Cloudflare R2 (free 10GB)
rclone copy "$FILE" gdrive:pos-backups/    # off-site 2: Google Drive
find /home/deploy/backups -name '*.sql.gz' -mtime +14 -delete   # giữ 14 ngày local
```
- Cấu hình 2 rclone remote (1 lần): `r2` (S3-compatible, dùng R2 token) và `gdrive` (OAuth Google).
- Cron đêm khác: cleanup `refresh_tokens`/`audit_logs` hết hạn (xem retention trong CLAUDE.md).

### 4.4 Monitoring + cảnh báo resize (phần mới)
`/home/deploy/mem_watch.sh` (cron 5 phút/lần) — logic "RAM > 70% liên tục ≥ 30 phút thì cảnh báo":
```bash
#!/usr/bin/env bash
# Đọc % RAM dùng; nếu > 70% thì tăng đếm, ngược lại reset.
# Khi đếm đạt 6 lần liên tiếp (6 × 5 phút = 30 phút) → gửi Telegram rồi reset.
set -euo pipefail
STATE=/home/deploy/.mem_watch_count
USED=$(free | awk '/Mem:/ {printf("%d", $3/$2*100)}')
if [ "$USED" -gt 70 ]; then c=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 )); else c=0; fi
echo "$c" > "$STATE"
if [ "$c" -ge 6 ]; then
  curl -s "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -d chat_id="$TG_CHAT" \
    -d text="⚠️ POS VPS: RAM > 70% suốt 30 phút (hiện ${USED}%). Cân nhắc resize lên 2GB lúc vắng khách." >/dev/null
  echo 0 > "$STATE"
fi
```
- Bổ trợ: UptimeRobot (free) ping health mỗi 5 phút → báo khi sập.
  ⚠️ Endpoint `/health` đăng ký ở **gốc uvicorn** (`backend/main.py`), nhưng nginx hiện chỉ proxy `/api/` → uvicorn,
  còn `/` là static FE. Nên cần **thêm 1 location vào `frontend/nginx.conf`** để health tới được API từ ngoài:
  ```nginx
  location = /health { proxy_pass http://api:8000/health; }
  ```
  (hoặc giám sát nội bộ trên VPS: `docker compose exec -T api curl -fs localhost:8000/health`).
- **Quyết định nâng là thủ công** (panel VPS → resize 2GB → reboot vài phút, chọn giờ vắng khách).
  VPS prepaid không auto-scale; resize dọc luôn cần reboot nên không nên giao máy tự làm trong giờ bán.

## 5. Nghiệm thu (Definition of Done)

- [ ] `https://pos.timxe-namdinh.com` mở được, hiện UI; SSL Full strict (ổ khóa hợp lệ).
- [ ] Site gốc `timxe-namdinh.com` **vẫn chạy bình thường** (không bị ảnh hưởng).
- [ ] Login → set cookie `Secure; HttpOnly; SameSite=Strict`; refresh token chạy (mở lại tab vẫn đăng nhập).
- [ ] Health trả `{"status":"ok","env":"production"}` — qua `https://pos.timxe-namdinh.com/health` (sau khi thêm location nginx ở mục 4.4) hoặc nội bộ `docker compose exec -T api curl -fs localhost:8000/health`.
- [ ] `ufw status`: chỉ 80/443/SSH; `docker ps`: KHÔNG bind 5432/8000 ra host.
- [ ] Tạo 2 tenant test → tenant A không thấy data tenant B.
- [ ] App Android trỏ `https://pos.timxe-namdinh.com/api` → đăng nhập + bán hàng chạy.
- [ ] Chạy `backup.sh` thủ công 1 lần → có file trên **cả R2 và Google Drive**; thử **restore vào DB tạm** để chắc backup dùng được.
- [ ] `mem_watch.sh` chạy thử (giả lập RAM cao) → nhận được tin Telegram.
- [ ] `free -h` cho thấy swap 2GB đã bật.

## 6. Lối thoát / Scale (khi chạm trigger)

| Trigger quan sát được | Hành động | Chi phí thêm |
|---|---|---|
| Cảnh báo RAM > 70% / 30 phút kéo dài nhiều ngày | **Resize 1GB → 2GB** trong panel (reboot ~vài phút, giữ data) + đổi `--workers 2` | +~40–110k/th (chỉ trả khi nâng; prorate phần còn lại của chu kỳ) |
| Cần ổn định/tài nguyên hơn, hoặc đổi nhà cung cấp | Đổi VPS khác (kể cả Hetzner/Oracle): vì cùng Docker → `pg_dump`/restore + đổi bản ghi `A` Cloudflare sang IP mới | tùy VPS đích (nếu đích ARM như Oracle thì lúc đó mới build image arm64) |
| Report làm chậm POS / DB tranh tài nguyên | Tách DB ra VPS riêng + private network (theo `deployment-plan.md` GĐ2) | +1 VPS |

**Khẳng định "dễ chuyển đổi":** BE đóng gói Docker (amd64), DB là PostgreSQL chuẩn, FE là build tĩnh.
Di chuyển giữa các nhà cung cấp = chạy lại cùng container + `pg_dump`/`pg_restore` + đổi DNS. Không khóa cứng.

## 7. Bảo mật (chốt lại)

1. **Postgres không bao giờ ra Internet** — không bind port ra host (compose chỉ network nội bộ).
2. **Secrets** (`.env.prod`, `origin.key`, R2/Google token) chỉ trên server, trong `.gitignore`. Không commit.
3. **`COOKIE_SECURE=true`** ở production (lần đầu triển khai sẽ logout toàn bộ user 1 lần — bình thường).
4. Đổi mặc định: `JWT_SECRET_KEY` random 64 ký tự, password Postgres mạnh, không dùng `pos_secret`.
5. (Tùy chọn, khi rảnh) `ufw` chỉ allow dải IP Cloudflare vào 443 → chặn truy cập thẳng IP gốc, không bypass WAF.

## 8. Tổng hợp chi phí

| Hạng mục | Khởi đầu | Khi scale |
|---|---|---|
| VPS VN 1GB | ~70–90k/tháng (trả trước, Momo/CK) | → 2GB: ~110–200k/tháng (chỉ khi nâng) |
| Cloudflare (SSL/CDN/DDoS) | 0đ | 0đ |
| Domain (subdomain) | 0đ thêm (đã có) | 0đ |
| Origin cert | 0đ | 0đ |
| CI/CD (GitHub Actions + GHCR) | 0đ | 0đ |
| Backup (R2 10GB + Google Drive) | 0đ | 0đ |
| **TỔNG** | **~70–90k/tháng** | ~110–200k/tháng khi cần |

Không có chi phí ẩn. Trả trước theo chu kỳ (không tính theo giờ), trả năm thường giảm ~15–20%.

## 9. Phụ thuộc / phần phải chỉnh trong repo

1. `frontend/nginx.conf` — đổi `server_name` `app.tencuahang.vn` → `pos.timxe-namdinh.com`; thêm `location = /health { proxy_pass http://api:8000/health; }`.
2. `docker-compose.deploy.yml` — `--workers 4` → `--workers 1`; thêm `mem_limit` cho `api` & `db`;
   thêm Postgres tuning (`command: -c shared_buffers=128MB -c ...`).
3. Thêm `scripts/backup.sh` và `scripts/mem_watch.sh` (hoặc đặt trực tiếp trên VPS — quyết định lúc viết plan).
4. `.env.prod` trên server — không commit; theo `.env.prod.example`.
5. GitHub secrets: `SSH_HOST`, `SSH_USER`, `SSH_KEY`.
