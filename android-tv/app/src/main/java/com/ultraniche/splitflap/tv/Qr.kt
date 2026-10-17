package com.ultraniche.splitflap.tv

import android.graphics.Bitmap
import android.graphics.Color
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter

/** Draws a QR code for [text], cream on charcoal like the board, [size] pixels square. */
fun qrBitmap(text: String, size: Int): Bitmap {
    val matrix = QRCodeWriter().encode(
        text,
        BarcodeFormat.QR_CODE,
        size,
        size,
        mapOf(EncodeHintType.MARGIN to 1),
    )
    val ink = Color.rgb(0xEE, 0xEA, 0xE1)
    val ground = Color.rgb(0x1C, 0x1B, 0x1A)
    val pixels = IntArray(size * size) { i -> if (matrix[i % size, i / size]) ground else ink }
    return Bitmap.createBitmap(pixels, size, size, Bitmap.Config.ARGB_8888)
}
