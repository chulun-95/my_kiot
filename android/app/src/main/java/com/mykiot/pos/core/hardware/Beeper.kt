package com.mykiot.pos.core.hardware

import android.media.AudioManager
import android.media.ToneGenerator

/**
 * Phát âm báo ngắn bằng ToneGenerator (không cần file asset).
 * - [pip]   : 1 tiếng "pip" — báo quét mã thành công.
 * - [error] : "tit tit" — báo không tìm thấy SP / hết hàng ở POS.
 *
 * Mọi lời gọi đều bọc try/catch để an toàn khi chạy unit test (không có audio).
 */
object Beeper {
    private val tone: ToneGenerator? by lazy {
        runCatching { ToneGenerator(AudioManager.STREAM_MUSIC, 90) }.getOrNull()
    }

    fun pip() {
        runCatching { tone?.startTone(ToneGenerator.TONE_PROP_BEEP, 120) }
    }

    fun error() {
        // TONE_PROP_BEEP2 là tiếng "bíp-bíp" kép → hợp với cảnh báo "tit tit".
        runCatching { tone?.startTone(ToneGenerator.TONE_PROP_BEEP2, 250) }
    }
}
