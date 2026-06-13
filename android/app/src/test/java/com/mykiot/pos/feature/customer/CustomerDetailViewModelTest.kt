package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.core.network.dto.CustomerResponseDto
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

class CustomerDetailViewModelTest {
    private val repo = mockk<CustomerRepository>()
    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load fetches customer by id`() = runTest {
        coEvery { repo.get(7) } returns ApiResult.Success(
            CustomerDetailDto(customer = CustomerResponseDto(id = 7, name = "Chị Tư", phone = "0911111111")),
        )
        val vm = CustomerDetailViewModel(repo)
        vm.load(7)
        testScheduler.advanceUntilIdle()
        assertEquals("Chị Tư", vm.state.value.customer?.customer?.name)
    }
}
