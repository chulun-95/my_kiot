# i18n / Centralize-strings Conventions (VN-only, no library)

Mục tiêu: bỏ mọi text hard-code trong UI, gom về file tài nguyên. **Chỉ tiếng Việt**, KHÔNG thêm
thư viện đa ngôn ngữ. Mỗi agent chỉ sửa file thuộc module của mình + tạo file tài nguyên riêng của
module → không đụng nhau.

## Quy tắc chung (BẮT BUỘC)
- KHÔNG sửa file tài nguyên chung: Android `res/values/strings.xml`; Web `src/i18n/common.ts`.
  Nếu thiếu chuỗi dùng chung → thêm vào **file module của bạn** (chấp nhận trùng lặp nhỏ).
- KHÔNG chạy `gradlew`/`npm build` (nhiều agent chạy song song sẽ kẹt lock). Chỉ sửa code + tự rà
  kỹ. Người điều phối build 1 lần ở cuối.
- Chỉ sửa file trong phạm vi module được giao (xem prompt). Không refactor logic, chỉ thay text.
- Giữ y nguyên nội dung tiếng Việt hiện tại (kể cả dấu câu) khi chuyển vào key.
- Bỏ qua: log/comment, mã code (UPPER_SNAKE error codes), test fixture strings không hiển thị cho user.

---

## ANDROID

### 1) Chuỗi trong @Composable → strings.xml + stringResource
File tài nguyên của module: `app/src/main/res/values/strings_<module>.xml` (vd `strings_pos.xml`).
```xml
<resources>
    <string name="pos_title">Bán hàng</string>
    <string name="pos_cart_empty">Giỏ hàng trống</string>
    <string name="pos_held_order">Đã treo đơn %1$s</string>   <!-- tham số: %1$s, %1$d -->
</resources>
```
Trong Composable:
```kotlin
import androidx.compose.ui.res.stringResource
import com.mykiot.pos.R
// ...
Text(stringResource(R.string.pos_title))
Text(stringResource(R.string.pos_held_order, code))   // có tham số
```
`contentDescription`, `label = { Text(...) }`, `placeholder` đều phải dùng stringResource.

### 2) Chuỗi trong ViewModel / non-Composable → ResProvider
Inject `ResProvider` (đã có sẵn ở `core/i18n/ResProvider.kt`) làm tham số cuối constructor:
```kotlin
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.R

@HiltViewModel
class PosViewModel @Inject constructor(
    private val repository: PosRepository,
    private val printer: ReceiptPrinter,
    private val res: ResProvider,           // <-- thêm
) : ViewModel() {
    // ...
    _state.update { it.copy(errorMessage = res.get(R.string.pos_cart_empty)) }
    _state.update { it.copy(infoMessage = res.get(R.string.pos_held_order, r.data.code)) }
}
```
LƯU Ý: chuỗi lỗi đến từ API (`r.error.message`) đã là tiếng Việt từ server → GIỮ NGUYÊN, không đụng.

### 3) Cập nhật unit test của ViewModel
Test trước đây so khớp chuỗi VN cứng → đổi sang `FakeResProvider` (đã có ở
`test/.../core/i18n/FakeResProvider.kt`) và so khớp qua resource id:
```kotlin
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.R

private val res = FakeResProvider()
val vm = PosViewModel(repo, printer, res)
// ...
assertEquals(res.get(R.string.pos_cart_empty), vm.state.value.errorMessage)
```
Mọi test đang construct ViewModel phải truyền thêm `res`.

---

## WEB (React + TS)

### File tài nguyên của module: `src/i18n/<module>.ts`
```ts
export const posT = {
  title: 'Bán hàng',
  cartEmpty: 'Giỏ trống. Quét mã hoặc tìm sản phẩm để bắt đầu.',
  // tham số → dùng hàm:
  shortage: (name: string, need: number, have: number) =>
    `${name}: cần ${need}, còn ${have}`,
} as const;
```
Trong component:
```tsx
import { posT } from '../../i18n/pos';
import { common } from '../../i18n/common';   // chuỗi dùng chung (chỉ đọc)
// ...
<h1>{posT.title}</h1>
<button>{common.save}</button>
<div>{posT.shortage(s.product_name, s.need, s.have)}</div>
```
Áp dụng cho: text hiển thị, `placeholder`, `aria-label`, `title`, thông báo `toast`/`alert`,
message validate (Zod/yup/react-hook-form), `setCustomValidity(...)`.
KHÔNG đụng: `error.code`, route path, key kỹ thuật, className.

### Test web
Nếu test assert text VN cứng mà bạn đổi sang biến → cập nhật test import cùng `*.T` và so khớp,
hoặc dùng `screen.getByText(posT.title)`.

---

## Bàn giao
Mỗi agent trả về: danh sách file đã sửa + file tài nguyên đã tạo + các điểm còn nghi ngờ
(chuỗi không chắc có phải hiển thị cho user). KHÔNG báo "done" nếu chưa rà hết file trong phạm vi.
