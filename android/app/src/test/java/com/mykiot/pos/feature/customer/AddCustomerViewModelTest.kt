package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerResponseDto
import com.mykiot.pos.feature.customer.data.CustomerRepository
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
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test

class AddCustomerViewModelTest {
    private val repo = mockk<CustomerRepository>(relaxed = true)
    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `submit with blank name sets error and does not call create`() = runTest {
        val vm = AddCustomerViewModel(repo)
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertEquals("Vui lòng nhập tên khách hàng", vm.state.value.errorMessage)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `submit success sets created`() = runTest {
        coEvery { repo.create(any()) } returns ApiResult.Success(CustomerResponseDto(id = 9, name = "Anh Năm"))
        val vm = AddCustomerViewModel(repo)
        vm.onName("Anh Năm")
        vm.onPhone("0901234567")
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertNotNull(vm.state.value.created)
        coVerify { repo.create(CustomerCreateDto(name = "Anh Năm", phone = "0901234567")) }
    }
}
