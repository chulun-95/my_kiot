package com.mykiot.pos.core.hardware.scanner

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.Executors

/**
 * Camera quét LIÊN TỤC, nhúng được (dùng cho chế độ quét nhiều SP trong 1 đơn).
 * Gọi [onScanned] mỗi lần thấy mã, có debounce: bỏ qua cùng 1 mã trong [debounceMs].
 * Caller tự đặt kích thước qua [modifier] (vd: 1/3 chiều cao màn POS).
 */
@Composable
fun EmbeddedScanner(
    onScanned: (String) -> Unit,
    modifier: Modifier = Modifier,
    debounceMs: Long = 1500L,
) {
    val lifecycleOwner = LocalLifecycleOwner.current
    val analysisExecutor = remember { Executors.newSingleThreadExecutor() }
    val scanner = remember { BarcodeScanning.getClient() }
    val lastCode = remember { arrayOf<String?>(null) }
    val lastTime = remember { longArrayOf(0L) }

    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { /* không có quyền thì màn hình chỉ là khung trống */ }

    LaunchedEffect(Unit) { permission.launch(android.Manifest.permission.CAMERA) }

    DisposableEffect(Unit) { onDispose { analysisExecutor.shutdown(); scanner.close() } }

    AndroidView(
        factory = { ctx ->
            val previewView = PreviewView(ctx)
            val providerFuture = ProcessCameraProvider.getInstance(ctx)
            providerFuture.addListener({
                val provider = providerFuture.get()
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }
                val analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                analysis.setAnalyzer(analysisExecutor) { proxy ->
                    @Suppress("UnsafeOptInUsageError")
                    val media = proxy.image
                    if (media != null) {
                        val img = InputImage.fromMediaImage(media, proxy.imageInfo.rotationDegrees)
                        scanner.process(img)
                            .addOnSuccessListener { codes ->
                                val raw = codes.firstOrNull()?.rawValue
                                if (raw != null) {
                                    val now = System.currentTimeMillis()
                                    val isDuplicate = raw == lastCode[0] && now - lastTime[0] < debounceMs
                                    if (!isDuplicate) {
                                        lastCode[0] = raw
                                        lastTime[0] = now
                                        onScanned(raw)
                                    }
                                }
                            }
                            .addOnCompleteListener { proxy.close() }
                    } else {
                        proxy.close()
                    }
                }
                provider.unbindAll()
                provider.bindToLifecycle(
                    lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis,
                )
            }, ContextCompat.getMainExecutor(ctx))
            previewView
        },
        modifier = modifier,
    )
}

/**
 * Overlay camera dùng ML Kit nhận diện barcode. Gọi onScanned đúng 1 lần khi
 * thấy mã đầu tiên rồi để caller đóng overlay.
 */
@Composable
fun MlKitScannerScreen(onScanned: (String) -> Unit, onClose: () -> Unit) {
    val lifecycleOwner = LocalLifecycleOwner.current
    val analysisExecutor = remember { Executors.newSingleThreadExecutor() }
    val scanner = remember { BarcodeScanning.getClient() }
    val handled = remember { booleanArrayOf(false) }

    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> if (!granted) onClose() }

    LaunchedEffect(Unit) { permission.launch(android.Manifest.permission.CAMERA) }

    DisposableEffect(Unit) { onDispose { analysisExecutor.shutdown(); scanner.close() } }

    Box(Modifier.fillMaxSize()) {
        AndroidView(
            factory = { ctx ->
                val previewView = PreviewView(ctx)
                val providerFuture = ProcessCameraProvider.getInstance(ctx)
                providerFuture.addListener({
                    val provider = providerFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }
                    val analysis = ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build()
                    analysis.setAnalyzer(analysisExecutor) { proxy ->
                        @Suppress("UnsafeOptInUsageError")
                        val media = proxy.image
                        if (media != null) {
                            val img = InputImage.fromMediaImage(media, proxy.imageInfo.rotationDegrees)
                            scanner.process(img)
                                .addOnSuccessListener { codes ->
                                    val raw = codes.firstOrNull()?.rawValue
                                    if (raw != null && !handled[0]) {
                                        handled[0] = true
                                        // KHÔNG beep ở đây: chỉ mới *thấy* mã, chưa biết SP có tồn tại không.
                                        // ViewModel sẽ pip khi thêm thành công / pipip khi không tìm thấy.
                                        onScanned(raw)
                                    }
                                }
                                .addOnCompleteListener { proxy.close() }
                        } else {
                            proxy.close()
                        }
                    }
                    provider.unbindAll()
                    provider.bindToLifecycle(
                        lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis,
                    )
                }, ContextCompat.getMainExecutor(ctx))
                previewView
            },
            modifier = Modifier.fillMaxSize(),
        )
    }
}
