package com.mykiot.pos.core.hardware

import com.mykiot.pos.core.hardware.printer.EscPosReceiptPrinter
import com.mykiot.pos.core.hardware.printer.ReceiptPrinter
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class HardwareModule {
    @Binds @Singleton
    abstract fun receiptPrinter(impl: EscPosReceiptPrinter): ReceiptPrinter
}
