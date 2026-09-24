package com.mediflow.mediflow_app

import android.content.Intent
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {
    // file_picker abre el selector del sistema. Excluir proveedores remotos
    // mantiene la selección del Sprint 1 limitada a archivos locales.
    @Suppress("DEPRECATION")
    override fun startActivityForResult(intent: Intent, requestCode: Int, options: Bundle?) {
        if (intent.action == Intent.ACTION_OPEN_DOCUMENT ||
            intent.action == Intent.ACTION_GET_CONTENT) {
            intent.putExtra(Intent.EXTRA_LOCAL_ONLY, true)
        }
        super.startActivityForResult(intent, requestCode, options)
    }
}
