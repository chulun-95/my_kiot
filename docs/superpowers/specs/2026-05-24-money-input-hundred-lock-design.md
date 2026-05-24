# Spec: Khóa "00" cuối cho ô nhập tiền (min 100 VNĐ)

**Ngày:** 2026-05-24
**Phạm vi:** Frontend only — sửa duy nhất `frontend/src/components/MoneyInput.tsx`

## Bối cảnh

Đơn vị tiền tệ tối thiểu trong hệ thống POS này là **100 VNĐ** (trăm đồng). Người dùng (chủ shop và thu ngân) không bao giờ cần nhập số tiền lẻ hơn 100. Cho phép gõ rời từng đơn vị 1 đồng vừa thừa thao tác vừa dễ sai sót.

Giải pháp: trong mọi ô nhập tiền của FE, hai chữ số cuối "00" được khóa cứng — user chỉ gõ phần "hàng trăm" trở lên, "00" cuối không bao giờ xóa được. Hệ quả: giá trị emit ra luôn là bội số 100.

## Mục tiêu

1. Mọi ô nhập tiền trong FE chỉ nhận bội số 100.
2. Hành vi gõ "tự nhiên": user gõ `5` → display `500`; gõ thêm `0` → `5.000`; backspace → `500`; backspace → empty.
3. Áp dụng đồng nhất cho tất cả 6 call site hiện tại của `MoneyInput`.
4. Không động database, không động backend, không cần migration.

## Không trong scope

- Backend Pydantic validation cho ràng buộc "bội 100". Lý do: YAGNI — frontend là rào duy nhất ở MVP, ngoài ra giá vốn bình quân (`average cost`) tính tự động ở backend có thể tạo non-multiple, không nên buộc bội 100 ở DB.
- Migration data legacy. Existing rows có thể không bội 100 (ví dụ `products.cost_price = 12.345` do bình quân nhập kho); MoneyInput hiển thị nguyên giá trị nhưng sẽ normalize về bội 100 ngay khi user gõ phím đầu tiên.
- Thay đổi cấu hình `tenants.settings` để cho phép tenant tùy chỉnh đơn vị tối thiểu. Hardcode 100 cho tất cả tenant.
- Đổi label tiền tệ ("VNĐ" → "₫" hay khác).

## Component contract

### Props

```ts
type Props = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'type' | 'inputMode'
> & {
  value: number | string | null | undefined;
  onChange: (value: number) => void;
  /** Ẩn nhãn "VNĐ" phía bên phải input khi parent đã đặt ký hiệu riêng. */
  hideCurrency?: boolean;
};
```

