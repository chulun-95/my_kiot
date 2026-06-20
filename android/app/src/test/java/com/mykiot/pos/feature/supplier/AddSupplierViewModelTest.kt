package com.mykiot.pos.feature.supplier

import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.SupplierCreateDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.network.dto.SupplierResponseDto
import com.mykiot.pos.feature.supplier.data.SupplierRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class AddSupplierViewModelTest {
    private val repo = mockk<SupplierRepository>(relaxed = true)
    private val res = FakeResProvider()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `blank name sets error, no api call`() = runTest {
        val vm = AddSupplierViewModel(repo, res)
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(com.mykiot.pos.R.string.cat_supplier_err_name_required), vm.state.value.error?.message)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `create path calls repo create`() = runTest {
        coEvery { repo.create(any()) } returns ApiResult.Success(SupplierDto(1, "NCC A", null, 0.0))
        val vm = AddSupplierViewModel(repo, res)
        vm.onName("NCC A")
        vm.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.create(SupplierCreateDto(name = "NCC A", phone = null, address = null)) }
    }

    @Test
    fun `startEdit loads then submit calls update`() = runTest {
        coEvery { repo.getById(9) } returns ApiResult.Success(
            SupplierResponseDto(9, "NCC Cũ", "0901", null, "Đ/c", null, null, 0.0),
        )
        coEvery { repo.update(eq(9), any()) } returns ApiResult.Success(
            SupplierResponseDto(9, "NCC Mới", "0901", null, "Đ/c", null, null, 0.0),
        )
        val vm = AddSupplierViewModel(repo, res)
        vm.startEdit(9)
        testScheduler.advanceUntilIdle()
        assertEquals("NCC Cũ", vm.state.value.name)
        vm.onName("NCC Mới")
        vm.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.update(eq(9), any()) }
    }
}
