---
name: push-code
description: Use when user says "push code", "push changes", or wants to commit and push current changes to remote. Auto-generates commit message, stages files, commits, and pushes without asking for confirmation.
---

# Push Code

Tự động stage, commit và push code đã thay đổi.

## Các bước thực hiện

### Bước 1 — Thu thập thông tin (chạy song song)

```bash
git status
git diff
git diff --cached
git log --oneline -5
```

### Bước 2 — Stage files

Stage tất cả file đã thay đổi (trừ file nhạy cảm):

```bash
git add <file1> <file2> ...
```

**Không bao giờ stage:** `.env`, `*.env.*`, file credentials, secrets.

Dùng tên file cụ thể, tránh `git add .` để không vô tình include file nhạy cảm.

### Bước 3 — Tự động sinh commit message

Phân tích diff để sinh message theo format:

```
<type>: <mô tả ngắn gọn bằng tiếng Anh, max 72 ký tự>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Ví dụ: `feat: add product unit conversion API`

### Bước 4 — Commit

```bash
git commit -m "$(cat <<'EOF'
<type>: <summary>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Nếu pre-commit hook fail → fix lỗi → stage lại → tạo commit MỚI (không dùng `--amend`, không dùng `--no-verify`).

### Bước 5 — Push

```bash
git push
# Nếu chưa có upstream:
git push -u origin <branch>
```

## Xử lý tình huống

| Tình huống | Xử lý |
|-----------|-------|
| Không có gì thay đổi | Báo "nothing to commit" và dừng |
| Phát hiện file nhạy cảm | Cảnh báo user, bỏ qua file đó, tiếp tục |
| Hook fail | Fix → re-stage → commit mới |
| Chưa có upstream | `git push -u origin <branch>` |