**Thay đổi so với hiện tại:** bỏ prop `showZeroAsEmpty`. Hành vi mới luôn là "value=0 ⇒ input trống". Call site duy nhất đang dùng prop này là [PaymentDialog.tsx:228](../../frontend/src/pages/pos/PaymentDialog.tsx#L228) — cần xóa prop khi áp dụng.

### Bất biến

- `value` truyền vào và emit qua `onChange` luôn là số nguyên không âm.
- Sau bất kỳ tương tác bàn phím nào của user, `value` emit ra **luôn là bội số 100**.
- Nếu parent truyền vào legacy value không bội 100, component hiển thị nguyên giá trị nhưng tương tác kế tiếp sẽ chuyển về bội 100.

## Behavior

### Display

| Điều kiện | Hiển thị |
|---|---|
| `value` là `null`, `undefined`, `''`, hoặc `0` | `""` (input rỗng), placeholder `"0 ₫"` |
| `value > 0` và finite | `Intl.NumberFormat('vi-VN').format(Math.round(value))` (vd. `5000` → `"5.000"`) |
| `value > 0` nhưng không bội 100 (legacy) | Format nguyên giá trị, không tự sửa |
| `value < 0` hoặc NaN | `""` (treat as empty) |

### Key handlers

Bắt sự kiện `onKeyDown`. Tất cả nhánh xử lý `preventDefault` để input không tự sửa text:

| Phím | Điều kiện | Hành động |
|---|---|---|
| `0`–`9` | Không kèm Ctrl/Alt/Meta | `onChange((value \|\| 0) * 10 + digit * 100)` |
| `Backspace` hoặc `Delete` | Không kèm Ctrl/Alt/Meta | Nếu `value > 0`: `onChange(Math.floor(value / 1000) * 100)`. Nếu `value = 0` hoặc empty: no-op (preventDefault để tránh blur) |
| `Ctrl/Cmd + V` | — | Không preventDefault, để `onPaste` xử lý |
| `Ctrl/Cmd + A`, `Ctrl/Cmd + C`, `Ctrl/Cmd + X`, mũi tên, Tab, Enter, Esc | — | Passthrough (không preventDefault) |
| Khác (chữ cái, ký tự đặc biệt) | — | preventDefault (chặn nhập rác) |

#### Ví dụ tuần tự

| Action | value trước | value sau | Display sau |
|---|---|---|---|
| Initial | — | 0 | `""` |
| Type `5` | 0 | 500 | `"500"` |
| Type `0` | 500 | 5000 | `"5.000"` |
| Type `0` | 5000 | 50000 | `"50.000"` |
| Type `5` | 50000 | 500500 | `"500.500"` |
| Backspace | 500500 | 50050 → no, `floor(500500/1000)*100 = 50000` | `"50.000"` |
| Backspace | 50000 | 5000 | `"5.000"` |
| Backspace | 5000 | 500 | `"500"` |
| Backspace | 500 | 0 | `""` |
| Backspace | 0 | 0 (no-op) | `""` |

### Paste

`onPaste`:
1. `preventDefault`.
2. Lấy `e.clipboardData.getData('text')`.
3. Lọc digits: `text.replace(/\D/g, '')` → `N`.
4. Nếu `N === ''`: no-op (không reset giá trị hiện tại; user paste rác chỉ là thao tác trượt tay).
5. Ngược lại: `onChange(Math.floor(Number(N) / 100) * 100)`.

Ví dụ:
- Paste `"12345"` → `12300`
- Paste `"12.300"` → `12300`
- Paste `"abc12300xyz"` → `12300`
- Paste `"-500"` → `500`
- Paste `"abc"` → no-op (giữ giá trị cũ)

### onChange fallback (IME / mobile)

Trong trường hợp input event vẫn lọt qua (mobile IME, autofill, browser extension), giữ logic phòng vệ:
1. Lấy `e.target.value.replace(/\D/g, '')` → `N`.
2. Nếu `N === ''`: `onChange(0)`.
3. Ngược lại: `onChange(Math.floor(Number(N) / 100) * 100)`.

Đảm bảo bất biến "bội 100" không bao giờ bị phá.

### Cursor

- `onFocus`: dùng `setSelectionRange(input.value.length, input.value.length)` đặt cursor cuối input.
- `useLayoutEffect` chạy mỗi khi `display` thay đổi: nếu input đang focus (`document.activeElement === input`), đặt cursor về cuối. Tránh nhảy cursor sau mỗi keystroke.

User không cần — và không thể có nghĩa — đặt cursor giữa các chữ số: model là "luôn append/pop ở hàng đơn vị hundreds".

## Edge cases

- **Disabled / readonly:** tôn trọng `disabled` từ `...rest`. Trong key handler, kiểm tra `disabled` trước khi `onChange` để tránh emit khi prop bị set ngoài.
- **value rất lớn (overflow):** `Number.MAX_SAFE_INTEGER` ~ `9.007 × 10^15`. Giá trị tiền tệ hợp lý cho tạp hóa tối đa cỡ tỷ đồng (10^9) — không có rủi ro overflow thực tế. Không cần guard.
- **Multiple instances trên 1 page:** mỗi instance giữ riêng ref input, không chia sẻ state. An toàn.
- **SSR:** dự án dùng Vite SPA, không SSR. Không cần guard `typeof window`.

## Migration

### Frontend call sites cần check (không sửa, chỉ verify hành vi vẫn đúng)

- [frontend/src/pages/products/ProductForm.tsx:207, 220](../../frontend/src/pages/products/ProductForm.tsx) — `cost_price`, `sale_price`
- [frontend/src/pages/goodsReceipts/GoodsReceiptForm.tsx:190, 240](../../frontend/src/pages/goodsReceipts/GoodsReceiptForm.tsx) — item cost + paid total
- [frontend/src/pages/pos/POSScreen.tsx:231](../../frontend/src/pages/pos/POSScreen.tsx) — giảm giá toàn hóa đơn
- [frontend/src/pages/pos/CartLine.tsx:38](../../frontend/src/pages/pos/CartLine.tsx) — override giá dòng
- [frontend/src/pages/pos/PaymentDialog.tsx:219](../../frontend/src/pages/pos/PaymentDialog.tsx) — số tiền từng phương thức (tiền KH đưa). **Xóa prop `showZeroAsEmpty` ở đây.**

### Backend / DB

Không thay đổi.

## Testing

### Component tests (tạo mới `frontend/src/components/MoneyInput.test.tsx`)

Dùng `@testing-library/react` + `vitest` (project đã có).

1. Render với `value={0}` → input value rỗng, placeholder hiển thị
2. Render với `value={5000}` → input value `"5.000"`
3. Render với `value={12345}` (legacy) → input value `"12.345"`, không tự sửa
4. Fire keydown `"5"` từ empty → `onChange` được gọi với `500`
5. Fire keydown `"5"`, `"0"`, `"0"` tuần tự → `onChange` lần lượt với 500, 5000, 50000
6. `value={500}`, fire Backspace → `onChange` với `0`
7. `value={0}`, fire Backspace → `onChange` KHÔNG được gọi
8. `value={12345}`, fire Backspace → `onChange` với `12300` (`floor(12345/1000)*100`)
9. Fire paste với clipboardData `"12345"` → `onChange` với `12300`
10. Fire paste với `"abc"` (không digit) → `onChange` KHÔNG được gọi (giữ value cũ)
11. Focus input → cursor ở vị trí cuối
12. `disabled={true}`, fire keydown `"5"` → `onChange` KHÔNG được gọi
13. Fire keydown chữ cái (vd. `"a"`) → `onChange` KHÔNG được gọi (rác bị chặn)

### Integration smoke tests

- [frontend/src/pages/pos/__tests__/PaymentDialog.test.tsx](../../frontend/src/pages/pos/__tests__/PaymentDialog.test.tsx): xác nhận test hiện có vẫn pass sau khi prop `showZeroAsEmpty` bị bỏ. Nếu test đang assert giá trị "tiền KH đưa" cụ thể, có thể cần cập nhật cho phù hợp.

### Manual QA checklist

- [ ] POS: gõ tiền KH đưa → "00" luôn ở cuối, không xóa được
- [ ] POS: tổng cộng hóa đơn không thay đổi do nhập tiền KH
- [ ] Sản phẩm: tạo SP mới, nhập giá vốn / giá bán → bội 100
- [ ] Phiếu nhập: nhập giá nhập cho từng item → bội 100
- [ ] Phiếu nhập: tổng tiền đã trả → bội 100
- [ ] POS CartLine: override giá dòng → bội 100
- [ ] PaymentDialog: nhập đa phương thức → mỗi ô bội 100
- [ ] Sản phẩm có cost legacy (do bình quân nhập) hiển thị đúng giá; khi sửa thì giá mới bội 100

## Open questions

Không.

## Tham chiếu

- Component hiện tại: [frontend/src/components/MoneyInput.tsx](../../frontend/src/components/MoneyInput.tsx)
- CLAUDE.md §"Đặc thù tạp hóa / siêu thị mini": bối cảnh tiền tệ và sale_price flexibility
