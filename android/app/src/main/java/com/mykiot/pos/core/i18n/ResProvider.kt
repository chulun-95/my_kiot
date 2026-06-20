package com.mykiot.pos.core.i18n

import android.content.Context
import androidx.annotation.StringRes
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Inject

/**
 * Lấy chuỗi tài nguyên ở tầng KHÔNG phải Composable (ViewModel, repository...).
 * Composable thì dùng thẳng [androidx.compose.ui.res.stringResource].
 *
 * Tách interface để ViewModel test được mà không cần Context thật:
 * trong test truyền [FakeResProvider] (xem androidTest/test).
 */
interface ResProvider {
    fun get(@StringRes id: Int, vararg args: Any): String
}

class AndroidResProvider @Inject constructor(
    @ApplicationContext private val context: Context,
) : ResProvider {
    override fun get(id: Int, vararg args: Any): String =
        if (args.isEmpty()) context.getString(id) else context.getString(id, *args)
}

@Module
@InstallIn(SingletonComponent::class)
abstract class ResModule {
    @Binds
    abstract fun bindResProvider(impl: AndroidResProvider): ResProvider
}
