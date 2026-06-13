package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.feature.customer.data.CustomerRepository
import io.mockk.coEvery
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

class CustomerListViewModelTest {
    private val repo = mockk<CustomerRepository>()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load populates items on success`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Success(
            listOf(CustomerDto(id = 1, name = "Anh Ba", phone = "0900000000")),
        )
        val vm = CustomerListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(1, vm.state.value.items.size)
        assertEquals("Anh Ba", vm.state.value.items.first().name)
    }

    @Test
    fun `load sets errorMessage on failure`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Failure(ApiError("X", "Lỗi tải"))
        val vm = CustomerListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals("Lỗi tải", vm.state.value.errorMessage)
    }
}
