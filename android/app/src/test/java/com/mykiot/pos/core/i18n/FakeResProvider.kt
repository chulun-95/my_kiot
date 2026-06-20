package com.mykiot.pos.core.i18n

/**
 * ResProvider giả cho unit test (không cần Context/Robolectric).
 * Trả token ổn định "res:<id>[:args]" để test so khớp đúng resource id mà ViewModel dùng:
 *
 *   val res = FakeResProvider()
 *   val vm = SomeViewModel(repo, res)
 *   ...
 *   assertEquals(res.get(R.string.cart_empty), vm.state.value.errorMessage)
 */
class FakeResProvider : ResProvider {
    override fun get(id: Int, vararg args: Any): String =
        if (args.isEmpty()) "res:$id" else "res:$id:" + args.joinToString(",")
}
