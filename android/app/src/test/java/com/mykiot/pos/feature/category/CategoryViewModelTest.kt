package com.mykiot.pos.feature.category

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.core.network.dto.CategoryDto
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import com.mykiot.pos.feature.category.data.CategoryRepository
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
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class CategoryViewModelTest {
    private val repo = mockk<CategoryRepository>(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load populates nodes`() = runTest {
        coEvery { repo.tree() } returns ApiResult.Success(listOf(CategoryNodeDto(1, "Đồ uống", null, 1)))
        val vm = CategoryViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(1, vm.state.value.nodes.size)
    }

    @Test
    fun `saveEditor add calls create then reloads`() = runTest {
        coEvery { repo.tree() } returns ApiResult.Success(emptyList())
        coEvery { repo.create(any()) } returns ApiResult.Success(CategoryDto(5, "Bánh kẹo", null, 1))
        val vm = CategoryViewModel(repo)
        vm.openAdd(parentId = null)
        vm.onEditorName("Bánh kẹo")
        vm.saveEditor()
        testScheduler.advanceUntilIdle()
        coVerify { repo.create(CategoryCreateDto(name = "Bánh kẹo", parentId = null)) }
    }

    @Test
    fun `delete failure sets error`() = runTest {
        coEvery { repo.tree() } returns ApiResult.Success(emptyList())
        coEvery { repo.delete(3) } returns ApiResult.Failure(ApiError("HAS_PRODUCTS", "Nhóm còn sản phẩm", 400))
        val vm = CategoryViewModel(repo)
        vm.delete(3)
        testScheduler.advanceUntilIdle()
        assertEquals("Nhóm còn sản phẩm", vm.state.value.error?.message)
    }

    @Test
    fun `blank editor name does not call create`() = runTest {
        val vm = CategoryViewModel(repo)
        vm.openAdd(null)
        vm.saveEditor()
        testScheduler.advanceUntilIdle()
        coVerify(exactly = 0) { repo.create(any()) }
        assertTrue(vm.state.value.editorOpen)
    }
}
